"""Practice endpoints (stub). Mirror the diagnostic path: serve items, accept
attempts, write evidence, update the twin."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import CurrentUser, get_current_user

router = APIRouter(prefix="/practice", tags=["practice"])


@router.get("/{course_id}/next")
def next_item(course_id: str, user: CurrentUser = Depends(get_current_user)):
    # TODO: pick the weakest skill from mastery_state and generate an item.
    return {"courseId": course_id, "item": None}
