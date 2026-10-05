"""Read-only bank selection and tenant-scoped exposure writes."""
from __future__ import annotations

import random
from datetime import UTC, datetime

from app.db import supabase as db

BANK_SURFACES = {"study", "test", "diagnostic", "lesson"}
MIN_USABLE = 5


def bank_enabled(course: dict, surface: str) -> bool:
    return bool(course.get("bank_serving")) and surface in BANK_SURFACES


def _approved_item_pool(*, institution_id: str, course_id: str, skill_id: str | None) -> list[dict]:
    params = {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        "origin": "eq.bank", "kind": "eq.practice", "retired_at": "is.null",
        "select": "id,skill_id,prompt,choices,correct_choice_id,explanation,bloom_level,source_chunk_ids,created_at",
        "skills.status": "eq.approved",
        "order": "created_at.asc",
    }
    if skill_id:
        params["skill_id"] = f"eq.{skill_id}"
    # PostgREST's embedded filter requires the relationship in select.
    params["select"] = params["select"] + ",skills!inner(status)"
    return db.select("generated_items", params)


def pick_bank_items(user_id: str, course_id: str, skill_id: str | None, n: int, mode: str,
                    *, institution_id: str) -> list[dict]:
    """Select reusable bank items without invoking a model."""
    return pick_bank_items_with_meta(
        user_id, course_id, skill_id, n, mode, institution_id=institution_id,
    )[0]


def pick_bank_items_with_meta(user_id: str, course_id: str, skill_id: str | None, n: int,
                              mode: str, *, institution_id: str) -> tuple[list[dict], bool]:
    """Select bank items and report whether the result used a repeat tier."""
    if n <= 0 or mode not in {"study", "test"}:
        return [], False
    pool = _approved_item_pool(institution_id=institution_id, course_id=course_id, skill_id=skill_id)
    tracked = db.select("srs_state", {
        "user_id": f"eq.{user_id}", "course_id": f"eq.{course_id}",
        "select": "item_id,skill_id",
    })
    tracked_ids = {r["item_id"] for r in tracked}
    if mode == "study":
        pool = [r for r in pool if r["id"] not in tracked_ids]
        return _round_robin(pool, n), False
    exposures = db.select("item_exposures", {
        "user_id": f"eq.{user_id}", "course_id": f"eq.{course_id}",
        "select": "item_id,last_tested_at,last_answered_at,last_correct",
    })
    by_id = {r["item_id"]: r for r in exposures}
    tier1 = [r for r in pool if not by_id.get(r["id"], {}).get("last_tested_at")]
    tier2 = [r for r in pool if by_id.get(r["id"], {}).get("last_correct") is False and r not in tier1]
    tier3 = [r for r in pool if r not in tier1 and r not in tier2]
    tier2.sort(key=lambda r: by_id.get(r["id"], {}).get("last_answered_at") or "")
    tier3.sort(key=lambda r: by_id.get(r["id"], {}).get("last_tested_at") or "")
    unseen = _round_robin(tier1, n)
    remaining = max(0, n - len(unseen))
    selected = unseen + (tier2 + tier3)[:remaining]
    return selected, len(selected) > len(unseen)


def pick_diagnostic_item(user_id: str, course_id: str, skill_id: str, *,
                         institution_id: str) -> dict | None:
    """Pick the oldest untested live bank item without writing exposure."""
    pool = _approved_item_pool(
        institution_id=institution_id, course_id=course_id, skill_id=skill_id,
    )
    exposures = db.select("item_exposures", {
        "user_id": f"eq.{user_id}", "course_id": f"eq.{course_id}",
        "select": "item_id,last_tested_at",
    })
    tested = {r["item_id"] for r in exposures if r.get("last_tested_at")}
    return next((item for item in pool if item["id"] not in tested), None)


def _round_robin(items: list[dict], n: int) -> list[dict]:
    buckets: dict[str, list[dict]] = {}
    for item in items:
        ids = item.get("source_chunk_ids") or ["__unattributed__"]
        key = str(ids[0]) if ids else "__unattributed__"
        buckets.setdefault(key, []).append(item)
    keys = list(buckets)
    random.SystemRandom().shuffle(keys)
    out: list[dict] = []
    while len(out) < n and keys:
        next_keys = []
        for key in keys:
            if buckets[key]:
                out.append(buckets[key].pop(0))
                if len(out) == n:
                    break
            if buckets[key]:
                next_keys.append(key)
        keys = next_keys
    return out


def record_exposure(*, institution_id: str, user_id: str, course_id: str, skill_id: str,
                    item_id: str, studied: bool = False, tested: bool = False,
                    answered: bool = False, correct: bool | None = None) -> None:
    now = datetime.now(UTC).isoformat()
    try:
        current = db.select("item_exposures", {
            "user_id": f"eq.{user_id}", "item_id": f"eq.{item_id}",
            "select": "times_tested", "limit": "1",
        })
        values = {
            "institution_id": institution_id, "user_id": user_id, "course_id": course_id,
            "skill_id": skill_id, "item_id": item_id,
            "updated_at": now,
        }
        if studied:
            values["last_studied_at"] = now
        if tested:
            values["last_tested_at"] = now
            values["times_tested"] = int(current[0].get("times_tested") or 0) + 1 if current else 1
        if answered:
            values["last_answered_at"] = now
            values["last_correct"] = bool(correct)
        db.upsert("item_exposures", [values], on_conflict="user_id,item_id")
    except Exception:  # noqa: BLE001 - telemetry must not block serving
        # Exposure is telemetry; it must not prevent a card or graded result
        # from reaching the student if the auxiliary write is unavailable.
        return
