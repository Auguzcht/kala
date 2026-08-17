"""Canvas connector (stub). Kept to prove the interface is LMS-agnostic.
Implement against the Canvas LMS REST API when a Canvas tenant is onboarded."""
from __future__ import annotations


class CanvasConnector:
    def get_roster(self, course_ref: str) -> list[dict]:
        return []

    def get_content(self, course_ref: str) -> list[dict]:
        return []

    def get_grades(self, course_ref: str) -> list[dict]:
        return []

    def post_grade(self, course_ref: str, user_ref: str, score: float) -> None:
        return None
