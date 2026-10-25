"""Run WI-26 against a fresh, network-disabled Docker Postgres database.

Usage: python3 services/api/tests/wi26_rls_local.py --container kala-wi26-sec-2d3d
No environment files, connection URLs or hosted credentials are used.
"""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import uuid
from pathlib import Path

from wi26_rls_extended import snapshot, verify

ROOT = Path(__file__).resolve().parents[3]
DB = "wi26_synthetic_" + uuid.uuid4().hex[:8]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True)
    args = parser.parse_args()
    assert args.container.startswith("kala-wi26-sec-")
    metadata = json.loads(subprocess.check_output(["docker", "inspect", args.container]))[0]
    assert metadata["HostConfig"]["NetworkMode"] == "none"
    assert not metadata["HostConfig"]["PortBindings"]
    out = Path(tempfile.mkdtemp(prefix="kala-wi26-rls-"))

    def sql(source, database=DB):
        result = subprocess.run(
            ["docker", "exec", "-i", args.container, "psql", "-X", "-U", "supabase_admin",
             "-d", database, "-v", "ON_ERROR_STOP=1", "-Atq"],
            input=source, text=True, capture_output=True, check=True,
        )
        return result.stdout.strip()

    sql(f"create database {DB};", "postgres")
    # Minimal Auth/Storage platform fixture, not application migrations or
    # a claim of full GoTrue/Storage/PostgREST integration.
    sql("""
        create schema auth;
        create schema storage;
        create schema extensions;
        create function auth.jwt() returns jsonb language sql stable as
        $$ select coalesce(nullif(current_setting('request.jwt.claims', true), ''), '{}')::jsonb $$;
        create function auth.uid() returns uuid language sql stable as
        $$ select nullif(auth.jwt()->>'sub', '')::uuid $$;
        grant usage on schema auth, storage to authenticated, anon, service_role;
        create table storage.buckets(id text primary key, name text, public boolean,
                                    file_size_limit bigint, allowed_mime_types text[]);
        create table storage.objects(id uuid primary key, bucket_id text, name text);
        alter table storage.objects enable row level security;
        create function storage.foldername(text) returns text[] language sql immutable as
        $$ select (string_to_array($1, '/'))[1:array_length(string_to_array($1, '/'), 1)-1] $$;
    """)
    migrations = sorted((ROOT / "packages/db/migrations").glob("*.sql"))
    baseline = [p for p in migrations if int(p.name[:4]) <= 37]
    assert len(baseline) == 37
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in baseline}
    for path in baseline:
        sql(path.read_text())
    print("Replay: 0001–0037 passed; " + sql("select version();"))
    (out / "migration-sha256.json").write_text(json.dumps(hashes, indent=2))
    # Synthetic institution/course/identity fixtures, never copied from users.
    sql("""
        insert into public.institutions(id,name,lms_type,lms_issuer,deployment_id)
        values ('10000000-0000-4000-8000-000000000001','Synthetic A','blackboard','https://lms.invalid','fake-a'),
               ('10000000-0000-4000-8000-000000000002','Synthetic B','blackboard','https://lms.invalid','fake-b');
    """)
    # Remaining fixture SQL is built from schema-required fields below.
    fixture = Path(__file__).with_name("wi26_rls_fixture.sql").read_text()
    sql(fixture)
    policies_query = """select jsonb_agg(to_jsonb(p) order by tablename,policyname)
                        from pg_policies p where schemaname='public';"""
    before = json.loads(sql(policies_query))
    (out / "policies-before.json").write_text(json.dumps(before, indent=2))
    schema_before = subprocess.check_output([
        "docker", "exec", args.container, "pg_dump", "-U", "supabase_admin", "-d", DB,
        "--schema-only", "--schema=public", "--no-owner",
    ])
    (out / "schema-before.sql").write_bytes(schema_before)

    def count(user, role, institution=1):
        claims = json.dumps({"sub": f"20000000-0000-4000-8000-{user:012d}",
                             "app_role": role,
                             "institution_id": f"10000000-0000-4000-8000-{institution:012d}"})
        return int(sql(f"""begin; set local role authenticated;
          set local request.jwt.claims = '{claims}';
          select count(*) from public.recommendations; rollback;"""))

    actors = [(1, "student", 1), (2, "instructor", 1), (3, "instructor", 1),
              (4, "admin", 1), (5, "instructor", 2), (6, "admin", 2),
              (2, "student", 1), (2, "instructor", 2)]
    pre_counts = [count(*a) for a in actors]
    assert pre_counts == [5, 5, 0, 5, 0, 0, 5, 5], pre_counts
    table_counts_query = """select jsonb_object_agg(table_name, row_count) from (
      select 'recommendations' table_name, count(*) row_count from public.recommendations
      union all select 'users',count(*) from public.users
      union all select 'enrollments',count(*) from public.enrollments
      union all select 'evidence_events',count(*) from public.evidence_events
      union all select 'mastery_state',count(*) from public.mastery_state
      union all select 'readiness_snapshots',count(*) from public.readiness_snapshots
      union all select 'srs_state',count(*) from public.srs_state
      union all select 'quiz_set_attempts',count(*) from public.quiz_set_attempts
      union all select 'item_exposures',count(*) from public.item_exposures
      union all select 'item_reviews',count(*) from public.item_reviews
      union all select 'lms_identity_aliases',count(*) from public.lms_identity_aliases
      union all select 'courses',count(*) from public.courses
      union all select 'skills',count(*) from public.skills
      union all select 'assessments',count(*) from public.assessments
      union all select 'guided_lessons',count(*) from public.guided_lessons
      union all select 'content_items',count(*) from public.content_items
      union all select 'generated_items',count(*) from public.generated_items
      union all select 'quiz_sets',count(*) from public.quiz_sets
      union all select 'ingest_jobs',count(*) from public.ingest_jobs
    ) counts;"""
    fixture_counts = sql(table_counts_query)
    grants_query = """select jsonb_agg(jsonb_build_object('table',t.tablename,
        'authenticatedSelect',has_table_privilege('authenticated',format('%I.%I',t.schemaname,t.tablename),'SELECT'),
        'rls',c.relrowsecurity) order by t.tablename)
      from pg_tables t join pg_class c on c.oid=format('%I.%I',t.schemaname,t.tablename)::regclass
      where t.schemaname='public';"""
    grant_inventory = sql(grants_query)
    assert all(not row['authenticatedSelect'] or row['rls'] for row in json.loads(grant_inventory))
    (out / 'table-access-before.json').write_text(grant_inventory)
    assert sql("select has_table_privilege('authenticated','public.ingest_jobs','SELECT');") == 'f'
    def remove_learner():
        sql("""delete from public.enrollments
            where user_id='20000000-0000-4000-8000-000000000001'
              and course_id='30000000-0000-4000-8000-000000000001';""")

    def restore_learner():
        sql("""insert into public.enrollments(institution_id,user_id,course_id,role)
          values ('10000000-0000-4000-8000-000000000001',
                  '20000000-0000-4000-8000-000000000001',
                  '30000000-0000-4000-8000-000000000001','student');""")

    remove_learner()
    removed_before = snapshot(sql)
    removed_rec_before = [count(1, 'student'), count(2, 'instructor'), count(4, 'admin')]
    restore_learner()
    extended_before = snapshot(sql)
    (out / "extended-before.json").write_text(json.dumps(extended_before, indent=2))
    migration = ROOT / "packages/db/migrations/0038_recommendation_visibility.sql"
    sql(migration.read_text())
    after = json.loads(sql(policies_query))
    (out / "policies-after.json").write_text(json.dumps(after, indent=2))
    changed = [a["policyname"] for a, b in zip(before, after) if a != b]
    expected_changes = {"recs_insert", "recs_read", "recs_update", "enroll_read", "evidence_read", "mastery_read", "readiness_read", "srs_read", "quiz_set_attempts_read", "item_exposures_read", "item_reviews_read", "users_read", "lms_identity_aliases_read", "courses_read", "skills_read", "assess_read", "lessons_read", "content_read", "items_read", "quiz_sets_read", "ingest_jobs_read", "profiles_read"}
    assert len(before) == len(after) and set(changed) == expected_changes, changed
    extended_after = snapshot(sql)
    (out / "extended-after.json").write_text(json.dumps(extended_after, indent=2))
    verify(extended_before, extended_after)
    assert sql(table_counts_query) == fixture_counts
    assert sql(grants_query) == grant_inventory
    (out / 'table-access-after.json').write_text(sql(grants_query))
    assert sql("select has_table_privilege('authenticated','public.ingest_jobs','SELECT');") == 'f'
    remove_learner()
    removed_after = snapshot(sql)
    removed_rec_after = [count(1, 'student'), count(2, 'instructor'), count(4, 'admin')]
    assert removed_rec_before == [5, 5, 5] and removed_rec_after == [3, 0, 0]
    for table in ['evidence_events', 'mastery_state', 'readiness_snapshots', 'srs_state',
                  'quiz_set_attempts', 'item_exposures', 'item_reviews', 'users', 'aliases']:
        assert removed_after['owner'][table] == removed_before['owner'][table] == 1
        for actor in ['teacher', 'admin']:
            assert removed_before[actor][table] == 1 and removed_after[actor][table] == 0, (actor, table)
    for actor in [(2, 'instructor'), (4, 'admin')]:
        user, role = actor
        claims = json.dumps({'sub': f'20000000-0000-4000-8000-{user:012d}',
                             'app_role': role, 'institution_id': '10000000-0000-4000-8000-000000000001'})
        assert sql(f"""begin; set local role authenticated; set local request.jwt.claims='{claims}';
          with changed as (update public.recommendations set instructor_note='synthetic'
                           returning id) select count(*) from changed; rollback;""") == '0'
        try:
            sql(f"""begin; set local role authenticated; set local request.jwt.claims='{claims}';
              insert into public.recommendations(institution_id,user_id,course_id,action)
              values ('10000000-0000-4000-8000-000000000001',
                      '20000000-0000-4000-8000-000000000001',
                      '30000000-0000-4000-8000-000000000001','practice'); rollback;""")
        except subprocess.CalledProcessError as exc:
            assert 'row-level security' in exc.stderr
        else:
            raise AssertionError('staff inserted a recommendation for a removed learner')
    assert removed_before['admin']['profile'] == 1 and removed_after['admin']['profile'] == 0
    assert removed_after['owner']['profile'] == 1
    restore_learner()
    (out / 'removed-learner.json').write_text(json.dumps({
        'before': removed_before, 'after': removed_after,
        'recommendationsBefore': removed_rec_before, 'recommendationsAfter': removed_rec_after,
    }, indent=2))
    print('Removed learner: teacher/admin reads and recommendation writes denied; own history retained')
    post_counts = [count(*a) for a in actors]
    assert post_counts == [3, 5, 0, 5, 0, 0, 0, 0], post_counts
    # No policy allows more rows for any tested actor.
    assert all(a <= b for a, b in zip(post_counts, pre_counts))
    for user, role, inst in actors:
        claims = json.dumps({"sub": f"20000000-0000-4000-8000-{user:012d}", "app_role": role,
                             "institution_id": f"10000000-0000-4000-8000-{inst:012d}"})
        affected = int(sql(f"""begin; set local role authenticated;
          set local request.jwt.claims = '{claims}';
          with changed as (update public.recommendations set instructor_note='synthetic'
                           returning id) select count(*) from changed; rollback;"""))
        assert affected == (5 if user in (2, 4) and role in ('instructor', 'admin') and inst == 1 else 0)
    for user, role, inst in actors:
        claims = json.dumps({"sub": f"20000000-0000-4000-8000-{user:012d}", "app_role": role,
                             "institution_id": f"10000000-0000-4000-8000-{inst:012d}"})
        statement = f"""begin; set local role authenticated;
          set local request.jwt.claims = '{claims}';
          insert into public.recommendations(institution_id,user_id,course_id,action)
          values ('10000000-0000-4000-8000-000000000001',
                  '20000000-0000-4000-8000-000000000001',
                  '30000000-0000-4000-8000-000000000001','practice'); rollback;"""
        allowed = user in (2, 4) and role in ('instructor', 'admin') and inst == 1
        try:
            sql(statement)
        except subprocess.CalledProcessError as exc:
            assert not allowed and 'row-level security' in exc.stderr
        else:
            assert allowed
    assert sql("select count(*) from public.recommendations;") == "5"
    assert hashes == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in baseline}
    schema_after = subprocess.check_output([
        "docker", "exec", args.container, "pg_dump", "-U", "supabase_admin", "-d", DB,
        "--schema-only", "--schema=public", "--no-owner",
    ])
    (out / "schema-after.sql").write_bytes(schema_after)
    def without_policies(dump):
        text = dump.decode()
        text = re.sub(r"^\\(?:un)?restrict .*\n", "", text, flags=re.MULTILINE)
        return re.sub(r"CREATE POLICY .*?;", "", text, flags=re.DOTALL)
    assert without_policies(schema_before) == without_policies(schema_after), "non-policy schema/grant change"
    (out / "counts.json").write_text(json.dumps({"before": pre_counts, "after": post_counts}))
    print("RLS read/update/insert actor matrix passed; policy-only schema/grant diff; 5 rows preserved; historical checksums unchanged")
    sql("""delete from public.enrollments
        where user_id='20000000-0000-4000-8000-000000000002'
          and course_id='30000000-0000-4000-8000-000000000001';""")
    revoked = snapshot(sql)
    for key in ["enrollments", "evidence_events", "mastery_state", "readiness_snapshots",
                "srs_state", "quiz_set_attempts", "item_exposures", "item_reviews",
                "users", "aliases", "courses:1", "skills:1", "assessments:1",
                "guided_lessons:1", "content_items:1", "generated_items:1", "quiz_sets:1",
                "ingest_jobs:1", "lesson-steps:1", "set-items:1"]:
        assert revoked['teacher'][key] == 0, key
    assert count(2, 'instructor', 1) == 0
    print("Removed instructor enrollment: 20 read boundaries and recommendations denied")
    print("Local proof artifacts:", out)


if __name__ == "__main__":
    main()
