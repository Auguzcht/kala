"""The LMS connector interface. One interface, per-LMS implementations, so the
rest of the backend is LMS-agnostic. Blackboard is the pilot; Canvas access
was removed at the vendor level and is out of scope.

get_content() items must include ``lms_content_id`` and ``parent_id`` (null
for top-level items). That's the only contract folder/module scoping in
app.lms.hierarchy depends on -- it walks whatever tree shape a given
institution's course actually has (however many folder levels deep, however
they name them), rather than assuming any one school's convention.

get_content() returns ``(items, attachment_stats)``. The stats dict is how a
caller learns whether to call again when attachment fetching is capped; on the
default cheap path it is a zeroed dict. ``items[*]["attachments"]`` holds
extracted document text (one entry per fetched file, each with its own chunks),
or an empty list when attachments were not requested."""
from __future__ import annotations

from typing import Protocol


class LMSConnector(Protocol):
    def resolve_course_ref(self, external_id: str) -> str: ...
    def get_roster(self, course_ref: str) -> list[dict]: ...
    def get_content(self, course_ref: str, *, include_attachments: bool = False,
                    max_attachments: int = 3) -> tuple[list[dict], dict]: ...
    def get_assessments(self, course_ref: str) -> list[dict]: ...
    def post_grade(self, course_ref: str, column_id: str, user_ref: str, score: float) -> None: ...
