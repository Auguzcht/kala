# WI-26 course authorization — Lane SEC

Staff-phase integration base: `00618c5d5b1bc16dc4f2f782d0f85ead6ef65bff`, including coordinator spec-first commits `0a2be125` / `872c464` and the documentation-only acceptance preparation in `00618c5`. Branch: `codex/wi26-course-authorization`. Initial checkpoint `01c30a4` remains in Git history (rebased as `9016faa` on the final integration base); its earlier route/target blockers were resolved by Amendments 4–5. This is local implementation/proof, not hosted acceptance. Coordinator owns specs, WI status and generated API artifacts.

## Staff-phase route and direct-read inventory

All staff admission reuses validated role, existing `_assert_teaches_course` and institution-scoped `_course_ref`; UUID validation proves shape only. The helper, including its admin early return, is unchanged. `_course_ref` proves admin institution scope. Current enrollment row presence represents current membership; there is no active flag.

| Route/source | Before | Final boundary |
| --- | --- | --- |
| Dashboard heatmap, at-risk | Staff role + filtered data | Caller course/institution admission before learning queries |
| Roster, stats and charts | Staff role + institution passed to cohort | Admission before cohort loading |
| Learner record | Target-student membership, no caller course gate | Caller admission then existing target-student guard |
| Another learner's Twin | Staff role + target-user institution only | Caller admission + enrolled target-student guard before identity/Twin loading |
| Recommendations GET/POST; interventions POST | Target membership only | Caller admission then target guard before read/model/write |
| Recommendation PATCH by rec_id | Scoped update only | Caller admission, one id/institution/course lookup, existing target guard, UPDATE bound to looked-up user_id; missing/zero-update retains 404 |
| Proposed/auto-matched skills GET | Staff role + scoped skill query | Admission before skills and course-keyed worker state |
| Review/detach/approved rejection | Inconsistent caller enrollment checks | Existing shared guards before validation/write/RPC/kick |
| Refresh skills/propose | Staff role only | Admission before unchanged queue/kick logic |
| Assessments GET / grade PATCH | Existing course gate with 403 translation | Staff 403; course/institution 404; existing LMS work unchanged |
| LMS roster preview | Session + institution resolver | Staff-only 403 for students; staff course/institution admission |
| LMS content preview | Session + institution resolver | Staff admission added; existing student preview branch unchanged |
| Ingest POST / status GET | Session; status used course-only lookup | Staff role/course/institution admission before unchanged enqueue/status work |
| Content upload / retag | Staff role + helper, admin early exemption | Add institution-scoped course resolution before processing/storage/RPC |
| Modules GET | Session + filtered content/skill counts | Staff admission; existing student branch unchanged |
| Diagnostic status/get/submit | Session, own identity | Staff admission before availability/generation/grading/evidence work; student branch unchanged |
| Own Twin/next-up/plan | Session, own user + institution | Staff admission; own-student data and responses unchanged |
| Course metadata/memory summary | Session + institution/own memory | Staff admission; student branch unchanged |
| Bank status | Student enrollment, staff exemption | Staff admission before bank reads/kick; student path preserved |

`/class/` consumes roster, stats/charts, at-risk, heatmap and skill review/refresh. Learner sheet/triage and `/class/student/$uid` consume learner record/at-risk plus recommendations/interventions. The class top bar reads course metadata. Students are redirected to `/unauthorized` by the class layout and independently refused by staff APIs.

There is exactly one recommendation-ID route: PATCH `/dashboard/{course_id}/recommendations/{rec_id}`. Lookup uses only user_id and is filtered by id, validated institution and route course. A moved target cannot pass the bound UPDATE. Decisions/notes/history/response shape remain unchanged.

Frontend source search found no direct Supabase table/RPC caller. `getSupabase()` is an unused factory. This does not establish Data API confidentiality; policies were independently tested below. No hosted exposure inspection occurred.

## Policy inventory and proof

0038 alters 22 policies on 20 tables, and nothing else. The migration remains unapplied to hosted systems and was extended in place under explicit coordinator release. All historical SQL/helper definitions are immutable.

| Surface | Concrete prior gap / final treatment |
| --- | --- |
| Evidence/mastery/readiness/enrollment/quiz attempts/exposures/reviews | Stale student token with instructor enrollment and wrong-institution teacher claims could use role-less teaches(); now token role/institution/course admission is explicit |
| SRS | Another-course instructor could read institution-wide learner schedules; now restricted to taught course/current learner |
| Users/aliases | Another-course instructor could read learner identity/aliases institution-wide; now instructor peer reads require enrolled learner in a taught course |
| Profiles | Peer reads remain admin-only; removed learner profiles now follow enrolled-target visibility through the tightened users policy; own profiles and admin institutional staff oversight retained |
| Recommendations | Own student previously saw suggested/rejected; staff could act on an unenrolled learner. Now only assigned statuses for owning student; staff read/INSERT/UPDATE require current target enrollment + student user role and course/institution admission |
| Courses/skills/assessments/guided lessons | Another-course instructor could read institution-wide curriculum. Staff branch narrowed; original non-staff curriculum and granted researcher access preserved |
| Content/generated items/quiz sets/ingest jobs | Role-less teacher helper accepted stale-role/foreign claims. Staff role/institution/enrollment explicit; ingest has no persistent authenticated SELECT grant in this local replay |
| Lesson steps / quiz-set items | Unchanged policies query RLS-protected parents; matrices prove the narrower staff scope propagates |
| Research views/grants | Definitions and grants unchanged; granted researcher still sees the same consented evidence/mastery rows and permitted courses |
| Institutions, launches, audit, consents, data-subject requests, researchers/grants | Governance/self/admin institution or explicit researcher-grant boundaries; no arbitrary instructor peer-learning branch. Institutional governance access after unenrollment is intentionally retained |
| Tutor conversations/messages/attachments | Self-only reads, without a staff peer override; retained own-history access rather than adding a new staff capability |
| Operational/service-only tables | Replay grant inventory confirms no authenticated SELECT path without RLS; no new grants. Hosted grants/exposure remain unknown |

Enrollment rows are admission metadata: the current teacher must read their own instructor enrollment so dependent policies can authorize the course. Instructors can read student enrollments in taught courses; admins retain institution enrollment oversight. Target user-role checks on learning records/identities prevent stale student enrollment on a staff identity becoming learner access. No policy helper is created and no recursive users/enrollments policy dependency is introduced. This is a staff course/learner boundary change, not a comprehensive audit of all governance APIs, researcher scope semantics, SQL RPCs or denormalized-data integrity.

## Real local PostgreSQL verification

Dedicated container `kala-wi26-sec-policy-2d3d`: Supabase Postgres image `17.6.1.158`, PostgreSQL 17.6 aarch64, Docker network `none`, no published ports. Each verifier run creates a fresh `wi26_synthetic_*` database and replays unchanged 0001–0037. Minimal Auth/Storage platform fixtures are explicitly not full Supabase service integration. No environment files, hosted credentials, real identities or content are used. Run the verifier with `cd services/api && uv run python tests/wi26_rls_local.py --container kala-wi26-sec-policy-2d3d`; Python 3.10+ is required by the verifier modules, and the API uv environment supplies the repository-supported Python 3.12+ runtime (verified here as 3.13.14).

- Ten authenticated actor cases × 35 read boundaries pass: own/other student, right/other teacher, same-institution admin, foreign teacher/admin, stale-role token, wrong-institution claim and granted researcher. Of 350 checks, 20 ingest policy checks use a temporary SELECT grant inside each rolled-back transaction. Persistent ingest SELECT stays absent before/after. Direct-grant and conditional-policy evidence are not conflated.
- Recommendations: owning student 5 → 3 statuses; right teacher/admin retain all five; outside-course/foreign staff remain zero; stale student token and wrong-institution teacher claim go 5 → 0. INSERT/UPDATE only succeed for authorized teacher/admin and are rolled back.
- Removed learner before/after counterexample: teacher/admin could previously read personal records, identity/aliases/profile and five recommendations. After tightening, staff personal reads and recommendation INSERT/UPDATE are denied; own student history/identity/profile remains and assigned recommendations remain three. Enrollment is restored only in the synthetic fixture.
- Removed instructor: 20 read boundaries plus recommendations deny after removing the teacher's enrollment.
- All sampled post-migration counts are subsets of the baseline audience. Shared student curriculum reads, own identity/history, admin staff profile oversight and granted researcher views retain tested behavior.
- Policy dumps identify exactly the 22 intended changes. Full public schema/grants/helpers/views/indexes compare identical after removing policy definitions. Fixture table counts and all 37 migration byte/checksum comparisons pass. Every public table with authenticated SELECT in this replay has RLS enabled. No rows are migrated or rewritten by 0038.
- Initial image setup failures (postgres cannot create vector; Auth helpers absent) did not progress to application table replay. The verifier uses the image's local superuser and explicit platform fixture. The expanded baseline probe also discovered missing ingest SELECT; the verifier now records this and rolls back its temporary policy-test grant. No historical SQL was changed to make tests pass.

Final local proof artifacts: `/var/folders/1q/cltfxktj0tb5rvs32t3n3nn40000gn/T/kala-wi26-rls-vyjyr6pw` — local only, not retained. Includes before/after policies/schema/access metadata, actor matrices, removed-target matrix and historical checksums. All fixtures are synthetic.

Official Supabase changelog/RLS and PostgreSQL row-security documentation were consulted on 2026-10-25. Numeric filenames and local-only execution follow the explicit task override. Pinned installed Supabase CLI is 2.114.0; initial pre-install probe resolved global 2.111.0. Docker performs replay directly; neither CLI nor any linked project is used.

## Application tests and scope proof

- Dedicated matrix: 34 operations × six actor cases, five target-student denials, four recommendation scoped-lookup/race cases and six decision-role/status cases: 219 passed. Real role/course/target guards execute; persistence/LMS/model/storage/worker boundaries are synthetic. Denials assert no protected work. Refresh queues/kicks once when allowed; recommendation decision updates once, with all four identity predicates.
- Full API: 829 passed, 30 existing dependency warnings, 28.42s on the final integration base. Worker: 117 passed, 0.34s on that base. Both use committed shared test isolation, fake settings, dotenv disabled and blocked network sockets.
- Reproduce the strict diagnostic proof with `cd services/api && uv run python tests/wi26_scope_local.py` (default final integration base), or `cd services/api && uv run python tests/wi26_scope_local.py --base da765cbd27bd06c53c04ef3698c9410b503eb94a` (original coordinator base). Both pass with the API uv runtime, Python 3.13.14. These verifier scripts require Python 3.10+ (`zip(strict=True)`); the repository API runtime requires Python 3.12+. Bare system python3 may resolve to 3.9 and is not the documented execution path. The verifier matches exact ASTs of the two authorized guard calls, exact guard-only staff blocks, the original translation wrapper on the two gradebook functions and exactly three dependency replacements. It compares every remaining module node, so it cannot hide arbitrary edits merely because they appear inside an if/try block.
- Diagnostic AST proof inventories all 13 routes and proves only authorized guard/dependency changes; helper, imports, queue/debounce/kick logic, upload/retag processing and response shaping are identical. The earlier gradebook translation removal is explicitly authorized. Retained dashboard/ingest/upload functional assertion ASTs are unchanged. The course-data regression changes only student roster expectations to the authorized 403; content remains 200.
- Other routers contain admission guards/imports and, for the sole recommendation-ID route, only the explicitly authorized scoped lookup/target guard/bound UPDATE. Decision state/notes/history/response logic is unchanged.
- Dedicated test/verifier Ruff passes. Changed-router lint adds no unsuppressed baseline findings; three new FastAPI role dependencies carry targeted B008 explanations.
- Web lint/typecheck/build pass on the amended base: 18 existing Fast Refresh warnings, existing route-generator circular dependency notice and large-bundle warning. No frontend or generated API/type file changed. Only SEC’s disposable Docker container/volumes were removed after all SQL verification. No dev server or browser suite was run; H owns the approved denial UI/browser follow-up.
- Documentation checker, its 18 unit tests and git diff whitespace checks pass. Frozen-lock installation changed no dependency manifest/lockfile. No infrastructure, Docker configuration, CI or shared spec file was edited.

## Student-read findings retained at the staff checkpoint

Student branches intentionally remained unchanged in the staff phase. AUTH-REQ-007 below supersedes this finding for the 19 named GETs; mutation routes remain unchanged. `diagnostic.py` GET content (`get_content`, line 149) resolves institution but does not check student course enrollment; GET modules (`list_modules`, line 387) filters by institution/course without enrollment. Diagnostic status/get/submit (lines 598/617/646) use own user/institution but no course enrollment gate. Own Twin/next-up/plan and course metadata/memory retain their prior student admission behavior. These are the requested follow-up findings; this lane does not claim complete student course-enrollment enforcement.

H owns Amendment 6 denial/error presentation: prior LearnerRecord/LearnerTriage/Heatmap connection advice and RosterTable false-empty behavior were reported. SEC does not claim browser/UI acceptance. FG-6, FG-8 and FG-9 remain Fred gates; WI-26 stays open until integration and real acceptance. No hosted policy/grant state, hosted major, full Supabase service stack or hosted Data API acceptance is claimed.

## Historical sources

- [APPROVAL-07](../approval-07.md), section 1 and confirmed Amendments 1–6, plus coordinator releases for policy and target-membership review.


## AUTH-REQ-007 / Amendment 7 student-read continuation

Read-only audit base: `105727ef2052ce8ebf8b6b0e5a78176a9c362735`. Coordinator committed AUTH-REQ-007 and cross-feature references before releasing implementation, and released this phase only after H then M merged. Implementation/scope-proof base: `38f6c75dbf025097bb5b09b45def24bc497450bd`. This continuation changes admission only; no shared spec, generated contract, SQL, infrastructure, frontend or mutation handler is edited.

### Guard placement and complete coverage

Each handler gains exactly `if user.app_role == "student": bank_router._course_for_user(course_id, user)` before existing work. The helper is reused unchanged: it resolves the course under token institution and requires an enrollment for token user/requested course. Its existing enrollment-query semantics are not expanded. No client tenant/role or session course claim establishes admission. Enrolled students can read a requested course they are enrolled in even when the session's launch course differs.

| Router | Guarded existing GET handlers | Count |
| --- | --- | --- |
| courses.py | get_course; memory_summary | 2 |
| twin.py | get_twin; next_up; learning_plan | 3 |
| diagnostic.py | get_content; list_modules; get_diagnostic_status; get_diagnostic | 4 |
| flashcards.py | skill_cards; deck | 2 |
| gamification.py | summary | 1 |
| practice.py | next_item; list_sets; get_set; get_set_results | 4 |
| lessons.py | get_lesson | 1 |
| tutor.py | list_conversations; get_conversation | 2 |

Tutor detail first retains its existing owned-conversation lookup, then checks the returned course before loading messages/attachments. The ownership helper is unchanged, so its mutation callers are unaffected. Diagnostic uses an approved function-local module-reference import inside each student branch, avoiding the Bank/Diagnostic cycle in either initialization order. Other modules gain only the necessary Bank module import.

The five existing GETs with side effects are explicitly included by the spec: Diagnostic question preparation, Study deck selection, Test next item, Test set detail and Lesson retrieval. Admission precedes their existing generation, claims, exposures and worker activity; allowed processing is unchanged. Bank status already has the guard and is byte-identical. H's new own-history endpoint has stronger student-role/institution/enrollment admission and is AST-identical; H's dashboard including staff history is byte-identical.

All 13 inventoried student POST/PATCH/DELETE routes remain unchanged, as do every non-target handler and helper in the eight edited modules. This is not a mutation-enrollment enforcement claim. Researcher/other role behavior is unchanged because the new condition matches only the validated student role. Direct SQL/RLS and the earlier retained own-history policies are unchanged.

### Tests and strict proof

`cd services/api && uv run pytest -q tests/test_wi26_student_read_admission.py` passes 116 cases: 19 GETs × enrolled/non-enrolled/foreign/missing-course/instructor/admin, plus fresh-process Bank/Diagnostic imports in both orders. Real `_course_for_user` executes; only database/LMS/model/business boundaries are synthetic. Non-enrolled and foreign/missing-course students receive the same 404/detail. Denial records no protected read or side effect. Tutor detail allows only its existing owner lookup before admission. Staff assertions prove the student guard is never called. Allowed student tests intentionally use a different session launch-course claim to prove persisted enrollment, rather than the claim, controls access.

`cd services/api && uv run python tests/wi26_student_scope_local.py` passes. It requires exactly 19 known branches, exact import nodes and exact placement (after docstring, except after Tutor's unchanged owner assignment). Removing only those exact nodes must reproduce the whole pre-change module AST. It does not normalize arbitrary if statements, helpers or processing blocks. It additionally checks Bank/dashboard byte identity. New verifiers run with API uv Python 3.13.14; repository runtime minimum remains 3.12+.

The retained full API suite passes 1,014 tests (30 existing dependency warnings, 29.21s); worker passes 117 (0.36s). New dedicated files pass Ruff. Changed files add no lint findings relative to base. Web lint/typecheck/build pass with 18 existing Fast Refresh warnings, the existing generator circular-dependency notice and large-bundle warning. No server/browser session is used. Documentation and immutable-file checks are recorded in the final lane report.

Initial full run found 82 failures while retained fixtures lacked new admission data; after fixture adaptation four higher-level-only tests still lacked a DB admission stub. Those now supply enrollment/course rows. Scope review also caught and restored logger declarations during import formatting before final verification. The final strict AST proof confirms no executable change beyond admission. No existing business assertion was changed or weakened.

### Exact additional retained-test paths and reasons

All ten files import the test-only `wi26_student_fixtures.enrolled_student_reads` adapter. It supplies valid synthetic rows only for the Bank guard's exact two projection shapes and delegates every other query to the original fixture. It is never used by the dedicated authorization matrix. Business-query logs remain business-query logs; the real additional admission reads are separately asserted in the dedicated matrix. No new production fixture or shared isolation harness is introduced.

| Existing test path under services/api/tests | Reason |
| --- | --- |
| test_twin_routes.py | Valid admission for own Twin/next-up/course metadata; add a stub to the helper-only empty next-up test |
| test_course_data_routes.py | Keep the allowed enrolled student content preview regression |
| test_lane_g_diagnostic_availability.py | Give the existing actionable-availability store enrollment/course admission rows |
| test_diagnostic_idempotency.py | Preserve question-read preparation/idempotency scenarios with enrolled admission |
| test_diagnostic_mastery_delta.py | Preserve enrolled question retrieval used by mastery-delta fixtures |
| test_study_deck_approved.py | Supply admission before unchanged deck counts/claims/session tests |
| test_membership_due_eligibility.py | Supply admission before card membership/due selection |
| test_async_item_generation_routes.py | Supply admission before existing Diagnostic/Test question/set GETs |
| test_learn_routes.py | Supply admission before saved-set/card/next-item reads; three helper-only next-item tests gain explicit DB stubs |
| test_tutor_conversation_management.py | Keep existing enrolled list/detail contracts while leaving management mutations intact |

AST comparison confirms every retained assertion in these ten files is identical to the base. New files are `test_wi26_student_read_admission.py`, `wi26_student_scope_local.py`, and `wi26_student_fixtures.py`. No new dependencies or shared conftest edits are needed.

### Acceptance limits

This closes the 19 inventoried student GET admission gaps locally. It deliberately does not add guards to student mutation methods, change Bank helper semantics, alter data/RLS, or claim hosted acceptance. H-owned history routes were re-inventoried and left unchanged. Integration, generated-contract work and Fred FG-6/FG-8/FG-9 remain coordinator/human responsibilities. The follow-up creates no deployment or hosted authorization.
