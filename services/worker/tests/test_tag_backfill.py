"""tag_backfill — the worker job that moved tagging off the api's 30s wall.

These tests pin the failure semantics that were hard-won over a whole
debugging session and MUST NOT regress:
  - a transport failure leaves the chunk UNMARKED (retried next run)
  - a genuine no-match MARKS the chunk (stops looping forever)
  - a course with no approved skills leaves its chunks UNMARKED (retried
    once skills are approved), and does not tag against another course's
    skills
"""
from app.jobs import tag_backfill


def _rows(*chunks):
    return list(chunks)


def _chunk(id, course_id="course-1", inst="inst-1", text="Cloud computing is...", module_ref=None):
    return {
        "id": id, "course_id": course_id, "institution_id": inst,
        "chunk_text": text, "module_ref": module_ref,
    }


def _wire(monkeypatch, *, pending, skills_by_course, tag_result=None, tag_raises=None):
    updates = []

    def fake_select(table, params):
        if table == "content_items":
            return pending
        if table == "skills":
            course = params["course_id"].split("eq.", 1)[1]
            return skills_by_course.get(course, [])
        raise AssertionError(f"unexpected select on {table}")

    def fake_update(table, filters, values):
        updates.append((table, filters, values))
        return [values]

    def fake_tag(*, text, skills):
        if tag_raises is not None:
            raise tag_raises
        return tag_result

    monkeypatch.setattr(tag_backfill.db, "select", fake_select)
    monkeypatch.setattr(tag_backfill.db, "update", fake_update)
    monkeypatch.setattr(tag_backfill, "tag_content", fake_tag)
    return updates


def test_a_match_sets_skill_id_and_marks_attempted(monkeypatch):
    updates = _wire(
        monkeypatch,
        pending=_rows(_chunk("c1")),
        skills_by_course={"course-1": [{"id": "skill-1", "name": "Cloud concepts"}]},
        tag_result={"skill_id": "skill-1", "bloom_level": "understand"},
    )
    result = tag_backfill.run()

    assert result["tagged"] == 1
    content_updates = [u for u in updates if u[0] == "content_items"]
    assert len(content_updates) == 1
    _, _, values = content_updates[0]
    assert values["skill_id"] == "skill-1"
    assert "tag_attempted_at" in values


def test_a_transport_failure_leaves_the_chunk_unmarked(monkeypatch):
    """The critical retry semantics: a provider/transport error must NOT set
    tag_attempted_at, or the chunk is lost to a permanent no-match instead of
    being retried on a healthy run."""
    updates = _wire(
        monkeypatch,
        pending=_rows(_chunk("c1")),
        skills_by_course={"course-1": [{"id": "skill-1", "name": "Cloud concepts"}]},
        tag_raises=RuntimeError("503 Service Unavailable"),
    )
    result = tag_backfill.run()

    assert result["failed"] == 1
    assert result["tagged"] == 0
    # No content_items write at all — the chunk stays pending for next run.
    assert [u for u in updates if u[0] == "content_items"] == []


def test_a_genuine_no_match_marks_attempted_without_a_skill(monkeypatch):
    """A real no-match (model answered, matched nothing) MUST mark the chunk
    attempted, or ingest loops forever on untaggable content — the exact bug
    the tag_attempted_at column was added to fix."""
    updates = _wire(
        monkeypatch,
        pending=_rows(_chunk("c1")),
        skills_by_course={"course-1": [{"id": "skill-1", "name": "Cloud concepts"}]},
        tag_result={"skill_id": None, "bloom_level": None},
    )
    result = tag_backfill.run()

    assert result["no_match"] == 1
    content_updates = [u for u in updates if u[0] == "content_items"]
    assert len(content_updates) == 1
    _, _, values = content_updates[0]
    assert "skill_id" not in values          # nothing matched
    assert "tag_attempted_at" in values      # but it is marked, so it won't loop


def test_a_course_with_no_approved_skills_is_left_pending(monkeypatch):
    """No approved skills yet -> leave the chunk UNMARKED so it is retried once
    the instructor approves skills (that is what /content/retag + this job are
    for). It must not be counted attempted and must not be tagged against
    anything."""
    updates = _wire(
        monkeypatch,
        pending=_rows(_chunk("c1", course_id="course-empty")),
        skills_by_course={},  # no skills for any course
        tag_result={"skill_id": "should-not-be-used", "bloom_level": "apply"},
    )
    result = tag_backfill.run()

    assert result["skipped_no_skills"] == 1
    assert result["attempted"] == 0
    assert updates == []  # nothing written at all


def test_each_course_is_tagged_against_its_own_skills(monkeypatch):
    """A batch spanning two courses must classify each chunk against its own
    course's approved skills, never the other's."""
    seen = {}

    def fake_tag(*, text, skills):
        # record which skill ids were offered for this call
        seen[text] = {s["id"] for s in skills}
        return {"skill_id": None, "bloom_level": None}

    pending = _rows(
        _chunk("c1", course_id="course-A", text="A-content"),
        _chunk("c2", course_id="course-B", text="B-content"),
    )
    skills_by_course = {
        "course-A": [{"id": "A-skill", "name": "A"}],
        "course-B": [{"id": "B-skill", "name": "B"}],
    }

    def fake_select(table, params):
        if table == "content_items":
            return pending
        if table == "skills":
            course = params["course_id"].split("eq.", 1)[1]
            return skills_by_course.get(course, [])
        raise AssertionError(table)

    monkeypatch.setattr(tag_backfill.db, "select", fake_select)
    monkeypatch.setattr(tag_backfill.db, "update", lambda *a, **k: [])
    monkeypatch.setattr(tag_backfill, "tag_content", fake_tag)

    tag_backfill.run()

    assert seen["A-content"] == {"A-skill"}
    assert seen["B-content"] == {"B-skill"}
