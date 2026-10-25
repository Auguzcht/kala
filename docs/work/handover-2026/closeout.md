# Handover closeout record — acceptance incomplete

Snapshot for DOCS-HYGIENE, 2026-10-25, source base `3a6a0aab27a8212f77b83e96b26127d830a696ba`. This is the first reading item for the initiative, **record, not authority**. Current operation uses [AGENTS.md](../../../AGENTS.md), [the task router](../../README.md), feature specs and engineering runbooks. All other initiative files record delivery history. This page does not declare the release complete.

## Included before these final lanes

Prior local integration contains provider diagnostics, Tutor conversation/UI work, Diagnostic availability/UI closeout, roster UUID identity reconciliation and the accepted feature/runbook documentation. Previous coordinator verification recorded 610 API tests, 117 worker tests, 21 frontend tests plus four Study component tests and 540 synthetic browser assertions, with web lint/typecheck/build and configuration inventory passing. Those are attributed prior results, not suites rerun by DOCS-HYGIENE. Existing lint/deprecation/bundle warnings and external renderer/browser fixtures remain limitations.

Fred reported 0037 applied to dev-hosted; read-only post-checks passed on 2026-10-25. The paid chat fallback setting was verified in Secrets Manager without altering the other 25 entries; Fred confirms API live alias v7 was deployed at 00:04 UTC (08:04 Asia/Manila), after the secret change at 00:01 UTC (08:01 Asia/Manila), so the backend runtime refresh is complete. I, G and U close-out backend code is in v7; their frontend half becomes live only after authorized publication and Vercel Ready. Live Hint/Explain/dock success remains FG-5 pending. Incomplete hosted migration history remains in the database stream and, by Fred's decision, does not block this approved deployment. Applied SQL stays immutable.

## Not closed

| Gate / stream | Status at this snapshot | Required next evidence |
| --- | --- | --- |
| DOCS-HYGIENE | Isolated docs/checker/comment lane under review; no merge or push | Its audit and planner acceptance |
| TOUR-REFRESH | Running in Kala U at Fred's request; not included in this base | Tour audit, synthetic desktop/mobile checks and web checks; frontend acceptance |
| Backend release / Git publication | API live v7 and runtime refresh confirmed by Fred at 00:04 UTC; frontend publication is authorized after the tour rebase/check gate | Fast-forward main publication, Vercel Ready and frontend revision verification; no backend redeploy for these lanes |
| Live acceptance | Unconfirmed | Fred's real synthetic-role LTI observations, Study Hint/Explain, Tutor persistence/files, Diagnostic and instructor checks |
| Local database workflow | Not installed; major confirmation still gates configuration | Confirmed hosted major, approved workflow/replay/types and two clean verifies |
| Fresh ITO recreation | All 13 runbooks remain execution-unverified drafts | Institutional accounts/decisions, named-human procedure execution and acceptance |

## Retained limitations

- WI-26 — open, planned, owner ITO: incomplete course-level instructor guards and direct recommendation status-policy gap remain disclosed; no privacy/tenancy completion claim.
- WI-24 — open, planned, owner ITO: legacy duplicate-user history is retained separately; H01(b) repair has not run. No history rewrite or merge happened.
- WI-25 — open, deferred, owner ITO: Twin/learner ledger windows remain bounded and labeled; full-history paging has not started.
- Standard frontend runner (WI-20), source citations (WI-23), broader sanitization (WI-19), Gateway access logs (WI-18), broader call bounds and global Bedrock policy remain planned.
- Lead designer review of the two narrow DESIGN.md dock/mascot exceptions remains a handover follow-up.
- Keep Kala Audit and existing worktrees until their live verification/acceptance and authorized cleanup. No worktree, file or chat deletion is part of this lane.

## Historical sources

- [Prior integrated checks](evidence/approval-06-integration.md)
- [0037 post-checks](evidence/0037-postchecks-2026-10-25.md)
- [Fallback setting verification](evidence/fg1-paid-fallback-2026-10-25.md)
- [Frontend handoff record](evidence/frontend-finalization-handoff.md)

Update this record only from actual reviewed results. Do not erase failed or unperformed gates to make a closeout appear complete.
