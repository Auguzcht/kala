# `/tutor/ask` returns 503 — the 30s Lambda wall, fourth instance

Found 2026-09-21 while verifying the frontend after the API redeploy. **Not a
frontend bug, and not caused by the sidebar crash** — confirmed independently.

## What happens

```
POST /tutor/ask                     -> 503 {"message":"Service Unavailable"}  (30.2s)
```

Both paths fail identically:

| path | result |
|---|---|
| with `conversation_id` | 503 after ~30s |
| without (stateless, used by Lessons hint and Quiz explain) | 503 after 30.2s |

## Cause

Lambda killed at exactly `Duration: 30000.00 ms ... Status: timeout`.

The handler does RAG retrieval, then a model generation, **in the request**:

```
1. rag.retrieve          -> embeddings call          ~1-2s
2. db.select attachments                             ~0.2s
3. db.select history                                 ~0.2s
4. model_router.answer   -> OpenRouter converse      the rest, and it is not bounded
```

Measured the model directly against the same configured endpoint
(`deepseek/deepseek-v4.1-flash:floor`): a two-token question — literally
"Say OK" — took **11.2 seconds** at `max_tokens: 64`, and it still emitted a
reasoning trace. The tutor asks for `max_tokens=2048` against a grounded
prompt containing retrieved chunks, history, and attachments. Reasoning length
scales with input length (the `max_tokens` rule stated at `converse()` in
`ai/bedrock.py`), so the call easily consumes the ~27s left after retrieval.

## Why it matters beyond tutor

This is the **fourth** instance of one shape: unbounded work behind a
request-response door.

| surface | status |
|---|---|
| tagging (one LLM call per chunk) | fixed — moved to the worker |
| ingest tree walk | fixed — moved to the worker, checkpointed |
| practice set generation (5 concurrent calls) | logged, not fixed |
| **`/tutor/ask` (one generation)** | **this one** |

`/tutor/ask` is the hardest case of the four, because unlike the others it is
inherently interactive — a student is waiting on the answer. It cannot simply
be moved to a scheduled worker. Options, none of them a constant to tune:

1. **Stream the response** (SSE / Lambda response streaming). Removes the
   generate-then-return shape entirely; the first token returns well inside
   the wall. The frontend already has `AssistantBlock`'s streaming renderer
   and `StudyStream` for it. Biggest change, best fit.
2. **Async job + poll** (the ingest pattern). Wrong shape for a chat: a
   student waiting on a poll loop is worse than a spinner.
3. **Smaller budget / faster model.** A real lever but not a fix — it moves
   the cliff to the next-longer answer, which is the same mistake as raising a
   timeout. It also conflicts with the `max_tokens` rule: shrinking the budget
   on a reasoning model risks empty content, which reads as "the model found
   nothing" rather than an error.

## The guardrail question, answered

The bundle asked what "never the answer to something graded" maps to. It is:

```python
_SYSTEM = (
    "You are Kala, a study tutor. Teach and give hints. Never reveal answers to graded work."
    ...
)
```

**Prompt-only, one sentence, no enforcement anywhere.** There is no check that
the model complied — no output filter, no refusal path, no separate policy.

It is **not shared** as a component: `_SYSTEM` lives in `routers/tutor.py` and
is appended to per style. The other `model_router.answer` callers
(`ai/skill_proposer.py`, `ai/prescriber.py`) are instructor-side generation and
are not the same policy at all — they are not student-facing.

Lessons' Hint and Quiz's explain do **not** have separate implementations:
they call the tutor's stateless `/tutor/ask` with a style hint, so they inherit
this exact prompt. That is the good news — one policy, already uniform. The
gap is that the policy is a sentence in a string rather than something checked.

So the copy is **roughly accurate** ("answers grounded in the actual course
content, and never the answer to something graded" describes what the prompt
asks for) but it is a description of an instruction, not of an enforced
behavior. Worth an explicit decision about whether to enforce it, not a copy
rewrite.

## Status

Not fixed. Needs a product decision on streaming vs something else before code.
