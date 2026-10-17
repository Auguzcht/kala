#!/usr/bin/env python3
"""Dry-run or explicitly reset one user's practice rows for one course.

The default action is read-only and prints counts. Applying requires both
--apply and --confirm with the exact --user-id. It only deletes practice
answer snapshots, that user's set-attempt rows, and item exposures for the
selected course; dependent answer rows cascade only from those attempts.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import UUID

REPO = Path(__file__).resolve().parent.parent
ENV_FILE = REPO / "services" / "api" / ".env"
SUPABASE_URL = "https://jcufmpxjlgdfzefvulvz.supabase.co"
TABLES = ("practice_answer_results", "quiz_set_attempts", "item_exposures")


def _load_env_file() -> None:
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if not match or match.group(1) in os.environ:
            continue
        value = match.group(2).split("#", 1)[0].strip().strip("'\"")
        os.environ[match.group(1)] = value


def _service_key() -> str:
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_KEY is required for the read-only count query")
    return key


def _count_rows(table: str, user_id: str, course_id: str, service_key: str) -> int:
    query = urlencode({
        "select": "id",
        "user_id": f"eq.{user_id}",
        "course_id": f"eq.{course_id}",
    })
    request = Request(
        f"{SUPABASE_URL}/rest/v1/{table}?{query}",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Prefer": "count=exact",
            "Range": "0-0",
        },
    )
    with urlopen(request, timeout=20) as response:
        content_range = response.headers.get("Content-Range", "")
    total = content_range.rsplit("/", 1)[-1]
    if not total.isdigit():
        raise RuntimeError(f"Could not read exact count for {table}: Content-Range={content_range!r}")
    return int(total)


def _apply(user_id: str, course_id: str) -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required for the transactional --apply path")
    user_literal = f"'{user_id}'::uuid"
    course_literal = f"'{course_id}'::uuid"
    sql = f"""
BEGIN;
ALTER TABLE public.practice_answer_results DISABLE TRIGGER practice_answer_results_immutable;
DELETE FROM public.practice_answer_results WHERE user_id = {user_literal} AND course_id = {course_literal};
DELETE FROM public.quiz_set_attempts WHERE user_id = {user_literal} AND course_id = {course_literal};
DELETE FROM public.item_exposures WHERE user_id = {user_literal} AND course_id = {course_literal};
ALTER TABLE public.practice_answer_results ENABLE TRIGGER practice_answer_results_immutable;
COMMIT;
"""
    env = {**os.environ, "PGDATABASE": database_url}
    subprocess.run(
        ["psql", "-X", "-v", "ON_ERROR_STOP=1"],
        input=sql, text=True, check=True, env=env,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--course-id", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", help="must exactly match --user-id when --apply is used")
    args = parser.parse_args()
    try:
        user_id = str(UUID(args.user_id))
        course_id = str(UUID(args.course_id))
    except ValueError:
        parser.error("--user-id and --course-id must be UUIDs")
    if args.apply and args.confirm != args.user_id:
        parser.error("--apply requires --confirm with the exact --user-id")

    _load_env_file()
    try:
        print(f"user_id={user_id} course_id={course_id}")
        key = _service_key()
        counts = {table: _count_rows(table, user_id, course_id, key) for table in TABLES}
        for table, count in counts.items():
            print(f"{table}: {count}")
        if not args.apply:
            print("DRY RUN — no rows changed")
            return 0
        _apply(user_id, course_id)
        print("Reset committed")
        return 0
    except (HTTPError, URLError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
