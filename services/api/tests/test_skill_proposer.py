from app.ai import skill_proposer


def test_parse_drops_vague_and_malformed_proposals():
    """Guardrail: only well-formed, valid-Bloom skills survive parsing."""
    raw = """{"skills": [
        {"name": "Construct a truth table", "bloom_level": "apply", "weight": 1.5},
        {"name": "", "bloom_level": "apply"},
        {"name": "Understand things", "bloom_level": "not-a-bloom-level"},
        {"name": "Analyze a circuit", "bloom_level": "analyze"}
    ]}"""
    out = skill_proposer._parse_proposals(raw)
    assert [s["name"] for s in out] == ["Construct a truth table", "Analyze a circuit"]
    assert out[0]["weight"] == 1.5  # preserved
    assert out[1]["weight"] == 1.0  # defaulted


def test_parse_clamps_weight_to_bounds():
    raw = '{"skills": [{"name": "X a thing", "bloom_level": "apply", "weight": 9.0}]}'
    assert skill_proposer._parse_proposals(raw)[0]["weight"] == 2.0


def test_parse_tolerates_markdown_fences():
    raw = '```json\n{"skills": [{"name": "Apply Y", "bloom_level": "apply"}]}\n```'
    assert skill_proposer._parse_proposals(raw)[0]["name"] == "Apply Y"


def test_parse_returns_empty_on_garbage():
    assert skill_proposer._parse_proposals("not json at all") == []


def test_group_content_by_module_matches_ingest_grouping():
    """Same grouping logic ingest_course() uses for content_items, so a
    proposed skill's module_ref is guaranteed consistent with how that
    course's content actually gets tagged."""
    items = [
        {"lms_content_id": "mod-1", "title": "Module 1", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l1", "title": "Lesson 1", "parent_id": "mod-1", "body_or_description": "logic gates content"},
        {"lms_content_id": "mod-2", "title": "Module 2", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l2", "title": "Lesson 2", "parent_id": "mod-2", "body_or_description": "embedded systems content"},
        {"lms_content_id": "root", "title": "Syllabus", "parent_id": None, "body_or_description": "course syllabus text"},
    ]
    groups = skill_proposer._group_content_by_module(items)
    assert groups["Module 1"] == "logic gates content"
    assert groups["Module 2"] == "embedded systems content"
    assert groups[None] == "course syllabus text"  # root-level content, no folder


def test_group_content_by_module_skips_empty_bodies():
    items = [
        {"lms_content_id": "folder-1", "title": "Module 1", "parent_id": None, "body_or_description": ""},
    ]
    assert skill_proposer._group_content_by_module(items) == {}


def test_seed_skips_when_course_already_has_skills(monkeypatch):
    """Idempotency: a re-launch of a course that already has skills does not
    re-propose (no duplicate work, no LLM calls)."""
    monkeypatch.setattr(skill_proposer.db, "select", lambda t, p: [{"id": "existing"}])
    called = {"proposed": False}
    monkeypatch.setattr(
        skill_proposer, "propose_skills_from_text",
        lambda **k: called.__setitem__("proposed", True) or [],
    )
    result = skill_proposer.seed_course_skills(
        institution_id="i", course_id="c", content_items=[],
    )
    assert result["skipped"] is True
    assert called["proposed"] is False


def test_seed_calls_propose_once_per_module_not_once_per_course(monkeypatch):
    """The bug this fixes: a real 3-module course was only ever seeing
    Module 1's content, because the old design made ONE whole-course call
    with a hard text cutoff. This asserts the fix directly: one proposal
    call per detected module, each receiving only that module's text."""
    items = [
        {"lms_content_id": "mod-1", "title": "Module 1", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l1", "title": "L1", "parent_id": "mod-1", "body_or_description": "module one text"},
        {"lms_content_id": "mod-2", "title": "Module 2", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l2", "title": "L2", "parent_id": "mod-2", "body_or_description": "module two text"},
        {"lms_content_id": "mod-3", "title": "Module 3", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l3", "title": "L3", "parent_id": "mod-3", "body_or_description": "module three text"},
    ]
    monkeypatch.setattr(skill_proposer.db, "select", lambda t, p: [])
    monkeypatch.setattr(skill_proposer.db, "rpc", lambda fn, args: [])
    monkeypatch.setattr(skill_proposer.db, "insert", lambda t, rows: rows)
    monkeypatch.setattr(skill_proposer.bedrock, "embed", lambda text, **k: [0.0] * 1024)

    seen_texts = []

    def fake_propose(*, course_content):
        seen_texts.append(course_content)
        return [{"name": f"Skill from {course_content}", "bloom_level": "apply", "weight": 1.0}]

    monkeypatch.setattr(skill_proposer, "propose_skills_from_text", fake_propose)

    result = skill_proposer.seed_course_skills(
        institution_id="i", course_id="c", content_items=items,
    )
    assert result["modulesProcessed"] == 3
    assert sorted(seen_texts) == ["module one text", "module three text", "module two text"]
    assert result["proposed"] == 3  # one skill per module, all novel


def test_seed_sets_module_ref_directly_from_the_producing_group(monkeypatch):
    """A proposed skill's module_ref comes from which module's content
    actually produced it, not a later inference step."""
    items = [
        {"lms_content_id": "mod-2", "title": "Module 2", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l2", "title": "L2", "parent_id": "mod-2", "body_or_description": "embedded systems"},
    ]
    monkeypatch.setattr(skill_proposer.db, "select", lambda t, p: [])
    monkeypatch.setattr(skill_proposer.db, "rpc", lambda fn, args: [])
    monkeypatch.setattr(skill_proposer.bedrock, "embed", lambda text, **k: [0.0] * 1024)
    monkeypatch.setattr(
        skill_proposer, "propose_skills_from_text",
        lambda **k: [{"name": "Diagnose a sensor fault", "bloom_level": "analyze", "weight": 1.0}],
    )
    inserted = []
    monkeypatch.setattr(skill_proposer.db, "insert", lambda t, rows: inserted.extend(rows) or rows)

    skill_proposer.seed_course_skills(institution_id="i", course_id="c", content_items=items)
    assert inserted[0]["module_ref"] == "Module 2"


def test_seed_auto_approves_on_strong_match(monkeypatch):
    """A proposal that strongly matches an already-approved skill in another
    course is reused verbatim and written straight to 'approved', no review."""
    items = [
        {"lms_content_id": "mod-1", "title": "Module 1", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l1", "title": "L1", "parent_id": "mod-1", "body_or_description": "truth tables"},
    ]
    monkeypatch.setattr(skill_proposer.db, "select", lambda t, p: [])
    monkeypatch.setattr(
        skill_proposer, "propose_skills_from_text",
        lambda **k: [{"name": "Construct a truth table", "bloom_level": "apply", "weight": 1.0}],
    )
    monkeypatch.setattr(skill_proposer.bedrock, "embed", lambda text, **k: [0.0] * 1024)
    monkeypatch.setattr(skill_proposer.db, "rpc", lambda fn, args: [{
        "id": "canon-1", "name": "Construct a truth table", "bloom_level": "apply",
        "blueprint_weight": 1.0, "course_id": "other-course", "similarity": 0.97,
    }])
    inserted = []
    monkeypatch.setattr(skill_proposer.db, "insert", lambda t, rows: inserted.extend(rows) or rows)

    result = skill_proposer.seed_course_skills(institution_id="i", course_id="c", content_items=items)
    assert result["auto_approved"] == 1
    assert result["proposed"] == 0
    assert inserted[0]["status"] == "approved"
    assert inserted[0]["canonical_skill_id"] == "canon-1"
    assert inserted[0]["module_ref"] == "Module 1"


def test_seed_flags_possible_duplicate_in_review_band(monkeypatch):
    """A proposal in the middle similarity band is staged as 'proposed' with a
    duplicate hint, so a human decides, never silently merged or split."""
    items = [
        {"lms_content_id": "mod-1", "title": "Module 1", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l1", "title": "L1", "parent_id": "mod-1", "body_or_description": "truth tables"},
    ]
    monkeypatch.setattr(skill_proposer.db, "select", lambda t, p: [])
    monkeypatch.setattr(
        skill_proposer, "propose_skills_from_text",
        lambda **k: [{"name": "Build a truth table", "bloom_level": "apply", "weight": 1.0}],
    )
    monkeypatch.setattr(skill_proposer.bedrock, "embed", lambda text, **k: [0.0] * 1024)
    monkeypatch.setattr(skill_proposer.db, "rpc", lambda fn, args: [{
        "id": "canon-1", "name": "Construct a truth table", "bloom_level": "apply",
        "blueprint_weight": 1.0, "course_id": "other", "similarity": 0.86,
    }])
    inserted = []
    monkeypatch.setattr(skill_proposer.db, "insert", lambda t, rows: inserted.extend(rows) or rows)

    result = skill_proposer.seed_course_skills(institution_id="i", course_id="c", content_items=items)
    assert result["proposed"] == 1
    assert result["flagged_possible_duplicate"] == 1
    assert inserted[0]["status"] == "proposed"
    assert "possible duplicate" in inserted[0]["proposed_source"]


def test_seed_creates_novel_proposal_when_no_match(monkeypatch):
    items = [
        {"lms_content_id": "mod-1", "title": "Module 1", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l1", "title": "L1", "parent_id": "mod-1", "body_or_description": "sensors"},
    ]
    monkeypatch.setattr(skill_proposer.db, "select", lambda t, p: [])
    monkeypatch.setattr(
        skill_proposer, "propose_skills_from_text",
        lambda **k: [{"name": "Diagnose a sensor fault", "bloom_level": "analyze", "weight": 1.0}],
    )
    monkeypatch.setattr(skill_proposer.bedrock, "embed", lambda text, **k: [0.0] * 1024)
    monkeypatch.setattr(skill_proposer.db, "rpc", lambda fn, args: [])  # no match at all
    inserted = []
    monkeypatch.setattr(skill_proposer.db, "insert", lambda t, rows: inserted.extend(rows) or rows)

    result = skill_proposer.seed_course_skills(institution_id="i", course_id="c", content_items=items)
    assert result["proposed"] == 1
    assert result["flagged_possible_duplicate"] == 0
    assert inserted[0]["status"] == "proposed"
