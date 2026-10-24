---
id: WI-22
status: in-progress
owner: Lane U; coordinator owns Tutor spec and design authority
---

# Diagnostic and Tutor presentation

Authority: [APPROVAL-05](../approval-05.md), section 3 and confirmed amendments. Requirements: [TUTOR-REQ-004–011](../../../features/tutor/README.md#tutor-presentation-lane-u) and U's DIAG-REQ-001 onward.

Diagnostic goes first: remove redundant introduction and Study-style controls, show answered count beside submission, keep the last question reachable, inventory routes, preserve API and due behavior. Fix hidden-face flip-card focus with inert and deliberate focus handling.

Then implement the responsive Tutor sidebar, confirmed deletion, local deterministic greeting/starters, scoped idle mascot, PromptInput attachments and honest waiting state while preserving TUTOR-REQ-001 recovery. Pin/rename wiring uses B's optional/nullable list capability, remains hidden on live v6, and is enabled only for supported list rows.

## Ownership

Lane U owns the paths in APPROVAL-05, its Diagnostic spec, and docs/work/handover-2026/evidence/ui-overhaul.md. Coordinator grants apps/web/src/components/shell/CourseShell.tsx only for the Tutor-route sidebar state, offsets and mobile header integration: activate the change only on Tutor routes, preserve other routes and prove that default behavior in tests. Shared primitive props must be opt-in with unchanged defaults. This is required because CourseShell owns the collapse state and content offset; no other lane edits it.

Coordinator exclusively owns shared Tutor/AI specs. B exclusively owns generated services/api/openapi.json and apps/web/src/lib/api/types.gen.ts; U updates its own Tutor Zod/client files, preserving optional/nullable pinnedAt. Both component-boundary tables belong in the Tutor and Diagnostic specs as scoped by this approval. No Study spec edits or ComposeDock behavior changes.

## Verification and delivery

Run tests for route entries/redirects, greetings, groups, capability gating, dock shape, lazy conversation creation, confirmed deletion and waiting state, plus existing saved/unsaved-answer regressions. Check shared primitive default behavior and non-Tutor shell behavior. Lint, typecheck and build must pass.

Capture 1440px and 375px screenshots for Diagnostic, Tutor empty, Tutor conversation, drag-over and sidebar menu; verify focus, last-question visibility and reduced motion. Label synthetic fixtures separately from Fred's authenticated LTI observation. Never capture tokens or identifying learning data in evidence.

Keep the one Vite server on port 5173 running from U's worktree; Fred alone supplies apps/web/.env.local, agent checks existence only. No other dev server. Baseline audit: 14 frontend tests pass, lint has 18 existing warnings, typecheck/build pass. Implementation and visual checks pending.

Lead designer review remains pending for both approved DESIGN.md exceptions, not an implementation blocker. Stop at AUDIT REPORT before merge; no deployment or push.
