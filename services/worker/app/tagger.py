"""Content tagging for the worker's tag-backfill job. Deliberate trimmed
duplicate of the tag path in services/api/app/ai/router.py + bedrock.py:
the same single-chunk classify-against-approved-skills call, the same
model role, the same 4096-token reasoning budget, and the same
prompt-enforced-JSON parsing — but tag_content() only. The worker never
calls converse() for anything else, so the rest of bedrock.py is not
reproduced here.

Why this file exists at all: the worker's Dockerfile only `COPY app ./app`
and cannot see services/api's source tree (see app/handler.py's module
docstring). app/embed.py is the established precedent — a trimmed copy of
the api's embed path living in the worker tree. This is the same move for
the tagger.

KEEP IN SYNC with services/api/app/ai/router.py `tag_content` and
bedrock.py `_openrouter_converse`/`_openrouter_post` if either changes:
- the model role (fast/tag) and its config key (openrouter_model_fast)
- the 4096 max_tokens floor (a reasoning model bills its thinking against
  max_tokens; 256/2048 both truncated the answer away on long pages —
  size for the LONGEST realistic input, not the typical one)
- the system prompt and the skill_id/bloom_level validation
Grep both trees for `tag_content` before changing either.

This module talks to OpenRouter directly (same as embed.py) rather than
importing the api's bedrock module. It intentionally does NOT reproduce
the cross-provider fallback in the api's converse(): the worker is a
background job on a 120s Lambda with no user waiting, so a transient
failure is simply left for the next scheduled run (the job does not mark
tag_attempted_at on an exception — see tag_backfill.py), which is a
better fit than an in-call fallback here.
"""
from __future__ import annotations

import json
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("kala.worker")

# Same floor as services/api/app/ai/router.py. See that file's comment and
# this module's docstring: a reasoning model spends 2500-3500 tokens thinking
# on a long module page before it answers, and that thinking is billed here.
# Below 4096 the JSON answer is truncated away and reads as "no match".
_TAG_MAX_TOKENS = 4096

_BLOOM_LEVELS = {"remember", "understand", "apply", "analyze", "evaluate", "create"}

_SYSTEM = (
    "Tag the supplied course content. Return only JSON with keys "
    "skill_id and bloom_level. skill_id must be one of the supplied IDs "
    "or null; bloom_level must be one of remember, understand, apply, "
    "analyze, evaluate, create or null."
)


def _openrouter_client() -> httpx.Client:
    s = get_settings()
    return httpx.Client(
        base_url=s.openrouter_base_url,
        headers={
            "Authorization": f"Bearer {s.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://kala.mmcm.edu.ph",
            "X-Title": "Kala",
        },
        # 120s, NOT the api's 8s. This is the whole reason tagging moved here:
        # the api client is 8s because it runs inside a 30s user-facing Lambda,
        # which is far too tight for a tag call that measured 3-150s. The
        # worker Lambda's ceiling is 120s (infra/terraform/lambda.tf), so a
        # single slow tag call can actually complete instead of being killed
        # mid-flight. A call that still overruns 120s is left unmarked and
        # retried next run, same as any other transient failure.
        timeout=120.0,
    )


def tag_content(*, text: str, skills: list[dict]) -> dict:
    """Classify one chunk against the course's approved skills.

    Returns {"skill_id": <id or None>, "bloom_level": <level or None>}.
    A skill_id not in the supplied candidate list, or a bloom level outside
    the fixed set, is coerced to None (never trust a hallucinated id into a
    row). Raises on transport/HTTP failure so the caller can leave the chunk
    unmarked for a later retry — an empty/garbage MODEL answer is NOT an
    exception, it returns {"skill_id": None, ...} (a real no-match), and the
    caller marks it attempted. This mirrors the api's tag_content contract.
    """
    s = get_settings()
    model_id = s.openrouter_model_fast
    skill_list = [{"id": skill["id"], "name": skill["name"]} for skill in skills]

    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": json.dumps({"skills": skill_list, "content": text})},
        ],
        "max_tokens": _TAG_MAX_TOKENS,
        "temperature": 0.2,
    }
    with _openrouter_client() as c:
        r = c.post("/chat/completions", json=payload)
        r.raise_for_status()  # transport/HTTP errors propagate — caller retries
        data = r.json()

    raw = _content(data)
    normalized = raw.strip()
    if normalized.startswith("```"):
        normalized = normalized.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        result = json.loads(normalized)
    except json.JSONDecodeError:
        # Empty or unparseable body. This is a genuine "no usable answer",
        # distinct from a transport failure: it is returned as no-match (not
        # raised), so the caller marks the chunk attempted rather than
        # retrying it forever. Logged because an empty body and a real
        # no-match are indistinguishable in the return value, and that
        # ambiguity is exactly what hid the token-budget bug for a whole
        # session.
        logger.warning(
            "tag_content got no usable JSON (len(raw)=%d, model=%s). Treating as no match.",
            len(raw), model_id,
        )
        return {"skill_id": None, "bloom_level": None}

    skill_ids = {skill["id"] for skill in skills}
    got_skill = result.get("skill_id")
    got_bloom = result.get("bloom_level")
    return {
        "skill_id": got_skill if got_skill in skill_ids else None,
        "bloom_level": got_bloom if got_bloom in _BLOOM_LEVELS else None,
    }


def _content(data: dict) -> str:
    """Assistant text from a chat-completion response, tolerating the two
    shapes that otherwise blow up downstream: a null content (some models
    emit only a reasoning field) and an empty choices array. Returns '' in
    both cases, which _content's caller treats as no-match."""
    choices = data.get("choices") or []
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content") or ""
