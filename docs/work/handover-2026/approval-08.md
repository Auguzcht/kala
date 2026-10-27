# APPROVAL-08: final frontend pass and Tutor polish

2026-10-27. Fred's same-day approval. This is a delivery record, not a substitute for DESIGN.md or the current feature requirements. Local main before this round: `d46e3e482bf07678b73e8aee0199630e2ca0a259`. The 07 application changes remain unpushed; only the separate compact-context utility was published. No hosted gate is assumed complete.

## Initial APPROVAL-07 status

H merged atbc8a2f5 after browser green; M finalcfe8311 merged at38f6c75 after governance proof; Amendment7 final9f2d5fb merged at63230a3. Generated contracts8e51040. Final local API1,014, worker117, frontend/tour33, Study4 and browser1,474 pass; web/config/docs/AST/local migration checks pass. WI-24/25/26 remain open awaiting actual human outcomes. FG-6/8/7a/7b/9 are not recorded as executed. Current main also includes the isolated published context utility; this does not publish 07.

## Coordinator first

Coordinator alone edits DESIGN.md and Diagnostic/Study/Tutor specs, with REQ IDs/change logs before code. DESIGN gains Pending and loading states: activated disabled submit controls only; never loading/skeleton/stat/status spinners; one model shimmer with disabled initiating control; page/card skeletons plus at most one line. Static mascot/skeleton loading card shared by Test/Study/Diagnostic; Diagnostic/Test content widths agree.

H02 material copy is never student-facing, while instructor skill review keeps it. Study completion defines Get new cards as due/new only, no replay, no already-rated resurfacing; empty stays on completion with truthful next-review date. Tutor defines rename dialog, prompt-only small talk, images planned because text-only sanitization cannot de-identify images, and the conditional last-prompt decision below.

## Lanes and scope

| Lane | Branch | Owned implementation paths | Required work |
| --- | --- | --- | --- |
| U2 | codex/final-ui-pass | apps/web/src/components/** and apps/web/src/features/** except features/tutor/**, matching tests; all07 paths excluded except E2 | Remove student material copy; exact New practice set/Fresh questions. Choose5,10,or20 wording; flag-accuracy finding only for reported IaaS/PaaS/SaaS four sets/20 attempts; complete Spinner/Loader2/animate-spin keep/remove inventory; shared loading card/column width; Get new cards and safe no-new state; tour compatibility; desktop/mobile tests |
| T2 | codex/tutor-polish | apps/web/src/features/tutor/**, Tutor prompt files under services/api/app/ai/, matching tests; tutor.py only E1 and conditional Amendment2B new function | Dialog rename; Tutor spinner sweep; short greeting/no-roadmap prompt; last-prompt feasibility before any implementation; FG-L aggregates |

Both branches start from current local main after coordinator spec commits. Shared specs, approvals, WI and evidence records belong to coordinator, not lanes. Lanes submit report/evidence text in chat. They stop at AGENTS AUDIT REPORT before merge. Coordinator reviews; no lane pushes, deploys, changes infrastructure/config/secrets, applies SQL or writes hosted data. Stop for migration, secret/config change, unowned file, changed evidence/mastery writes or unresolved brief/spec contradiction. All other scoped work is pre-approved.

## Amendment 1 — two named exceptions to the07 path freeze

These exceed the AGENTS comment/attribute exception and are approved by name. Every other07 path stays protected.

**E1, T2, services/api/app/routers/tutor.py:** change only the one module-level tutor system prompt string constant after Amendment7 is merged, rebasing onto that main. No other existing line/import/guard/signature. If the prompt is not one module-level constant, stop; no refactor. Compare AST dumps: only that string literal differs. List Amendment7 guards by function name and confirm each survives. Rerun full API plus Amendment7 enrollment tests.

**E2, U2, apps/web/src/features/diagnostic/tests/frontend-closeout.browser.mjs:** wait for H merge, then rebase onto main. Only material-copy assertions may change: absent for students, present for instructors if that test covers them. Do not change H history fixtures, paging setup, seeds or other assertions. Attach an assertion-lines-only diff. Rerun H full browser suite plus U2 suites on5173, one server at a time.

Merge order: 07 first (already H,M,Amendment7), then T2, then U2. Each later lane rebases and proves earlier edits survive. Each report names E1/E2 and includes its proof.

## Amendment 2A — FG-L, delegated by Fred, read-only

Only these AWS commands are allowed:

- aws logs describe-log-groups --log-group-name-prefix /aws/lambda/
- aws logs start-query
- aws logs get-query-results
- aws logs filter-log-events
- aws sts get-caller-identity (print Account only; no ARN/user name)

Discover the API Lambda log group from returned groups; if more than one could be API, stop and ask. Query the last48 hours:

```text
fields @timestamp, @message
| filter @message like /tutor_timing/ or @message like /provider/
| sort @timestamp desc
| limit 50
```

Compute stage median/max for retrieval/embedding, primary model, fallback and total; count requests using fallback; count primary429/other errors by model/status. Answer whether15–20s is primarily slow primary, failed-primary+fallback, retrieval, or not established by the sample. Recommend keep config, swap primary/fallback as a separate Fred-gated secret edit, or streaming as an ITO follow-up. Never apply.

Print/save only aggregate numbers, stage names, model names and statuses. Do not print/save raw lines, bodies, user/institution IDs, email, tokens or secrets. Parse captures in memory, never a repo output file. Any evidence notes raw data as local only, not retained. Stop for missing/expired credentials, needing another AWS command, or a body/personal-data field; report the field name only as a diagnostics finding. Never write/put/delete/update/tag. No other gate is delegated.

## Amendment 2B — edit only the most recent sent prompt

Latest user prompt only; no edit control on older messages. Hover/focus pencil under the last user message. Inline editor, Cancel/Send, Esc cancels; Send disabled for blank/unchanged. Saving replaces the last exchange (old user prompt and Kala reply), then sends edited text.

Build only after feasibility proves no migration, no evidence/mastery table change, and owner/institution/course-scoped last-exchange deletion respecting Amendment7. If any fails: do not build; record planned TUTOR requirement and exact ITO deferral reason. Either way coordinator updates the spec first. A built API route is a **new function only**, separately permitted beyond E1; pre-existing functions/guards stay untouched and E1 AST proof continues to cover them. No refactor or new helper policy. Concrete route/error/retry/concurrency contract is committed before implementation.

## Gates and acceptance

Order unchanged: FG-6, FG-8, FG-7a/7b, FG-9. Land reviewed08 changes on local main before FG-8 for one combined release. No agent deploy/push of application changes.

FG-9 adds student dashboard with no material copy, one hint indicator, Get new cards empty behavior, rename dialog, short Hello reply and matching loading/content width at375px/1440px. Conditional edit acceptance is recorded only if implemented under Amendment2B. Each lane and FG-L end with the full AGENTS AUDIT REPORT block. Synthetic checks do not fill live rows.


## Amendment 3 — E3, coordinator-only tour proof update

Coordinator alone edits apps/web/src/components/shell/tests/tour-anchors.test.mjs on main before lanes rebase; lanes never touch it. Preserve all seven original historical AST comparisons against accepted TOUR-REFRESH fullSHAc3d6b6351f7adbfc6e8da1d43e371014473c8b74 and pre-tour3a6a0aab27a8212f77b83e96b26127d830a696ba. Prefer committed AST checksums for both sides so shallow/fresh clones run. If Git objects are read instead, a missing object fails clearly, never skips.

Check every current tour target/selector against its current rendering component, including forwarded IDs/anchors, not only the original seven. Keep current PracticePanel documentation-comment check. No skip, only, todo, weakened assertion or deleted comparison; never delete/rename an anchor to make the test pass. A genuine disappeared target stops for coordinator tour-definition then TOUR-spec resolution. If an element moves, retain/report its anchor.

Record old-test run before change, any failures attributable to08, new-test run on main and post-T2/U2 merge run. Name all seven comparisons and identify TwinBody as the one already historical rather than a current-body check. Run full tour browser after both merges, zero mutating requests, report its assertion count beside old616.


## Amendment 4 — TOUR-2 and neutral Diagnostic empty copy

Coordinator commits TOUR-REQ-002/003/004/007 before implementation. New lane codex/tour-rework owns tour shell and definitions under apps/web/src/components/shell (*Tour* files and student/instructor definitions) and tour browser suites, never E3. U2 does not edit these paths. CourseShell's tour start/planning region is the tour shell and is reserved for TOUR-2; U2 reports its Spinner findings for that file rather than editing it.

Build complete plan before step1 using read-only GETs/counts only, fixed x of N, every step target+centered same-page fallback, no silent skips/toasts, dev-only missing-target warning, bounded page-loading wait, exact target/fixed-padding highlight, popover flipping clear of target, cross-page Back. Never click Continue/Start/rating/submit; no data writes or mutating requests. Copy at most two short sentences, no semicolons or material-availability wording. Start tour follows C1, one pending indicator.

Student outline replaces17 steps with12: workspace Next up / centered “Kala suggests your next step here.”; workspace Your twin at a glance; Diagnostic start / centered “Your baseline check opens when its questions are ready. Until then, practice in Skills.”; Skills first row / “Skills appear here once your course is set up.”; Lesson content/Continue explanation only; Lesson dock button; Study Start studying button only/due count; centered completion explanation (Go through these again replays, Get new cards checks due/new); Test saved sets or New practice set; Tutor composer; Tutor history/... rename/pin/delete explanation; Twin ledger/Load older activity / “Your learning evidence will show here as you practice.” General unexpected-target fallback still applies to steps expected always present.

TOUR-2 first submits required anchors. U2/T2 add owned attributes only; coordinator merges anchors before TOUR-2 rebases. A required anchor in07-protected source stops. Tests: happy, empty(no Diagnostic questions,0due,0sets,empty ledger), mixed, at375px/1440px; fixed total/order, target-or-fallback each step, no toast/mutation and correct highlight bounds. Instructor audit same rules, fix violations only without restructure. Stop if a step needs a write, a required anchor is07-protected, or all three states cannot pass before integration cutoff; no partial merge, Fred decides.

U2-1 also gives student Diagnostic empty state exactly “Your baseline check isn't ready yet. Check back later.” No material/course-team copy; instructor wording retained.

## Amendment 5 — E4, workspace route ownership

U2 may edit apps/web/src/routes/course/index.tsx only to remove the material notice89–93 and unused variable45 (only if no other reader), after checking whether any07 lane touched it and rebasing if so. Role audit first: student-only route removes notice; if staff also reach it, retain staff-only notice. Never remove shared hooks/queries, Diagnostic badges/action counts, other queries, navigation/layout or unrelated imports. Only now-unused imports may be removed. TOUR-2-required Next up/Twin glance data-tour anchors are separately allowed as attribute-only edits in this file, same commit. Report route role reachability, anchors, narrow diff, student absence and instructor presence if reachable, workspace tour tests and lint/typecheck/build. Every other07 path remains frozen.
