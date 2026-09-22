# Model benchmark: ling-3.0 vs deepseek across the three real prompts

Measured 2026-09-22, on the live endpoint with REAL inputs (a 4000-char
content chunk, the 10 approved AWS101 skills, and the actual prompt
constants imported from the app — not retyped).

## The correction that prompted this

The earlier "provider routing" fix was diagnosed from a BAD benchmark: a
two-sentence prompt at `max_tokens: 768` measured 2.8-8.5s, so I concluded
provider choice was the variable. On the REAL tutor prompt (4052 chars,
`max_tokens: 2048`) the same model takes **34-103s**. The benchmark was sized
to the small case and generalised to the large one, which is the same error
as measuring ingest on the smallest course.

## Results

| prompt | model | latency | usable? |
|---|---|---|---|
| **tutor** (4052 chars, 2048 tok) | ling-3.0 | **10.2s, 15.9s** | yes, coherent |
| | deepseek | 67.3s, 103.4s | yes, but far past the 30s wall |
| **tagging** (5859 chars, 4096 tok) | ling-3.0 | 64.5s, 46.6s | **NO — wrong shape** |
| | deepseek | 47.2s, **168.0s** | **1 of 2 EMPTY** |
| **item** (4467 chars, 2048 tok, +schema) | ling-3.0 | 0.8s | **NO — HTTP 400** |
| | deepseek | 51.2s, 81.7s | yes, well-formed MCQ |

## Three separate findings, not one

**1. TUTOR — ling-3.0 is a clear win.** 10-16s vs 67-103s, both return
coherent grounded answers. Only ling-3.0 fits inside the 30s Lambda wall.

**2. TAGGING — BOTH models are broken, differently.** This is the important
one and it validates the original free-model concern, but not in the way
expected.

*deepseek returned `finish_reason=length` with `content=None`* on run 2 — it
burned the entire 4096-token budget on reasoning and emitted nothing. That is
precisely the empty-tag failure the 256 -> 2048 -> 4096 raises were meant to
fix, and **4096 is no longer sufficient for a 4000-char chunk**. The bug is
back on the largest content, which is the same "looks fixed while silently
failing on exactly the valuable content" trap documented in the original fix.

*ling-3.0 returned an ARRAY instead of an object.* The prompt asks for one
`{"skill_id","bloom_level"}`; ling returned a JSON list with one entry per
skill supplied. `tag_content` calls `result.get(...)`, and a list has no
`.get`, so this raises `AttributeError` at runtime. The worker's per-chunk
`except Exception` would swallow it and leave the chunk untagged-but-retried
— tagging would silently never complete, the exact failure mode this project
has hit repeatedly.

So ling-3.0 is NOT a drop-in for tagging without a prompt/parser change.

**3. ITEM — ling-3.0 cannot do it at all.** HTTP 400 from the provider:

```
"model features structured outputs not support"
```

`_MCQ_RESPONSE_FORMAT` is a strict JSON schema, and ling-3.0's provider
(Novita) does not support structured outputs. deepseek produces well-formed
4-choice MCQs with `correct_choice_id`, but takes 51-82s.

## The practice-generation timeout, answered

The standing "practice set generation intermittently times out" bug from
earlier in this project **is the same root cause**, confirmed: item generation
takes 51-82s per call on deepseek, and `POST /practice/{id}/set` fans out
N=5 concurrently. That was never 5x slower — it was the same 30s wall against
a call that takes 50-80s on its own.

## What this implies (no changes made yet)

| role | ling-3.0 viable? |
|---|---|
| tutor (`default`) | **yes** — 10-16s, coherent |
| tag (`fast`) | no, as-is — wrong response shape; needs prompt+parser work |
| item | no — provider lacks structured outputs |
| lesson step 1 (`reasoning`) | already ling-3.0, already fast (1.8-2.4s) |

A role-by-role assignment is therefore possible for tutor only. Tagging and
item generation need a different answer: a faster STRUCTURED-OUTPUT-capable
model, or moving them off the request path (tagging already is; item
generation is the one still on it).

## Caveats

- Small samples (2-3 runs per cell) against a load-balanced endpoint whose
  provider mix changes. Latencies are indicative, not distributions.
- Only the 4000-char chunk was tested for tagging. The `finish_reason=length`
  failure may be specific to that size; smaller chunks may still fit in 4096.
- No quality judgement beyond "coherent" / "well-formed" — a human should read
  actual outputs before any role is switched.
