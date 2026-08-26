"""The LMS connector interface. One interface, per-LMS implementations, so the
rest of the backend is LMS-agnostic. Blackboard is the pilot; Canvas access
was removed at the vendor level and is out of scope.

get_content() items must include ``lms_content_id`` and ``parent_id`` (null
for top-level items). That's the only contract folder/module scoping in
app.lms.hierarchy depends on -- it walks whatever tree shape a given
institution's course actually has (however many folder levels deep, however
they name them), rather than assuming any one school's convention."""
from __future__ import annotations

from typing import Protocol


class LMSConnector(Protocol):
    def resolve_course_ref(self, external_id: str) -> str: ...
    def get_roster(self, course_ref: str) -> list[dict]: ...
    def get_content(self, course_ref: str) -> list[dict]: ...
    def get_assessments(self, course_ref: str) -> list[dict]: ...
    def post_grade(self, course_ref: str, column_id: str, user_ref: str, score: float) -> None: ...
