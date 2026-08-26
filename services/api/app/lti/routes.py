"""The auth spine. Two endpoints implement the LTI 1.3 launch:

  POST/GET /lti/login   third-party OIDC initiation -> redirect to the platform
  POST     /lti/launch  receive the signed id_token -> validate -> resolve the
                        tenant -> upsert the user -> mint the session token ->
                        redirect into the SPA

  GET      /lti/jwks    the tool's public keyset (for AGS/NRPS service calls)

Identity comes from the LMS. The tenant is (iss, deployment_id). The minted
token carries sub, institution_id, and app_role, which the database RLS reads.
"""
from __future__ import annotations

import logging
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import get_settings
from app.db import supabase as db
from app.deps import get_lms_connector
from app.ai.skill_proposer import seed_course_skills
from app.lti import claims as C
from app.lti.security import build_tool_jwks, sign_state, verify_id_token, verify_state
from app.lms.blackboard import BlackboardConnector
from app.security.jwt import mint_session_token

router = APIRouter(prefix="/lti", tags=["lti"])

logger = logging.getLogger(__name__)

_STATE_COOKIE = "kala_lti_state"


def _roster_role(course_role: str | None) -> str:
    """Blackboard courseRoleId -> Kala app_role. Only an explicit Student
    membership is a student; everything else (Instructor, Teaching
    Assistant, Grader, ...) is enrolled as instructor (upsert_enrollment
    coerces admin/instructor the same way)."""
    return "student" if (course_role or "").strip().lower() == "student" else "instructor"


def _seed_course_skills(*, institution_id: str, course_id: str, course_ref: str,
                        connector: BlackboardConnector) -> dict:
    """Seed the skill graph from AI proposals on first launch (see
    docs/SKILL_PIPELINE.md). Same non-blocking contract as roster sync: any
    failure logs and is skipped, never blocks the 302. Guarded so we only
    propose when the course has no skills yet (avoids a pointless content
    fetch on every instructor launch)."""
    try:
        existing = db.select("skills", {
            "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
            "select": "id", "limit": "1",
        })
        if existing:
            return {"skipped": True, "reason": "course already has skills"}
        items = connector.get_content(course_ref)
        content = "\n".join(i.get("body_or_description") or "" for i in items).strip()
        if not content:
            return {"skipped": True, "reason": "course has no content"}
        return seed_course_skills(
            institution_id=institution_id, course_id=course_id, course_content=content,
        )
    except Exception:
        logger.exception("skill proposal failed for %s; skipping", course_ref)
        return {"skipped": True, "reason": "error"}


def _sync_roster(*, institution_id: str, course_id: str, course_ref: str,
                 connector: BlackboardConnector) -> int:
    """NRPS-style roster pull (masterplan 3.1). Enrolls every member the LMS
    returns, so the cohort exists before each student has individually
    launched Kala once. Best-effort by design: a roster failure (LMS hiccup,
    one malformed member) must never break the launching instructor's own
    session — members are upserted one at a time and failures are logged and
    skipped."""
    try:
        members = connector.get_roster(course_ref)
    except Exception:
        logger.exception("roster pull failed for %s; skipping roster sync", course_ref)
        return 0

    enrolled = 0
    for member in members:
        lms_user_id = member.get("lms_user_id")
        if not lms_user_id:
            continue
        try:
            user = db.upsert_user(
                institution_id=institution_id,
                lms_user_id=lms_user_id,
                role=_roster_role(member.get("role")),
                display_name=member.get("name"),
                email=member.get("email"),
            )
            db.upsert_enrollment(
                institution_id=institution_id, user_id=user["id"],
                course_id=course_id, role=_roster_role(member.get("role")),
            )
            enrolled += 1
        except Exception:
            logger.exception("roster member %s skipped", lms_user_id)
    return enrolled


async def _login(request: Request) -> RedirectResponse:
    s = get_settings()
    params = dict(request.query_params)
    if request.method == "POST":
        params.update(dict(await request.form()))

    login_hint = params.get("login_hint", "")
    lti_message_hint = params.get("lti_message_hint", "")
    target_link_uri = params.get("target_link_uri", f"{_base_url(request)}/lti/launch")

    state = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(24)

    auth_params = {
        "scope": "openid",
        "response_type": "id_token",
        "response_mode": "form_post",
        "prompt": "none",
        "client_id": s.lti_client_id,
        "redirect_uri": target_link_uri,
        "login_hint": login_hint,
        "lti_message_hint": lti_message_hint,
        "state": state,
        "nonce": nonce,
    }
    redirect = RedirectResponse(f"{s.lti_auth_login_url}?{urlencode(auth_params)}", status_code=302)
    redirect.set_cookie(
        _STATE_COOKIE,
        sign_state({"state": state, "nonce": nonce}),
        max_age=600, httponly=True, secure=True, samesite="none",
    )
    return redirect


@router.get("/login")
async def login_get(request: Request):
    return await _login(request)


@router.post("/login")
async def login_post(request: Request):
    return await _login(request)


@router.post("/launch")
async def launch(request: Request, id_token: str = Form(...), state: str = Form(...),
                 connector: BlackboardConnector = Depends(get_lms_connector)):
    s = get_settings()

    # 1. verify state (CSRF) against the signed cookie, then the id_token itself
    cookie = request.cookies.get(_STATE_COOKIE, "")
    try:
        state_data = verify_state(cookie)
    except Exception:
        return JSONResponse({"error": "invalid state"}, status_code=400)
    if not secrets.compare_digest(state_data.get("state", ""), state):
        return JSONResponse({"error": "state mismatch"}, status_code=400)

    try:
        payload = verify_id_token(id_token)
    except Exception as exc:
        return JSONResponse({"error": f"invalid id_token: {exc}"}, status_code=401)

    # 2. LTI message checks
    if payload.get("nonce") != state_data.get("nonce"):
        return JSONResponse({"error": "nonce mismatch"}, status_code=400)
    if payload.get(C.MESSAGE_TYPE) != C.EXPECTED_MESSAGE_TYPE:
        return JSONResponse({"error": "unexpected message type"}, status_code=400)
    deployment_id = payload.get(C.DEPLOYMENT_ID, "")
    if s.deployment_id_list and deployment_id not in s.deployment_id_list:
        return JSONResponse({"error": "unknown deployment"}, status_code=403)

    # 3. resolve tenant, upsert user + course + enrollment
    lms_type = "blackboard"  # iss https://blackboard.com; branch here for canvas
    institution = db.get_or_create_institution(
        iss=payload["iss"], deployment_id=deployment_id,
        name="Institution", lms_type=lms_type,
    )
    app_role = C.map_role(payload.get(C.ROLES, []))
    user = db.upsert_user(
        institution_id=institution["id"],
        lms_user_id=payload["sub"],
        role=app_role,
        display_name=payload.get("name"),
        email=payload.get("email"),
    )
    ctx = C.extract_context(payload)
    course = None
    if ctx["lms_course_external_id"]:
        try:
            lms_course_id = connector.resolve_course_ref(ctx["lms_course_external_id"])
        except Exception as exc:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"could not resolve Blackboard course: {exc}",
            ) from exc
        course = db.get_or_create_course(
            institution_id=institution["id"],
            lms_course_id=lms_course_id,
            title=ctx["title"],
        )
        db.upsert_enrollment(
            institution_id=institution["id"], user_id=user["id"],
            course_id=course["id"], role=app_role,
        )

        # NRPS roster pull (masterplan 3.1): the full class list already
        # exists in Blackboard — enroll every member, not just this launcher,
        # so an instructor sees their cohort before any student has opened
        # Kala. Students launching do not trigger this (avoid hammering the
        # LMS on every student launch); best-effort, never blocks the launch.
        if app_role in ("instructor", "admin"):
            _sync_roster(
                institution_id=institution["id"], course_id=course["id"],
                course_ref=lms_course_id, connector=connector,
            )
            # AI skill proposal (docs/SKILL_PIPELINE.md): seed the skill
            # graph from the course's own content on first launch. Same
            # best-effort contract — a proposal failure never blocks the
            # 302. By the time students launch, proposals/matches are staged.
            _seed_course_skills(
                institution_id=institution["id"], course_id=course["id"],
                course_ref=lms_course_id, connector=connector,
            )

    # 4. mint the session token and hand off to the SPA (fragment is not logged)
    token = mint_session_token(
        user_id=user["id"],
        institution_id=institution["id"],
        app_role=app_role,
        course_id=course["id"] if course else None,
        display_name=payload.get("name"),
    )
    frag = urlencode({"token": token, "course": course["id"] if course else ""})
    resp = RedirectResponse(f"{s.frontend_url}/launch#{frag}", status_code=302)
    resp.delete_cookie(_STATE_COOKIE)
    return resp


@router.get("/jwks")
def jwks():
    return build_tool_jwks()


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")
