from app.lms.hierarchy import build_folder_paths, module_ref_for


def test_top_level_content_has_no_module():
    """Content with no parent folder at all (a school that doesn't use
    folders, or a course-root item) gets an empty path, not an error."""
    items = [{"lms_content_id": "syllabus", "title": "Syllabus", "parent_id": None}]
    paths = build_folder_paths(items)
    assert paths["syllabus"] == []
    assert module_ref_for(paths["syllabus"]) is None


def test_single_level_module_convention():
    """MMCM-style: one folder level, "Module N", directly containing items."""
    items = [
        {"lms_content_id": "mod-1", "title": "Module 1 | AWS Prototype Building", "parent_id": None},
        {"lms_content_id": "item-1", "title": "M1|FA1", "parent_id": "mod-1"},
    ]
    paths = build_folder_paths(items)
    assert paths["item-1"] == [{"lmsRef": "mod-1", "title": "Module 1 | AWS Prototype Building"}]
    assert module_ref_for(paths["item-1"]) == "Module 1 | AWS Prototype Building"


def test_arbitrary_deeper_nesting_from_a_different_school_convention():
    """A school that nests Module -> Week -> Lesson (three levels) works the
    same way, with no code change, only the data shape differs. module_ref
    still resolves to the top-level ancestor; the full chain is available
    via folder_path for anything that needs a different depth."""
    items = [
        {"lms_content_id": "mod-2", "title": "Module 2", "parent_id": None},
        {"lms_content_id": "week-3", "title": "Week 3", "parent_id": "mod-2"},
        {"lms_content_id": "lesson-a", "title": "Lesson A", "parent_id": "week-3"},
    ]
    paths = build_folder_paths(items)
    assert paths["lesson-a"] == [
        {"lmsRef": "mod-2", "title": "Module 2"},
        {"lmsRef": "week-3", "title": "Week 3"},
    ]
    assert module_ref_for(paths["lesson-a"]) == "Module 2"


def test_dangling_parent_id_does_not_crash():
    """A parent_id that doesn't resolve to any item in this batch (partial
    fetch, deleted folder, etc.) degrades to "no ancestors" instead of
    raising, so one bad reference can't fail an entire course's ingest."""
    items = [{"lms_content_id": "orphan", "title": "Orphan", "parent_id": "missing-parent"}]
    paths = build_folder_paths(items)
    assert paths["orphan"] == []


def test_cyclical_parent_chain_does_not_infinite_loop():
    """Defensive: a malformed or cyclical parent chain terminates instead of
    recursing forever."""
    items = [
        {"lms_content_id": "a", "title": "A", "parent_id": "b"},
        {"lms_content_id": "b", "title": "B", "parent_id": "a"},
    ]
    paths = build_folder_paths(items)
    assert isinstance(paths["a"], list)
    assert isinstance(paths["b"], list)
