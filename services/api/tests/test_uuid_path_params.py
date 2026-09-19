"""Boundary validation for UUID path params.

Before this guard, a malformed `course_id` (or any other UUID path param)
went straight into a PostgREST filter string. Postgres answered
`22P02 invalid input syntax for type uuid`, the resulting
`httpx.HTTPStatusError` escaped the handler unhandled, and Lambda returned a
bare 500 with a text/plain body reading "Internal Server Error".

That made a client-side mistake (a mistyped or hand-edited token, a stale
bookmark) look like a server outage. Found live on 2026-09-19 when a session
token carried a course_id whose last segment was 13 hex chars instead of 12,
and every course-scoped route 500'd.

The contract these tests pin: every failure mode on a course-scoped path looks
IDENTICAL to the client — malformed id, nonexistent id, and an id the caller
cannot access are all one 404. That is a consistency choice, so the frontend
has a single case, not three.
"""
import uuid

from fastapi import FastAPI, Depends, HTTPException, Path
from fastapi.testclient import TestClient

from app.deps import (
    UUID_PATH_DEPS,
    require_valid_course_id,
    require_valid_set_id,
    _validated_uuid,
)

VALID = "ae4e7680-f94b-4652-b3f6-b9c32f4420de"
# The real id from the 2026-09-19 incident: same as VALID but with ONE extra
# hex character in the final segment, so it is 13 chars and not a UUID.
MALFORMED = "ae4e7680-f94b-4652-b3f6-b9c332f4420de"


# ---- the two-by-two: shape x handling ------------------------------------


def test_a_well_formed_uuid_passes_through_unchanged() -> None:
    assert _validated_uuid(VALID) == VALID


def test_the_incident_id_is_rejected() -> None:
    """The exact shape that caused the outage — a near-miss for a real id."""
    try:
        _validated_uuid(MALFORMED)
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 404


def test_the_error_does_not_echo_the_rejected_value() -> None:
    """A malformed id is often one character off a real one, so reflecting it
    into an error body is a needless way to confirm a guess."""
    try:
        _validated_uuid(MALFORMED)
        assert False, "expected HTTPException"
    except HTTPException as exc:
        assert MALFORMED not in str(exc.detail)


def test_non_uuid_garbage_is_rejected() -> None:
    for junk in ("", " ", "not-a-uuid", "12345", "course-1", None, "../../etc/passwd"):
        try:
            _validated_uuid(junk)
            assert False, f"expected rejection for {junk!r}"
        except HTTPException as exc:
            assert exc.status_code == 404


def test_a_uuid_shaped_string_with_the_wrong_length_is_rejected() -> None:
    """Truncated or over-long hex must not slip through — that is the incident
    shape (one character too many).

    The no-hyphens form IS accepted, deliberately: `uuid.UUID` parses it and
    Postgres does too, so rejecting it would 404 a request the database would
    have answered. Only genuinely wrong length is refused.
    """
    assert _validated_uuid(str(uuid.UUID(VALID))) == VALID
    for bad in (VALID[:-1], VALID + "a"):
        try:
            _validated_uuid(bad)
            assert False, f"expected rejection for {bad!r}"
        except HTTPException:
            pass
    # Accepted by both uuid.UUID and Postgres, so it must pass here.  
    assert _validated_uuid(VALID.replace("-", "")) == VALID.replace("-", "")


# ---- the dependency, through a real route --------------------------------


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/courses/{course_id}")
    def one(course_id: str = Depends(require_valid_course_id)):
        return {"courseId": course_id}

    @app.get("/courses/{course_id}/sets/{set_id}")
    def two(
        course_id: str = Depends(require_valid_course_id),
        set_id: str = Depends(require_valid_set_id),
    ):
        return {"courseId": course_id, "setId": set_id}

    return app


def test_malformed_course_id_returns_404_not_500() -> None:
    """The regression this whole change exists for. Before the guard this was
    a 500 with an unhandled Postgres error behind it."""
    c = TestClient(_app())
    r = c.get(f"/courses/{MALFORMED}")
    assert r.status_code == 404
    assert r.status_code != 500


def test_happy_path_still_returns_the_value() -> None:
    c = TestClient(_app())
    r = c.get(f"/courses/{VALID}")
    assert r.status_code == 200
    assert r.json()["courseId"] == VALID


def test_two_uuid_params_are_validated_independently() -> None:
    """A malformed SECOND param must 404 too — the guard is per parameter, not
    a single check on the first one."""
    c = TestClient(_app())
    good_set = "253ed060-fb41-4c19-a198-6aae467beaad"
    assert c.get(f"/courses/{VALID}/sets/{good_set}").status_code == 200
    assert c.get(f"/courses/{MALFORMED}/sets/{good_set}").status_code == 404
    assert c.get(f"/courses/{VALID}/sets/{MALFORMED}").status_code == 404


def test_the_dependency_binds_to_the_path_not_a_query_param() -> None:
    """A bare `value: str` dependency is read by FastAPI as a REQUIRED QUERY
    param and 422s on every call. Each dep must bind its name with
    Path(..., alias=...) — this pins that, since the failure is silent at
    import time and only shows up as a 422 at request time."""
    c = TestClient(_app())
    r = c.get(f"/courses/{VALID}")
    assert r.status_code == 200, f"dep did not bind to the path: {r.status_code}"
    assert r.status_code != 422


# ---- coverage of the dep table -------------------------------------------


def test_every_supported_path_param_has_a_dependency() -> None:
    """The table is what the signature rewrite is driven from. A name missing
    here means a route using it is unguarded and can still 500."""
    expected = {
        "course_id", "set_id", "skill_id", "user_id", "column_id",
        "conversation_id", "step_id", "rec_id", "attachment_id",
    }
    assert set(UUID_PATH_DEPS) == expected


def test_dependencies_are_distinct_functions() -> None:
    """sharing one function across names would bind the wrong path segment."""
    assert len(set(UUID_PATH_DEPS.values())) == len(UUID_PATH_DEPS)


def test_blackboard_column_ids_are_NOT_uuid_guarded() -> None:
    """`column_id` in /courses/{course_id}/assessments/{column_id}/grade is a
    BLACKBOARD gradebook column ref (e.g. "_8_1"), passed to the LMS connector
    and never used in a PostgREST filter. Guarding it would 404 a perfectly
    valid call. It is the one UUID-ish name that must NOT use the guard, so it
    is pinned here rather than left implicit."""
    from app.routers import diagnostic

    src = __import__("inspect").getsource(diagnostic.post_grade)
    assert "require_valid_column_id" not in src
    assert "column_id: str," in src
