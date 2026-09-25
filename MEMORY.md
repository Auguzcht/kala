# Project Memory

## Project Overview

**Kala** — AI learning companion / digital learning twin for the **LMS (Blackboard)**.
Not a competitor to the LMS: it reads Blackboard as source of truth and produces
what the LMS can't — a longitudinal, Bloom's-aligned learner model plus
early-warning analytics for teachers. Entered via **LTI 1.3** from inside a course.

Pilot: **Mapua Malayan Colleges Mindanao**, College of Engineering and Architecture.
Hard demo deadline: **September 1**.

Reference product for feel: **Gizmo.AI** (deck → subdeck → generated lesson/quiz/
flashcard). Kala's difference is ingest: it reads Blackboard content, not
user-uploaded material.

---

## Key Architecture / Decisions

### Stack
- `apps/web` — React + Vite SPA, TanStack Router/Query, Zustand (ephemeral UI only),
  shadcn. Server data → TanStack Query. Auth/session → Supabase. Never mirror server
  data into Zustand.
- `services/api` — FastAPI on Lambda (`kala-api`, **30s wall**, API Gateway also 30s).
- `services/worker` — `kala-worker`, **120s timeout**, EventBridge every 15 min.
  Four jobs in order: `reconcileMastery` → `embedBackfill` → `tagBackfill` → `readinessSnapshot`.
- `packages/db` — SQL migrations + RLS. `packages/schema` — generated types.
- Both API and worker are **image-based Lambdas** on ECR `:latest`.

### Multi-tenancy (non-negotiable)
Every row carries `institution_id`. Tenant resolves from the LTI launch
(`iss` + `deployment_id`), never a signup. Enforced by Postgres RLS.

### Auth
LTI launch → FastAPI validates → mints a Supabase-compatible JWT. The frontend never
runs its own login for the LTI path. Never trust a client-supplied `institution_id`
or `role`.

### Two-layer staff gate (the pattern used everywhere)
`require_role("instructor","admin")` proves staff **somewhere**; a second check
(`_assert_teaches_course`, or dashboard's `_assert_teaches_student`) proves staff of
**THIS course**. 404 not 403 so an unauthorized staffer can't probe which ids exist.
Route-level role alone is insufficient whenever `course_id` comes from the path.

### Models (OpenRouter, interim until real Bedrock in the school's AWS org)
`AI_PROVIDER=openrouter`. Config defaults in `services/api/app/config.py`:
- `openrouter_model_item`, `_default`, `_fast`(=`tag`), `_fallback` →
  **`deepseek/deepseek-v4.1-flash:floor`**
- `_reasoning`, `_premium` → `inclusionai/ling-3.0-flash-vl` (paid slug; the `:free`
  variant now returns HTTP 404 "unavailable for free")
- `openrouter_model_chat` → same ling paid slug; `openrouter_model_chat_fallback` →
  `nex-agi/nex-n2.5-mini:free`
- **The `chat` role is tutor-only.** `default` also serves lessons phase 2
  (`learn/lessons.py:131`), skill_proposer and prescriber — repointing `default`
  moves four surfaces at once. `converse()` takes `fallback_model_id=None`; only
  the tutor passes a chat-specific fallback, everyone else keeps the global one.

**THE `max_tokens` RULE** (documented at `bedrock.py:converse`, read it before adding
a caller): reasoning models bill their thinking against `max_tokens`. A budget too
small returns **empty content**, not an error — so it surfaces as a null/parse
failure and reads as "the model found nothing". **Size for the LONGEST realistic
input, not the typical one.** Floor 1024; 4096 for document-sized input.
This bug cost **three** debugging rounds (`generate_question` 768→1536;
`tag_content` 256→2048→4096). Even 4096 is now insufficient for the largest chunks
(deepseek `finish_reason=length, content=None` on a 4000-char chunk).

### Tagging lives in the WORKER, not the API
Measured: one tag call takes **3-150s** and a single call can exceed 30s. No batch
size or time-slice fits a 30s request. So `/ingest` and `/content/upload` **store +
embed only**; the worker's `tagBackfill` tags on its 120s ceiling.

`_tag_pending`'s four failure semantics are load-bearing — do not simplify:
- transport failure → left **UNMARKED**, retried next run
- genuine no-match → **MARKED** (else untaggable content loops forever)
- no approved skills → left UNMARKED (so approving skills later tags it, no re-POST)
- empty text → marked attempted

### Content pipeline
`content_items` rows are the progress record (no job table, no cursor):
`skill_id` set = tagged · `tag_attempted_at` set + no skill = matched nothing ·
both null = pending.
`POST /content/retag` nulls `tag_attempted_at` on unmatched rows — the lever that
makes "approve skills → worker tags them" work. **Approving skills does NOT retry
on its own**, because attempted rows are excluded from the pending query.

---

## Current State

### Latest verification — 2026-09-25

- **Async lesson checks are live and verified end to end.** The API first-open
  returned HTTP 200 in 18.4s with five ready teaching steps and null checks;
  three worker invocations claimed `2 + 2 + 1` lesson jobs, all five completed
  with `item_id` values, and the later lesson GET returned all five real checks.
  API Lambda `CodeSha256` matched ECR `kala-api:latest`.
- **Tutor conversation switching was traced at the component lifecycle level.**
  The `/course/tutor` route persists the same `TutorChat` instance when only the
  `conversation` search param changes; there is no key-based remount. That is
  safe because `TutorChat` has an effect keyed on `activeId` which clears both
  `pendingTurn` and `lastQuestion` on an external conversation switch. A live
  Chrome reproduction was not claimed because browser automation access was
  unavailable during verification.
- **Practice cold-generation is explicitly accepted on shared-plumbing evidence
  for this pass, not silently marked live-verified.** The API route tests cover
  the generating response and stable set/job creation, the worker tests cover
  practice job claiming/completion, the shared item-generation worker path is
  live-verified by diagnostic and lesson checks, and the frontend polls the
  stable set URL without re-POSTing. A dedicated cold practice POST → worker →
  ready run remains an optional follow-up, not an unrecorded gap.

### Deployed and verified (newest first)
- **API `09:53Z` 2026-09-24**, worker `09:53Z` — both `State=Active`, update
  `Successful`. ECR `:latest` digest == deployed `CodeSha256` (verified).
- Piece 1 is LIVE and verified on the real path: `POST /tutor/ask` → **HTTP 200 in
  7.5s**, grounded well-formed answer. The old 500/503 (deepseek too slow for the
  30s wall) is gone; the chat role now uses ling-3.0 paid + nex fallback.
- Piece 0b (partial-tolerant diagnostic) is LIVE; **it does NOT fix the cold
  start** — with the question bank EMPTY and Piece 2 not deployed, the diagnostic
  GET still blows the 30s wall (deepseek item gen inline) → 503. **Blocked on
  Piece 2**, which is the remaining live failure.
- Migrations through **0018** applied (the ingest/dedupe/backoff pair).
- **Corpus grew after the PDF ingest run: `pdfs_fetched=8`,
  `pdf_chunks_live=15`, 72 folders expanded; content rows 88 → 120+; embedded 103;
  tagged 42; pending 0.** The 8 PDFs include the two AWS teaching docs (5 + 4
  chunks) — the REAL material, via embedded-attachment extraction (see Notes).
- **296 API tests, 39 worker tests passing.** Ruff non-blocking (163 errors repo-wide).

### Done since the last memory write (28 commits, `964db50`..`874eeb9`)

**Live-ingest round 1 (Piece 0a)** — real Blackboard PDF ingest ran and completed:
`folders_expanded=72`, `pdfs_fetched=8`, `pdf_chunks_live=15`, content 88→120+,
embedded 103, tagged 42, pending 0 — incl. the two AWS teaching docs (5 + 4
chunks). Job `40742dba-…`. Engines at
`docs/bugs/model-latency-and-capability-benchmark.md`.

**Inline-image + embedded-PDF extraction** — `lms/base.py` + worker chunking now pull
images/attachments out of Ultra document bodies (c0b2b72 path).

**Ingest pipeline hardening** — retry-after backoff + persisted dedupe for
`ingest_walk` (c426044), `not_before` pickup via `or=(...)` (47dee0b), rate-limit-
respecting download (ab0ac35), and **0018** wiring the async path that was never
actually connected (5a11caf). Real chunk folding (376b3a4), GPT file resolver.

The **bank reset** (`packages/db/reset_question_bank_aws101.sql`): cleared 297 items
(diagnostic/practice/flashcard), kept 16 tutor + 145 evidence_events + 4
mastery_state + 15 tutor srs + 30 lesson checks; 4 flashcard srs rows cascaded
(accepted). `items_stored: 0` after re-ingest is CORRECT (all 86 page items were
already present; dedupe skipped them).

**Diagnostic partial-tolerance (Piece 0b)** — `map_concurrent` →
`map_concurrent_partial` in `get_diagnostic`; one contentless skill now yields 4/5
questions + `skippedSkillCount:1` + HTTP 200 (was 503). **Match results by skill id,
never zip** (mis-aligns after a failure). 4 regression tests. `7fe235c`.

**Tutor to ling (Piece 1)** — dedicated `chat` role, NOT a repoint of `default`
(lessons phase 2 `learn/lessons.py:131`, skill_proposer, prescriber all ride
default; changing it moves four surfaces at once). Primary
`inclusionai/ling-3.0-flash-vl` (PAID slug — the `:free` variant now returns HTTP
404 "unavailable for free"); fallback `nex-agi/nex-n2.5-mini:free` (different
provider on purpose, 1.8-2.5s on the REAL prompt). `converse()` gained
`fallback_model_id` (None keeps global deepseek fallback). Fallback verified to
actually fire. 5 tests. `9826f5b`.

**CI-red fix (`874eeb9`)** — the chat-role tests passed locally but failed CI:
`config.ai_provider` defaults to `"bedrock"` and every `bedrock_model_*` default
is `""`, so a bare-default env (CI, no .env) resolves **every** role to the empty
string. Only `AI_PROVIDER=openrouter` (deployed secret) ever exercised the
openrouter branch. Fixed by pinning `ai_provider` in the tests; confirmed green on
GitHub across all steps.

**The 30s wall is the top structural risk** — the tutor's 500/503 (deepseek 34-103s
on the real 4052-char prompt) is provider-independent; raised the client timeout to
25s but that alone didn't fix it. ling-3.0 wins ONLY for chat (10-16s); it CANNOT
do item gen (HTTP 400 "model features structured outputs not support") and returns
the WRONG SHAPE for tagging (array instead of object — crashes `tag_content`'s
`.get()`). Tagging is broken on BOTH models (deepseek `finish_reason=length`,
`content=None` on a 4000-char chunk — 4096 no longer enough for the largest chunks).

**Earlier on this branch (context carried in):** AI overhaul v2 Checkpoint 2 tail +
Checkpoint 3 (StudySurface/SessionBar/ComposeDock, SkillHub, quiz_sets 0013),
model reliability (deepseek-v4.1-flash:floor, no `require_parameters`, partial
tolerance), content pipeline + tagging-in-worker, identity bug (0015 `resolve_user`
+ `lms_identity_aliases`).

### Open todos

| # | Item | Notes |
|---|---|---|
| **P3** | Diagnostic `GET` 503 from empty-bank cold start | **The remaining LIVE failure** (confirmed against the deployed image 2026-09-24). Piece 2 = move `generate_question` (diagnostic + practice) into the worker, keep deepseek there (120s ceiling). If too big for demo: pre-warm bank out of band as bridge. Flag which route + why. Do NOT reorder |
| **P3b** | Tagging returns wrong shape / burns budget (Piece 3) | Broken on BOTH models (see Done). Either raise budget >4096 +/or cap chunk, OR fast non-reasoning structured-output model (Cohere North Mini Code free candidate). Harden parser to accept object AND array FIRST. Structured-output test, not latency |
| **DEADBAND** | Fresh none is **not** a Piece-3 wart: `items_stored=0` after re-ingest is CORRECT dedupe, not a bug | |
| **16** | Question repetition | Corpus depth fixed the worst; 1-2 chunk skills still repeat. Related: "According to the excerpt" stems (separate, arguably higher-leverage) — scenario `apply` stems read best |
| **17** | Practice done-state + confetti | `celebrate()` used by LessonChat; PracticePanel still never calls it |
| **19** | Graduated study queue goes empty | Design question; `docs/AI_OVERHAUL_TODO.md` parking lot |
| **20** | Cross-student aggregate on set cards | Optional; `quiz_set_attempts` has the rows |
| **22** | Blackboard admin bulk export feasibility | Cheap check, not built |

**The confirmed piecing plan (do NOT reorder):** 0a ingest ✓ · 0b diagnostic
partial-tolerance ✓ · **1 tutor→ling ✓ (deployed + verified)** · **2 item
generation off the request path (NEXT)** · **3 tagging fix**. Pieces 2 and 3 are
both undone. Before repointing `default` anywhere, re-check what rides on it.

### Closed / settled
- #18 debug/lms routes — **removed** (`1749cb0`)
- #21 content strategy — decided: staff upload; service-account scraping **rejected outright** (fragile, ToS risk)
- #23 duplicate accounts — fixed (`resolve_user`, 0015); **historical 4 pairs left alone by decision**; the 149 evidence events stay orphaned (append-only trigger, cannot be repointed) — see Open Q3
- The bank reset (`reset_question_bank_aws101.sql`) — **already ran**; scope recorded above
- `4f14665c` ("Kala LTI Test") has duplicate `lms_ref`s (`_17_1`,`_18_1`,`_20_1` each twice) — **unresolved, low priority, worth a look**
- The tutor guardrail is **prompt-only**: `_SYSTEM = "You are Kala, a study tutor. Teach and give hints. Never reveal answers to graded work."` — no enforcement, no output filter. Lessons/quiz inherit it via the stateless `/tutor/ask` path
- Provider pinning (Relace) + 25s timeout was **NOT** the tutor fix — the real prompt is 34-103s on deepseek regardless of provider. Owned as a bad benchmark. ling-3.0 is the tutor-only fix
- **"Loosen the constant once the bug is fixed"** rule: a workaround tightened to route around a platform kill was never loosened and became the outage
- **Verification discipline**: deployed hash *matches* ECR `:latest` and State=Active ≠ behavior; always probe the real endpoint. Stateless `/tutor/ask` verified 200/7.5s

### The 30s wall — why the diagnostic still 503s (current live failure)
Piece 0b removed the *contentless-skill* 503, but the bank is EMPTY, so the live
diagnostic path still calls inline deepseek item-gen per missing skill (51-82s each)
— far past the 30s Lambda wall. The old warm buffer used to hide this cold start;
the reset removed it. That is precisely Piece 2's job: move item gen into the worker
(120s ceiling is plenty for deepseek).

---

## Notes / Gotchas

### Question quality (measured 2026-09-17, 50 questions / 10 skills)
- **Repetition tracks corpus DEPTH, not size.** Skills with 1-2 chunks produce 4 of
  5 questions as rephrasings of one fact. With 6 chunks/8008 chars it's still ~3 of 5
  on the same fact. Nothing cross-contaminated; distractors are now plausible (were
  nonsense when ungrounded).
- **"According to the excerpt" appears in ~23 of 50 stems** and produces **citation**
  questions ("what does the Overview explain differences between?"), not comprehension.
  Scenario-based questions (mostly in `apply` skills) read markedly better and rarely
  use it.
- A question's correct option is often **the phrase from the source** with obviously
  wrong distractors — answerable by elimination without reading.

### `evidence_events` is APPEND-ONLY by trigger
`P0001: append-only table: UPDATE not allowed on evidence_events`. **Even service_role
cannot update it.** Same for `lti_launches`, `audit_log`. So historical evidence
**cannot be re-pointed** to another user. This is why the merge script
(`scripts/merge_duplicate_user.py`) can't fix the 4 historical duplicate pairs.

### Blackboard file exposure — SOLVED for embedded PDFs, still true for bare files
`resource/x-bb-file` returns `{fileName, mimeType}` and nothing else — no `uploadId`,
no `resourceUrl`; `/download` and `/file` both 404. The only link is a browser-session
Ultra redirect. **BUT** this session we extracted the professor's AWS PDFs from *Ultra
document bodies* (embedded `resource/x-bb-file` attachments) — that's how the 8 PDFs
(live 15 chunks, incl. the 2 AWS teaching docs) landed. Bare top-level files are still
unreachable via API; staff `POST /content/upload` remains the workaround for those.

### What the corpus actually is
Mostly Blackboard scaffolding. The real AWS teaching material lives in the PDFs
(now ingested). What is still thin: module descriptions, publisher onboarding
(Wiley/ALEKS/Cengage/MindTap), institution boilerplate. **~63 of the pre-PDF 88
chunks were under 500 chars and matched no skill correctly** — depth per skill is
what drives question redundancy (see Open Q1).

### Verification discipline (learned the hard way, three times)
Declaring "fixed" without measuring cost this thread three separate rounds. Before
claiming a fix: **deploy, then verify live at the scale the bug occurs** — a single
successful call proves nothing for an intermittent failure. Also: **size against the
longest realistic input**, and when you tighten a constant to work around a bug,
**loosen it again once the bug is fixed** (that's how `TAG_SLICE_SECONDS` got stuck
at 6, then renamed `EMBED_SLICE_SECONDS`).

### Environment facts
- Supabase project ref **`jcufmpxjlgdfzefvulvz`**; API base
  `https://14vua0ys43.execute-api.ap-southeast-1.amazonaws.com`
- Pilot course id **`ae4e7680-f94b-4652-b3f6-b9c32f4420de`**
- Institution id **`64a59889-ba9c-44ae-87c8-765f86c92c78`**
- The Supabase CLI is **not linked** and there's no DB password here, so **migrations
  must be applied by the user** (0012-0018 all were).
- The Blackboard EC2 host is **firewalled from the local machine** — reachable only
  from inside the Lambda.
- `services/api/.env` and the deployed secret hold different things; the deployed
  secret is authoritative and sets **no `OPENROUTER_MODEL_*` overrides**, so code
  defaults are the runtime values.
- **`AI_PROVIDER=openrouter` comes from the deployed secret.** Default (no env) is
  `"bedrock"`, and every `bedrock_model_*` default is `""`. A bare-default env
  resolves EVERY role to empty — this bit us in CI. Tests must pin the provider.
- All current users are **test accounts** (`kala.student*@example.com`). No live
  students — so auth changes are low-risk right now.
- Local probes: mint a student/teacher token from the `kala/app` secret's
  `SUPABASE_JWT_SECRET` (HS256, `app_role`, `institution_id`, `course_id` custom
  claims). API base
  `https://14vua0ys43.execute-api.ap-southeast-1.amazonaws.com`. Probe script pattern:
  `scripts/aws-cli.sh secretsmanager get-secret-value --secret-id kala/app …` then
  HMAC-sign a JWT; the token expiry is 60s-1h so re-mint per run.
- Deployed image check: `scripts/aws-cli.sh lambda get-function-configuration
  --function-name kala-api --region ap-southeast-1` — compare `CodeSha256` to ECR
  `:latest` digest. "State=Active" alone proves nothing; probe the endpoint.

---

## Open Questions

1. **#16 — does question repetition close, shrink, or stay?** Your call from the
   sample. Corpus depth fixed the worst; 1-2 chunk skills still repeat.
2. **"According to the excerpt" phrasing** — close, shrink, or stay? Separate item
   from #16.
3. **The 4 historical duplicate pairs** — repair another way, or leave? Their evidence
   can't move. A launch now resolves them by email to the **oldest** account, which
   for Hanna is the *enrolled* one — correct going forward, but her 149 existing
   events stay orphaned, so the instructor still sees `0 evidence events` until new
   activity lands.
4. **Reset Hanna's test data** — still deferred, separate call not made.
5. **Model piecing order** — 0a ✓ · 0b ✓ · 1 ✓ · **2 (item gen off request path,
   fixes the live diagnostic 503) NEXT** · 3 (tagging). See Current State piecing
   plan. UI sequencing of #17/#19/#20/#22 + Diagnostic shell waits for the model
   work and the (1)/(2) calls.
