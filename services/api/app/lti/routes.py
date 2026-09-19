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
from app.lms.blackboard import BlackboardConnector, BlackboardRateLimitedError
from app.security.jwt import mint_session_token

router = APIRouter(prefix="/lti", tags=["lti"])

logger = logging.getLogger(__name__)

_STATE_COOKIE = "kala_lti_state"

# How long a successful roster sync / skill seed suppresses the next attempt.
#
# Both functions are documented as self-healing "on a timescale of minutes, not
# migrations" — these windows keep exactly that promise while stopping them
# from re-firing on every single relaunch during a dev or demo burst, where one
# instructor reloading to test something repays a full paginated roster pull and
# a content walk each time. Ten minutes still self-heals within a class period;
# it does not gut the feature, it just stops a reload costing what a day costs.
_ROSTER_SYNC_COOLDOWN_SECONDS = 600
_SKILL_SEED_COOLDOWN_SECONDS = 600


def _roster_role(course_role: str | None) -> str:
    """Blackboard courseRoleId -> Kala app_role. Only an explicit Student
    membership is a student; everything else (Instructor, Teaching
    Assistant, Grader, ...) is enrolled as instructor (upsert_enrollment
    coerces admin/instructor the same way)."""
    return "student" if (course_role or "").strip().lower() == "student" else "instructor"


def _seed_course_skills(*, institution_id: str, course_id: str, course_ref: str,
                        connector: BlackboardConnector) -> dict:
    """Seed the skill graph from AI proposals (docs/SKILL_PIPELINE.md). Same
    non-blocking contract as roster sync: any failure logs and is skipped,
    never blocks the 302. Incremental by module (see ai/skill_proposer.py):
    the proposer itself tracks which modules already have skills and only
    processes new ones, so this is safe on every instructor launch — the
    all-or-nothing "course already has skills" pre-check is deliberately
    gone, it would have blocked a partial result from ever being topped up."""
    try:
        # Cheap path, and it MUST stay that way: this runs on every instructor
        # launch under a "never blocks the 302" contract, and that flow is what
        # burned this instance's request quota on 2026-09-17. include_attachments
        # defaults False, so no PDFs are fetched here.
        items, _stats = connector.get_content(course_ref)
        if not items:
            return {"skipped": True, "reason": "course has no content"}
        # Pass the raw items through: the proposer groups by module itself
        # (one model call per module, lms/hierarchy.py) — a joined string
        # here would silently starve every module after the first on a
        # content-rich course.
        return seed_course_skills(
            institution_id=institution_id, course_id=course_id, content_items=items,
        )
    except Exception:
        logger.exception("skill proposal failed for %s; skipping", course_ref)
        return {"skipped": True, "reason": "error"}


def _sync_roster(*, institution_id: str, course_id: str, course_ref: str,
                 connector: BlackboardConnector) -> dict:
    """NRPS-style roster reconciliation (masterplan 3.1). Enrolls every
    member the LMS currently reports for this course, AND removes any
    student enrollment Kala has that the LMS no longer reports — so a
    one-off test launch, a student who dropped the course, or a stale row
    from before this reconciliation existed cannot linger permanently.

    Runs on every instructor launch, which for an actively-used course
    means this self-heals on a timescale of minutes, not migrations.

    Best-effort in both directions: a roster-pull failure never blocks the
    launching instructor's own session (unchanged from before), and now
    ALSO never triggers a deletion. An empty or failed pull is treated as
    "unknown," not as "nobody is enrolled" — the one failure mode that
    would be worse than the phantom-row bug this fixes is a transient LMS
    hiccup wiping a real class roster on the next launch.
    """
    try:
        members = connector.get_roster(course_ref)
    except Exception:
        logger.exception("roster pull failed for %s; skipping roster sync", course_ref)
        return {"enrolled": 0, "removed": 0, "skipped": "pull_failed"}

    if not members:
        # A genuinely empty class is vanishingly unlikely for a course an
        # instructor is actively launching into Kala from. Far more likely:
        # a partial response, an unexpected schema, or a permissions edge
        # case. Either way, reconciling against zero would delete every
        # real student enrollment — treat it the same as a failure.
        logger.warning(
            "roster pull for %s returned zero members; skipping reconciliation", course_ref,
        )
        return {"enrolled": 0, "removed": 0, "skipped": "empty_pull"}

    enrolled = 0
    current_ids: list[str] = []
    for member in members:
        lms_user_id = member.get("lms_user_id")
        if not lms_user_id:
            continue
        try:
            # resolve_user, same as the launch path. This direction matters too:
            # if a student LAUNCHED first (creating a `sub`-keyed row) and then
            # appears in a roster pull, upsert_user would key on `userId` and
            # mint a SECOND row — the same twin, from the other side. The
            # alias map means whichever path runs second finds the first's row.
            user = db.resolve_user(
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
            current_ids.append(user["id"])
            enrolled += 1
        except Exception:
            logger.exception("roster member %s skipped", lms_user_id)

    # The reconciliation step. Anyone Kala currently has as a STUDENT in
    # this course who did not appear in this fresh pull is not on the LMS
    # roster right now — remove their enrollment. Their user row, profile,
    # and evidence history are untouched, so a real re-enrollment (or the
    # same test account launching again) picks up exactly where it left
    # off rather than starting over.
    removed = db.remove_stale_student_enrollments(
        institution_id=institution_id, course_id=course_id, keep_user_ids=current_ids,
    )
    if removed:
        logger.info(
            "roster sync for %s removed %d stale student enrollment(s): %s",
            course_ref, len(removed), [r.get("user_id") for r in removed],
        )
    return {"enrolled": enrolled, "removed": len(removed)}


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
    # resolve_user, NOT upsert_user. The launch's identifier is Blackboard's LTI
    # `sub`, but the roster sync writes the connector's REST `userId` — two
    # different values for the same person. upsert_user would key on `sub` and
    # mint a twin for a student who already exists (and is already enrolled)
    # under `userId`, stranding their evidence on an account no instructor can
    # see. resolve_user checks the alias map, then email, so a launch finds the
    # existing person. See migration 0015 and db/supabase.py:resolve_user.
    user = db.resolve_user(
        institution_id=institution["id"],
        lms_user_id=payload["sub"],
        role=app_role,
        display_name=payload.get("name"),
        email=payload.get("email"),
    )
    ctx = C.extract_context(payload)
    course = None
    if ctx["lms_course_external_id"]:
        external_id = ctx["lms_course_external_id"]
        # Fix 1: resolve the course LOCALLY first. resolve_course_ref is a
        # Blackboard REST call that used to run on every single launch,
        # because the courses table stored only the resolved internal id and
        # had no way to look the course up by the external id the launch
        # carries. Now it does. This is the difference between a launch
        # costing one request and costing one request EVERY time.
        local = db.course_by_lms_external_id(
            institution_id=institution["id"], lms_course_external_id=external_id,
        )
        if local:
            # Known course: use the stored internal id and never call
            # Blackboard for resolution again for this course.
            lms_course_id = local["lms_course_id"]
        else:
            try:
                lms_course_id = connector.resolve_course_ref(external_id)
            except BlackboardRateLimitedError as exc:
                # A useful message beats a stack-trace-shaped string for
                # whoever hits this next. 502 is unchanged; only the body is.
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    "Blackboard is rate limiting this application; retry after "
                    f"roughly {exc.retry_after} seconds.",
                ) from exc
            except Exception as exc:
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    f"could not resolve Blackboard course: {exc}",
                ) from exc
        course = db.get_or_create_course(
            institution_id=institution["id"],
            lms_course_id=lms_course_id,
            title=ctx["title"],
            # Persist the external id so the NEXT launch takes the local path
            # above. This is the write that makes Fix 1 stick.
            lms_course_external_id=external_id,
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
            # Fix 2: cooldown gate. The self-healing intent is preserved (a
            # real change still reconciles within minutes), but a relaunch
            # burst no longer repays the full paginated cost each time. The
            # timestamp is only written on SUCCESS, so a skip or a failure
            # never blocks a genuine retry later.
            if db.course_synced_within(
                course=course, column="last_roster_sync_at",
                cooldown_seconds=_ROSTER_SYNC_COOLDOWN_SECONDS,
            ):
                logger.info(
                    "skipping roster sync for course %s: synced within the %ds cooldown",
                    course["id"], _ROSTER_SYNC_COOLDOWN_SECONDS,
                )
            else:
                result = _sync_roster(
                    institution_id=institution["id"], course_id=course["id"],
                    course_ref=lms_course_id, connector=connector,
                )
                if not result.get("skipped"):
                    db.touch_course_sync_timestamp(
                        course_id=course["id"], column="last_roster_sync_at",
                    )
            # AI skill proposal (docs/SKILL_PIPELINE.md): seed the skill
            # graph from the course's own content on first launch. Same
            # best-effort contract — a proposal failure never blocks the
            # 302. By the time students launch, proposals/matches are staged.
            # Same cooldown reasoning as the roster above: propose_skills is
            # incremental by module, so re-running is not WRONG, it is just a
            # content walk nobody needs on a relaunch.
            if db.course_synced_within(
                course=course, column="last_skill_seed_at",
                cooldown_seconds=_SKILL_SEED_COOLDOWN_SECONDS,
            ):
                logger.info(
                    "skipping skill seeding for course %s: seeded within the %ds cooldown",
                    course["id"], _SKILL_SEED_COOLDOWN_SECONDS,
                )
            else:
                result = _seed_course_skills(
                    institution_id=institution["id"], course_id=course["id"],
                    course_ref=lms_course_id, connector=connector,
                )
                if not result.get("skipped"):
                    db.touch_course_sync_timestamp(
                        course_id=course["id"], column="last_skill_seed_at",
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
