"""Synthetic before/after actor matrix for the extended WI-26 policy scope."""
import json

ACTORS = {
    "owner": (1, "student", 1),
    "other-student": (7, "student", 1),
    "teacher": (2, "instructor", 1),
    "other-teacher": (3, "instructor", 1),
    "admin": (4, "admin", 1),
    "foreign-teacher": (5, "instructor", 2),
    "foreign-admin": (6, "admin", 2),
    "stale-role": (2, "student", 1),
    "wrong-institution": (2, "instructor", 2),
    "granted-researcher": (99, "researcher", 2),
}
PERSONAL = ["enrollments", "evidence_events", "mastery_state", "readiness_snapshots",
            "srs_state", "quiz_set_attempts", "item_exposures", "item_reviews"]
SHARED = ["courses", "skills", "assessments", "guided_lessons"]
STAFF_ONLY = ["content_items", "generated_items", "quiz_sets", "ingest_jobs"]


def snapshot(sql):
    queries = {}
    for table in PERSONAL:
        queries[table] = f"select count(*) from public.{table} where course_id='30000000-0000-4000-8000-000000000001' and user_id='20000000-0000-4000-8000-000000000001'"
    for table in SHARED + STAFF_ONLY:
        column = "id" if table == "courses" else "course_id"
        for course in (1, 2):
            queries[f"{table}:{course}"] = f"select count(*) from public.{table} where {column}='30000000-0000-4000-8000-{course:012d}'"
    queries["users"] = "select count(*) from public.users where id='20000000-0000-4000-8000-000000000001'"
    queries["aliases"] = "select count(*) from public.lms_identity_aliases where user_id='20000000-0000-4000-8000-000000000001'"
    queries["profile"] = "select count(*) from public.user_profiles where user_id='20000000-0000-4000-8000-000000000001'"
    queries["admin-staff-profile"] = "select count(*) from public.user_profiles where user_id='20000000-0000-4000-8000-000000000004'"
    queries["self-identity"] = "select count(*) from public.users where id=auth.uid()"
    for course in (1, 2):
        queries[f"lesson-steps:{course}"] = f"select count(*) from public.guided_lesson_steps where lesson_id='70000000-0000-4000-8000-{course:012d}'"
        queries[f"set-items:{course}"] = f"select count(*) from public.quiz_set_items where set_id='60000000-0000-4000-8000-{course:012d}'"
    for table in ("research_mastery_anon", "research_evidence_anon"):
        queries[table] = f"select count(*) from public.{table} where course_id='30000000-0000-4000-8000-000000000001'"
    result = {}
    for label, (user, role, institution) in ACTORS.items():
        claims = json.dumps({"sub": f"20000000-0000-4000-8000-{user:012d}", "app_role": role,
                             "institution_id": f"10000000-0000-4000-8000-{institution:012d}"})
        counts = sql(f"begin; grant select on public.ingest_jobs to authenticated; set local role authenticated; set local request.jwt.claims='{claims}';"
                     + ";".join(queries.values()) + ";rollback;")
        result[label] = dict(zip(queries, map(int, counts.splitlines()), strict=True))
    return result


def verify(before, after):
    # Every sampled audience narrows or stays equal; no table-level grant changes.
    for actor in ACTORS:
        for key in before[actor]:
            assert after[actor][key] <= before[actor][key], (actor, key, before[actor], after[actor])
    for table in PERSONAL + ["users", "aliases"]:
        for actor in ACTORS:
            expected = int(actor in {"owner", "teacher", "admin"})
            assert after[actor][table] == expected, (actor, table, after[actor][table])
    for table in SHARED:
        for course in (1, 2):
            key = f"{table}:{course}"
            for actor in ACTORS:
                expected = int(actor in {"owner", "other-student", "stale-role", "admin"}
                               or actor == ("teacher" if course == 1 else "other-teacher")
                               or actor == "granted-researcher" and table == "courses")
                assert after[actor][key] == expected, (actor, key, after[actor][key])
    for course in (1, 2):
        for actor in ACTORS:
            expected = int(actor == "admin" or actor == ("teacher" if course == 1 else "other-teacher"))
            for table in STAFF_ONLY + ["set-items"]:
                assert after[actor][f"{table}:{course}"] == expected, (actor, table, course)
            # Child lesson policies inherit the parent's narrowed staff audience.
            assert after[actor][f"lesson-steps:{course}"] == after[actor][f"guided_lessons:{course}"]
    for table in ("research_mastery_anon", "research_evidence_anon"):
        assert before["granted-researcher"][table] == after["granted-researcher"][table] == 1
    for actor in ACTORS:
        assert after[actor]["profile"] == int(actor in {"owner", "admin"})
        assert before[actor]["admin-staff-profile"] == after[actor]["admin-staff-profile"]
        assert before[actor]["self-identity"] == after[actor]["self-identity"]
    # Concrete former counterexamples, demonstrated rather than inferred.
    for table in PERSONAL:
        if table != "srs_state":
            assert before["stale-role"][table] == 1 and after["stale-role"][table] == 0
            assert before["wrong-institution"][table] == 1 and after["wrong-institution"][table] == 0
    for table in ["srs_state", "users", "aliases"]:
        assert before["other-teacher"][table] == 1 and after["other-teacher"][table] == 0
    for table in SHARED:
        assert before["other-teacher"][f"{table}:1"] == 1 and after["other-teacher"][f"{table}:1"] == 0
    print("Extended RLS: 10 authenticated actors ×", len(after["owner"]), "read boundaries passed")
