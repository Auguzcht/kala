#!/usr/bin/env python3
"""Poll one ingest job and log its progress. READ-ONLY.

Why this exists: a drain advances one bounded slice per worker tick (the
worker runs every 15 minutes), so watching it by hand means sitting at a
terminal for an hour. This polls once a minute, appends ONLY when something
actually changed, and exits on its own.

It deliberately does not:
  - write to ingest_jobs (or anything else — no INSERT/UPDATE/DELETE at all)
  - mint a token (plain REST reads against Supabase with the service key)
  - re-enqueue on failure, or retry a stall (a human decides those)
  - poll faster than 60s (the worker advances every 15 min; faster is load
    with no signal)

Usage:
    python3 scripts/poll_ingest.py [job_id] [course_id]

Defaults to the AWS101 job this was written for.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_JOB_ID = "40742dba-538a-4cbd-9d10-872139fb71a3"
DEFAULT_COURSE_ID = "ae4e7680-f94b-4652-b3f6-b9c32f4420de"

# The worker advances every 15 minutes, so nothing can change faster than that.
POLL_SECONDS = 60
# Two full 15-minute ticks with no movement = genuinely stuck, not just slow.
# One flat tick means "the worker has not run yet"; two means "it ran and
# moved nothing", which is the real failure signal.
STALL_SECONDS = 30 * 60
STALL_POLLS = 15
# The earlier live probe found exactly 8 PDFs on this course. Reaching 8
# extracted PDF chunks is the success condition; the job may still be
# mid-walk over containers that hold no documents.
TARGET_PDF_CHUNKS = 8

REPO_ROOT = Path(__file__).resolve().parent.parent
AWS_BIN = REPO_ROOT / ".tools" / "aws-cli" / "bin" / "aws"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_supabase() -> tuple[str, str]:
    """Read creds from the kala/app secret. Never hardcoded in this file."""
    out = subprocess.run(
        [str(AWS_BIN), "secretsmanager", "get-secret-value",
         "--secret-id", "kala/app", "--region", "ap-southeast-1",
         "--query", "SecretString", "--output", "text"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    if out.returncode != 0:
        sys.exit(f"could not read kala/app secret: {out.stderr[:300]}")
    sec = json.loads(out.stdout)
    return sec["SUPABASE_URL"], sec["SUPABASE_SERVICE_KEY"]


def _get(url: str, key: str, path: str, params: dict) -> list:
    req = urllib.request.Request(
        f"{url}/rest/v1/{path}?" + urllib.parse.urlencode(params),
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _count(url: str, key: str, path: str, params: dict) -> int:
    """Exact count via Content-Range, so no page size can mislead.
    (A paginated read was misread twice in this project already.)"""
    req = urllib.request.Request(
        f"{url}/rest/v1/{path}?" + urllib.parse.urlencode(params),
        headers={"apikey": key, "Authorization": f"Bearer {key}",
                 "Prefer": "count=exact", "Range": "0-0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return int(r.headers.get("Content-Range", "*/0").split("/")[-1])


def snapshot(url: str, key: str, job_id: str, course_id: str) -> dict:
    job = _get(url, key, "ingest_jobs", {
        "id": f"eq.{job_id}",
        "select": "status,folders_expanded,items_stored,pdfs_fetched,last_error,updated_at",
        "limit": "1",
    })[0]
    job["pdf_chunks_live"] = _count(url, key, "content_items", {
        "course_id": f"eq.{course_id}", "lms_ref": "like.*::*", "select": "id",
    })
    return job


def main() -> int:
    job_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_JOB_ID
    course_id = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_COURSE_ID

    url, key = load_supabase()
    log_dir = REPO_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"ingest_poll_{job_id}.log"

    started = time.monotonic()
    last_sig = None
    flat_polls = 0
    stall_flagged = False

    def emit(line: str) -> None:
        stamped = f"{_utc()}  {line}"
        with log_path.open("a") as f:
            f.write(stamped + "\n")
        print(stamped, flush=True)

    emit(f"START job={job_id} course={course_id} poll={POLL_SECONDS}s "
         f"target_pdf_chunks={TARGET_PDF_CHUNKS}")

    while True:
        try:
            s = snapshot(url, key, job_id, course_id)
        except Exception as exc:  # noqa: BLE001 — a blip must not kill the script
            emit(f"QUERY FAILED ({type(exc).__name__}: {str(exc)[:120]}) — retrying next tick")
            time.sleep(POLL_SECONDS)
            continue

        sig = (s["status"], s["folders_expanded"], s["items_stored"],
               s["pdfs_fetched"], s["pdf_chunks_live"], str(s.get("updated_at")))
        if sig != last_sig:
            emit(f"status={s['status']:11} folders={s['folders_expanded']:3} "
                 f"items={s['items_stored']:4} pdfs_fetched={s['pdfs_fetched']} "
                 f"pdf_chunks={s['pdf_chunks_live']}")
            last_sig = sig
            flat_polls = 0
        else:
            flat_polls += 1

        # Two full 15-minute windows with no movement at all.
        if (flat_polls * POLL_SECONDS >= STALL_SECONDS
                and s["status"] not in ("complete", "failed")
                and not stall_flagged):
            stall_flagged = True
            emit(f"STALLED: no change across "
                 f"{flat_polls * POLL_SECONDS // 60} min "
                 f"(folders={s['folders_expanded']}, items={s['items_stored']}) "
                 f"— still polling; a human should decide whether to intervene")

        if s["status"] in ("complete", "failed") or s["pdf_chunks_live"] >= TARGET_PDF_CHUNKS:
            wall = time.monotonic() - started
            with log_path.open("a") as f:
                f.write("\n" + "=" * 60 + "\nSUMMARY\n" + "=" * 60 + "\n")
                f.write(f"job_id          : {job_id}\n")
                f.write(f"final status    : {s['status']}\n")
                f.write(f"folders_expanded: {s['folders_expanded']}\n")
                f.write(f"items_stored    : {s['items_stored']}\n")
                f.write(f"pdfs_fetched    : {s['pdfs_fetched']}\n")
                f.write(f"pdf_chunks_live : {s['pdf_chunks_live']}\n")
                f.write(f"wall time       : {wall/60:.1f} min "
                        f"({int(wall)}s, {int(wall)//POLL_SECONDS} polls)\n")
                f.write(f"updated_at      : {s.get('updated_at')}\n")
                if s["status"] == "failed":
                    f.write(f"\nlast_error:\n{s.get('last_error') or '(empty)'}\n")
                if s["status"] != "complete" and s["pdf_chunks_live"] >= TARGET_PDF_CHUNKS:
                    f.write("\nStopped because the PDF-chunk target was reached "
                            "while the walk is still in_progress.\n")
                f.write("=" * 60 + "\n")
            print(f"\nDone — see {log_path}", flush=True)
            return 0

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
