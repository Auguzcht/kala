# WI-26 course authorization — Lane SEC

Source base: `9c24a85b4bd21ca9995073dd078e2b3f66ea8325`; branch `codex/wi26-course-authorization`. This records local implementation and synthetic checks, not hosted acceptance. Coordinator owns all feature specs, WI status and generated API artifacts.

## Inventory and resulting boundary

Every changed staff route reuses `require_role('instructor', 'admin')` where staff-only, `_assert_teaches_course` and existing institution-scoped `_course_ref`. Shared own-user routes apply the two course guards only for instructor/admin callers; student behavior remains unchanged. UUID validation is shape-only. The helper's admin early return is unchanged, so `_course_ref` is necessary to refuse foreign admins. Current enrollment row presence represents current enrollment; there is no active flag in the schema.

| Source / operation | Before: role / course / institution | Result or explicit remainder |
| --- | --- | --- |
| dashboard heatmap, at-risk | Staff / no caller enrollment / filtered learning queries | Course + institution admission before queries |
| dashboard roster, stats and charts | Staff / no caller enrollment / institution passed to cohort | Course + institution admission before cohort loading |
| learner record | Staff / target student only / institution-filtered | Caller course admission, then existing target membership |
| learner Twin drill-down | Staff / no caller or target enrollment / target user institution | Caller admission + existing target-student guard before identity/Twin loading |
| recommendation GET/POST, intervention POST | Staff / target student only / institution-course filters | Caller admission before target guard, model/read/write |
| recommendation PATCH decision | Staff / none / institution-course update filter | Caller admission before update; target membership remains unresolved below |
| proposed/auto-matched skills GET | Staff / none / scoped skills, course-keyed worker state | Admission before skills/state reads |
| proposed review, detach | Staff / none / scoped updates | Admission before validation/write/wake |
| approved rejection | Staff / instructor enrollment, admin exemption / RPC institution | Reuse existing helper plus institution course resolver before RPC |
| refresh POST skills/propose | Staff / none / course-keyed queue | Admission before queue and worker kick; existing queue logic unchanged |
| GET assessments / PATCH grade | Staff / helper / course resolver | Remove 404-to-403 translation; wrong-role 403, course denial 404 |
| own Twin / next-up / plan | Session / no enrollment admission / token institution, own user | Guard staff callers; preserve own-student queries and response fields |
| course metadata / memory summary | Session / no enrollment admission / institution queries, own memory | Guard staff callers; preserve own-student access |
| bank status | Session / students enrolled, staff exempt / institution course | Staff teacher + institution admission before bank reads/kick; student path preserved |
| LMS roster/content preview | Session / none / institution course resolver | Unchanged by explicit diagnostic three-route restriction; existing student preview access retained |
| ingest POST/status GET | Session / none / POST receives institution; status uses course only | Unchanged by diagnostic restriction; material unresolved gap |
| modules GET | Session / none / institution-filtered content/skills | Unchanged by diagnostic restriction; staff admission gap remains |
| upload / retag | Staff / existing helper / filtered content, helper exempts admin | Unchanged by diagnostic restriction; explicit institution course admission missing for admin |

`/class/` renders roster, cohort stats/charts, at-risk, heatmap and skill review/refresh through the listed API client. Learner sheet, triage and `/class/student/$uid` use learner-record/at-risk plus recommendations/interventions; the legacy student-Twin API is also inventoried and guarded. The class top bar uses course metadata. The class layout redirects students to `/unauthorized`; backend denial does not depend on this UI guard.

Static frontend search found no direct Supabase table/RPC read: `apps/web/src/lib/supabase/client.ts` defines `getSupabase()` with no callers/imports. Learning data is read through the API. No hosted exposure inspection was performed.

## RLS inventory

- 0002 `recs_read` allows own rows regardless of status, teachers via `teaches(course_id)`, or institution admins. 0009 adds staff insert/update. Service-role API access bypasses RLS.
- 0001 `teaches()` checks caller user/course and enrollment role only, without token institution or app role. All historical helper bytes remain unchanged.
- 0038 tightens only recommendation policies: explicit token institution/course match; student self-read limited to approved/modified/completed; instructor token role and matching institution enrollment; institution admin retained. INSERT/UPDATE gain the same staff boundaries. No additional privilege, table, helper or index is created.
- Evidence, mastery, readiness and enrollment policies still use self/teacher/admin branches. Users permit institution-wide staff reads; courses permit institution/grant reads; skills and assessments permit institution reads. 0023 content/item/quiz-set reads and 0017 ingest-job reads use teacher/admin policies. These other policies were inventoried, not changed; full exposed-schema hardening is not claimed. No current frontend direct reader was found.

## Local proof

- `test_wi26_course_authorization.py`: 24 route operations × six actor cases, plus five target-student denials. Real role/course helpers execute; only persistence/LMS/model/worker boundaries are synthetic. Denials assert no protected operation; allowed refresh asserts queue then kick. Shared routes separately preserve student success.
- Existing Lane S tests now expect 404 for course denial and retain wrong-role 403. Existing dashboard/ingest functional assertions are unchanged by AST comparison; only valid admission fixtures were added.
- Diagnostic AST comparison against the base proves exactly `get_assessments`, `post_grade`, `propose_course_skills` changed. The first two only lose the translation wrapper; refresh gains the two existing guard calls. The helper, imports, student previews, queue and debounce logic are identical.
- Complete 0001–0037 byte-preserving replay plus 0038 ran on PostgreSQL 17.6 (aarch64), image `public.ecr.aws/supabase/postgres:17.6.1.158`, inside the dedicated `kala-wi26-sec-2d3d` container, Docker network `none`, no published ports. Each successful verifier run creates a fresh `wi26_synthetic_*` database. Minimal Auth/Storage platform SQL is a fixture, not full Supabase integration. No environment files or hosted credentials were used.
- Final local RLS proof: owning student sees 5 → 3 recommendation rows; right instructor 5 → 5; other-course instructor 0 → 0; same-institution admin 5 → 5; foreign instructor/admin 0 → 0; student token carrying stale instructor enrollment 5 → 0; teacher token with wrong institution 5 → 0. UPDATE/INSERT succeed only for authorized teacher/admin and are rolled back. Five fixture rows are preserved. Policy dumps differ only in recs_read/recs_insert/recs_update. Public schema/grants compare identical after removing policy definitions. Historical migration SHA-256 checks remain equal.
- Initial local setup attempts found that the image's `postgres` role cannot create vector and Auth functions are absent. No application replay progressed past that missing platform setup. The committed verifier uses the image's local superuser and minimal platform fixture, then fresh application databases. No historical SQL was altered to make replay pass.
- Public Supabase changelog and RLS documentation were checked on 2026-10-25. No relevant breaking change changes the approved policy workflow. Numeric filenames and local-only execution follow the task's explicit overrides.

Local proof directory: `/var/folders/1q/cltfxktj0tb5rvs32t3n3nn40000gn/T/kala-wi26-rls-o0j0psh0` — local only, not retained. Contains policy/schema before/after, counts and 37-file hash manifest; all data is synthetic.

## Final verification

| Command / proof | Result |
| --- | --- |
| `cd services/api && uv run pytest -q --tb=short` | 759 passed, 30 existing dependency warnings, 28.04s |
| `cd services/worker && uv run pytest -q` | 117 passed, 0.61s |
| Focused matrix + Lane S + dashboard | 180 passed before final fixture-only ingest update |
| `uv run --project services/api ruff check services/api/tests/test_wi26_course_authorization.py services/api/tests/wi26_rls_local.py` | Passed |
| Changed router lint against base | No added findings; existing Depends/datetime/style findings remain |
| Diagnostic AST ownership proof | Only the three authorized functions changed; helper/preview/queue logic identical |
| Other changed router AST proof | After removing admission imports/calls and the replaced inline enrollment gate, all executable AST nodes identical |
| Retained dashboard/ingest assertion AST proof | Every functional assertion identical to base |
| Local Docker SQL verifier | Two fresh complete replays passed; read/update/insert allow/deny and policy-only schema/grant proof passed |
| `pnpm --filter web lint` | Passed, 0 errors / 18 existing Fast Refresh warnings |
| `pnpm --filter web typecheck` | Passed, existing route-generator circular dependency notice |
| `pnpm --filter web build` | Passed, existing large bundle warning |
| `python3 scripts/docs_check.py` | Passed, zero record-link / machine-path violations |
| `python3 -m unittest discover -s scripts -p 'test_docs_check.py'` | 18 passed |
| `git diff --check` | Passed |

`pnpm install --frozen-lockfile` installed locked dependencies without manifest/lock changes. The initial version probe resolved global CLI 2.111.0 before installation; the installed pinned CLI is 2.114.0. Replay used Docker directly, not either CLI or a linked project. No db:* or hosted type-generation command ran. The dedicated Docker container and its anonymous volumes were removed after verification; no other container, worktree or server was touched. No browser suite ran because the port-5173 server belongs to another worktree and no server handoff was requested. Generated OpenAPI/API types and shared specs are unchanged by this lane.

The first focused run found missing valid-admission fixtures in ten retained dashboard tests. The first full run found the same omission in one refresh/ingest test (758 passed / 1 failed). Adding valid synthetic enrollment/course rows fixed these fixtures; no business assertion was removed or weakened. Final full API run passed all 759 tests.

## Unresolved scope and acceptance blockers

1. `diagnostic.py` may change executable behavior only in three named routes. Roster/content previews, ingest/status, modules, upload and retag cannot gain the missing admission checks in this lane. Particularly, ingest/status remains session-only with a course-only job lookup. Moving the check into ingest_jobs would require changing signatures/callers or creating a new gate; neither is authorized. These remain material gaps under INSTR-REQ-009.
2. Recommendation decision has rec_id but no target user argument or pre-update lookup. Caller course/institution is now guarded, but target student membership cannot be established solely by an existing guard call. A scoped recommendation lookup plus target guard needs coordinator approval beyond guard-call-only edits. No full target-membership completion is claimed.
3. Broader Data API policy exposures above remain unmodified; hosted grants, exposure, policy state and authenticated acceptance are unknown. Local service-role mocks cannot establish hosted isolation.
4. Staff error UI needs H/U follow-up: LearnerRecord, LearnerTriage and Heatmap give connection advice for 404. RosterTable ignores query errors and may show “No students enrolled yet.” No API denial was weakened and no frontend file was edited. Static source findings only; browser worktree server was not started or borrowed.
5. FG-6 migration application, FG-8 deployment and FG-9 live role/course click-through remain Fred gates. Keep WI-26 open; green local tests are not full security sign-off.

## Historical sources

- [APPROVAL-07](../approval-07.md), including all three confirmed amendments and the coordinator's implementation release.
