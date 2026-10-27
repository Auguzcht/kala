---
id: WI-14
title: Bound inline lesson generation
status: planned
owner: unassigned
requirements: [LESSON-REQ-007]
depends_on: []
tests:
  - id: WI-14-T01
    kind: integration
---

# WI-14: Bound inline lesson generation

## Current state
Lesson outline and step generation still run on the API request path and can exceed the Lambda wall. Queued lesson checks do not bound teaching-content generation.

Current requirement: [LESSON-REQ-007](../../../features/lessons/README.md#lesson-req-007-bound-first-open-generation-within-an-explicit-request-deadline). The original endpoint finding is historical; the current spec now assigns the request-budget gap. An async behavior change needs a spec amendment before implementation. This is planned work, not a completed fix.

## What
Choose an async or whole-request deadline design for outline plus steps. Preserve ready-lesson replay and null-check compatibility.

## Where
[services/api/app/learn/lessons.py](<../../../../services/api/app/learn/lessons.py>) and the current lesson spec/tests. No implementation is authorized by this estimate.

## How
Design in the owning lane, preserving existing contracts unless separately approved. Preserve tenant/enrollment guards, ready replay, null checks and evidence/mastery behavior. A state column by itself does not make the work durable or safe under concurrent opens.

## FG-1b read-only schema check — 2026-10-27

At source `eb9409a8`, [0008](../../../../packages/db/migrations/0008_learn_loop_v2.sql) already defines `public.guided_lessons.status`, non-null text, default `ready`, constrained to `generating`, `ready`, `failed`. A hosted metadata-only query through the pinned CLI, inside `BEGIN READ ONLY` / `ROLLBACK`, confirms the same column, default and check. It returned schema metadata only, no lesson rows. There is no separate `state` column, generation lease, attempt counter or generation heartbeat on this table.

This status can represent background-generation progress without a status-column migration. It is not sufficient to provide reliable claim/retry/recovery. Current `get_or_generate_lesson` reclaims any non-ready row and regenerates inline. Existing `item_generation_jobs.kind='lesson'` requires an existing lesson step and generates **check questions**, not lesson outline/teaching content. Reusing that queue unchanged for whole-lesson generation would be incorrect. The frontend already polls `generating`; the worker dispatcher and API lifecycle still need changes.

## Planning estimate, not implementation approval

Assume one engineer familiar with Kala, existing worker invocation and development tooling, focused scope, and prompt/model behavior preserved. Estimates include spec changes, implementation, mocked regression/concurrency/failure tests, local worker smoke and web checks. Human review, hosted migration scheduling and live acceptance add elapsed time. No new SQL is written or executed by this estimate.

| Approach | Engineering estimate | Scope and limit |
| --- | --- | --- |
| Without a migration | 16–24 hours, about 2–3 working days | Reuse lesson `status`, explicit async worker dispatch and existing polling, preserve ready replay and bound the API path. Requires a deliberately limited, approved retry/recovery design. Existing state cannot distinguish queued/running lease ownership, so this estimate is **not** a promise of durable automatic recovery or exactly-once work. Stop and redesign if those guarantees require schema support. |
| With a focused migration | 24–40 hours, about 3–5 working days | Add explicit durable whole-lesson work identity, atomic claim/lease and retry/recovery metadata, then integrate dispatch/polling, partial-step recovery and duplicate prevention. Includes running new SQL once on local Postgres, migration pre/post-checks and regression coverage. Fred applies hosted SQL; approval/wait time is additional. |

The migration adds reliability metadata, not a missing status column. Decide failure/retry semantics before selecting an approach. This does not authorize a queue migration, worker/config changes or background generation in the current polish lanes. The chat-model swap is independent and will not fix lesson-content timeout behavior.

## Historical sources

- [Accepted endpoint audit](../evidence/audit-endpoints.md), source `e9de105`, 2026-10-24.
- [APPROVAL-01 sections 3 and 5](../approval-01.md), original scope boundary.

## Testing

### WI-14-T01: Verify the designed bound and safe behavior
- Preconditions: isolated configuration and mocked dependencies (ITO-approved test environment for logging).
- Action: exercise the slow/failure case described above.
- Expected result: On a slow mocked outline/step path, the chosen bounded behavior completes without relying on a Lambda kill.
- Result: not-run; behavior implementation is planned.

## Evidence
- Date: 2026-10-24 (Asia/Manila)
- Revision: `e9de105` / Lane D documentation only
- Environment: local static source audit
- Result: not-run (scenario); source finding preserved by APPROVAL-01

## Delivery
Merged: no. Deployed: no. Hosted migrations: none. Confirmation: pending implementation and named verification.
