# APPROVAL-06 (rev 2, same-day mode): close-out of the frontend handoff findings (H01 to H12)

For Astra (coordinator). Authority: AGENTS.md, APPROVAL-05 rev 2 with its amendments, and the frontend finalization handoff at `e1b0250` (`codex/ui-overhaul`). These all still apply:
- the stop rule
- the standing ownership rule
- coordinator-owned tutor and AI specs
- the DESIGN.md exceptions

**Goal: deploy and close out today, 2026-10-25.** Agents work in parallel and proceed without waiting for planner approval where this document pre-approves the work. **Agents always stop at a FRED GATE.** Those are the steps only Fred can do. A gate is a hard stop: report what is ready, the exact steps for Fred, and what to check afterwards, then wait.

## FRED GATES (hard stops, never done by an agent)

| Gate | What Fred does | Who waits on it |
| --- | --- | --- |
| **FG-1 Provider config** | Checks the OpenRouter rate limits, credits and 429s. Sets a **paid** fallback model on a different provider from the primary in `kala/app` (no `:free` model). Forces fresh Lambda instances. Retests the hint | Acceptance of H03. Nothing else waits, so it runs in parallel |
| **FG-2 Postgres version** | Reads the hosted Postgres major from Supabase (Project Settings > Infrastructure) and posts it | Lane DB only |
| **FG-3 Apply migration 0037** | Runs `docs/runbooks/0037-apply.md` in the Supabase SQL editor, including the post-checks, and posts the results | The deploy (FG-4). The live v6 keeps working because the change only adds a column |
| **FG-4 Deploy** | `make deploy`, checks the `live` alias moved and the worker updated, then `git push origin main` and waits for Vercel to show Ready | The click-through (FG-5) |
| **FG-5 Click-through** | Runs the acceptance pass in section 6 on the live system and posts the results | Close-out (section 7) |
| **FG-R Rollback (only if needed)** | Points the `live` alias back to the previous version and promotes the previous Vercel deployment | n/a |

Before every gate, the coordinator sends Fred one message containing: the gate name, the exact commands or console steps, the expected result, and the rollback.

## 0. Planner decisions on the handoff

| Ref | Decision |
| --- | --- |
| H01 identity split | **(a) The code fix ships today.** ITO builds from a clean database, so the code path is what they inherit. **(b) The dev-hosted data repair is deferred.** No repair script is built or run today. Record it as a `planned` work item: the dev-hosted test records for Alfred and Hanna are split, and this does not affect ITO's fresh build |
| H02 baseline count | Policy in section 3, pre-approved |
| H03 provider | The primary model returned HTTP 429, so this is operational first (FG-1). Code only integrates the approved diagnostics |
| H04 rename and pin | Integrate Lane B. Migration `0037` is applied at FG-3 |
| H05 to H11 | Lane U, pre-approved (section 4) |
| H12 count windows | Label the windows honestly now. Full-history paging is `deferred` |
| Legacy routes | Keep `/course/lessons` and the course-wide due-review deck in `/course/flashcards`, and fix their copy and error states. `/course/practice` without a skill redirects to `/course/skills`. Delete no routes |
| Tours | Rehearse at FG-5. Fix only real breakage |
| Lateness rule | When Fred is ready for FG-4, whatever is not green is left out and recorded as `planned` with its branch. **The deploy never waits on an unfinished lane** |

## 1. Start now, in parallel

| Lane | Starts from | First action |
| --- | --- | --- |
| Coordinator (integration) | `cab26de` | Section 2 |
| I (identity) | fresh branch from `cab26de` | Read-only investigation. Rebases onto the integrated main before implementing |
| G (Diagnostic availability) | fresh branch from `cab26de` | Read-only investigation. Rebases onto the integrated main before implementing |
| U (frontend fixes) | branch from `e1b0250` | H05 to H11. Rebases onto the integrated main |
| R, P, C2 (docs) | as before | Continue |
| DB | gated on FG-2 | Waits |

The coordinator posts the FG-1 and FG-2 instructions to Fred **immediately**, so they happen while the lanes run.

## 2. Integration (coordinator)

Record exact revisions, then merge into local `main` in this order, running the full checks after each merge:

1. `codex/tutor-provider-502` at `7f484bb` (diagnostics only)
2. `codex/tutor-conversation-api` at `0ccbb22` (Lane B with migration `0037`)
3. `codex/ui-overhaul` at `e1b0250` (Lane U first pass)

After all three:
- full API and worker suites, all frontend tests, lint, typecheck and build
- the three browser suites (one server on 5173, from `main`)
- confirm the only migration change is `0037` and no Terraform changed
- regenerate the OpenAPI types if B changed the contract

Then commit the coordinator-owned docs:
- the tutor and AI spec text for TUTOR-REQ-002 to 011 and the AI diagnostics
- the two DESIGN.md exceptions
- the H12 window correction

When green, **post FG-3 to Fred** (apply `0037`). Do not push.

## 3. Lane I: identity convergence (H01a), pre-approved

Spec first: `AUTH-REQ-00x` in `docs/features/lti-auth/README.md`. Lane I owns that section today, and Lane P stays out of `lti-auth` until I merges. *One person in one institution has exactly one Kala user, whichever path first saw them (LTI launch or roster sync). Repeated launches and syncs never split or unenroll them.*

1. **Investigate (read-only):** which identifier Blackboard puts in the LTI 1.3 `sub` claim, which one roster sync uses (REST `id`, `uuid` or `userName`), and whether roster sync can read the identifier that matches the launch (REST user `uuid`, or the `user_id` from LTI Names and Roles). Prove it from the code and Anthology's documentation. Record the field mapping with no real values.
2. **Pre-approved fix:**
   - roster sync resolves users by the identifier that matches the launch
   - roster reconciliation never unenrolls a user who has launched into that course through LTI
   - email alone never merges two existing users
3. **Stop only if** neither matching identifier is available, the fix needs a migration, or it would change tenancy or role handling.
4. **Tests:**
   - student-first then instructor sync
   - instructor-first then student launch
   - a repeated sync
   - a returning launch
   - two different people with the same name
   - cross-institution isolation

   Each one must end with one user per person, enrolled, and no evidence moved or lost.
5. End with the AUDIT REPORT. Merging still goes through the coordinator's combined checks.

Owned: `services/api/app/db/supabase.py` (resolver only), `services/api/app/lti/routes.py` (roster sync only), `services/api/app/lms/blackboard.py` (roster reads only), their tests, and the auth spec section above.

## 4. Lane G: Diagnostic availability (H02), pre-approved

Spec first: `DIAG-REQ-009` to `011` in `docs/features/diagnostic/README.md`. Lane G owns those sections and Lane U keeps the rest.

**Policy:**
- A skill needs a baseline only when it is approved, the learner has **no evidence of any kind** for it, and at least one question can be served now.
- A skill the learner has already practiced or studied does not need a baseline.
- Skills with no course material are not counted as due.
- Candidates are filtered by availability **before** the 10-question sitting limit.
- If nothing can be served, the response says why: waiting for material, or questions still being prepared. It never claims question creation failed when it did not.
- Never write fake evidence to clear the notice.

The status endpoint returns `dueSkillCount` (actionable) and `waitingForMaterialCount`, both optional, so the current frontend keeps working.

**Stop only if** this needs a migration or changes grading or evidence semantics.

Tests: mixed no-material, ready, preparing and exhausted skills; more than 10 due; a skill already practiced; an empty course; the completed sitting; and the workspace count matching what the Diagnostic page can serve.

Owned: `services/api/app/routers/diagnostic.py` (status and selection only), `services/api/app/bank/serving.py` (the diagnostic pick only), tests, and the spec sections above.

## 5. Lane U: frontend fixes, pre-approved

The dev server runs on 5173 from Lane U's worktree. If the coordinator needs 5173 for the integration browser suites, U pauses its server and resumes after.

| Ref | Fix |
| --- | --- |
| H05 | Wire Diagnostic load-error Retry to the query refetch. Test pointer and keyboard |
| H06 | Roster, proposal and Twin pagers become real buttons or links that Tab can reach, with disabled semantics at the ends. Match the new ledger and keep 40px sizing |
| H07 | Skills and the legacy pickers distinguish a failed fetch (error with Retry) from a genuinely empty course |
| H08 | Twin "Practice this" opens the canonical skill hub on the Test browse tab for that skill. No automatic start |
| H09 | Root error and not-found send staff to `/class` and students to `/course`. With no session, show the H11 message |
| H10 | `/` becomes a short page: "Open Kala from your course in Blackboard." No password sign-in |
| H11 | Session-expired copy: "Your session ended. Go back to your Blackboard course and open Kala again." Remove the dead re-launch button |
| H12 copy | Label evidence windows exactly ("Last 20 events", "Last 25 events", "Based on recent activity") wherever a number could read as a lifetime total |
| Legacy | `/course/practice` without a skill redirects to `/course/skills`. Fix the error and empty copy in `/course/lessons` and in the course-wide deck in `/course/flashcards`. Fix the stale SessionBar comment in `routes/course/tutor.tsx` |
| H02 copy | The workspace badge uses `dueSkillCount` when present, plus a quiet "N topics are waiting for course material" line with no button. Hide the line when the field is absent |

Tests for each, then lint, typecheck, build and the browser suites. Screenshots at 375px and 1440px for H05, H07, H09, H10 and H11.

## 6. Final merge, then the gates

1. Merge order once each lane is green: integration set, then I, then G, then U fixes. Full checks after the last merge. Apply the lateness rule from section 0.
2. **STOP at FG-3** if `0037` is not yet applied. Post the runbook steps to Fred.
3. **STOP at FG-4.** Post the final SHA, the list of what is in this deploy and what was left out, and the exact deploy steps:
   - `make deploy`
   - check the alias moved and the worker updated
   - check CloudWatch for startup errors
   - `git push origin main`
   - wait for Vercel to show Ready
4. **STOP at FG-5.** Post this click-through checklist for Fred. He records the results in `docs/work/handover-2026/evidence/acceptance-2026-10-25.md`:
   - Launch as student and as instructor
   - Study: hint, Explain more, dock follow-up. Review-missed dock. Test dock
   - Diagnostic: the workspace badge matches what the page can serve. Load error Retry if reproducible
   - Tutor: new chat with the centered dock, file drop and send, rename, pin and unpin, delete with confirmation
   - Instructor: a learner who launched as a student today appears in the roster with their recent activity (after Lane I)
   - `/`, session expired, and not-found as each role
   - 375px and 1440px
   - CloudWatch: provider diagnostic lines show stage and status for any remaining failure

   If anything fails, the coordinator triages it from Fred's evidence. **FG-R** is available if the deploy itself is the problem.

## 7. Close-out (after FG-5)

The coordinator writes `docs/work/handover-2026/closeout.md`:
- what shipped: SHAs, alias version, Vercel deployment
- the acceptance results from FG-5
- every open item as a `planned` or `deferred` work item with owner "ITO", the reason and the branch

Open items include H01(b) data repair, Lane DB if FG-2 is still pending, full-history evidence paging, streaming, Sources and Inline Citation, image attachments, restored-file previews, the frontend test runner, the global Bedrock timeout policy, API Gateway access logs, and any lane left out under the lateness rule.

Then remove merged worktrees. Keep "Kala Audit" until Fred releases it. The code freeze begins, and only docs, runbooks and specs change until Nov 8.

## Confirmed ownership amendment — 2026-10-25

Fred assigns the coordinator sole edit ownership of docs/features/diagnostic/README.md for this round, matching Tutor/AI ownership. G submits DIAG-REQ-009–011 and U submits H05/H07/H02-copy spec changes. Coordinator commits each lane's text to main in its own small docs commit in separate sections; each lane rebases onto that commit before implementing the affected part. Lanes reference REQ IDs but never edit this file; incorrect specs require stopping and submitting a correction. Lane I remains sole auth-spec editor today; P stays out until I merges. Independent audits and integration continue.

## Confirmed identity reconciliation amendment — 2026-10-25

This supersedes section 3's unconditional protection of prior LTI launchers. Fred rejects additive roster sync: stale course enrollment controls access and retaining removed members would regress tenancy/privacy.

Ship the REST user `uuid` identity fix (matching LTI `sub`) while retaining enrollment reconciliation, including removals. Remove enrollments only after every roster page succeeds, with no error and a non-empty result. Partial, failed or empty fetches skip removals; warnings contain counts only. No migration or history repair is authorized.

Tests additionally prove UUID/launch convergence, removal of the legacy REST-id alias user's enrollment while the launch user remains enrolled, no removals after failed/partial fetches, and removal of a genuinely departed instructor after the next successful sync. Legacy duplicate users retain their history but lose enrollment after a successful sync; H01(b) remains planned. Alfred's older 40 events remain with the legacy user and will not appear in the roster until that repair. Proceed without another stop unless some roster users lack UUIDs.
