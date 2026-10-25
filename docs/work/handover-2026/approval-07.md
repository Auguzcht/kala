# APPROVAL-07: finish WI-24, WI-25 and WI-26 today

For Astra (coordinator). Base: current `main` (after DOCS-HYGIENE and TOUR-REFRESH merge). These all still apply:
- AGENTS.md
- the stop rule
- the standing ownership rule and its comment/attribute refinement
- coordinator-owned shared specs (any spec two lanes need is edited only by the coordinator; lanes submit text first)

**Same-day mode with hard Fred gates.** Lanes work in parallel and proceed without planner approval where this document pre-approves the work. Every step that touches the hosted system is a FRED GATE. Before each gate, the coordinator sends Fred one message with: the gate name, exact steps, the expected result, and how to undo it.

## FRED GATES for this round

| Gate | What Fred does | Blocks |
| --- | --- | --- |
| **FG-6 Apply new migrations** | Applies any reviewed `0038+` migration from this round in the SQL editor, with its runbook's pre-checks and post-checks | FG-8 deploy |
| **FG-7a Repair dry run** | Runs the WI-24 repair script in dry-run mode against dev-hosted with his own credentials, and pastes the counts-only output | FG-7b |
| **FG-7b Repair apply** | After planner review of the dry run, runs the reviewed apply SQL or script once, then pastes the post-check output | Close-out |
| **FG-8 Deploy** | `make deploy`, alias and worker checks, `git push origin main`, waits for Vercel Ready | FG-9 |
| **FG-9 Click-through** | Runs the section 5 acceptance pass on the live site | Close-out |

Rollback for FG-8 is the same as before: previous `live` alias, the saved worker image, and the previous Vercel deployment. Rollback for FG-7b is described in the repair runbook. It must exist **before** FG-7a.

## Order

1. **Lane SEC (WI-26)** and **Lane M (WI-24)** start now, in parallel.
2. **Lane H (WI-25)** starts now on its query function and frontend work. It adds its routes **after SEC merges**, because both touch instructor and twin routers.
3. Merge order: SEC, then H. M is a script plus a runbook and merges whenever it is green.
4. FG-6 (if any migrations), then FG-8, then FG-7a and FG-7b, then FG-9.

## 1. Lane SEC: instructor course authorization (WI-26), pre-approved

Spec first: the coordinator commits the requirement text to the instructor and twin specs before implementation. Proposed requirement:

> `INSTR-REQ-0xx`: Every instructor-facing read or write of course or learner data requires (a) an instructor or admin role from the validated token, and (b) for instructors, an active instructor enrollment in that exact course in the same institution. Admins are limited to their own institution. Students can read only their own data. Cross-course and cross-institution requests are refused without revealing whether the resource exists.

1. **Inventory (read-only):** list every route and every direct Supabase read the frontend makes that returns course-level or learner-level data to staff. Include at least: roster, cohort stats and charts, heatmap, at-risk list, learner record, student drill-down, Twin for another user, plan, recommendations (read and decide), skill review, refresh skills, and any `/class/*` data source. For each, record: the role check, the course check, the institution check, and the gap if any. Include the RLS policies on `recommendations` and any other table the frontend reads directly, because WI-26 names "direct recommendation visibility".
2. **Pre-approved fix at the route level, no migration:**
   - Reuse the existing staff course gate (`require_role('instructor','admin')` plus `_assert_teaches_course`, as Lane S did) on every route with a gap.
   - Do not write a new gate.
   - Denials return 403 for wrong role or course, and 404 where the existing pattern hides existence.
3. **RLS:** if a table's RLS policy lets a role read beyond the requirement, write a migration `0038_*` that only tightens policies. Run it once on a throwaway local replay of `0001` to `0037`, with before and after policy dumps. Write `docs/runbooks/0038-apply.md`. That migration goes to **FG-6**. Never loosen a policy.
4. **Stop only if:**
   - a fix would remove access a student legitimately has to their own data
   - it would change admin scope beyond their institution
   - it needs a schema change other than policy tightening
5. **Tests, for every fixed route:**
   - student on a staff route: 403
   - instructor of another course: 404
   - instructor from another institution: 404
   - admin of another institution: 404
   - correct instructor: allowed
   - admin of the same institution: allowed

   Plus RLS tests against the local replay for any policy change, covering authenticated reads as student, as instructor of another course, and as the correct instructor.

Owned:
- instructor and twin router files: auth dependencies and guard calls only
- the recommendations router: guards only
- the new migration file and its runbook
- tests

The coordinator commits all spec text.

## 2. Lane H: full evidence history (WI-25), pre-approved

Spec first: the coordinator commits `TWIN-REQ-0xx` (student, own history) and `INSTR-REQ-0xx` (instructor, learner history) before H adds routes.

1. **API:**
   - `GET /courses/{course_id}/twin/evidence?cursor=&limit=` for the student's own history.
   - The matching instructor route for a learner, guarded by SEC's gate.
   - Keyset pagination on `(created_at desc, id desc)`, default limit 25, maximum 100, returning an opaque `nextCursor`.
   - Existing response fields are unchanged. All new fields are optional.
2. **Query cost:** check the existing indexes on `evidence_events` for `(user_id, course_id, created_at)`.
   - If a suitable index exists, no migration.
   - If not, write an index-only migration `0039_*` with a runbook. It goes to **FG-6**. Use `create index if not exists`, no table rewrite.
3. **Frontend:** the shared evidence ledger keeps its 10-row pages and labels, and adds "Load older activity" from the cursor for student Twin and instructor learner views. Change "Last 20/25 events" labels to "Showing N of your activity" wording only where full paging is active. Keep reduced motion, keyboard access and 40px controls.
4. **Tests:**
   - first page, next page, last page
   - a stable order with equal timestamps
   - an invalid or tampered cursor gets 422
   - other-user or other-course access is refused (SEC gate)
   - limit bounds
   - browser tests for "Load older activity" at 375px and 1440px
5. **Stop only if** paging needs a schema change other than an index.

Owned:
- the new evidence routes, added after SEC merges
- the evidence query functions in `services/api/app/twin/`
- the shared ledger component and its callers
- tests
- the index migration and its runbook, if needed

## 3. Lane M: duplicate identity history repair (WI-24), gated at FG-7

Scope: only the duplicate pairs found in this tenant (Alfred, Hanna, and any other pair the inventory proves). This is a one-time repair of dev-hosted test data, not a product feature.

1. **Inventory (local and static):**
   - Every table and column that references a user ID: aliases, enrollments, evidence, mastery and SRS state, card schedules, quiz set attempts and answers, exposures, tutor conversations and attachments, recommendations and decisions, readiness snapshots, gamification and XP, and audit rows.
   - Every unique constraint that could collide when two users' rows land on one user (for example per-skill mastery, per-card schedule, per-set attempt numbers).
   - Every trigger that blocks updates. `evidence_events` and `audit_log` are append-only by design.
2. **Design**, and write it into `docs/runbooks/identity-repair.md` before any code:
   - The canonical user is the one the current resolver maps the LMS uuid and LTI `sub` to after Lane I's fix. Both histories are preserved.
   - **Evidence:** append-only rows are re-attributed to the canonical user inside one transaction. The append-only trigger is suspended only for that statement and only for the listed user IDs, then restored in the same transaction. An `audit_log` row records the merge: who, when, which user IDs, and row counts. If the design cannot do this safely, stop and propose the alternative.
   - **Derived state** (mastery, readiness) is not merged by hand. Delete the duplicate's derived rows and let the existing `reconcile_mastery` and readiness jobs recompute from evidence. Document how to trigger them.
   - **Collisions:** for SRS or card schedules and attempts, define a deterministic rule for each table (for example keep the most recent review state, renumber attempts after the canonical user's highest). List any table where no safe rule exists, and stop.
   - The legacy user's aliases point to the canonical user. The legacy user row stays as an empty, unenrolled shell. No delete.
3. **Script:** `scripts/repair_identity_split.py`.
   - **Dry run by default.** It prints per-table counts that would move, collisions found and how each resolves, and whether the pair is already converged. No names, emails, IDs or content in the output, only per-pair labels like "pair 1".
   - `--apply --confirm` runs everything in one transaction and prints post-check counts.
   - Pair IDs come from a local, gitignored input file that Fred creates. The script never queries by name or email.
4. **Prove it locally first:** on a throwaway local Supabase replay of all migrations, with synthetic fixtures that recreate both cases. A Hanna-like case has all history on one side. An Alfred-like case has history on both sides, including colliding schedules and attempts. Show dry run, apply, post-checks, a re-run that is a no-op, and that the append-only trigger is restored.
5. **Rollback** in the runbook: a pre-apply `pg_dump` of the affected rows for the listed users (Fred takes it, stored locally and never committed), plus how to restore it.
6. **Stop** before FG-7a with the AUDIT REPORT. The planner reviews the design, the local proof and the dry-run output format before Fred runs anything on dev-hosted.

Owned: `scripts/repair_identity_split.py`, its tests and fixtures, `docs/runbooks/identity-repair.md`, the WI-24 work item. No application code changes.

## 4. Integration and gates

1. After SEC, H and M are green: merge SEC, then H, then M. Run full API and worker suites, all frontend and browser suites (including tours), lint, typecheck, build, the docs check, and the migration checksums. Only new `0038`/`0039` migrations may appear.
2. **FG-6:** post the runbooks for any new migrations. Fred applies them and posts the post-checks.
3. **FG-8:** post the final SHA and the deploy steps.
4. **FG-7a, after FG-8:** post the dry-run steps. The planner reviews the output.
5. **FG-7b:** post the apply steps and post-checks. After apply, trigger or wait for the worker's recompute, then post-check that mastery and readiness are rebuilt for the canonical users.
6. **FG-9:** the click-through in section 5.

## 5. FG-9 acceptance additions

Add these to the existing FG-5 checklist and record them in `acceptance-2026-10-25.md`:

- **WI-26:**
  - The instructor sees only their own course.
  - Pasting another course's learner URL is refused.
  - A student opening a `/class/*` URL is refused.
- **WI-25:**
  - The student Twin and the instructor learner record can load older activity until the first event.
  - The labels match what is shown.
- **WI-24:**
  - Alfred and Hanna each appear once in the roster.
  - Each shows their full combined activity and recent last-active.
  - The student Twin and the instructor record agree on counts for the same window.
  - Opening the views creates no new XP or evidence.

## 6. Close-out

The coordinator updates `closeout.md`: WI-24, WI-25 and WI-26 move to confirmed done, or partial with the exact remainder and branch. The record includes the new SHA, alias version, applied migrations and the repair's post-check counts. Then remove merged worktrees, and the freeze begins.

If a lane is not green when Fred is ready for FG-8, it is left out and recorded with its branch. The deploy does not wait. WI-26 is the exception: if SEC is not green, Fred is told plainly, because it is the security item. He decides whether to deploy without it.

## Confirmed amendments — 2026-10-25

### Amendment 1: created_at, not occurred_at

The original paging column did not exist. Lane H pages on `(created_at DESC, id DESC)` and preserves the existing `createdAt` response field. The ID tiebreak is required for equal timestamps. The index check is `(user_id, course_id, created_at)`; if needed, 0039 indexes those columns plus `id` for the tiebreak, using `create index if not exists`, index-only. Lane M must not change `evidence_events.created_at` when re-attributing rows; before/after post-checks prove identical timestamps for every moved row. No other schema change is authorized.

### Amendment 2: course denial is 404, role denial is 403

An untaught/unavailable course or learner and another institution return 404, hiding existence. A wrong role on a staff route returns 403. SEC tests require other-course instructor 404, cross-institution instructor/admin 404, student on a staff route 403, correct instructor allowed and same-institution admin allowed. Reuse the existing helper behavior. SEC may remove the gradebook routes' 404-to-403 translation in GET assessments and PATCH grade; the coordinator updates INGEST-REQ-001 first and SEC updates Lane S tests. Confirm staff screens show a truthful unavailable/not-found state for 404; record any crash or misleading empty roster for H/U rather than changing API denial semantics.

### Amendment 3: refresh route added to SEC's diagnostic.py scope

SEC may add existing staff/course guards to `POST /courses/{course_id}/skills/propose`. Denials match Amendment 2; correct instructors and same-institution admins can queue refresh. Denied requests enqueue nothing and kick no worker. In diagnostic.py, only guard calls on GET assessments, PATCH grade and POST skills/propose may change executable behavior. Do not change the helper, queue/debounce logic or student preview routes. Prove this narrow scope by AST/diff comparison.

Standing clarification: every route the inventory finds serving staff course/learner data or triggering staff course actions is in SEC's scope for guard calls in any router file no other active lane owns. Stop when another active lane owns the file or the fix needs more than guard calls. H's router additions remain serialized after SEC merges. Preserve legitimate student own-data and existing preview access; do not broaden admin scope.
