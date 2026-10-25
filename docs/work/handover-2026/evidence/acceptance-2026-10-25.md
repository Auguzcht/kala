# Fred's live acceptance — 2026-10-25

Release records: [APPROVAL-06](../approval-06.md) and [APPROVAL-07 with confirmed amendments](../approval-07.md). Owner/operator: Fred. This is a prepared checklist, not executed acceptance. Record only sanitized status, counts and timing; no credentials, tokens, launch URLs, provider bodies or student content. Append failures and later retests separately.

## Release identity and prerequisite gates

| Field | Recorded result |
| --- | --- |
| Approved source SHA | pending final coordinator report |
| FG-1 paid fallback on a different serving provider, fresh runtime and hint retest | Paid fallback saved/verified by explicitly delegated CLI update at08:01+08; fresh runtime and hint retest pending. [Evidence](fg1-paid-fallback-2026-10-25.md) |
| FG-2 hosted Postgres major (Lane DB only) | Direct authorized pre-check observed17.6/major17 on2026-10-25; dashboard confirmation not reported |
| FG-3 migration0037 operator/time/environment | Fred reports applied on2026-10-25, dev-hosted; post-checks verified at07:50+08 |
| FG-3 checksum / pre-checks / post-checks | Passed; unchanged RLS/policies/grants, count1, pins0, Data API200. [Post-check evidence](0037-postchecks-2026-10-25.md) |
| Previous API live alias version / previous Vercel deployment | API6 verified before deploy; Fred records Vercel deployment privately |
| Previous immutable worker image | Captured in gitignored .tmp/fg4-rollback-predeploy.json |
| FG-4 API published version / live alias / worker update | not-run |
| FG-4 health / startup errors | not-run |
| FG-4 fast-forward push / Vercel Ready | not-run |
| Tester/time/timezone and tested frontend revision | pending |

## FG-5 checks

| Check | 375px | 1440px | Status/timing/notes |
| --- | --- | --- | --- |
| Student Blackboard launch into correct course | not-run | not-run | |
| Instructor Blackboard launch into correct course | not-run | not-run | |
| Study hint, Explain more and dock follow-up | not-run | not-run | |
| Review-missed dock and Test dock | not-run | not-run | |
| Diagnostic badge matches actionable availability / ten-question sitting cap | not-run | not-run | |
| Diagnostic material-only waiting / load-error Retry if reproducible | not-run | not-run | |
| Tutor centered new-chat dock | not-run | not-run | |
| Tutor file drop stages locally; Send uploads then asks | not-run | not-run | |
| Tutor rename, pin/unpin and refresh persistence | not-run | not-run | |
| Tutor delete cancellation and confirmed deletion | not-run | not-run | |
| Launched learner appears in instructor roster with canonical recent history | not-run | not-run | Legacy history remains separate under WI-24 |
| Public root, session-expired and not-found under student/staff/no-session states | not-run | not-run | |
| Existing tours: record actual broken step only | not-run | not-run | |
| CloudWatch stage/status diagnostics for any remaining provider failure | not-run | not-run | No raw log bodies |

Synthetic automated checks do not fill these live rows. A healthy health endpoint does not prove model access, LTI, permissions or pin persistence. If a case is not reproducible, record not-run with its reason. Full-history paging and historical identity repair are added below for APPROVAL-07; they were not included in the original FG-5 pass.

## Failure/retest record

Append date/time, role, check, expected/observed outcome, sanitized status/count/timing, source revision, owner and disposition. No failure has been reported in this prepared record.

## Acceptance decision

Pending Fred. Do not begin post-FG-5 cleanup/code freeze or describe the release as accepted before Fred records the outcome. If deployment regression requires FG-R, Fred restores the recorded previous API alias and Vercel deployment after compatibility review; leave additive0037 in place and never delete learning history.

## Read-only prerequisite update — 2026-10-25

Fred directly authorized provider metadata review and0037 pre-checks. [Results](provider-and-0037-prechecks-2026-10-25.md): target-table checks passed, count1, PG17.6,0035/0036 markers present; CLI migration history is not a complete numeric baseline record. Provider credits remain approximately2.63USD; primary remains listed, configured free fallback has no endpoints. No model setting, application or live acceptance result changed. Earlier not-run entries remain accurate for application/refresh/click-through.

## FG-3 verification update — 2026-10-25

Fred reported applying0037. [Read-only post-checks](0037-postchecks-2026-10-25.md) pass, including a zero-row Data API column probe. Git fetch confirms main is0 behind origin/main and the remote is an ancestor. Schema/Git prerequisites for the approved deploy are green; provider paid-fallback configuration and live recovery remain FG-1. No deployment, push or live feature acceptance is claimed.

## FG-1 configuration update — 2026-10-25

Fred delegated the single fallback edit through AWS CLI. The paid chat fallback is now stored and readback-verified, with all25 prior entries unchanged and a retained previous version. No deployment/runtime refresh or model answer is claimed. Fred confirms the migration-history finding is recorded for the database stream and does not block this deploy.

## Runtime correction recorded before APPROVAL-07

Fred confirmed API live alias v7 deployed at 00:04 UTC on 2026-10-25, after the paid fallback change at 00:01 UTC. Runtime refresh is complete; live Hint/Explain/dock success is still not-run here. The earlier pending-refresh entries above preserve the state when written. No APPROVAL-07 deployment is implied.

## APPROVAL-07 gates — not executed

Order is FG-6, FG-8, FG-7a, FG-7b, then FG-9. Local lane tests do not satisfy a Fred gate. The coordinator supplies reviewed commands, expected results and rollback before each gate.

| Gate / field | Result |
| --- | --- |
| Reviewed integrated source SHA | `8e51040f1dda4235f9b12ad344da4cd81442e1e9` code/contracts; final documentation-only SHA in coordinator report |
| FG-6: reviewed 0038 / 0039, operator, environment, time and post-checks | not-run |
| FG-8: previous alias, immutable worker image and Vercel rollback identity | Fred records privately before deploy |
| FG-8: new API alias/version, worker update and health | not-run |
| FG-8: Fred's fast-forward push and Vercel Ready revision | not-run |
| FG-7a: counts-only repair dry run and planner review | not-run; after FG-8 |
| FG-7b: apply, source/timestamp conservation, alias/enrollment convergence and restored triggers | not-run |
| FG-7b: worker completeness, rebuilt mastery/readiness and exact rollback artifact | not-run |
| FG-7 valid safe refusal | not-run; record pair label and consent/DSR counts only as `refused: governance ambiguity`; no repair or policy/consent change |
| FG-9: tester, time/timezone, frontend revision and API version | not-run |

## FG-9 additions — APPROVAL-07

Run alongside the still-pending FG-5 cases. Use approved test accounts; record only sanitized observations and counts. Inaccessible resources must remain non-disclosing.

| Check | 375px | 1440px | Status/timing/notes |
| --- | --- | --- | --- |
| WI-26: instructor sees only the course they teach | not-run | not-run | |
| WI-26: another course's learner URL is unavailable; no learner data or misleading empty class | not-run | not-run | |
| WI-26: student opening a staff `/class/*` URL is refused | not-run | not-run | |
| WI-25: student Twin loads older activity through the first event; labels match loaded rows | not-run | not-run | |
| WI-25: instructor learner record loads older activity through the first event; labels match | not-run | not-run | |
| WI-24: Alfred and Hanna each appear once in the roster after approved repair | not-run | not-run | |
| WI-24: each shows combined activity and recent last-active | not-run | not-run | |
| WI-24: student Twin and instructor record agree for the same activity window | not-run | not-run | |
| WI-24: opening these views creates no new XP or evidence | not-run | not-run | |

WI-24/25/26 remain open until their actual checks pass. No repair, new migration, deploy, push or acceptance is claimed by preparing this checklist.

## APPROVAL-07 local integration prerequisite update

H, M and Amendment7 are merged locally in the approved order. Generated contracts and full merged local tests are prepared; exact final counts/source, browser server restoration and migration checksum proof are in the coordinator report. These do not fill any hosted or live row. A real governance refusal is a valid FG-7 outcome, with the affected history explicitly unrepaired; success-only FG-9 repair rows must be marked not-run with that reason rather than fabricated as passed.
