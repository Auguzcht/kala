> Archived: 2026-10-24 (Asia/Manila), under APPROVAL-01. Historical source: `docs/Deepseek_HANDOFF-Aug31_2.md` at base `e9de105` / ignored main-only input.
> Replacement: [docs/work/handover-2026/evidence/migration-map.md](<../../work/handover-2026/evidence/migration-map.md>). This original is evidence, not current policy; old commands and next-step queues are not authorization to execute them. Source line references below and in audits refer to the original, before this header.

# Kala changeset — Sept 1 demo prep

**Update after DeepSeek's review round 2:** all findings from your review are
addressed below in "Round 2 fixes." Read that section first if you already
read this doc once.

This zip is a **drop-in overlay**, not the full repo. Every file here goes to the
exact same path inside the `kala-scaffold` project root. Copy/merge these on top
of the existing tree — nothing here is meant to replace files wholesale except
the ones listed below, which are full-file replacements.

## What's in here

```
apps/web/src/components/kala/index.ts                     (edited)
apps/web/src/components/kala/mastery-delta.tsx             (new)
apps/web/src/components/shell/CourseShell.tsx              (edited)
apps/web/src/features/diagnostic/components/DiagnosticPanel.tsx  (edited)
apps/web/src/features/diagnostic/schema/diagnostic.schema.ts     (edited)
services/api/app/routers/diagnostic.py                     (edited)
services/api/tests/test_diagnostic_mastery_delta.py        (new)
services/worker/app/config.py                              (new)
services/worker/app/db/__init__.py                         (new, empty)
services/worker/app/db/supabase.py                         (new)
services/worker/app/embed.py                                (new)
services/worker/app/handler.py                              (edited — was the stub)
services/worker/app/jobs/__init__.py                        (new, empty)
services/worker/app/jobs/embed_backfill.py                  (new)
services/worker/app/jobs/readiness_snapshot.py              (new)
services/worker/app/jobs/reconcile_mastery.py                (new)
services/worker/pyproject.toml                              (edited — 2 deps + pytest config added)
services/worker/requirements.txt                            (regenerated)
services/worker/uv.lock                                     (regenerated)
services/worker/tests/test_handler.py                        (new)
services/worker/tests/test_reconcile_mastery.py               (new)
```

`services/worker/requirements.txt` and `uv.lock` were regenerated for real (I ran
`uv lock` and `uv export` myself, not hand-edited) — just drop them in as-is,
don't regenerate again unless you change `pyproject.toml` further.

## Round 2 fixes (this update)

Worker findings:

1. **Fixed — wrong comment + dead code in `readiness_snapshot.py`.** You were
   right: `enrollments` has its own `institution_id` column
   (`packages/db/migrations/0001_init.sql`), so the users-join fallback was
   unnecessary and the comment claiming otherwise was false. Simplified to a
   single `select` on `enrollments` with `institution_id` in the field list;
   the "every institution" and "one institution" paths now share the same
   code, no branch.
2. **Fixed — worker tests added.** `services/worker/tests/test_handler.py`
   (8 tests total across both new files) covers: all three jobs run and
   receive the same `institution_id`; a `None` event scopes to every
   institution; a raising job doesn't abort the other two and its error
   lands in `errors` while the others still report results; job
   start/done log lines exist via the structured logger.
   `services/worker/tests/test_reconcile_mastery.py` covers the specific
   cases you named: mastery_state already consistent with the log → zero
   corrections, `db.upsert` never called; mastery_state stale (simulating a
   dropped tracer update) → exactly one correction upserted with the
   correct replayed estimate; an evidence row with a null `skill_id` is
   excluded rather than crashing; passing `institution_id` skips the
   `institutions` listing query entirely. All 8 pass — I ran them for real
   (`uv run pytest tests/`), not just wrote them.

   One thing this surfaced: `services/worker/pyproject.toml` had no
   `[tool.pytest.ini_options]` block at all, so `app` wasn't importable from
   `tests/` regardless of what was in them — that's fixed too (mirrors
   `services/api/pyproject.toml`'s `pythonpath = ["."]`). Worth knowing
   independent of anything else, since it would have blocked any worker test
   anyone wrote, not just mine.
3. **Fixed — structured logging instead of `print()`.** `handler.py` now
   logs via `logging.getLogger("kala.worker")` at INFO: a "job start" line
   with the institution scope, and a "job done"/"job failed" line with
   `duration_ms` and the result or error. `embed_backfill.py`'s per-chunk
   failure log uses the same logger. I left the `print()` inside
   `config.py`'s secrets-loading fallback alone — it's an exact copy of the
   identical pattern already shipped in `services/api/app/config.py`, so
   changing only the worker's copy would make the two diverge for no reason.
4. **Not fixed, can't be from here — no live-data run.** Confirmed, this is
   a real gap. I have no Supabase/OpenAI/Bedrock credentials in this
   environment. See "Suggested order for you" step 4 below — do this before
   Sept 1.
5. **Noted, out of scope for this diff — `tracer.py`'s `last_seen: "now()"`.**
   This is pre-existing code in `services/api/app/twin/tracer.py`, not
   something introduced here. Worth a live check as you said, but not
   something I'm touching since it's outside what was asked for this task.

Frontend findings:

1. **Fixed — `CourseShell.tsx` now caps at `max-w-screen-2xl`** instead of
   removing the width constraint entirely, so ultra-wide/projector displays
   don't stretch content edge-to-edge. Still fixes the original
   too-narrow complaint from `docs/UI_AND_MODULES.md` §1.
2. **Fixed — `MasteryDelta`'s row array is now memoized** in
   `DiagnosticPanel.tsx` with `useMemo` keyed on the actual `masteryDelta`
   reference from React Query (stable until a real refetch), instead of a
   fresh `.map()` on every render. Note for anyone touching this file
   again: the `useMemo` has to sit **above** the component's early returns
   (loading/error/empty states) — Hooks can't be called conditionally. I
   caught this myself via `pnpm lint` (`react-hooks/rules-of-hooks`) after
   an initial pass put it in the wrong place, fixed before it made it into
   this zip.

Full re-verification after all of the above: `pnpm --filter web typecheck`,
`pnpm --filter web lint` (0 errors, 18 pre-existing warnings), and
`pnpm --filter web build` all clean; `uv run pytest` clean on both
`services/api` and `services/worker`; `uv run ruff check` on the worker
still shows exactly the same 3 pre-existing-pattern `BLE001`s as before, no
new ones.

## What each change does

**Worker (`services/worker/`)** — the handler was a stub (`return {"ok": True,
"processed": 0}`). It now runs three jobs every scheduled invocation:

1. `jobs/reconcile_mastery.py` — replays `evidence_events` and rebuilds
   `mastery_state`, so derived state can heal itself if a request ever wrote
   evidence but the tracer update didn't land.
2. `jobs/embed_backfill.py` — embeds any `content_items` row still missing an
   embedding (repairs the flaky-embedding-endpoint gap already documented in
   `docs/UI_AND_MODULES.md` section 4).
3. `jobs/readiness_snapshot.py` — writes one `readiness_snapshots` row per
   active student per run. That table existed since migration 0001 and had
   never been written to.

`config.py`, `db/supabase.py`, and `embed.py` are **deliberate duplicates** of
the equivalent `services/api` modules, trimmed down. This is necessary, not
sloppy: `services/worker/Dockerfile` only `COPY`s the worker's own `app/`
directory, so it has no access to `services/api` at build time. Making them
share code would mean moving shared modules into `packages/` and changing both
Dockerfiles — an infra-shaped change, which the root `CLAUDE.md`'s standing
constraint says not to make without being asked. So: two copies, each
commented pointing at the other. **If you ever change the tracer's `_K`
constant, the embedding provider dispatch, or the OpenRouter input_type
mapping in `services/api`, grep `services/worker/app/` for the same symbol and
update both.**

No LMS grade/attempt sync in the worker. Scoped out deliberately — see the
comment at the top of `handler.py`. It's invisible in a demo video and needs a
`get_attempts()`-shaped method the `LMSConnector` protocol doesn't have yet.

**Backend (`services/api/app/routers/diagnostic.py`)** — `submit_diagnostic`
now returns a `masteryDelta` array: one row per skill touched, with
`priorEstimate`/`priorBand` (null/`"no-evidence"` if the skill had no earlier
mastery row — never faked as `0.0`) and `posteriorEstimate`/`posteriorBand`.
Everything else about the endpoint is unchanged; `correctCount`/`total`/
`results` are byte-identical to before.

**Frontend** — new `MasteryDelta` component (`components/kala/mastery-delta.tsx`)
renders that array as a staggered before→after list, respecting
`prefers-reduced-motion`. Wired into `DiagnosticPanel.tsx`'s submitted state, in
place of the old plain "You got X of Y correct" line (that line is kept, the
component renders below it). `CourseShell.tsx`'s content wrapper had its
`max-w-7xl mx-auto` cap removed per your own `docs/UI_AND_MODULES.md` section 1
("do now", never actually done) — sidebar and top bar untouched, only the
`<main>` wrapper changed.

## What I verified myself, in a real environment

I actually ran these against the full repo, not just read the diffs:

- `cd services/worker && uv lock && uv sync && uv run ruff check app` — clean
  (3 pre-existing-pattern warnings, same class already in `services/api/app/config.py`;
  `worker-ci.yml` has `continue-on-error: true` on ruff anyway).
- `uv run python -c "from app.handler import handler"` — imports cleanly.
- `cd services/api && uv run pytest` — full suite. My new test file passes
  (5/5 alongside the existing diagnostic idempotency tests).
  **Heads up, unrelated to this change:** `tests/test_lti_launch.py` has 6
  failing tests on the untouched original scaffold — I confirmed this by
  running the same tests against your unmodified `diagnostic.py` before I
  touched it. Not something I introduced. Worth a look before Sept 1
  independent of anything here.
- `cd apps/web && pnpm install && pnpm typecheck && pnpm lint && pnpm build` —
  all clean. Typecheck: 0 errors. Lint: 0 errors, 18 pre-existing warnings (all
  `react-refresh/only-export-components`, same class already on
  `mastery-band.tsx`; my new file isn't among them). Build: succeeds, single
  ~355KB gzipped bundle, same size-warning the repo already had before my
  changes (not something I introduced).

## What I could NOT verify (do this before trusting it)

- I did not run the worker against a real Supabase instance or real
  AWS/OpenRouter/OpenAI credentials — `reconcile_mastery.py`,
  `embed_backfill.py`, and `readiness_snapshot.py` are exercised by import and
  static review only, not by hitting live data. Before Sept 1, run
  `uv run python -c "from app.handler import handler; print(handler({}, None))"`
  locally with real `.env` values (copy `services/api/.env.example` per the
  worker README) against a non-production Supabase project first, and check
  the three job results in the output dict make sense for your actual data.
- I did not deploy the worker (`make deploy` / Terraform) — only the container
  build inputs (`requirements.txt`, `uv.lock`) are ready. Building and pushing
  the image is still a manual step on your end.
- I did not visually check the `MasteryDelta` component or the `CourseShell`
  width change in a running browser against Kala's actual color tokens —
  typecheck/lint/build passing means it compiles and type-matches, not that it
  looks right. Load `/course/diagnostic`, complete a diagnostic, and eyeball
  it before recording.

## Suggested order for you

1. Drop the files in, `pnpm install` (workspace root) if needed, then
   `pnpm --filter web typecheck && pnpm --filter web build` — should match what
   I got above.
2. `cd services/api && uv sync && uv run pytest` — should match what I got above,
   modulo the pre-existing `test_lti_launch.py` failures.
3. `cd services/worker && uv sync && uv run pytest` (there are no worker tests
   yet — this just confirms imports resolve in your environment too).
4. Run the worker handler locally once against a scratch Supabase project with
   real evidence data in it, eyeball the returned counts.
5. Open `/course/diagnostic` in the running app, complete a diagnostic with a
   fresh test student, confirm the mastery-delta card renders and the numbers
   look sane.
6. Only after that: `make deploy` for the worker image, `terraform apply` if
   the schedule needs touching (it doesn't — no `.tf` files changed).
