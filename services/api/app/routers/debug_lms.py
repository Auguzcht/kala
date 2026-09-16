import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import get_settings
from app.db import supabase as db
from app.deps import CurrentUser, get_lms_connector, require_role
from app.lms.blackboard import BlackboardConnector

logger = logging.getLogger(__name__)

# TEMPORARY DIAGNOSTIC ROUTER — tracked for removal, see the todo list.
#
# Why this exists: we could not tell whether Blackboard's content listing
# carries a usable file-download reference for `resource/x-bb-file` items,
# because the connector's flatten() keeps only five fields and there is no way
# to see the raw payload through the deployed API. The LMS is unreachable from
# a local machine (firewalled), so the only place this can be inspected is from
# inside the Lambda. Guessing produced one wrong fix already (see a0c3420's
# correction of bed1799), so this exists to answer the question with evidence.
#
# ACCESS: the same two-layer gate the rest of the app uses, not a bare role
# check. `require_role` proves the caller holds a staff role somewhere;
# `_assert_teaches_course` proves they are staff of THIS course. These routes
# take a course_id from the path and echo raw third-party payloads back, which
# is exactly the shape where "any instructor, anywhere" is not good enough —
# an instructor from another course must not be able to read this course's
# Blackboard tree just by guessing its id.
router = APIRouter(prefix="/debug", tags=["debug"])


def _assert_teaches_course(*, user: CurrentUser, course_id: str) -> None:
    """The caller must be enrolled as an instructor of THIS course.

    The course_id is caller-supplied, so the role dependency alone is not
    enough — it only says "this person is staff somewhere". Mirrors
    dashboard.py's _assert_teaches_student, at course scope rather than student
    scope. 404 rather than 403 so the route does not confirm a course exists to
    someone who has no business asking.
    """
    # Admins are institution-wide by definition; they do not need a per-course
    # enrollment row.
    if user.app_role == "admin":
        return
    rows = db.select("enrollments", {
        "institution_id": f"eq.{user.institution_id}",
        "user_id": f"eq.{user.user_id}",
        "course_id": f"eq.{course_id}",
        "role": "eq.instructor",
        "select": "course_id", "limit": "1",
    })
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found")


def _course_ref(*, user: CurrentUser, course_id: str) -> str:
    courses = db.select("courses", {
        "id": f"eq.{course_id}",
        "institution_id": f"eq.{user.institution_id}",
        "select": "lms_course_id", "limit": "1",
    })
    if not courses:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found")
    return courses[0]["lms_course_id"]


@router.get("/lms/content-raw/{course_id}")
def content_raw(
    course_id: str,
    content_id: str | None = None,
    sample: int = 3,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
    connector: BlackboardConnector = Depends(get_lms_connector),
):
    """The RAW Blackboard content listing for a course, unmapped.

    `content_id` fetches that item's children (the documented nesting path).
    Returns the FULL raw item objects, not the connector's five-field mapping,
    so `contentHandler` — and any file reference inside it — is visible. That
    is the whole point: flatten() discards exactly the field we need to see.
    """
    _assert_teaches_course(user=user, course_id=course_id)
    ref = _course_ref(user=user, course_id=course_id)

    s = get_settings()
    base = f"{s.lms_rest_base_url}/courses/{ref}/contents"
    path = f"{base}/{content_id}/children" if content_id else base

    import httpx
    resp = httpx.get(path, headers=connector._headers(),
                     verify=s.lms_verify_tls, timeout=20.0)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return {"path": path, "count": len(results), "items": results[:sample]}


@router.get("/lms/item-raw/{course_id}/{content_id}")
def item_raw(
    course_id: str,
    content_id: str,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
    connector: BlackboardConnector = Depends(get_lms_connector),
):
    """ONE item fetched directly, not via its parent's children list. Some
    Blackboard builds put handler detail (a file's download reference) on the
    single-item GET and omit it from the listing."""
    _assert_teaches_course(user=user, course_id=course_id)
    ref = _course_ref(user=user, course_id=course_id)

    s = get_settings()
    path = f"{s.lms_rest_base_url}/courses/{ref}/contents/{content_id}"
    import httpx
    resp = httpx.get(path, headers=connector._headers(),
                     verify=s.lms_verify_tls, timeout=20.0)
    if resp.status_code >= 400:
        return {"path": path.split("/courses/")[-1], "status": resp.status_code,
                "body": resp.text[:400]}
    return {"path": path.split("/courses/")[-1], "status": resp.status_code,
            "item": resp.json()}


@router.get("/lms/file-probe/{course_id}/{content_id}")
def file_probe(
    course_id: str,
    content_id: str,
    user: CurrentUser = Depends(require_role("instructor", "admin")),
    connector: BlackboardConnector = Depends(get_lms_connector),
):
    """Try the documented download paths for a file item and report which, if
    any, returns bytes. The whole PDF question reduces to this: if one yields a
    PDF, the real AWS module material is reachable and ingest can fetch it. If
    none do, the content is not exposed over this API and the plan changes.

    Reports status / content-type / size only — never the file body — so it is
    safe to call and cheap to read."""
    _assert_teaches_course(user=user, course_id=course_id)
    ref = _course_ref(user=user, course_id=course_id)

    s = get_settings()
    import httpx
    candidates = [
        f"{s.lms_rest_base_url}/courses/{ref}/contents/{content_id}/download",
        f"{s.lms_rest_base_url}/courses/{ref}/contents/{content_id}/file",
        f"{s.lms_rest_base_url}/courses/{ref}/contents/{content_id}/attachments",
    ]
    out = []
    for url in candidates:
        label = url.split("/contents/")[-1]
        try:
            r = httpx.get(url, headers=connector._headers(),
                          verify=s.lms_verify_tls, timeout=20.0, follow_redirects=True)
            out.append({
                "path": label,
                "status": r.status_code,
                "content_type": r.headers.get("content-type"),
                "bytes": len(r.content),
                "looks_like_pdf": r.content[:5] == b"%PDF-",
            })
        except Exception as exc:  # noqa: BLE001 — a probe reports, never raises
            out.append({"path": label, "error": str(exc)[:120]})
    return {"course_ref": ref, "content_id": content_id, "attempts": out}
