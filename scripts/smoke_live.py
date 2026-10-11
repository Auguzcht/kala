#!/usr/bin/env python3
"""Run a small authenticated smoke check against the live practice API.

Set KALA_SMOKE_TOKEN to a student bearer token. The script answers one
previously unanswered item in the newest available set, then checks that a
repeat submit returns the stored result and the recap survives a fresh GET.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import uuid


BASE_URL = os.getenv(
    "KALA_API_BASE",
    "https://14vua0ys43.execute-api.ap-southeast-1.amazonaws.com",
).rstrip("/")
COURSE_ID = os.getenv("KALA_SMOKE_COURSE_ID", "ae4e7680-f94b-4652-b3f6-b9c32f4420de")
TOKEN = os.getenv("KALA_SMOKE_TOKEN")


def request(path: str, body: dict | None = None) -> tuple[int, dict]:
    headers = {"authorization": f"Bearer {TOKEN}"}
    data = None
    method = "GET"
    if body is not None:
        headers["content-type"] = "application/json"
        data = json.dumps(body).encode()
        method = "POST"
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} returned {exc.code}: {detail}") from exc


ANSWER_KEY_FIELDS = {
    "correct_choice_id", "correctChoiceId", "correct_option_id", "correctOptionId",
    "correct_answer_text", "correctAnswerText", "explanation",
}


def has_answer_key(value: object) -> bool:
    if isinstance(value, dict):
        return bool(ANSWER_KEY_FIELDS.intersection(value)) or any(
            has_answer_key(child) for child in value.values()
        )
    if isinstance(value, list):
        return any(has_answer_key(child) for child in value)
    return False


def main() -> int:
    if not TOKEN:
        print("Set KALA_SMOKE_TOKEN to an authenticated student bearer token.", file=sys.stderr)
        return 2

    status, listing = request(f"/practice/{COURSE_ID}/sets")
    assert status == 200
    selected = None
    selected_results = None
    selected_set = None
    for row in listing.get("sets", []):
        set_id = row["setId"]
        set_status, set_body = request(f"/practice/{COURSE_ID}/sets/{set_id}")
        assert set_status == 200
        result_status, results = request(f"/practice/{COURSE_ID}/sets/{set_id}/results")
        assert result_status == 200
        assert not has_answer_key(set_body), "set GET exposed answer key data"
        assert all(
            q.get("correctAnswer") is None and q.get("explanation") is None
            for q in results.get("questions", []) if not q.get("answered")
        ), "results exposed an answer key for an unanswered item"
        answered_ids = {
            q["itemId"] for q in results.get("questions", []) if q.get("answered")
        }
        candidate = next(
            (item for item in set_body.get("items", [])
             if item["id"] not in answered_ids and len(item.get("choices") or []) >= 2),
            None,
        )
        if candidate:
            selected, selected_results, selected_set = candidate, results, set_body
            break

    if not selected:
        raise RuntimeError("No set with an unanswered item and two choices was found")

    set_id = selected_set["setId"]
    session_id = str(uuid.uuid4())
    choices = selected["choices"]
    submit_path = f"/practice/{COURSE_ID}/submit"
    common = {"item_id": selected["id"], "set_id": set_id, "session_id": session_id}
    first_status, first = request(submit_path, {
        **common, "choice_id": choices[0]["id"], "idempotency_key": f"smoke-{session_id}",
    })
    repeat_status, repeated = request(submit_path, {
        **common, "choice_id": choices[1]["id"],
        "idempotency_key": f"smoke-repeat-{session_id}",
    })
    assert first_status == repeat_status == 200
    assert first == repeated, "repeat submit did not return the original stored result"

    recap_status, recap = request(f"/practice/{COURSE_ID}/sets/{set_id}/results")
    assert recap_status == 200
    assert recap["score"]["answered"] == selected_results["score"]["answered"] + 1
    assert recap["totalXp"] == selected_results["totalXp"] + first["xpAwarded"]
    assert all(
        q.get("correctAnswer") is None and q.get("explanation") is None
        for q in recap["questions"] if not q.get("answered")
    )
    assert next(q for q in recap["questions"] if q["itemId"] == selected["id"])["answered"]

    print("check\tresult")
    print(f"set list\t{status}")
    print(f"set GET / answer key absent\t{set_status} / PASS")
    print(f"results GET / unanswered keys absent\t{recap_status} / PASS")
    print(f"submit\t{first_status}")
    print(f"repeat submit returns stored result\t{repeat_status} / PASS")
    print(f"results GET after refresh\t{recap_status} / PASS")
    print(f"answered count\t{selected_results['score']['answered']} -> {recap['score']['answered']}")
    print(f"total XP\t{selected_results['totalXp']} -> {recap['totalXp']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
