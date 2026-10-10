from app.twin import cohort


def test_cohort_stats_limits_mastery_aggregates_to_approved_skills(monkeypatch):
    approved = "skill-approved"
    rejected = "skill-rejected"
    mastery_query = []

    def fake_select(table, params):
        if table == "enrollments":
            return [{"user_id": "student-1"}]
        if table == "users":
            return [{"id": "student-1"}]
        if table == "skills":
            return [{"id": approved, "name": "Approved", "bloom_level": "apply"}]
        if table == "mastery_state":
            mastery_query.append(params)
            assert params["skill_id"] == f"in.({approved})"
            # The live PostgREST filter excludes the rejected row.
            return [{"user_id": "student-1", "skill_id": approved,
                     "estimate": 0.6, "attempts": 2, "last_seen": None}]
        return []

    monkeypatch.setattr(cohort.db, "select", fake_select)
    result = cohort.stats(institution_id="inst", course_id="course")
    assert result["cohortReadiness"] == 0.6
    assert result["bandDistribution"] == [
        {"band": "no-evidence", "count": 0},
        {"band": "developing", "count": 0},
        {"band": "proficient", "count": 1},
        {"band": "mastered", "count": 0},
    ]
    assert result["skillsCovered"] == 1
    assert mastery_query
