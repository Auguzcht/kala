"""Shared item generation and grading for the learn loop (diagnostic,
practice, flashcards). One RAG-grounded generator, three surfaces call it.

Correct answers never leave the server: every item is persisted with its
answer key on creation, the client only ever gets the sanitized view, and
submissions are graded by looking the item back up, not by trusting a
client-supplied "correct" flag.
"""
from __future__ import annotations

import json
import logging

from app.ai import bedrock, rag
from app.ai.errors import ModelUnavailableError
from app.ai.router import get_model_for
from app.db import supabase as db

logger = logging.getLogger(__name__)

# Why this prompt is shaped the way it is (measured, not guessed):
#
# The generator used to open with "grounded ONLY in the supplied course
# excerpt", and the payload key was literally "excerpt". The model did what
# that framing invited: it treated the material as a TEXT TO LOCATE A FACT IN
# rather than A FACT THE STUDENT MUST KNOW. Roughly 23 of 50 sampled stems came
# back as "According to the excerpt, ...", which is a citation exercise, not a
# comprehension check — the student only has to find the sentence, not know the
# thing. Scenario-framed stems (mostly on `apply` skills) almost never did this,
# which is the tell that the framing causes it rather than the model's ability.
#
# Two levers here, both deliberate:
#   1. Name the banned framings explicitly. Vague instructions ("write a good
#      question") do not move this; naming the exact token that leaks does.
#   2. Frame the task as writing a question a student answers from KNOWLEDGE,
#      with the material as the ground truth the question must agree with —
#      never as the thing the student is being asked to read.
#
# The grounding rule and the strict-JSON contract are unchanged: this rewrites
# the framing, not the safety. The banned-phrase check in _validated_mcq is the
# enforcement backstop, because a prompt is a request and a validator is a rule.
_MCQ_SYSTEM = (
    "You write a single multiple-choice question that tests whether a student "
    "KNOWS a course concept. The supplied source_material is the ground truth "
    "your question must agree with — it is NOT something the student is "
    "reading. Write the question as if the student must already know the fact, "
    "not look it up.\n\n"
    "Return strict JSON and nothing else: "
    '{"prompt": str, "choices": [{"id": "a".."d", "label": str}], '
    '"correct_choice_id": str, "explanation": str}. '
    "Write exactly four choices with exactly one correct.\n\n"
    "FORBIDDEN in the prompt and in every choice — never refer to the "
    "material itself or to a source. Do not write the words or phrases "
    "\"excerpt\", \"passage\", \"text\", \"reading\", \"overview\", "
    "\"document\", \"module\", \"chapter\", \"according to\", \"the "
    "reading states\", \"as mentioned\", \"the author\", \"the material\", "
    "or \"this section\", and do not otherwise frame the question as "
    "\"what does X say/explain/list\". A question that only works if the "
    "student can see the source is a bad question.\n\n"
    "Match the requested bloom_level: at remember/understand levels ask "
    "directly about the concept; at apply/analyze/evaluate levels, when the "
    "material supports it, frame a short concrete scenario the student must "
    "reason about. Distractors must be plausible to someone who does NOT "
    "know the concept — common misconceptions, not obviously-wrong filler.\n\n"
    "Ground every fact in the source_material: do not invent facts, numbers, "
    "or terminology that are not supported by it."
)

# Meta-referential framings that turn a comprehension question into a citation
# exercise. Checked against the stem (and choices) AFTER parsing; a hit is a
# validation failure, which generate_question already retries exactly once. See
# _MCQ_SYSTEM for why these are treated as a hard failure rather than a nudge.
_BANNED_STEM_PHRASES = (
    "according to",
    "excerpt",
    "passage",
    "the reading",
    "as mentioned",
    "the author",
    "the material",
    "this section",
    "the document",
    "the module",
)


def _find_banned_phrase(text: str) -> str | None:
    """The first banned meta-reference in `text`, or None.

    Word-boundary-ish matching via substring is enough: these phrases are long
    and specific, and a false positive costs one bounded reroll, never a
    dropped item. Case-insensitive because the model does not reliably
    capitalize consistently ("According to" vs "according to").
    """
    lowered = text.lower()
    for phrase in _BANNED_STEM_PHRASES:
        if phrase in lowered:
            return phrase
    return None

_MCQ_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "study_question",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string"},
                "choices": {
                    "type": "array",
                    "minItems": 4,
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "enum": ["a", "b", "c", "d"]},
                            "label": {"type": "string"},
                        },
                        "required": ["id", "label"],
                        "additionalProperties": False,
                    },
                },
                "correct_choice_id": {"type": "string", "enum": ["a", "b", "c", "d"]},
                "explanation": {"type": "string"},
            },
            "required": ["prompt", "choices", "correct_choice_id", "explanation"],
            "additionalProperties": False,
        },
    },
}


class ItemGenerationError(RuntimeError):
    """Raised when model output cannot form a safe study item."""


class NoCourseContentError(ItemGenerationError):
    """The skill has no grounded course content to build a question from.

    A subclass of ItemGenerationError so every existing caller/handler that
    already maps that to a clean 502 keeps working, while routers that want to
    say something more specific ("no material for this skill yet" rather than
    "could not create a question") can catch this narrower type. The message
    is student-facing: it names the missing prerequisite rather than blaming
    the model.
    """

    def __init__(self, *, skill_name: str):
        super().__init__(
            f"Kala has no course material for \"{skill_name}\" yet, so it can't "
            "write questions for it. Course content needs to be ingested first."
        )
        self.skill_name = skill_name


def _parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def _validated_mcq(raw: str) -> tuple[str, list[dict[str, str]], str, str]:
    parsed = _parse_json(raw)
    prompt = parsed.get("prompt")
    choices = parsed.get("choices")
    correct_choice_id = parsed.get("correct_choice_id")
    explanation = parsed.get("explanation", "")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("generated item is missing a prompt")
    # The stem must test knowledge, not point at a source. "According to the
    # excerpt, what does X explain?" is a citation exercise: the student finds
    # the sentence instead of recalling the concept. generate_question retries
    # a validation failure exactly once, so a meta-referential stem gets one
    # reroll rather than shipping — that is the intended behavior here, not a
    # reason to soften the check.
    banned = _find_banned_phrase(prompt)
    if banned:
        raise ValueError(f"generated prompt is meta-referential (contains {banned!r})")
    if not isinstance(choices, list) or len(choices) != 4:
        raise ValueError("generated item must contain exactly four choices")
    if not isinstance(correct_choice_id, str) or not isinstance(explanation, str):
        raise ValueError("generated item has invalid answer metadata")

    expected_ids = {"a", "b", "c", "d"}
    actual_ids: set[str] = set()
    validated: list[dict[str, str]] = []
    for choice in choices:
        if not isinstance(choice, dict):
            raise ValueError("generated choice must be an object")
        choice_id, label = choice.get("id"), choice.get("label")
        if not isinstance(choice_id, str) or not isinstance(label, str) or not label.strip():
            raise ValueError("generated choice is missing an id or label")
        # Same meta-reference ban on choices: "The excerpt says ..." as an
        # option is the same failure one level down.
        banned_choice = _find_banned_phrase(label)
        if banned_choice:
            raise ValueError(f"generated choice is meta-referential (contains {banned_choice!r})")
        actual_ids.add(choice_id)
        validated.append({"id": choice_id, "label": label.strip()})
    if actual_ids != expected_ids or correct_choice_id not in expected_ids:
        raise ValueError("generated choices must be a, b, c, and d")
    return prompt.strip(), validated, correct_choice_id, explanation.strip()


# How many chunks RAG pulls per skill. Widened from 3 to 5 (retrieve's own
# default) so a skill with real depth hands the model more DISTINCT facts to
# draw on. Measured effect: repetition tracks corpus DEPTH, not size — a 1-2
# chunk skill still repeats, and no prompt fixes that (it is a content problem;
# the real fix is staff uploading the AWS PDFs). But on skills with 4+ chunks
# the wider window plus the round-robin in _context_for is what actually
# spreads a batch across facts. Token budget checked: 5 chunks at the corpus's
# observed chunk size stays far under _MAX_CONTEXT_CHARS, and max_tokens in
# _call_and_validate is sized for the worst case per the max_tokens rule.
_RETRIEVAL_K = 5

# Ceiling on the joined context handed to the model. The max_tokens rule says
# size for the LONGEST realistic input, not the typical one: a reasoning model
# bills its thinking against max_tokens, and an undersized budget returns EMPTY
# content rather than an error, which reads as "the model found nothing". This
# bound plus the 2048-token response budget in _call_and_validate is the pair
# that has to stay comfortable, so the context is trimmed here, visibly, rather
# than silently truncated by the provider.
_MAX_CONTEXT_CHARS = 12000


def _context_for(*, institution_id: str, course_id: str, skill: dict) -> list[str]:
    """Grounded course text for a skill, or raise if there is none.

    Returns a LIST of individual chunk texts, not one joined blob, so the
    caller can hand each batch roll a different slice (see _rotated_context).
    Joining here and re-splitting downstream would be fragile — a chunk can
    itself contain "---".
    This USED to fall back to `skill["name"]` when retrieval came back empty,
    with a comment about "degrading gracefully rather than hard-failing the
    learn loop". That was the wrong trade: it turned a loud, visible
    misconfiguration into SILENT GARBAGE. With no excerpt, the model is asked
    to write an evaluative MCQ grounded in a single sentence, so it rewords
    that sentence into a stem, makes the skill's own phrase the correct answer
    every time ("operational and cost trade-offs"), and invents nonsense
    distractors ("social media engagement metrics") because it has no facts to
    draw plausible wrong answers from. Every item passes schema validation, so
    nothing flagged it — the questions were simply meaningless, which is the
    worst possible failure for a student studying for board exams.

    A course with skills but no content_items is a setup error (ingest has not
    run), not a runtime condition to paper over. Fail it here, at the source,
    so every caller surfaces "no material yet" instead of shipping plausible-
    looking questions with no substance.
    """
    chunks = rag.retrieve(
        institution_id=institution_id, course_id=course_id, query=skill["name"],
        k=_RETRIEVAL_K,
    )
    # Filter to chunks that actually carry text BEFORE joining. Joining first
    # and stripping the result is not enough: blank chunks still contribute
    # separators, so "  " + "" join to "   \n---\n" which survives a strip and
    # reads as grounded content.
    texts = [(c.get("chunk_text") or "").strip() for c in chunks]
    texts = [t for t in texts if t]
    if not texts:
        raise NoCourseContentError(skill_name=skill.get("name") or "this skill")
    return texts


def _rotated_context(chunks: list[str], offset: int) -> str:
    """The grounding text for ONE batch roll: the chunk list rotated so a
    different chunk leads each time, then joined.

    Why rotation rather than the identical joined excerpt for every roll:
    batch generation runs N INDEPENDENT calls (map_concurrent_partial over
    range(size) — see routers/practice.py). They cannot see each other's stems,
    so with an identical prompt and identical context they tend to reach for
    the same top-ranked chunk and produce "4 of 5 questions rephrase one fact"
    on skills that DO have depth. Rotating the lead chunk changes which fact is
    most salient to each roll, which is the cheapest available lever: no extra
    model calls, no regeneration path, no new filtering stage.

    All chunks stay present in every slice — only the order changes — so this
    can never ground a question in less material than before, it just changes
    what the model attends to first. On a 1-2 chunk skill there is nothing to
    rotate and every roll matches, which is expected and is a content
    limitation, not a bug.
    """
    if not chunks:
        raise ValueError("_rotated_context requires at least one chunk")
    start = offset % len(chunks)
    ordered = chunks[start:] + chunks[:start]
    joined = "\n---\n".join(ordered)
    if len(joined) > _MAX_CONTEXT_CHARS:
        # Trim on a chunk boundary where possible so the model never sees a
        # half-sentence that reads as a complete fact.
        joined = joined[:_MAX_CONTEXT_CHARS].rsplit("\n---\n", 1)[0] or joined[:_MAX_CONTEXT_CHARS]
    return joined


def _call_and_validate(*, skill: dict, context: str) -> tuple[str, list[dict[str, str]], str, str]:
    """One model call, parsed and validated. Raises on anything unusable —
    a transport failure, a malformed/truncated body, or a semantically invalid
    MCQ. The caller decides whether to try again."""
    raw = bedrock.converse(
        model_id=get_model_for("item"),
        system=_MCQ_SYSTEM,
        messages=[{"role": "user", "content": [{"text": json.dumps({
            "skill": skill["name"], "bloom_level": skill.get("bloom_level"),
            # Deliberately NOT "excerpt". That key primed the model to write
            # "According to the excerpt, ..." stems — the exact token leaked
            # from the payload key into the question. A neutral name removes
            # the invitation. See _MCQ_SYSTEM.
            "source_material": context,
        })}]}],
        # Sized for the LONGEST realistic input, not the typical one: the
        # system prompt is long, the context now spans up to 5 chunks, and a
        # reasoning model bills its thinking against THIS budget. Too small
        # returns empty content, not an error. Was 1536, raised to 2048 to keep
        # headroom over the wider context rather than sit at the edge of it.
        max_tokens=2048,
        response_format=_MCQ_RESPONSE_FORMAT,
    )
    return _validated_mcq(raw)


def generate_question(*, institution_id: str, course_id: str, skill: dict, kind: str,
                      set_id: str | None = None, context_offset: int = 0) -> dict:
    """Generate one RAG-grounded MCQ for a skill, persist it with its answer
    key, and return only the client-safe view.

    `set_id` groups the item under a quiz_sets row (batch practice generation,
    see routers/practice.py). Optional and backward-compatible: every existing
    caller omits it and gets an ungrouped item exactly as before. Threaded into
    the insert rather than patched after, so an item is never briefly persisted
    outside the set it was generated for.

    `context_offset` selects which retrieved chunk LEADS the grounding text for
    this roll (see _rotated_context). Batch callers pass each roll a different
    offset so independent rolls do not all fixate on the same top chunk. The
    single-item path omits it and gets offset 0, i.e. the plain ranked order —
    unchanged behavior for every existing caller.

    One bounded retry on a VALIDATION failure. This is a distinct failure mode
    from the transport/capability retry inside bedrock.converse: that one
    catches a call that could not be delivered (5xx, timeout, structured-output
    rejection). Here the HTTP call succeeded but the body was unusable —
    malformed or truncated JSON, or a semantically wrong MCQ — which
    _validated_mcq rejects. Those are independent events, so they get
    independent retries; a free-tier model that returns garbage once will very
    often return a good item on a second roll, and without this the failure
    propagates straight out of map_concurrent (which is all-or-nothing by
    design) and 502s an entire batch because ONE of five concurrent rolls was
    bad. Retried once, never looped: a model that fails twice in a row is a
    real signal, not something to keep hammering.
    """
    context = _rotated_context(
        _context_for(institution_id=institution_id, course_id=course_id, skill=skill),
        context_offset,
    )
    try:
        try:
            prompt, choices, correct_choice_id, explanation = _call_and_validate(
                skill=skill, context=context,
            )
        except ModelUnavailableError:
            # A provider-side failure (429, 5xx, timeout, retired model). This
            # is NOT a validation failure: bedrock.converse already gave it one
            # cross-provider fallback attempt, and retrying it here would just
            # hammer the same rate limit a second time. Surface it as-is.
            raise
        except Exception as first_exc:
            logger.warning(
                "Generated item failed validation, retrying once "
                "(course=%s skill=%s kind=%s): %s",
                course_id, skill.get("id"), kind, first_exc,
            )
            prompt, choices, correct_choice_id, explanation = _call_and_validate(
                skill=skill, context=context,
            )
    except Exception as exc:
        logger.error(
            "Refusing to store an invalid generated item (course=%s skill=%s kind=%s): %s",
            course_id,
            skill.get("id"),
            kind,
            exc,
        )
        raise ItemGenerationError(
            "Kala could not create a valid question. Please try again."
        ) from exc

    item_row = {
        "institution_id": institution_id,
        "course_id": course_id,
        "skill_id": skill["id"],
        "kind": kind,
        "bloom_level": skill.get("bloom_level"),
        "prompt": prompt,
        "choices": choices,
        "correct_choice_id": correct_choice_id,
        "explanation": explanation,
    }
    if set_id is not None:
        item_row["set_id"] = set_id
    rows = db.insert("generated_items", [item_row])
    item = rows[0]
    return {
        "id": item["id"],
        "skillId": skill["id"],
        "bloomLevel": skill.get("bloom_level"),
        "prompt": prompt,
        "choices": choices,
    }


def grade(*, institution_id: str, item_id: str, choice_id: str) -> dict:
    """Look up the stored answer key and grade server-side."""
    rows = db.select("generated_items", {
        "id": f"eq.{item_id}", "institution_id": f"eq.{institution_id}",
        "select": "id,skill_id,course_id,correct_choice_id,explanation,set_id", "limit": "1",
    })
    if not rows:
        raise ValueError(f"item {item_id} not found")
    item = rows[0]
    correct = choice_id == item["correct_choice_id"]
    return {
        "skillId": item["skill_id"],
        "courseId": item["course_id"],
        "correct": correct,
        "explanation": item.get("explanation") or "",
        # Which quiz set this item belonged to, if any. Ungrouped items
        # (/next, flashcards, tutor checks) have set_id null and the caller
        # (practice.submit) simply skips the attempt bookkeeping for them.
        "setId": item.get("set_id"),
    }


def correct_label(item: dict) -> str | None:
    """The label of an item's correct choice, or None if choices/answer are
    missing (defensive — bad data degrades to a null label, never a crash).

    This is the one place that resolves an answer key to a human-readable
    label. Study mode's flip-back uses it (see routers/flashcards.py), so the
    flashcard deck never has to re-implement the lookup. It does NOT leak a
    full answer key: it returns a single label string, which the study
    endpoint is allowed to show; grading still happens server-side against
    correct_choice_id, never against this label.
    """
    choices = item.get("choices") or []
    return next(
        (c.get("label") for c in choices if c.get("id") == item.get("correct_choice_id")),
        None,
    )


def weakest_skill(*, institution_id: str, user_id: str, course_id: str) -> dict | None:
    """Pick the skill this student is weakest on for practice: lowest
    mastery estimate, with never-attempted skills ranked weakest of all."""
    skills = db.select("skills", {
        "institution_id": f"eq.{institution_id}", "course_id": f"eq.{course_id}",
        "status": "eq.approved",
        "select": "id,name,bloom_level",
    })
    if not skills:
        return None
    mastery = db.select("mastery_state", {
        "institution_id": f"eq.{institution_id}", "user_id": f"eq.{user_id}",
        "course_id": f"eq.{course_id}", "select": "skill_id,estimate",
    })
    estimates = {m["skill_id"]: float(m["estimate"]) for m in mastery}
    return min(skills, key=lambda s: estimates.get(s["id"], -1.0))
