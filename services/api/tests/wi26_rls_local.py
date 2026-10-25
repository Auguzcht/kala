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
    migration = ROOT / "packages/db/migrations/0038_recommendation_visibility.sql"
    sql(migration.read_text())
    after = json.loads(sql(policies_query))
    (out / "policies-after.json").write_text(json.dumps(after, indent=2))
    changed = [a["policyname"] for a, b in zip(before, after) if a != b]
    assert len(before) == len(after) and changed == ["recs_insert", "recs_read", "recs_update"], changed
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
    print("Local proof artifacts:", out)


if __name__ == "__main__":
    main()
