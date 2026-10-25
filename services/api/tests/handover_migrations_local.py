"""Optional coordinator proof of 0038 + 0039 together; Docker/synthetic only.

From services/api: uv run python tests/handover_migrations_local.py
Reuses the committed SEC replay/RLS verifier and H's runbook/query fixture.
Never loads application configuration, dotenv, URLs or hosted credentials.
"""
from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
IMAGE = "public.ecr.aws/supabase/postgres:17.6.1.158"


def main():
    container = "kala-wi26-sec-integrated-" + uuid.uuid4().hex[:10]
    env = {"PATH": os.environ["PATH"], "PYTHON_DOTENV_DISABLED": "1"}
    created = False

    def docker(*args, source=None):
        result = subprocess.run(
            ["docker", *args], input=source, text=True, capture_output=True,
            env=env, timeout=60, check=False,
        )
        if result.returncode:
            raise RuntimeError("local integration command failed; raw output suppressed")
        return result.stdout.strip()

    try:
        docker("run", "--detach", "--pull=never", "--network", "none",
               "--name", container, "--env", "POSTGRES_HOST_AUTH_METHOD=trust", IMAGE)
        created = True
        for _ in range(150):
            if docker("inspect", "--format", "{{.State.Health.Status}}", container) == "healthy":
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("local integration image health timeout")

        # The SEC verifier checks network=none/no published ports itself.
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        proof = runpy.run_path(str(Path(__file__).with_name("wi26_rls_local.py")))
        sys.argv = ["wi26_rls_local.py", "--container", container]
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            proof["main"]()
        assert "policy-only schema/grant diff" in captured.getvalue()
        print("PASS 0001–0037 replay + 0038; authenticated RLS and removed-member proofs")

        def sql(source):
            return docker("exec", "-i", container, "psql", "-X", "-U", "supabase_admin",
                          "-d", proof["DB"], "-v", "ON_ERROR_STOP=1", "-Atq", source=source)

        policies = "select coalesce(jsonb_agg(to_jsonb(p) order by tablename,policyname),'[]') from pg_policies p where schemaname='public';"
        before = sql(policies)
        migration = (ROOT / "packages/db/migrations/0039_evidence_history_index.sql").read_text()
        sql(migration)
        sql(migration)
        runbook = (ROOT / "docs/runbooks/0039-apply.md").read_text()
        blocks = re.findall(r"```sql\n(.*?)```", runbook, flags=re.DOTALL)
        assert len(blocks) == 2
        sql(blocks[0])
        sql(blocks[1])
        sql((ROOT / "services/api/tests/fixtures/evidence_history_local.sql").read_text())
        assert sql(policies) == before
        print("PASS 0039 repeated apply, guarded runbook and keyset fixture after 0038")

        # Exercise the documented additive-index recovery on this database only.
        sql("drop index public.evidence_events_history_idx;")
        assert sql("select to_regclass('public.evidence_events_history_idx') is null;") == "t"
        sql(blocks[1])
        sql(blocks[0])
        assert sql("select count(*) from pg_index where indexrelid=to_regclass('public.evidence_events_history_idx') and indisvalid and indisready;") == "1"
        assert sql(policies) == before
        print("PASS documented index removal/reapply; tightened policies unchanged")
        print("PASS local PostgreSQL " + sql("show server_version;") + "; no hosted access")
    finally:
        if created:
            docker("rm", "--force", "--volumes", container)


if __name__ == "__main__":
    main()
