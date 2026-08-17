"""Instructor dashboard. Reads cohort analytics scoped to the caller's course
(RLS enforces the boundary; the API adds convenience shaping)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.db import supabase as db
from app.deps import CurrentUser, require_role

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/{course_id}/heatmap")
def heatmap(course_id: str, user: CurrentUser = Depends(require_role("instructor", "admin"))):
    rows = db.select("mastery_state", {
        "course_id": f"eq.{course_id}", "select": "skill_id,estimate,attempts",
    })
    return {"courseId": course_id, "cells": rows}
