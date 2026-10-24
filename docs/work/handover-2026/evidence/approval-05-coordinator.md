# APPROVAL-05 coordinator evidence

Date: 2026-10-25. Base: main at 4f3ec29, already published after Fred's API v6 deployment. Scope: APPROVAL-05 rev 2 and Fred's direct ownership/design/CLI amendments. These are setup and review results, not live recovery evidence.

## Spec-first releases

| Commit on local main | Scope |
| --- | --- |
| 0e7602e | Preserve APPROVAL-05 and confirmed amendments; route authority and current initiative |
| 6676b9e | DESIGN.md chat-entry-container and Tutor empty-state mascot exceptions only |
| ab4cefc | B's TUTOR-REQ-002/003 and WI-21; generated API contract path grants |
| c961b83 | U's TUTOR-REQ-004–011, WI-22 and planned WI-23; Tutor-only CourseShell grant |
| 11d69de | X's AI-REQ-002 and WI-01 follow-up; per-budget correlation grant |

Coordinator alone edits Tutor and AI-platform specs. B/U/X submitted proposed text before release and were told to rebase onto the named spec commit before implementation. U alone authors Diagnostic's spec. All exceptions remain scoped to the approved feature; lead designer review remains a recorded follow-up.

## Parallel chats and paths

All six chats use GPT-6.1 sol and separate branches/worktrees.

| Lane | Chat ID | Branch | Worktree suffix |
| --- | --- | --- | --- |
| X | 01a16f09-32e8-7c81-8288-516d6f9fc296 | codex/tutor-provider-502 | 9a3f/kala |
| B | 01a16f09-64fe-7a92-9fbd-f7cb5e0616aa | codex/tutor-conversation-api | bab4/kala |
| U | 01a16f08-faed-78b2-999b-e8f04e3e7073 | codex/ui-overhaul | 2e93/kala |
| R | 01a16f09-955a-7803-aad3-6ec799b77147 | codex/handover-runbooks | 97b5/kala |
| P | 01a16f09-bb7c-7971-a94e-d4e233aae2e6 | codex/feature-specs-wi08 | 9cf7/kala |
| C2 | 01a16f09-dcff-7e92-b58f-51cfaa2a24fa | codex/config-cost-docs | 8f13/kala |

Worktrees are beneath Fred's local Codex worktrees directory. Existing Kala Audit and earlier worktrees are preserved. No cleanup was performed.

## Frontend setup

Lane U verified HTTP 200 on localhost:5173, with Vite PID 70116 running from its apps/web directory. Strict port; no previous listener needed to be stopped. Its apps/web/.env.local was absent at setup. Fred alone copies it; agents check existence only. Live LTI/browser observation remains Fred's responsibility. U keeps this server running for direct feedback in its chat.

U's pre-change baseline: 14 frontend tests pass, lint passes with 18 existing warnings, typecheck/build pass. These are baseline checks, not acceptance of the overhaul.

## Provider evidence and limits

X's sanitized CLI investigation found three stateless Tutor requests with completed retrieval, primary OpenRouter HTTP 429 from inclusionai/ling-3.0-flash-vl, and a failed nex-agi/nex-n2.5-mini:free fallback whose status is absent from emitted logs. Five other observed requests succeeded, and one Tutor chat timeout is consistent with an application 503; it is not yet tied to Fred's console entry. This is intermittent failure evidence, not proof that every surface fails or has recovered.

Fred reports $2.63 in OpenRouter credit. Under his CLI/key-access authorization, X read the current credential in process memory solely for the official read-only key-status endpoint. It returned HTTP 200, no per-key spend cap or expiry, is_free_tier=false, and a free-model daily counter of 0 used / 50 remaining. No disabled flag was returned. These are point-in-time metadata, not proof of generation availability, historical quota state or the precise underlying 429 cause. No credential or secret payload was emitted or persisted in reports.

X's pre-fix investigation suite reports 500 API tests passing, including 69 new investigation cases. The production logging fix is approved only to resolve the diagnosed observability gap, with no model, fallback, retry or timeout policy change. Operational recovery and live smoke tests remain pending. Exact source/status mappings and sanitized timing evidence are maintained in X's branch evidence file.

## Documentation review

C2 submitted a4ae528 with changes only to secrets.md and infrastructure-requirements.md. Coordinator reviewed the diff: names-only Lambda precedence is attributed to Fred; source-only uncertainty remains explicit; cost inputs are placeholders; exposure log and cutover rotation policy are preserved. C2 reports configuration inventory passing (67 names, zero issues), six local links checked and clean whitespace. No runtime checks are needed for this docs-only lane. It remains unmerged.

R and P are still preparing their reports at this snapshot. P reports baseline 431 API and 117 worker tests passing; this does not establish hosted or browser verification. R marks missing operational inputs Fred to confirm.

## Delivery and gates

Only coordinator documentation is committed on local main. No APPROVAL-05 lane code is merged, pushed or deployed. Each lane stops at its full AUDIT REPORT. B's local 0037 replay is required before review; Fred alone applies hosted 0037, then deploys the accepted backend before a later authorized publication. Lane DB retains the hosted-major gate and owns database type regeneration/relocation. Unfinished work after Oct 28 becomes planned with branch/status.

## AUDIT REPORT

- Task / brief ID: APPROVAL-05 coordinator setup and spec releases.
- Branch and worktree: main; /Users/fred/Documents/Repository/kala.
- Base revision: 4f3ec29.
- Files changed: AGENTS.md, DESIGN.md, shared Tutor/AI specs, approval/initiative/coordinator evidence, WI-01 follow-up and WI-21/22/23 documentation.
- REQ / WI IDs touched: AI-REQ-002; TUTOR-REQ-002–011; WI-01, WI-21, WI-22, WI-23. Existing AI-REQ-001/TUTOR-REQ-001 preserved.
- Commands and results: repository/authority/source review; clean initial main; lane setup and scoped report review; git diff --check for every coordinator commit; no application source changed by coordinator.
- Spec changes: separate B/U/X commits precede their implementations; DESIGN exceptions precede U.
- Evidence added: dispatch, provider findings, baseline checks and C2 review above.
- Not done: implementation acceptance, integrated tests, merges, hosted migration, deployment and push; these retain their gates.
- Risks/questions: exact provider limit/fallback cause and recovery still unknown; frontend env pending at setup; lead designer review; DB hosted major pending.
- Secrets printed: none (confirmed).
