"""Gamification endpoint. Surfaces the derived reward view (XP, streak,
badges) computed purely from the evidence log + mastery state — no writable
balance, so it cannot drift from the twin or be gamed from the client."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import CurrentUser, get_current_user
from app.learn import xp

router = APIRouter(prefix="/gamification", tags=["gamification"])


@router.get("/{course_id}/summary")
def summary(course_id: str, user: CurrentUser = Depends(get_current_user)):
    return xp.summary(
        institution_id=user.institution_id, user_id=user.user_id, course_id=course_id,
    )
