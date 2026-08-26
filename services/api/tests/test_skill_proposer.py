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


def test_seed_skips_when_course_already_has_skills(monkeypatch):
    """Idempotency: a re-launch of a course that already has skills does not
    re-propose (no duplicate work, no LLM call)."""
    monkeypatch.setattr(skill_proposer.db, "select", lambda t, p: [{"id": "existing"}])
    called = {"proposed": False}
    monkeypatch.setattr(
        skill_proposer, "propose_skills_from_text",
        lambda **k: called.__setitem__("proposed", True) or [],
    )
    result = skill_proposer.seed_course_skills(
        institution_id="i", course_id="c", course_content="...",
    )
    assert result["skipped"] is True
    assert called["proposed"] is False


def test_seed_auto_approves_on_strong_match(monkeypatch):
    """A proposal that strongly matches an already-approved skill in another
    course is reused verbatim and written straight to 'approved', no review."""
    monkeypatch.setattr(skill_proposer.db, "select", lambda t, p: [])  # no existing
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

    result = skill_proposer.seed_course_skills(
        institution_id="i", course_id="c", course_content="...",
    )
    assert result["auto_approved"] == 1
    assert result["proposed"] == 0
    assert inserted[0]["status"] == "approved"
    assert inserted[0]["canonical_skill_id"] == "canon-1"


def test_seed_flags_possible_duplicate_in_review_band(monkeypatch):
    """A proposal in the middle similarity band is staged as 'proposed' with a
    duplicate hint, so a human decides, never silently merged or split."""
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

    result = skill_proposer.seed_course_skills(
        institution_id="i", course_id="c", course_content="...",
    )
    assert result["proposed"] == 1
    assert result["flagged_possible_duplicate"] == 1
    assert inserted[0]["status"] == "proposed"
    assert "possible duplicate" in inserted[0]["proposed_source"]


def test_seed_creates_novel_proposal_when_no_match(monkeypatch):
    monkeypatch.setattr(skill_proposer.db, "select", lambda t, p: [])
    monkeypatch.setattr(
        skill_proposer, "propose_skills_from_text",
        lambda **k: [{"name": "Diagnose a sensor fault", "bloom_level": "analyze", "weight": 1.0}],
    )
    monkeypatch.setattr(skill_proposer.bedrock, "embed", lambda text, **k: [0.0] * 1024)
    monkeypatch.setattr(skill_proposer.db, "rpc", lambda fn, args: [])  # no match at all
    inserted = []
    monkeypatch.setattr(skill_proposer.db, "insert", lambda t, rows: inserted.extend(rows) or rows)

    result = skill_proposer.seed_course_skills(
        institution_id="i", course_id="c", course_content="...",
    )
    assert result["proposed"] == 1
    assert result["flagged_possible_duplicate"] == 0
    assert inserted[0]["status"] == "proposed"
