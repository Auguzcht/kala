<!-- Historical lane submission, preserved verbatim below. Delivery state is tracked in approval-02-coordinator.md. Local scratch paths are historical evidence locations, not fresh-clone dependencies. -->

AUDIT REPORT — Lane F / APPROVAL-02 amendment
Date: 2026-10-24 (Asia/Manila)
Disposition: committed locally; STOPPED BEFORE MERGE. Coordinator owns integration.

Task: satisfy the conditions on approval of Lane F commit 8e06e6a.
Branch: codex/study-deck
Worktree: /Users/fred/.codex/worktrees/0e52/kala
Original lane base: e9de105d7f3074ec39f54e32b1f2b5e2bda669ed
Amendment base: 8e06e6a2a6a1df1f91ceff23c48435f75599b6aa
Final commit: 7041bc70dc465a33ff58c36bac034e265c1d9f27
Commit: docs(study): record approved availability requirements
REQ IDs touched in amendment: STUDY-REQ-004, STUDY-REQ-005; STUDY-REQ-002
clarified by moving native-fresh selection to its own requirement, and
STUDY-REQ-003 verification limitation documented. Cumulative lane: REQ-001–005.
WI IDs: none separately assigned.

FILES CHANGED IN AMENDMENT (three owned paths)
/Users/fred/.codex/worktrees/0e52/kala/docs/features/study/README.md
/Users/fred/.codex/worktrees/0e52/kala/services/api/tests/test_study_deck_approved.py
/Users/fred/.codex/worktrees/0e52/kala/apps/web/src/features/flashcards/tests/study-deck.test.mjs
Cumulative lane still changes the same nine files listed in audit-report.txt.
No runtime code, test body, shared conftest, harness, config, package manifest
or lockfile changed in this amendment.

DECISIONS / JUSTIFICATION
Both original fixes are retained within the Study availability defect class.
- STUDY-REQ-004: membership and Study all already support native flashcards,
  but the old fresh selection omitted them. That could leave an empty review
  deck and display caught up while eligible native cards remained. Study's
  include_flashcards opt-in fixes that omission; default shared MCQ selector
  behavior for Test/diagnostic/lesson is preserved.
- STUDY-REQ-005: the empty course-wide deck lookup returned no preparing skill
  when every visible bank was ready, then treated absence of that candidate as
  Preparing. This fixes the same empty-deck availability-classification
  boundary: deriving a displayed state from actual bank readiness and queue
  availability. It makes the already-approved caught-up versus no-cards-yet
  distinction observable for ready courses. This particular symptom was false
  Preparing; it is not claimed to have omitted cards from the server queue.

SPEC AND TEST ALIGNMENT
Added separate implemented requirements with rules, rationale, acceptance and
verification pointers. Added separate APPROVAL-02 change-log entries for
STUDY-REQ-004 and STUDY-REQ-005, dated 2026-10-24.
Renamed only:
  test_STUDY_REQ_002_study_fresh_pool_includes_native_flip_cards
  -> test_STUDY_REQ_004_study_fresh_pool_includes_native_flip_cards
  STUDY-REQ-003 empty ready course distinguishes caught up from no cards
  -> STUDY-REQ-005 empty ready course distinguishes caught up from no cards
A source comparison against the amendment base confirmed the two test files
are byte-for-byte identical after those single name substitutions. A path-set
assertion confirmed only the three approved amendment paths changed.

Added explicit known limitation: frontend interaction tests need the external
matching react/react-test-renderer fixture (verified 19.2.8) selected through
KALA_STUDY_TEST_DEPS and the --experimental-vm-modules flag. A clean checkout
cannot run them without that fixture. Provider hooks/UI shells are mocked;
layout and live HTTP integration are unverified. Renderer is deprecated.
No dependencies were installed or added for APPROVAL-02. Integration harness
work remains coordinator-owned and was not touched.

EXACT VERIFICATION COMMANDS / RESULTS
All commands run from /Users/fred/.codex/worktrees/0e52/kala.
1. env -i PATH="$PATH" services/api/.venv/bin/python services/api/tests/run_study_checks.py services/api/tests/test_study_deck_approved.py services/api/tests/test_membership_due_eligibility.py services/api/tests/test_bank_serving.py -q --tb=short
   PASS: 22 tests, 0.22s; one existing FastAPI/Starlette httpx deprecation
   warning. Network is blocked, dotenv discovery disabled, synthetic signing
   key generated but never displayed by the existing dedicated launcher.
2. KALA_STUDY_TEST_DEPS=/tmp/kala-lane-f-renderer node --experimental-vm-modules --test apps/web/src/features/flashcards/tests/study-deck.test.mjs
   PASS: 4 component tests, including renamed STUDY-REQ-005; 313ms total.
   Existing VM-module and react-test-renderer deprecation warnings.
3. services/api/.venv/bin/ruff check services/api/tests/test_study_deck_approved.py
   PASS: all checks passed.
4. pnpm --filter web lint
   PASS: 0 errors, 18 pre-existing Fast Refresh warnings.
5. git diff --check; git diff --cached --check
   PASS. Scope and naming-only source assertions described above PASS.
6. git status --short --branch; git rev-parse HEAD
   PASS: clean status, codex/study-deck, final SHA recorded above.

PRIOR CHECKS STILL APPLICABLE (not rerun for docs/test-name-only amendment)
Full API suite: 389 passed. Web typecheck and production build: passed.
See audit-report.txt for original exact commands, warnings, setup failures,
resource inventory, all nine cumulative paths and implementation evidence.
No runtime or test-body changes invalidate those results. Current affected
regressions and lint were rerun as listed above.

LIMITATIONS / RISKS
No live smoke, hosted database/API/provider/LMS calls, Blackboard verification,
SQL replay, browser visual check or deployment performed. No SQL/RPC changes.
External renderer limitation is now explicit in the spec. Existing broader
Ruff/dependency/build warnings remain recorded in the original audit.
Remaining integration work and any test-harness adjustments belong to the
coordinator; Fred owns the eventual integrated manual click-through.

EXTRA-PATH GRANTS: none requested or required.
CLEAN STATUS: clean after commit 7041bc70dc465a33ff58c36bac034e265c1d9f27.
RESOURCE STATE: no servers, listeners, Docker containers or browser sessions
created. Existing main, Kala Audit, other worktrees and Vite :5173 untouched.
Previously created worktree-local ignored dependencies/caches/build output and
/private/tmp/kala-lane-f-renderer fixture retained; no active task processes.
No push, merge, rebase or deploy. Stopped for coordinator review.
Secrets printed: none. No secret files or .env.example read.
