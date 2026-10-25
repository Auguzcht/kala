---
runbook: first-launch-smoke
applies_to: [dev-hosted, prod]
who_runs_it: Fred / ITO tester with Learn administrator
time_needed: "55 minutes baseline; release checks [Fred to confirm]"
last_verified: "unverified; source review at 6e21eed on 2026-10-25, Lane R"
status: in-progress
---

# Runbook 10 — first-launch acceptance

## When to use it

Accept a new environment or verify a release after 01–09. This WI-07 draft extends the preserved [manual checklist](../../TESTING.md). Human testers perform hosted actions; this smoke writes synthetic learning records and can incur model costs. No agent invocation is authorized.

## Before you start

- For the same-day release, this is Fred's FG-5 after FG-3 [0037 pre/post-checks](../../runbooks/0037-apply.md) and FG-4 deploy/alias/worker/startup checks, Fred's push and Vercel Ready, under [APPROVAL-06](../../work/handover-2026/approval-06.md). Repository base 6e21eed contains 37 migrations, not a claim that hosted 0037 is applied.
- Record frontend/API revision, environment, database manifest and named tester. Confirm approved synthetic course/material, instructor, two students and separate browser sessions with the Learn administrator. Current identities are kept privately: [Fred to confirm].
- Confirm configured providers/billing and worker/schedule readiness. Agree an observation window and expected ingest latency: [Fred to confirm]. Avoid repeated refresh/launch bursts against Learn quotas.
- Resolve all blocking `[Fred to confirm]` items in earlier runbooks. Secrets/access follow [the catalogue](../secrets.md). Never attach raw HAR files, tokens, browser storage, question text or provider bodies to evidence.

## Steps

1. In Learn, sign in as the test instructor and launch the course placement. Check correct course and instructor surfaces. Sign in separately as each test student and launch the same placement; check the correct course and student view. Do not manufacture institution/role claims. Capture only role/outcome, not the launch URL or fragment.
2. With the instructor, verify the cohort matches synthetic enrollments. Trigger one approved course ingest/refresh flow if the course needs material. Source has staff course ingest routes and asynchronous work; exact current UI trigger and expected completion criteria for this environment: [Fred to confirm]. Observe one job to completion before trying again; avoid duplicate operations or direct SQL cleanup.
3. Confirm the approved course's content produces usable skills/material through the intended instructor review flow. Distinguish no material, queued work and a failed job. Do not approve real-course proposals merely to make smoke pass.
4. Complete every student/instructor row in [TESTING.md](../../TESTING.md), recording pass/fail/not-run individually. Use the current [Study spec](../../features/study/README.md) for accepted count/replay behavior if old checklist labels differ. Include one complete diagnostic, lesson check, Study session, Test set/recap and Tutor answer; complete instructor roster, student sheet, decision, skill review and heatmap checks.
5. For the accepted Study corrections, verify counts-only landing does not spend the cap, claimed-unrated cards can return, native flashcards remain eligible, and end-of-deck replay is labelled practice with no extra rating posts. A skill showing zero due after four ratings is not by itself a defect: successfully rated cards can be scheduled into the future. Record visible state and sanitized counts, never edit schedules to force a result.
6. Verify Tutor in both saved-conversation and stateless contexts: Study hint, Explain more, Study dock, Review-missed dock and Test dock follow-up. Record HTTP status and elapsed time per path. Successful stored Test explanations alone do not prove a live tutor/provider call. If an ask fails, use [12](incident-response.md) and stop repeated model attempts.
7. Using an approved tester method, confirm a student's gradebook read/write request is denied and does not reach Learn. The [INGEST spec](../../features/lms-ingest/README.md) requires 403 for the protected routes; exact private request harness: [Fred to confirm]. Do not test grade writes on real records or claim AGS passback exists.
8. B/U first-pass code is integrated locally at this source base; hosted rollout remains unverified. After FG-4, Fred checks new-chat centered dock, file drop and Send, rename, pin/unpin and delete confirmation at 1440px/375px. Current accepted Tutor behavior stages files in memory until Send; new-chat starters are retired. Use the [current Tutor spec](../../features/tutor/README.md), not the initial APPROVAL-05 attachment timing. Add APPROVAL-06 section 6's badge/servable Diagnostic match and load-error Retry if reproducible, root/session-expired/not-found per role, and launched-student roster/recent activity after Lane I ships. I/G/U close-out code is not implied shipped by its committed spec: use the final coordinator inclusion list and lateness rule, marking omitted work not-run.
9. Fred records FG-5 results in the coordinator-designated `docs/work/handover-2026/evidence/acceptance-2026-10-25.md` when created; Lane R does not create/edit it. Confirm any remaining provider failure has stage/status diagnostic evidence after the diagnostics deploy. Record outcomes in release evidence: date/time with timezone, environment, revisions, role, check, result, elapsed time/status, sanitized failure and owner. Mark not-run items explicitly. Only a named human can accept the release. No report/work-item outside this lane is edited here.

## Verify it worked

Each required scenario passes under both roles as applicable; ingest has an observed terminal success and usable material, and both tutor modes answer. A healthy API alone does not pass acceptance. The v6 record left these live checks outstanding; APPROVAL-06 identifies primary HTTP 429 and leaves paid fallback/runtime refresh/hint recovery at FG-1; merged diagnostics do not prove live recovery. This draft contains no recovery claim. Do not transfer or shut down personal environments until ITO separately verifies and authorizes cutover.

## Undo / roll back

Stop testing on failure and preserve sanitized evidence. Do not delete append-only learning/audit history to clean a smoke. Test-data retention/removal needs an approved scoped procedure: [Fred to confirm]. Recovery uses [07](deploy-backend.md)/[09](vercel-web.md); database fixes go forward. Test-account changes are not a rollback of production learning records.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Empty material | Ingest/review/worker incomplete | Check the specific job and source material; do not repeatedly refresh. |
| Roles/course differ | Registration or enrollment mismatch | Learn admin checks 08 before continuing. |
| Tutor 502/503 | Provider failure or bounded timeout | Record status/time and use 12. |
| Checklist control absent | Different deployed UI revision | Mark not-run with revision; use approved spec, not guessed clicks. |

## History

| Date | Change to this runbook | Why |
| --- | --- | --- |
| 2026-10-25 | Draft acceptance sequence and release-specific checks | APPROVAL-05 rev 2, Lane R, WI-07. |
| 2026-10-25 | Refresh to current staged-file behavior and Fred-only 0037/deploy/acceptance gates | APPROVAL-06 rev 2; source 6e21eed. |

## Historical sources

These links preserve provenance only. Required rules, commands and limits are stated above; do not read the records unless the task explicitly names them.

- [The v6 record](../../work/handover-2026/evidence/deployment-2026-10-25.md)
