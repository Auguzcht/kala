from app.learn import lessons


def test_lesson_check_read_filters_retired_and_rejected_skill_items(monkeypatch):
    query = {}

    def select(table, params):
        if table == "guided_lesson_steps":
            return [{"id": "step-1", "position": 0, "summary": "step",
                     "detail_points": [], "check_item_id": "retired-1"}]
        if table == "courses":
            return [{"bank_serving": False}]
        if table == "generated_items":
            query.update(params)
            return []
        return []

    monkeypatch.setattr(lessons.db, "select", select)
    lesson = lessons._assemble_lesson(
        lesson_row={"id": "lesson-1", "course_id": "course-1", "skill_id": "skill-1",
                    "title": "Lesson", "status": "ready"},
        institution_id="institution-1",
    )
    assert lesson["steps"][0]["check"] is None
    assert query["retired_at"] == "is.null"
    assert query["skills.status"] == "eq.approved"
