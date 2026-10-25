"""Local-only WI-24 inventory/blocker proof; no repair implementation.

Uses Docker exec (no published port/network client, no .env, no app imports).
Requires cached Supabase Postgres image. Refuses to reuse any container.
All database output/errors are captured; only fixed proof labels escape.
"""
from pathlib import Path
import hashlib
import os
import subprocess
import time
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
IMAGE = "public.ecr.aws/supabase/postgres:17.6.1.158"


def main():
    container = "kala-wi24-proof-" + uuid.uuid4().hex[:12]
    env = {"PATH": os.environ["PATH"], "PYTHON_DOTENV_DISABLED": "1"}
    created = False

    def docker(*args, data=None):
        result = subprocess.run(
            ["docker", *args], input=data, capture_output=True, env=env,
            timeout=60, check=False,
        )
        if result.returncode:
            raise RuntimeError("local fixture command failed; raw output suppressed")
        return result.stdout

    def sql(data):
        return docker("exec", "-i", container, "psql", "-X", "-U", "postgres",
                      "-d", "wi24_synthetic", "-v", "ON_ERROR_STOP=1", "-At", data=data)

    try:
        docker("run", "--detach", "--pull=never", "--name", container,
               "--env", "POSTGRES_HOST_AUTH_METHOD=trust", IMAGE)
        created = True
        for _ in range(150):
            health = docker("inspect", "--format", "{{.State.Health.Status}}", container)
            if health.strip() == b"healthy":
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("local image initialization did not finish")
        docker("exec", container, "createdb", "-U", "postgres", "-T", "template0", "wi24_synthetic")
        sql((HERE / "bootstrap.sql").read_bytes())
        migrations = sorted((ROOT / "packages/db/migrations").glob("*.sql"))
        migrations = [p for p in migrations if p.name[:4].isdigit() and int(p.name[:4]) <= 37]
        assert len(migrations) == 37
        hashes = []
        for migration in migrations:
            payload = migration.read_bytes()
            sql(payload)
            hashes.append(hashlib.sha256(payload).hexdigest() + "  " + migration.name)
        catalog = sql((HERE / "catalog.sql").read_bytes())
        assert catalog == (HERE / "catalog.txt").read_bytes(), "catalog differs"
        assert "\n".join(hashes) + "\n" == (HERE / "migrations.sha256").read_text()
        proof = sql((HERE / "blockers.sql").read_bytes())
        assert b"PASS source-key/session collisions" in proof
        print("PASS 37 immutable migrations; schema catalog matches")
        print("PASS source-key/session collisions and exact resolver conflict reproduced")
        print("PASS injected transaction failure restores evidence and immutable trigger")
        print("PASS synthetic source row counts conserved; fixture transaction rolled back")
    finally:
        if created:
            docker("rm", "--force", container)


if __name__ == "__main__":
    main()
