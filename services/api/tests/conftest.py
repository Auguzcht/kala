"""Shared test fixtures and canonical fake identifiers.

WHY THE FAKE IDS ARE REAL UUIDs
    Every route with a path param now runs that param through
    `require_valid_*(...)` (app/deps.py), which 404s anything that is not a
    well-formed UUID. Before that guard, Postgres rejected a malformed id with
    `22P02` and the error escaped as a bare 500 — so routes accepted `"course-1"`
    in tests while failing the same way in production against a mistyped token.

    That means fake ids in tests must be VALID UUIDs, or the test exercises the
    404 path instead of the handler. Rather than hand-write 270 literal UUIDs,
    these constants name the roles. They are fixed (not generated per run) so a
    failing assertion prints a stable, greppable id.

    Using obviously-fake but well-formed UUIDs (all zeros apart from a trailing
    marker) keeps them visually distinguishable from anything real.
"""
from __future__ import annotations

# Distinct, stable, well-formed UUIDs. The tail marks the role so a failure
# message reads unambiguously.
COURSE_ID = "00000000-0000-4000-8000-000000000001"
COURSE_ID_2 = "00000000-0000-4000-8000-000000000002"
SKILL_ID = "00000000-0000-4000-8000-000000000010"
SKILL_ID_2 = "00000000-0000-4000-8000-000000000011"
SET_ID = "00000000-0000-4000-8000-000000000020"
ITEM_ID = "00000000-0000-4000-8000-000000000030"
USER_ID = "00000000-0000-4000-8000-000000000040"
USER_ID_2 = "00000000-0000-4000-8000-000000000041"
INSTITUTION_ID = "00000000-0000-4000-8000-000000000050"
CONVERSATION_ID = "00000000-0000-4000-8000-000000000060"
STEP_ID = "00000000-0000-4000-8000-000000000070"
COLUMN_ID = "00000000-0000-4000-8000-000000000080"
REC_ID = "00000000-0000-4000-8000-000000000090"
ATTACHMENT_ID = "00000000-0000-4000-8000-0000000000a0"

# The legacy string ids the tests used before the UUID guard existed. Kept as a
# mapping so the mechanical rename in the test files is reviewable rather than
# a wall of hex.
LEGACY_TO_UUID = {
    "course-1": COURSE_ID,
    "course-2": COURSE_ID_2,
    "skill-1": SKILL_ID,
    "skill-2": SKILL_ID_2,
    "set-1": SET_ID,
    "item-1": ITEM_ID,
    "user-1": USER_ID,
    "conv-1": CONVERSATION_ID,
    "step-1": STEP_ID,
}
