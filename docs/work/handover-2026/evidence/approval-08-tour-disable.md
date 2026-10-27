# APPROVAL-08 Amendment7a — minimal student tour disable

2026-10-27. New branch codex/disable-student-tour, basead7a9acbeefaae05a3a4d6d77a722db5a9179ccb, candidate0dbc3e31679bf67594942bcee8ca859c61b93c8c. Coordinator reviewed the two-file diff and merged locally ateb3e739795f0f0ece5c9e4568cb68b71216b19c0. No full TOUR-2 implementation is included.

One false source flag gates the student runner, manual entry, auto-offer and confirmation. Removing the flag and four rendering gates restores the original executable AST exactly: SHA-256 d4f72522ac0e5af167a766b239e5a4bac76eb2faf1c84bc02b5db9cf39f46174. Tour definitions, copy and anchors are unchanged. No API-client/store/query-hook mode or read-only barrier was implemented.

Instructor decision: **keep unchanged**. The destination audit traces10 mounted GET handlers and42 reachable local functions; their database operations are SELECTs. The instructor shell/definitions/runner are byte-identical. This is source evidence for the retained destinations, not a promise about future routes or hosted execution.

Browser suite: **646 assertions passed**, compared with historical616. At375px/1440px it checks no student offer/manual entry for fresh, dismissed and previous-marker states, no runner after stale local tour state, ordinary navigation, all27 retained instructor steps, empty roster, Back and exits. Zero mutating HTTP requests were observed under synthetic fixtures. That network observation is not a database-side proof for the blocked student destinations. No twelve-step student walkthrough is claimed.

E3 passes53, retaining seven historical proofs; tour-route passes3, no skips/todo. Lint/typecheck/build pass with18 existing Fast Refresh warnings, existing router circular-dependency and bundle-size notices. Only CourseShell.tsx and tour.browser.mjs differ from base. Visual inspection covered mobile student absence and the retained instructor overlay. Vite PID16268 and parent16219 exited;5173 was free before release to T2. Screenshots are local only, not retained.

Preserved full codex/tour-rework stays clean atbeccf5915c4caea045fc5a6e8be2945aaf8812ad. Original audit Git blob d68ac6c13e7bc3c1923152ebebd2874b30619877 remains untouched; coordinator independently verifies file SHA-256 e80a3c91f6a0ac85881adcd4d41150da61e01d66dc1a4fa860ce5b98278f80d4. WI-30 stays blocked, WI-32 is planned for ITO. FG-9 now asks for absent student entry and the retained instructor walkthrough.

```text
AUDIT REPORT
Task / brief ID: APPROVAL-08 Amendment7a; WI-33
Branch and worktree: codex/disable-student-tour; separate lane worktree
  (local only, not retained)
Base revision: ad7a9acbeefaae05a3a4d6d77a722db5a9179ccb
Files changed:
  apps/web/src/components/shell/CourseShell.tsx
  apps/web/src/components/shell/tests/tour.browser.mjs
REQ / WI IDs touched: TOUR-REQ-008; WI-33
Commands run and results: browser646 versus old616; E3 53; routes3;
  lint/typecheck/build; one-flag/four-gate AST and disjoint scope proofs pass.
Spec changes made: none by lane; coordinator committed before implementation.
Evidence added: this reconciled lane report; original TOUR-2 audit unchanged.
Anything not done, and why: full TOUR-2 remains blocked/unmerged;
  no hosted execution or human acceptance; no read-only client/store mode.
Risks or questions for the planner: source/synthetic evidence is not hosted
  acceptance; future no-write proof needs DB writes or side-effect logs.
Secrets printed: none (confirmed).
```
