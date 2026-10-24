"""AUTH-REQ-006 disposable-local persistence check; never a data repair tool.

Run with PYTHONPATH=. uv run python tests/identity_lane_i_postgrest.py.
Requires Docker and the two cached Supabase images named below. Creates only
its own disposable containers, binds PostgREST to loopback and removes both on
exit. No application credentials or dotenv are read. This is a focused fixture
using committed table definitions, not a full migration/RLS replay.
"""
import os
import re
import subprocess
import time
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

os.environ["PYTHON_DOTENV_DISABLED"] = "1"

import httpx

from app.db import supabase as db
from app.lti.routes import _sync_roster


def run():
    # Fixture-only transport: local PostgREST's anonymous role owns this isolated
    # schema. Production _client/config/auth are never invoked or changed.
    db._client = lambda **_: httpx.Client(base_url="http://127.0.0.1:55436", timeout=10)
    created = db.insert("institutions", [
        {"name": "Synthetic tenant A", "lms_type": "blackboard", "lms_issuer": "https://a.example.test", "deployment_id": "identity-fixture-a"},
        {"name": "Synthetic tenant B", "lms_type": "blackboard", "lms_issuer": "https://b.example.test", "deployment_id": "identity-fixture-b"},
    ])
    tenant, other_tenant = (row["id"] for row in created)
    course, other_course = (row["id"] for row in db.insert("courses", [
        {"institution_id": tenant, "lms_course_id": "fixture-course", "title": "Synthetic course"},
        {"institution_id": other_tenant, "lms_course_id": "fixture-course", "title": "Synthetic course"},
    ]))

    def resolve(subject, institution=tenant, role="student"):
        return db.resolve_user(institution_id=institution, lms_user_id=subject, role=role,
                               display_name="Same synthetic name", email="shared@example.test")

    def enroll(user, institution=tenant, target_course=course, role="student"):
        db.upsert_enrollment(institution_id=institution, user_id=user["id"], course_id=target_course, role=role)

    def member(subject, role="Student"):
        return {"lms_user_id": subject, "role": role, "name": "Same synthetic name", "email": "shared@example.test"}

    def sync(members=None, failure=False):
        def pull(_):
            if failure:
                raise RuntimeError("synthetic private exception")
            return members
        return _sync_roster(institution_id=tenant, course_id=course, course_ref="fixture-course",
                            connector=SimpleNamespace(get_roster=pull))

    first = resolve("subject-first")
    enroll(first)
    legacy = resolve("legacy-rest-id")
    enroll(legacy)
    departed = resolve("departed-instructor", role="instructor")
    enroll(departed, role="instructor")
    isolated = resolve("subject-first", other_tenant)
    enroll(isolated, other_tenant, other_course, "instructor")
    db.insert("evidence_events", [
        {"institution_id": tenant, "course_id": course, "user_id": user["id"], "type": "practice", "correct": True}
        for user in (first, legacy, departed)
    ])
    before = deepcopy(db.select("evidence_events", {"select": "*", "order": "id.asc"}))
    initial = db.select("enrollments", {"select": "*", "order": "user_id.asc"})
    assert sync(failure=True)["removed"] == 0
    assert sync([])["removed"] == 0
    assert sync([member(None)])["removed"] == 0
    assert db.select("enrollments", {"select": "*", "order": "user_id.asc"}) == initial
    assert sync([member("subject-first"), member("subject-second")]) == {"enrolled": 2, "removed": 2}
    second = resolve("subject-second")
    assert first["id"] != second["id"]
    for _ in range(2):
        assert sync([member("subject-first"), member("subject-second")]) == {"enrolled": 2, "removed": 0}
        assert resolve("subject-first")["id"] == first["id"]
        enroll(first)
    assert len(db.select("users", {"select": "id"})) == 5
    remaining = db.select("enrollments", {"select": "*"})
    assert {row["user_id"] for row in remaining} == {first["id"], second["id"], isolated["id"]}
    assert db.select("evidence_events", {"select": "*", "order": "id.asc"}) == before
    assert resolve("subject-first", other_tenant)["id"] == isolated["id"]
    print("PASS: local Postgres/PostgREST exact identity, both orders, repeat/return, shared name/email, tenant isolation, guarded removals, legacy/instructor removal, unchanged evidence")


def local_fixture():
    postgres = "kala-identity-lane-i-pg"
    rest = "kala-identity-lane-i-rest"
    created = []

    def docker(*args, **kwargs):
        return subprocess.run(["docker", *args], check=True, capture_output=True, text=True, **kwargs)

    try:
        docker("run", "--detach", "--pull=never", "--name", postgres,
               "--publish", "127.0.0.1:55436:3000", "--env", "POSTGRES_HOST_AUTH_METHOD=trust",
               "public.ecr.aws/supabase/postgres:17.6.1.158")
        created.append(postgres)
        for _ in range(100):
            ready = subprocess.run(["docker", "exec", postgres, "pg_isready"], capture_output=True, check=False)
            if ready.returncode == 0:
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("local Postgres fixture did not become ready")

        repo = Path(__file__).resolve().parents[3]
        original = (repo / "packages/db/migrations/0001_init.sql").read_text()
        aliases = (repo / "packages/db/migrations/0015_lms_identity_aliases.sql").read_text()
        statements = ["create schema identity_lane_i;"]
        for name in ("institutions", "users", "user_profiles", "courses", "enrollments", "skills", "evidence_events", "lms_identity_aliases"):
            source = aliases if name == "lms_identity_aliases" else original
            match = re.search(r"create table public\." + name + r" \(.*?\n\);", source, re.DOTALL)
            assert match is not None
            statements.append(match.group().replace("public.", "identity_lane_i."))
        docker("exec", "-i", postgres, "psql", "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1",
               input="\n".join(statements))
        docker("run", "--detach", "--pull=never", "--name", rest, "--network", "container:" + postgres,
               "--env", "PGRST_DB_URI=postgres://postgres@127.0.0.1:5432/postgres",
               "--env", "PGRST_DB_SCHEMAS=identity_lane_i", "--env", "PGRST_DB_ANON_ROLE=postgres",
               "public.ecr.aws/supabase/postgrest:v14.15")
        created.append(rest)
        for _ in range(100):
            try:
                ready = httpx.get("http://127.0.0.1:55436", timeout=0.5)
                if ready.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        else:
            raise RuntimeError("local PostgREST fixture did not become ready")
        run()
    finally:
        for container in reversed(created):
            docker("rm", "--force", container)


if __name__ == "__main__":
    local_fixture()
