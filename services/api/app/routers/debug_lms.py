import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import get_settings
from app.db import supabase as db
from app.deps import CurrentUser, get_current_user, get_lms_connector
from app.lms.blackboard import BlackboardConnector

logger = logging.getLogger(__name__)

# TEMPORARY DIAGNOSTIC ROUTER — delete before the pilot ships.
#
# Why this exists: we could not tell whether Blackboard's content listing
# carries a usable file-download reference for `resource/x-bb-file` items,
# because the connector's flatten() keeps only five fields and there is no way
# to see the raw payload through the deployed API. The LMS is unreachable from
# a local machine (firewalled), so the only place this can be inspected is from
# inside the Lambda. Guessing produced one wrong fix already (see the
# bed1799 correction), so this probe exists to answer the question with
# evidence instead of inference.
#
# It is read-only and gated to course staff, but it does return raw LMS
# payloads, so it must not survive past this investigation.
router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/lms/content-raw/{course_id}")
def content_raw(
    course_id: str,
    content_id: str | None = None,
    sample: int = 3,
    user: CurrentUser = Depends(get_current_user),
    connector: BlackboardConnector = Depends(get_lms_connector),
):
    """The RAW Blackboard content listing for a course, unmapped.

    `content_id` fetches one item's children (the documented nesting path), so
    pass a folder id to walk. `sample` caps how many items come back so the
    response stays readable.

    Returns the FULL raw item objects, not the connector's five-field mapping,
    so `contentHandler` (and any file reference inside it) is visible. This is
    the whole point: flatten() discards exactly the field we need to see.
    """
    courses = db.select("courses", {
        "id": f"eq.{course_id}",
        "institution_id": f"eq.{user.institution_id}",
        "select": "lms_course_id", "limit": "1",
    })
    if not courses:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found")

    s = get_settings()
    base = f"{s.lms_rest_base_url}/courses/{courses[0]['lms_course_id']}/contents"
    path = f"{base}/{content_id}/children" if content_id else base

    import httpx
    resp = httpx.get(path, headers=connector._headers(),
                     verify=s.lms_verify_tls, timeout=20.0)
    resp.raise_for_status()
    results = resp.json().get("results", [])

    return {
        "path": path,
        "count": len(results),
        "items": results[:sample],
    }


@router.get("/lms/item-raw/{course_id}/{content_id}")
def item_raw(
    course_id: str,
    content_id: str,
    user: CurrentUser = Depends(get_current_user),
    connector: BlackboardConnector = Depends(get_lms_connector),
):
    """ONE item, fetched directly (not via its parent's children list).

    Some Blackboard builds put handler detail (a file's upload/download
    reference) on the single-item GET and omit it from the listing. This
    checks that without needing a second deploy.
    """
    courses = db.select("courses", {
        "id": f"eq.{course_id}",
        "institution_id": f"eq.{user.institution_id}",
        "select": "lms_course_id", "limit": "1",
    })
    if not courses:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found")

    s = get_settings()
    path = (
        f"{s.lms_rest_base_url}/courses/{courses[0]['lms_course_id']}"
        f"/contents/{content_id}"
    )
    import httpx
    resp = httpx.get(path, headers=connector._headers(),
                     verify=s.lms_verify_tls, timeout=20.0)
    if resp.status_code >= 400:
        return {"path": path, "status": resp.status_code, "body": resp.text[:400]}
    return {"path": path, "status": resp.status_code, "item": resp.json()}


@router.get("/lms/file-probe/{course_id}/{content_id}")
def file_probe(
    course_id: str,
    content_id: str,
    user: CurrentUser = Depends(get_current_user),
    connector: BlackboardConnector = Depends(get_lms_connector),
):
    """Try the documented download paths for a file item and report which, if
    any, returns bytes. The whole PDF question reduces to this: if one of these
    yields a PDF, the real AWS module material is reachable and ingest can be
    wired to fetch it. If none do, the content genuinely is not exposed over
    this API and the plan changes.

    Reports only status/content-type/size — never the file body — so this is
    safe to call and cheap to read.
    """
    courses = db.select("courses", {
        "id": f"eq.{course_id}",
        "institution_id": f"eq.{user.institution_id}",
        "select": "lms_course_id", "limit": "1",
    })
    if not courses:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "course not found")
    ref = courses[0]["lms_course_id"]

    s = get_settings()
    import httpx
    candidates = [
        f"{s.lms_rest_base_url}/courses/{ref}/contents/{content_id}/download",
        f"{s.lms_rest_base_url}/courses/{ref}/contents/{content_id}/file",
        f"{s.lms_rest_base_url}/courses/{ref}/contents/{content_id}/attachments",
    ]
    out = []
    for url in candidates:
        try:
            r = httpx.get(url, headers=connector._headers(),
                          verify=s.lms_verify_tls, timeout=20.0, follow_redirects=True)
            out.append({
                "url": url.split("/contents/")[-1],
                "status": r.status_code,
                "content_type": r.headers.get("content-type"),
                "bytes": len(r.content),
                "looks_like_pdf": r.content[:5] == b"%PDF-",
            })
        except Exception as exc:  # noqa: BLE001 — a probe reports, never raises
            out.append({"url": url.split("/contents/")[-1], "error": str(exc)[:120]})
    return {"course_ref": ref, "content_id": content_id, "attempts": out}
