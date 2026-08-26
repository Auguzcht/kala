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


def test_seed_skips_only_modules_that_already_have_skills(monkeypatch):
    """Incremental: a module that already has skills is skipped; a module
    that doesn't is processed. This is the core of the refresh-button
    behavior, safe to re-run, only does new work."""
    items = [
        {"lms_content_id": "mod-1", "title": "Module 1", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l1", "title": "L1", "parent_id": "mod-1", "body_or_description": "module one text"},
        {"lms_content_id": "mod-2", "title": "Module 2", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l2", "title": "L2", "parent_id": "mod-2", "body_or_description": "module two text"},
        {"lms_content_id": "mod-3", "title": "Module 3", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l3", "title": "L3", "parent_id": "mod-3", "body_or_description": "module three text"},
    ]
    # Module 1 already has skills (e.g. from a first partial run); Modules 2/3 don't.
    monkeypatch.setattr(
        skill_proposer.db, "select",
        lambda t, p: [{"module_ref": "Module 1"}],
    )
    monkeypatch.setattr(skill_proposer.db, "rpc", lambda fn, args: [])
    monkeypatch.setattr(skill_proposer.db, "insert", lambda t, rows: rows)
    monkeypatch.setattr(skill_proposer.bedrock, "embed", lambda text, **k: [0.0] * 1024)

    seen = []

    def fake_propose(*, course_content):
        seen.append(course_content)
        return [{"name": f"Skill from {course_content}", "bloom_level": "apply", "weight": 1.0}]

    monkeypatch.setattr(skill_proposer, "propose_skills_from_text", fake_propose)

    result = skill_proposer.seed_course_skills(
        institution_id="i", course_id="c", content_items=items,
    )
    assert result["modulesProcessed"] == 2
    assert result["modulesSkipped"] == 1
    # Module 1 was never sent to the model; Modules 2 and 3 were.
    assert sorted(seen) == ["module three text", "module two text"]


def test_seed_is_a_noop_when_all_modules_already_done(monkeypatch):
    """Re-running once every module is covered does nothing, and reports it
    cleanly rather than erroring. This is the 'instructor hits refresh again,
    nothing new' case."""
    items = [
        {"lms_content_id": "mod-1", "title": "Module 1", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l1", "title": "L1", "parent_id": "mod-1", "body_or_description": "module one text"},
    ]
    monkeypatch.setattr(skill_proposer.db, "select", lambda t, p: [{"module_ref": "Module 1"}])
    called = {"proposed": False}
    monkeypatch.setattr(
        skill_proposer, "propose_skills_from_text",
        lambda **k: called.__setitem__("proposed", True) or [],
    )
    result = skill_proposer.seed_course_skills(
        institution_id="i", course_id="c", content_items=items,
    )
    assert result["skipped"] is True
    assert result["modulesProcessed"] == 0
    assert result["modulesSkipped"] == 1
    assert called["proposed"] is False  # no model call at all


def test_seed_treats_root_content_as_its_own_trackable_module(monkeypatch):
    """Course-root content (module_ref None) is proposed once then skipped,
    not re-run on every refresh."""
    items = [
        {"lms_content_id": "syllabus", "title": "Syllabus", "parent_id": None, "body_or_description": "syllabus text"},
    ]
    # None already recorded as done.
    monkeypatch.setattr(skill_proposer.db, "select", lambda t, p: [{"module_ref": None}])
    called = {"proposed": False}
    monkeypatch.setattr(
        skill_proposer, "propose_skills_from_text",
        lambda **k: called.__setitem__("proposed", True) or [],
    )
    result = skill_proposer.seed_course_skills(
        institution_id="i", course_id="c", content_items=items,
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


def test_seed_continues_past_a_failed_insert(monkeypatch):
    """A single failed skill insert (e.g. a timeout on a heavy vector write)
    must not abort the run and discard already-processed modules. Found
    live: one 500 in the middle of the module loop lost every module that
    had already succeeded. The run now logs, counts insertFailed, and
    continues, so a refresh only ever re-does the failed skill, not the
    whole course."""
    items = [
        {"lms_content_id": "mod-1", "title": "Module 1", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l1", "title": "L1", "parent_id": "mod-1", "body_or_description": "sensors"},
        {"lms_content_id": "mod-2", "title": "Module 2", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l2", "title": "L2", "parent_id": "mod-2", "body_or_description": "actuators"},
    ]
    monkeypatch.setattr(skill_proposer.db, "select", lambda t, p: [])
    monkeypatch.setattr(
        skill_proposer, "propose_skills_from_text",
        lambda **k: [{"name": "Skill X", "bloom_level": "apply", "weight": 1.0}],
    )
    monkeypatch.setattr(skill_proposer.bedrock, "embed", lambda text, **k: [0.0] * 1024)
    monkeypatch.setattr(skill_proposer.db, "rpc", lambda fn, args: [])  # no match at all

    calls = {"n": 0, "failed_once": False}

    def flaky_insert(table, rows):
        if not calls["failed_once"]:  # first write fails, the rest land
            calls["failed_once"] = True
            raise TimeoutError("vector insert timed out")
        calls["n"] += 1
        return rows

    monkeypatch.setattr(skill_proposer.db, "insert", flaky_insert)

    result = skill_proposer.seed_course_skills(institution_id="i", course_id="c", content_items=items)
    assert result["modulesProcessed"] == 2  # both modules were processed
    assert result["insertFailed"] == 1     # the one failed write is counted, not fatal
    assert result["proposed"] == 1         # the second skill landed


def test_flag_in_batch_duplicates_annotates_both_sides_of_a_near_pair():
    """Two proposals with near-identical embeddings both get a dup note
    pointing at each other; a distinct third is left alone."""
    items = [
        {"name": "Convert numbers between bases", "embedding": [1.0, 0.0, 0.0], "dup_note": None},
        {"name": "Apply number system conversions", "embedding": [0.99, 0.01, 0.0], "dup_note": None},
        {"name": "Diagnose a sensor fault", "embedding": [0.0, 0.0, 1.0], "dup_note": None},
    ]
    n = skill_proposer._flag_in_batch_duplicates(items)
    assert n == 2  # the pair, not the loner
    assert "Apply number system conversions" in items[0]["dup_note"]
    assert "Convert numbers between bases" in items[1]["dup_note"]
    assert items[2]["dup_note"] is None


def test_flag_in_batch_duplicates_never_collapses_only_annotates():
    """Design guarantee: the flagger only writes notes, it never removes or
    merges an item. Both survive for the human to decide."""
    items = [
        {"name": "A", "embedding": [1.0, 0.0], "dup_note": None},
        {"name": "A prime", "embedding": [1.0, 0.001], "dup_note": None},
    ]
    skill_proposer._flag_in_batch_duplicates(items)
    assert len(items) == 2  # nothing dropped


def test_seed_flags_in_batch_duplicates_and_keeps_both(monkeypatch):
    """End to end: a module producing two near-duplicate proposals stages
    BOTH as 'proposed', each carrying an in-batch dup note, never one
    silently collapsed. This is the exact case seen live (two number-system
    skills from one run)."""
    items = [
        {"lms_content_id": "mod-1", "title": "Module 1", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l1", "title": "L1", "parent_id": "mod-1", "body_or_description": "number systems"},
    ]
    monkeypatch.setattr(skill_proposer.db, "select", lambda t, p: [])
    monkeypatch.setattr(skill_proposer.db, "rpc", lambda fn, args: [])  # no cross-course match
    # Two near-duplicate proposals; identical embedding forces a dup flag.
    monkeypatch.setattr(
        skill_proposer, "propose_skills_from_text",
        lambda **k: [
            {"name": "Convert numbers between bases", "bloom_level": "apply", "weight": 2.0},
            {"name": "Apply number system conversions", "bloom_level": "apply", "weight": 1.2},
        ],
    )
    monkeypatch.setattr(skill_proposer.bedrock, "embed", lambda text, **k: [1.0, 0.0, 0.0])
    inserted = []
    monkeypatch.setattr(skill_proposer.db, "insert", lambda t, rows: inserted.extend(rows) or rows)

    result = skill_proposer.seed_course_skills(
        institution_id="i", course_id="c", content_items=items,
    )
    assert result["proposed"] == 2  # both kept, neither collapsed
    assert result["flagged_in_batch_duplicate"] == 2
    assert all(r["status"] == "proposed" for r in inserted)
    assert all("this batch" in r["proposed_source"] for r in inserted)


def test_seed_cross_course_automatch_still_auto_approves(monkeypatch):
    """The in-batch work must not change cross-course behavior: a proposal
    that strongly matches an APPROVED skill elsewhere still auto-approves,
    now with an auditable proposed_source noting what it matched."""
    items = [
        {"lms_content_id": "mod-1", "title": "Module 1", "parent_id": None, "body_or_description": ""},
        {"lms_content_id": "l1", "title": "L1", "parent_id": "mod-1", "body_or_description": "truth tables"},
    ]
    monkeypatch.setattr(skill_proposer.db, "select", lambda t, p: [])
    monkeypatch.setattr(
        skill_proposer, "propose_skills_from_text",
        lambda **k: [{"name": "Construct a truth table", "bloom_level": "apply", "weight": 1.0}],
    )
    monkeypatch.setattr(skill_proposer.bedrock, "embed", lambda text, **k: [0.0] * 3)
    monkeypatch.setattr(skill_proposer.db, "rpc", lambda fn, args: [{
        "id": "canon-1", "name": "Construct a truth table", "bloom_level": "apply",
        "blueprint_weight": 1.0, "course_id": "other", "similarity": 0.97,
    }])
    inserted = []
    monkeypatch.setattr(skill_proposer.db, "insert", lambda t, rows: inserted.extend(rows) or rows)

    result = skill_proposer.seed_course_skills(
        institution_id="i", course_id="c", content_items=items,
    )
    assert result["auto_approved"] == 1
    assert inserted[0]["status"] == "approved"
    assert inserted[0]["canonical_skill_id"] == "canon-1"
    assert "auto-matched" in inserted[0]["proposed_source"]  # auditable
