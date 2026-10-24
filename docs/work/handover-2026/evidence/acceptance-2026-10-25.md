# Fred's live acceptance — 2026-10-25

Authority: [APPROVAL-06](../approval-06.md). Owner/operator: Fred. This is a prepared checklist, not executed acceptance. Record only sanitized status, counts and timing; no credentials, tokens, launch URLs, provider bodies or student content. Append failures and later retests separately.

## Release identity and prerequisite gates

| Field | Recorded result |
| --- | --- |
| Approved source SHA | pending final coordinator report |
| FG-1 paid fallback on a different serving provider, fresh runtime and hint retest | not-run / not reported |
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

Synthetic automated checks do not fill these live rows. A healthy health endpoint does not prove model access, LTI, permissions or pin persistence. If a case is not reproducible, record not-run with its reason. Full-history paging and historical identity repair are not included.

## Failure/retest record

Append date/time, role, check, expected/observed outcome, sanitized status/count/timing, source revision, owner and disposition. No failure has been reported in this prepared record.

## Acceptance decision

Pending Fred. Do not begin post-FG-5 cleanup/code freeze or describe the release as accepted before Fred records the outcome. If deployment regression requires FG-R, Fred restores the recorded previous API alias and Vercel deployment after compatibility review; leave additive0037 in place and never delete learning history.

## Read-only prerequisite update — 2026-10-25

Fred directly authorized provider metadata review and0037 pre-checks. [Results](provider-and-0037-prechecks-2026-10-25.md): target-table checks passed, count1, PG17.6,0035/0036 markers present; CLI migration history is not a complete numeric baseline record. Provider credits remain approximately2.63USD; primary remains listed, configured free fallback has no endpoints. No model setting, application or live acceptance result changed. Earlier not-run entries remain accurate for application/refresh/click-through.

## FG-3 verification update — 2026-10-25

Fred reported applying0037. [Read-only post-checks](0037-postchecks-2026-10-25.md) pass, including a zero-row Data API column probe. Git fetch confirms main is0 behind origin/main and the remote is an ancestor. Schema/Git prerequisites for the approved deploy are green; provider paid-fallback configuration and live recovery remain FG-1. No deployment, push or live feature acceptance is claimed.
