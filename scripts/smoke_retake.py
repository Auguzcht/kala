#!/usr/bin/env python3
"""Check live retakes through the API, only as smoke_live's dedicated student.

Run from services/api: uv run python ../../scripts/smoke_retake.py
Creates one five-question set, completes it, and leaves retake two partial.
Stops immediately on any unexpected status or response; never resets data.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import uuid
from pathlib import Path

import smoke_live as live


def request(path: str, body: dict | None = None) -> tuple[int, dict]:
    """Reuse the existing transport, exposing expected conflict responses."""
    try:
        return live.request(path, body)
    except RuntimeError as exc:
        if isinstance(exc.__cause__, urllib.error.HTTPError) and exc.__cause__.code == 409:
            return 409, json.loads(str(exc).split("returned 409: ", 1)[1])
        raise


def check(step: int, status: int, expected: int, condition: bool, **fields) -> None:
    passed = status == expected and condition
    print(f"Step {step}: {'PASS' if passed else 'FAIL'} HTTP {status} "
          + json.dumps(fields, sort_keys=True), flush=True)
    if not passed:
        raise RuntimeError(f"Step {step} failed; stopping")


def main() -> int:
    if not live.TOKEN:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))
        from app.security.jwt import mint_session_token

        live.TOKEN = mint_session_token(
            user_id=live.SMOKE_USER_ID,
            institution_id=live.SMOKE_INSTITUTION_ID,
            app_role="student",
            course_id=live.COURSE_ID,
        )
    live.validate_smoke_token()
    root = f"/practice/{live.COURSE_ID}"
    status, listing = request(root + "/sets")
    if status != 200:
        raise RuntimeError(f"Set discovery failed: HTTP {status}")
    candidate = next((s for s in listing.get("sets", [])
                      if s.get("size", 0) >= 5 and s.get("skillId")), None)
    if candidate is None:
        raise RuntimeError("No usable five-item AWS101 skill found; stopping")
    existing_ids = {s["setId"] for s in listing["sets"]}
    status, created = request(root + f"/set?skill_id={candidate['skillId']}&size=5", {})
    items = created.get("items", [])
    set_id = created.get("setId")
    check(1, status, 200, bool(set_id) and set_id not in existing_ids
          and len(items) == 5 and all(i.get("choices") for i in items),
          setId=set_id, skillId=candidate["skillId"], total=len(items),
          state=created.get("status"))
    set_path = root + f"/sets/{set_id}"
    session_id = str(uuid.uuid4())
    first_body = None
    first_snapshot = None
    attempt_id = None
    for item in items:
        body = {"item_id": item["id"], "choice_id": item["choices"][0]["id"],
                "set_id": set_id, "session_id": session_id,
                "idempotency_key": f"retake-smoke-{uuid.uuid4()}"}
        if attempt_id:
            body["attemptId"] = attempt_id
        status, answer = request(root + "/submit", body)
        current_id = answer.get("attemptId")
        check(2, status, 200, bool(current_id) and answer.get("attemptNumber") == 1
              and answer.get("xpAwarded") in (2, 12)
              and (attempt_id is None or current_id == attempt_id),
              itemId=item["id"], attemptId=current_id,
              attemptNumber=answer.get("attemptNumber"), xpAwarded=answer.get("xpAwarded"))
        attempt_id = current_id
        if first_body is None:
            first_body, first_snapshot = body, answer
    status, original = request(set_path + "/results")
    attempts = original.get("attempts", [])
    score = original.get("score", {})
    check(3, status, 200, original.get("attemptNumber") == 1
          and score.get("answered") == score.get("total") == 5
          and len(attempts) == 1 and bool(attempts[0].get("completedAt")),
          attemptNumber=original.get("attemptNumber"), score=score, attempts=attempts)
    status, conflict = request(root + "/submit", {
        **first_body, "idempotency_key": f"retake-smoke-{uuid.uuid4()}"})
    check(4, status, 409, conflict == {"code": "attempt_complete"}, response=conflict)
    status, replay = request(root + "/submit", first_body)
    check(5, status, 200, replay == first_snapshot, originalSnapshot=replay == first_snapshot,
          attemptId=replay.get("attemptId"), xpAwarded=replay.get("xpAwarded"))
    status, retake = request(set_path + "/retake", {})
    retake_id = retake.get("attemptId")
    check(6, status, 201, bool(retake_id) and retake_id != attempt_id
          and retake.get("attemptNumber") == 2, **retake)
    status, conflict = request(set_path + "/retake", {})
    check(7, status, 409, conflict == {"code": "attempt_in_progress"}, response=conflict)
    status, answer = request(root + "/submit", {
        **first_body, "attemptId": retake_id, "session_id": str(uuid.uuid4()),
        "idempotency_key": f"retake-smoke-{uuid.uuid4()}"})
    check(8, status, 200, answer.get("attemptId") == retake_id
          and answer.get("attemptNumber") == 2 and answer.get("xpAwarded") == 0,
          attemptId=answer.get("attemptId"), attemptNumber=answer.get("attemptNumber"),
          xpAwarded=answer.get("xpAwarded"))
    status, latest = request(set_path + "/results")
    check(9, status, 200, latest.get("attemptNumber") == 2
          and latest.get("xpNote") == "Retakes don't earn XP. Your first try counts."
          and len(latest.get("attempts", [])) == 2
          and latest.get("score", {}).get("answered") == 1,
          attemptNumber=latest.get("attemptNumber"), xpNote=latest.get("xpNote"),
          attempts=latest.get("attempts"), score=latest.get("score"))
    status, historical = request(set_path + f"/results?attemptId={attempt_id}")
    check(10, status, 200, historical.get("attemptNumber") == 1
          and historical.get("score") == score, attemptNumber=historical.get("attemptNumber"),
          score=historical.get("score"))
    status, listing = request(root + "/sets")
    row = next((s for s in listing.get("sets", []) if s["setId"] == set_id), {})
    best = {"correct": score["correct"], "total": score["total"]}
    partial = latest["score"]
    latest_score = {"correct": partial["correct"], "total": partial["total"]}
    check(11, status, 200, row.get("attemptCount") == 2
          and row.get("bestScore") == best and row.get("latestScore") == latest_score,
          attemptCount=row.get("attemptCount"), bestScore=row.get("bestScore"),
          latestScore=row.get("latestScore"), setId=set_id)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
