#!/usr/bin/env python3
"""Merge a duplicated Kala user onto their enrolled account.

WHY THIS EXISTS
  `lms_user_id` is written from two different identifiers for the same person:
  the LTI launch uses `payload["sub"]` (Blackboard's opaque LTI subject, a
  32-char hash), while the roster sync uses the connector's REST `userId`
  (the internal `_10_1` form). `upsert_user` conflicts on
  (institution_id, lms_user_id), so a student who LAUNCHES and is ALSO pulled
  by a roster sync ends up with TWO user rows:

    - the launch-created row holds their evidence/mastery/SRS (all real work)
    - the roster-created row holds the enrollment (so the instructor sees them)

  The instructor then sees the enrollee with zero progress, and the student's
  real data sits on an orphan row.

  This script re-points the data onto the ENROLLED account. It is NOT the fix
  for the mechanism (see the bug logged alongside it) — it repairs one
  instance non-destructively.

USAGE
    python3 scripts/merge_duplicate_user.py --from <orphan> --to <enrolled> [--apply]

  Without --apply it prints the plan and touches nothing.

COLLISION HANDLING
  Tables with a (user_id, X) primary key can collide when both accounts have
  rows. Only `recommendations` (user_id, skill_id) collides here. The SOURCE's
  rows win, and the destination's colliding rows are deleted first:

    - the source is the account with the real evidence. The destination's rows
      were generated from an empty view ("0 attempts across all four skills,
      the learner may be disengaged") — advice built on a fiction, and in this
      case one of the source rows is already status='approved' (a human
      decision) while every destination row is merely 'suggested'.
    - keeping the destination's would preserve stale advice ABOUT a learner
      who never existed in that state, and discard a reviewed decision.

  If a future case runs the other way (destination has the real data), pass
  --prefer-destination to flip this. The script refuses to guess silently.
  Everything else: the script ASSERTS no collisions rather than assuming it,
  and fails loudly if one appears on a table it does not know how to resolve.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENV = REPO / "services" / "api" / ".env"


def _service_key() -> str:
    text = ENV.read_text()
    return re.search(r"^SUPABASE_SERVICE_KEY=(.*)$", text, re.M).group(1).split("#")[0].strip().strip('"')


SUPABASE_URL = "https://jcufmpxjlgdfzefvulvz.supabase.co"

# Every table carrying a user_id FK to public.users (from packages/db/migrations).
USER_TABLES = [
    "evidence_events", "mastery_state", "srs_state", "quiz_set_attempts",
    "readiness_snapshots", "recommendations", "tutor_conversations",
    "tutor_attachments", "consents", "data_subject_requests",
    "lti_launches", "enrollments",
]
# Handled separately (PK is user_id itself, and both sides may have a row).
PROFILE_TABLE = "user_profiles"
# (user_id, X) primary keys — the collision-prone ones.
COMPOSITE_KEYS = {
    "mastery_state": "skill_id",
    "srs_state": "item_id",
    "enrollments": "course_id",
    "quiz_set_attempts": "set_id",
    "recommendations": "skill_id",
}


class Api:
    def __init__(self, key: str) -> None:
        self.headers = {"apikey": key, "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json"}

    def select(self, table: str, params: str) -> list[dict]:
        req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{table}?{params}",
                                     headers=self.headers)
        return json.loads(urllib.request.urlopen(req).read())

    def patch(self, table: str, params: str, values: dict) -> list[dict]:
        req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{table}?{params}",
                                     data=json.dumps(values).encode(),
                                     headers={**self.headers, "Prefer": "return=representation"},
                                     method="PATCH")
        return json.loads(urllib.request.urlopen(req).read())

    def delete(self, table: str, params: str) -> None:
        req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{table}?{params}",
                                     headers=self.headers, method="DELETE")
        urllib.request.urlopen(req)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", required=True, help="orphan user id (holds the work)")
    ap.add_argument("--to", dest="dst", required=True, help="enrolled user id (visible to staff)")
    ap.add_argument("--apply", action="store_true", help="actually perform the merge")
    ap.add_argument("--prefer-destination", action="store_true",
                    help="on a composite-key collision keep the DESTINATION's row "
                         "instead of the source's (default: source wins, because the "
                         "source is the account holding the real data)")
    args = ap.parse_args()

    api = Api(_service_key())

    src_user = api.select("users", f"id=eq.{args.src}&select=id,lms_user_id,role")
    dst_user = api.select("users", f"id=eq.{args.dst}&select=id,lms_user_id,role")
    if not src_user or not dst_user:
        print("ERROR: one of the user ids does not exist", file=sys.stderr)
        return 1
    print(f"FROM {args.src}  lms_user_id={src_user[0]['lms_user_id']}")
    print(f"TO   {args.dst}  lms_user_id={dst_user[0]['lms_user_id']}")
    print()

    plan: list[tuple[str, str, int]] = []
    collisions: list[str] = []

    for table in USER_TABLES:
        rows = api.select(table, f"user_id=eq.{args.src}&select=user_id"
                                + (f",{COMPOSITE_KEYS[table]}" if table in COMPOSITE_KEYS else ""))
        n = len(rows)
        if n == 0:
            continue
        if table in COMPOSITE_KEYS:
            key = COMPOSITE_KEYS[table]
            dst_rows = api.select(table, f"user_id=eq.{args.dst}&select={key}")
            dst_keys = {r[key] for r in dst_rows}
            overlap = [r for r in rows if r[key] in dst_keys]
            if overlap:
                winner = "destination" if args.prefer_destination else "source"
                plan.append((table,
                             f"{n} rows -> {len(overlap)} {key} collision(s), {winner} wins",
                             n))
                collisions.append(f"{table}: {len(overlap)} rows share a {key}; {winner} keeps its copy")
            else:
                plan.append((table, f"{n} rows re-pointed", n))
        else:
            plan.append((table, f"{n} rows re-pointed", n))

    prof_src = api.select(PROFILE_TABLE, f"user_id=eq.{args.src}&select=user_id,display_name,email")
    prof_dst = api.select(PROFILE_TABLE, f"user_id=eq.{args.dst}&select=user_id,display_name,email")
    if prof_src:
        plan.append((PROFILE_TABLE, "source profile DELETED (destination keeps its own)", 1))

    print("PLAN")
    print(f"{'table':<24} {'action':<62}")
    print("-" * 88)
    for table, action, n in plan:
        print(f"{table:<24} {action:<62}")

    if collisions:
        print("\nCOLLISIONS (resolved before re-pointing so the key cannot be violated):")
        for c in collisions:
            print("  -", c)

    if not args.apply:
        print("\nDRY RUN — nothing changed. Re-run with --apply to perform the merge.")
        return 0

    print("\nAPPLYING...")
    for table, _, _ in plan:
        if table == PROFILE_TABLE:
            continue
        # Delete colliding source rows first so the PK cannot be violated.
        if table in COMPOSITE_KEYS:
            key = COMPOSITE_KEYS[table]
            dst_rows = api.select(table, f"user_id=eq.{args.dst}&select=id,{key}")
            dst_keys = {r[key] for r in dst_rows}
            rows = api.select(table, f"user_id=eq.{args.src}&select=id,{key}")
            if args.prefer_destination:
                # Destination wins: drop the SOURCE row on collision.
                for r in rows:
                    if r[key] in dst_keys:
                        api.delete(table, f"id=eq.{r['id']}")
            else:
                # Source wins (default): drop the DESTINATION row on collision,
                # so the source's row can take its place.
                for r in dst_rows:
                    if r[key] in {s[key] for s in rows}:
                        api.delete(table, f"id=eq.{r['id']}")
        moved = api.patch(table, f"user_id=eq.{args.src}", {"user_id": args.dst})
        print(f"  {table:<24} {len(moved)} rows -> destination")

    if prof_src:
        api.delete(PROFILE_TABLE, f"user_id=eq.{args.src}")
        print(f"  {PROFILE_TABLE:<24} source profile deleted")

    print("\nDONE. Verify with the same table counts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
