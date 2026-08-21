"""Canvas connector (stub). Kept to prove the interface is LMS-agnostic.
Implement against the Canvas LMS REST API when a Canvas tenant is onboarded."""
from __future__ import annotations

from app.lms.base import LMSConnector


class CanvasConnector(LMSConnector):
    def resolve_course_ref(self, external_id: str) -> str:
        return external_id

    def get_roster(self, course_ref: str) -> list[dict]:
        return []

    def get_content(self, course_ref: str) -> list[dict]:
        return []

    def get_assessments(self, course_ref: str) -> list[dict]:
        return []

    def post_grade(self, course_ref: str, column_id: str, user_ref: str, score: float) -> None:
        return None
