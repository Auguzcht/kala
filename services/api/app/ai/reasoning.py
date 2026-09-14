"""Post-processing for model prose output.

Why this exists: the interim OpenRouter free-tier models (see config.py) are
reasoning-style models that sometimes emit their chain of thought *into the
message content* rather than a separate reasoning channel — e.g. an answer
that literally begins "Here's a thinking process:\n\n1. **Analyze User
Input:** …". Two consequences, both observed live in the lesson Explain flow:

  1. The student sees the model's internal monologue, which is both confusing
     (it restates the prompt and grades itself) and off-brief (Kala must not
     surface reasoning traces to learners).
  2. The preamble is long enough to consume the response's token budget, so
     the actual answer never arrives — the reply truncates mid-sentence.

Prompting alone is not a reliable fix for a free model, so this strips the
leak defensively on the way out. It only ever removes a *leading* preamble;
the real answer is preserved verbatim. Both Bedrock and OpenRouter paths pass
through here, so swapping providers later needs no change.
"""
from __future__ import annotations

import re

# A leading self-identification line: the model restating its own name on
# its own line ("Kala", "Kala:", "As Kala…"). The interface already labels
# every assistant message, so this is always redundant chrome — and when it
# slipped through it was the second of two stacked "Kala" headings on screen.
_SELF_ID = re.compile(
    r"^\s*(?:as\s+)?kala\s*[:.\-—]?\s*\n+",
    re.IGNORECASE,
)

# A leading "thinking"/"reasoning"/"analysis" preamble, with or without a
# self-identification line ("Kala") above it, up to and including the blank
# line that ends it. Matched case-insensitively and non-greedily so it stops
# at the first paragraph break after the heading it found.
#
# Everything before the FIRST real content line is dropped, which is why this
# is anchored at the string start and refuses to run if nothing matches.
_PREAMBLE_HEADING = re.compile(
    r"""^\s*
    (?: (?:i\s*am\s*)?kala [\s:.\-—]*\n+ )?          # optional self-id line
    (?: here(?:'|’)s\s+(?:my\s+)?(?:a\s+)? )?        # optional "Here's a…"
    (?: thinking(?:\s+process)? | reasoning | thought\s+process |
        analysis | chain\s+of\s+thought )
    [^\n]* \n                                        # rest of the heading line
    (?: .*? \n\n )?                                  # the preamble block, if any
    """,
    re.IGNORECASE | re.VERBOSE | re.DOTALL,
)

# The numbered/bulleted self-interrogation shape the leak usually takes
# ("1. **Analyze User Input:**", "- **Task:** …"). Used only as a secondary
# signal so we don't strip a legitimate answer that happens to start with a
# list — we require the coaching vocabulary these preambles always contain.
_COACHING_MARKERS = (
    "analyze user input",
    "analyze the user",
    "deconstruct the",
    "identify the core task",
    "self-correction",
    "self correction",
    "my task:",
    "formulate the",
    "draft:",
    "check constraints",
    "refinement",
)


def _looks_like_reasoning(block: str) -> bool:
    """True if this leading block reads like an internal monologue rather
    than an answer. Deliberately narrow: a real answer can be a numbered
    list, so the list shape alone proves nothing — at least one of the
    coaching phrases these preambles reliably contain must also be present.
    """
    lowered = block.lower()
    return any(marker in lowered for marker in _COACHING_MARKERS)


def strip_reasoning(text: str) -> str:
    """Remove a leaked chain-of-thought preamble from the front of `text`.

    Returns the text unchanged when there is nothing to strip, and falls back
    to the original text if stripping would leave nothing behind (better to
    show a slightly noisy answer than an empty one).
    """
    if not text:
        return text

    candidate = text

    match = _PREAMBLE_HEADING.match(candidate)
    if match and _looks_like_reasoning(candidate[: max(match.end(), 400)]):
        candidate = candidate[match.end():].lstrip()

    # Some models skip the heading and open straight into the numbered
    # self-analysis. Catch that by scanning the first block only.
    if candidate is text or not candidate:
        head, sep, _rest = candidate.partition("\n\n")
        if sep and _looks_like_reasoning(head) and "**" in head:
            candidate = _rest.lstrip()

    # Drop a lone leading self-identification line last, so it is removed
    # whether or not a preamble followed it. Safe on its own: a reply whose
    # first line is exactly "Kala" is never real content.
    candidate = _SELF_ID.sub("", candidate, count=1)

    candidate = candidate.strip()
    if not candidate:
        return text.strip()
    return candidate
