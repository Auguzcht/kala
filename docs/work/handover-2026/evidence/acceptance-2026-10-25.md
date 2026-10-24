# Fred's live acceptance — 2026-10-25

Authority: [APPROVAL-06](../approval-06.md). Owner/operator: Fred. This is a prepared checklist, not executed acceptance. Record only sanitized status, counts and timing; no credentials, tokens, launch URLs, provider bodies or student content. Append failures and later retests separately.

## Release identity and prerequisite gates

| Field | Recorded result |
| --- | --- |
| Approved source SHA | pending final coordinator report |
| FG-1 paid fallback on a different serving provider, fresh runtime and hint retest | not-run / not reported |
| FG-2 hosted Postgres major (Lane DB only) | not reported |
| FG-3 migration0037 operator/time/environment | not-run / not reported |
| FG-3 checksum / pre-checks / post-checks | pending; use [exact runbook](../../../runbooks/0037-apply.md) |
| Previous API live alias version / previous Vercel deployment | Fred records before FG-4 |
| Previous immutable worker image | Fred records privately before FG-4 |
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
