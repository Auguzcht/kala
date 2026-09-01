"""Prescriptive recommendations for one learner, for a teacher to decide on.

The loop this serves: Kala reads the learner's twin -> proposes 3-5 next
actions with the evidence behind each -> the TEACHER approves, modifies, or
rejects -> only then does the action reach the learner. Nothing here writes
anything a student can see; routers/dashboard.py persists these with
status='suggested' and the student-facing plan endpoint filters on the
decided statuses.

Two hard constraints shape this module:

1. De-identify first (CLAUDE.md rule 4). The prompt receives a pseudonym,
   skill names, and numbers. It never receives a display name, an email, an
   LMS id, or a raw evidence row. `_model_context` is the only thing that
   crosses the boundary and it is built by allow-list, not by stripping —
   an allow-list cannot leak a field someone adds to the twin later.

2. The demo must never depend on a model being reachable. `_heuristic`
   produces the same shape from mastery state alone, and it runs whenever
   the model is unavailable, slow, or returns something unparseable. A
   teacher-facing queue that is empty because Bedrock timed out is worse
   than one built from arithmetic, and the `source` field records honestly
   which produced each row.
"""
from __future__ import annotations

import json

from app.ai import router as ai_router

MAX_RECOMMENDATIONS = 5

# Which learner surface each kind of recommendation sends the learner to.
VALID_KINDS = {"practice", "lesson", "flashcards", "tutor", "diagnostic", "outreach"}
VALID_PRIORITIES = {"high", "medium", "low"}

SYSTEM = """You advise a university instructor about ONE learner in their course.

You are given de-identified mastery data: a pseudonym, per-skill mastery
estimates (0 to 1), attempt counts, Bloom's taxonomy levels, and recent
accuracy. You never receive names.

Propose at most 5 next actions the INSTRUCTOR could assign. The instructor
decides; you advise. Return ONLY a JSON array, no prose, no markdown fence.
Each element:

{
  "title": "short imperative sentence, max 60 chars",
  "kind": "practice" | "lesson" | "flashcards" | "tutor" | "diagnostic" | "outreach",
  "skill_name": "exact skill name from the input, or null",
  "priority": "high" | "medium" | "low",
  "rationale": "2 sentences max, plain language, addressed to the instructor",
  "evidence": [{"label": "short fact", "detail": "the number behind it"}],
  "confidence": 0.0-1.0,
  "expected_gain": 0.0-0.3
}

Rules:
- Every recommendation must cite at least one evidence item drawn from the
  supplied numbers. Never assert something the data does not show.
- Order by priority, highest first.
- Prefer the weakest skills with the most blueprint weight.
- Use "outreach" when the pattern is disengagement (no recent attempts)
  rather than difficulty — the action is a conversation, not more practice.
- Write about the learner supportively. Describe what would help, never
  judge the person."""


def _model_context(*, pseudonym: str, record: dict) -> dict:
    """The allow-listed payload that crosses to the model. Nothing else does."""
    return {
        "learner": pseudonym,
        "readiness": record.get("readiness"),
        "cohort_readiness": record.get("cohortReadiness"),
        "accuracy": record.get("accuracy"),
        "momentum": record.get("momentum"),
        "days_inactive": record.get("daysInactive"),
        "total_attempts": record.get("attempts"),
        "hints_used": record.get("hintsUsed"),
        "skills": [
            {
                "name": s.get("name"),
                "bloom": s.get("bloomLevel"),
                "estimate": s.get("estimate"),
                "attempts": s.get("attempts"),
            }
            for s in (record.get("skills") or [])
        ],
    }


def _coerce(raw: str) -> list[dict]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("["), text.rfind("]")
        if start == -1 or end <= start:
            return []
        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return []
    return data if isinstance(data, list) else []


def _clean(items: list[dict], *, skill_ids: dict[str, str]) -> list[dict]:
    """Validate at the boundary. A model-authored row is untrusted input:
    unknown kinds, invented skill names, and out-of-range numbers are
    normalized here rather than at the database or in the UI."""
    out: list[dict] = []
    for item in items[:MAX_RECOMMENDATIONS]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()[:120]
        if not title:
            continue
        kind = str(item.get("kind") or "practice").lower()
        priority = str(item.get("priority") or "medium").lower()
        skill_name = item.get("skill_name")
        evidence = item.get("evidence")
        out.append({
            "title": title,
            "kind": kind if kind in VALID_KINDS else "practice",
            "priority": priority if priority in VALID_PRIORITIES else "medium",
            "skill_id": skill_ids.get(str(skill_name).strip().lower()) if skill_name else None,
            "rationale": str(item.get("rationale") or "").strip()[:600],
            "evidence": [
                {"label": str(e.get("label") or "")[:80], "detail": str(e.get("detail") or "")[:120]}
                for e in evidence[:5]
                if isinstance(e, dict)
            ] if isinstance(evidence, list) else [],
            "confidence": _clamp(item.get("confidence"), 0.0, 1.0),
            "expected_gain": _clamp(item.get("expected_gain"), 0.0, 0.3),
        })
    return out


def _clamp(value, low: float, high: float) -> float | None:
    try:
        return round(max(low, min(high, float(value))), 3)
    except (TypeError, ValueError):
        return None


def _pct(value: float | None) -> str:
    return "no evidence" if value is None else f"{round(value * 100)}%"


def _heuristic(record: dict) -> list[dict]:
    """Deterministic fallback. Same shape, arithmetic instead of a model.

    Reads the way a teacher would read the row: has this learner stopped
    showing up, which skills are weakest, are they guessing, and is the
    ladder broken at a lower rung than where the course currently is.
    """
    skills = record.get("skills") or []
    ranked = sorted(skills, key=lambda s: (s.get("estimate") is not None, s.get("estimate") or 0))
    out: list[dict] = []

    days_inactive = record.get("daysInactive")
    if days_inactive is not None and days_inactive >= 7:
        out.append({
            "title": "Reach out before assigning more work",
            "kind": "outreach",
            "priority": "high",
            "skill_id": None,
            "rationale": (
                f"No activity for {days_inactive} days. The gap here looks like "
                "engagement, not difficulty, so a short conversation will do more "
                "than another practice set."
            ),
            "evidence": [
                {"label": "Last active", "detail": f"{days_inactive} days ago"},
                {"label": "Evidence on file", "detail": f"{record.get('evidenceCount', 0)} events"},
            ],
            "confidence": 0.9,
            "expected_gain": 0.0,
        })

    for skill in ranked[:2]:
        never = skill.get("estimate") is None
        out.append({
            "title": (
                f"Start {skill['name']} with a baseline set" if never
                else f"Assign focused practice on {skill['name']}"
            ),
            "kind": "diagnostic" if never else "practice",
            "priority": "high" if not out or never else "medium",
            "skill_id": skill.get("skillId"),
            "rationale": (
                "No evidence on this skill yet, so its mastery estimate is a "
                "placeholder rather than a measurement. One short set gives the "
                "twin something real to work from."
                if never else
                f"Lowest mastery on record at {_pct(skill.get('estimate'))} after "
                f"{skill.get('attempts', 0)} attempts. Practice moves the readiness "
                "rollup most here."
            ),
            "evidence": [
                {"label": "Mastery", "detail": _pct(skill.get("estimate"))},
                {"label": "Attempts", "detail": str(skill.get("attempts", 0))},
                {"label": "Bloom's level", "detail": str(skill.get("bloomLevel") or "unmapped")},
            ],
            "confidence": 0.75,
            "expected_gain": 0.08 if never else 0.06,
        })

    accuracy = record.get("accuracy")
    if accuracy is not None and accuracy < 0.5 and (record.get("attempts") or 0) >= 5:
        weakest = ranked[0] if ranked else None
        out.append({
            "title": "Book a guided lesson instead of more practice",
            "kind": "lesson",
            "priority": "medium",
            "skill_id": weakest.get("skillId") if weakest else None,
            "rationale": (
                f"Accuracy is {_pct(accuracy)} across recent attempts. At this rate "
                "practice is rehearsing the misconception rather than fixing it, so "
                "a step-by-step walkthrough should come first."
            ),
            "evidence": [
                {"label": "Recent accuracy", "detail": _pct(accuracy)},
                {"label": "Attempts", "detail": str(record.get("attempts") or 0)},
                {"label": "Hints used", "detail": str(record.get("hintsUsed") or 0)},
            ],
            "confidence": 0.7,
            "expected_gain": 0.07,
        })

    proficient = [s for s in skills if (s.get("estimate") or 0) >= 0.7]
    if proficient:
        out.append({
            "title": "Schedule spaced review to hold what's solid",
            "kind": "flashcards",
            "priority": "low",
            "skill_id": proficient[0].get("skillId"),
            "rationale": (
                f"{len(proficient)} skill{'s' if len(proficient) != 1 else ''} already "
                "sit at proficient or above. Short spaced review keeps them there "
                "while attention goes to the weaker rungs."
            ),
            "evidence": [
                {"label": "Skills at proficient+", "detail": str(len(proficient))},
                {"label": "Strongest", "detail": f"{proficient[0]['name']} · {_pct(proficient[0].get('estimate'))}"},
            ],
            "confidence": 0.65,
            "expected_gain": 0.03,
        })

    return out[:MAX_RECOMMENDATIONS]


def recommend(*, pseudonym: str, record: dict) -> tuple[list[dict], str]:
    """Return (recommendations, source). source is the model id, or
    'heuristic' when the deterministic path produced them."""
    skills = record.get("skills") or []
    skill_ids = {str(s.get("name", "")).strip().lower(): s.get("skillId") for s in skills}

    if not skills:
        return [], "heuristic"

    try:
        raw = ai_router.answer(
            system=SYSTEM,
            user_text=json.dumps(_model_context(pseudonym=pseudonym, record=record)),
        )
        cleaned = _clean(_coerce(raw), skill_ids=skill_ids)
        if cleaned:
            return cleaned, ai_router.get_model_for("default")
    except Exception:  # noqa: BLE001 — any model failure falls through to arithmetic
        pass

    return _heuristic(record), "heuristic"
