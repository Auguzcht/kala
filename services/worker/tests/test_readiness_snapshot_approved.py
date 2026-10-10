from app.jobs import readiness_snapshot


def test_snapshot_averages_approved_skills_only(monkeypatch):
    calls = []
    inserted = []
    def fake_select(table, params):
        calls.append((table, params))
        if table == "enrollments":
            return [{"user_id": "student-1", "course_id": "course-1", "institution_id": "inst-1"}]
        if table == "skills":
            return [{"id": "approved", "course_id": "course-1"}]
        if table == "mastery_state":
            return [
                {"user_id": "student-1", "course_id": "course-1", "skill_id": "approved", "estimate": 0.6},
                {"user_id": "student-1", "course_id": "course-1", "skill_id": "rejected", "estimate": 0.0},
            ]
        return []
    monkeypatch.setattr(readiness_snapshot.db, "select", fake_select)
    monkeypatch.setattr(readiness_snapshot.db, "insert", lambda table, rows: inserted.extend(rows))
    assert readiness_snapshot.run() == {"snapshots": 1}
    assert inserted[0]["score"] == 0.6
    assert calls[1][0] == "skills" and calls[1][1]["status"] == "eq.approved"

