---
feature: lti-auth
req_prefix: AUTH
owner_role: product owner
status: active
code:
  web: apps/web/src/lib/auth/
  api: services/api/app/lti/
  worker: []
  db: [packages/db/migrations/0001_init.sql, packages/db/migrations/0002_rls.sql, packages/db/migrations/0015_lms_identity_aliases.sql, packages/db/migrations/0016_lms_course_resolution_cache.sql]
tests:
  - services/api/tests/test_lti_launch.py
  - services/api/tests/test_course_sync_cache.py
  - services/api/tests/test_uuid_path_params.py
  - services/api/tests/test_identity_convergence_lane_i.py
  - services/api/tests/identity_lane_i_postgrest.py
---

# LTI authentication and course entry

## Purpose
Kala uses an LMS launch to establish the learner's institution, identity, course and role. It does not provide a separate password registration flow or host courses. Blackboard is the implemented connector; wording mentioning another LMS is not implementation evidence.

## Actors and permissions

| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| student | Launch into the student workspace and use their signed session | Select a trusted institution or role from browser input |
| instructor | Launch into the class workspace; reconcile the course roster | Treat an arbitrary client role as authorization |
| admin | Receive an admin session from validated platform claims | Bypass platform signature validation |
| LMS platform | Supply signed LTI claims for the configured issuer/client | Use an unconfigured deployment when the allow-list is populated |

## Requirements

### AUTH-REQ-001: Validate the platform launch before establishing a session
- Rule: GET or POST login starts OIDC with state and nonce in a signed, HttpOnly, Secure, SameSite=None cookie lasting 600 seconds. Launch checks state signature/expiry/equality, RS256 platform signature, configured issuer/audience, required exp/iat/nonce, nonce equality, ResourceLinkRequest message type and configured deployment allow-list.
- Acceptance: invalid state returns 400; token verification failure 401; mismatched nonce/message 400; unknown allow-listed deployment 403; successful launch redirects 302. LTI version/replay limitations are recorded below.
- Status: implemented
- Verified by: static `app/lti/security.py::verify_id_token`, `sign_state`, `verify_state`; `app/lti/routes.py::launch`. Launch tests mock token verification; they do not independently exercise real JWKS cryptography or all rejection branches.

### AUTH-REQ-002: Resolve tenant and stable identity from verified LMS claims
- Rule: institution resolves from issuer plus deployment ID; admin precedes instructor, which precedes learner, with student as the default. Resolve identity by institution-scoped exact alias or LMS identifier; record aliases on every successful resolution. Blackboard roster UUID matches the validated launch subject (AUTH-REQ-006). Email may be absent and is profile data, never sufficient identity evidence.
- Acceptance: a rostered account launching with its matching LTI sub retains the same Kala user and evidence; distinct identifiers remain distinct even when email matches. Course enrollment is upserted from validated role.
- Status: implemented
- Verified by: `test_lti_launch.py::test_launch_resolves_to_the_rostered_account_by_exact_subject`, `test_launch_records_the_alias_on_every_resolution`, `test_launch_without_email_still_creates_a_user`, `test_launch_with_no_matching_email_creates_a_user`; static `claims.py::map_role` and `db/supabase.py::resolve_user`.

### AUTH-REQ-003: Reuse course resolution and reconcile roster conservatively
- Rule: map context label to Blackboard course reference once, then use the local external-ID cache. Staff launch roster reconciliation has a 600-second success-only cooldown. Students do not trigger roster pulls; failed/empty pulls do not delete enrollments. Only complete, error-free, nonempty pulls with every member resolved remove stale enrollments, including instructors, without deleting user/evidence rows. Any page, identity-resolution or enrollment-write failure skips removals with counts-only warnings (AUTH-REQ-006).
- Acceptance: the second launch avoids course-resolution REST; staff relaunch inside cooldown skips roster work; failures permit retries; stale enrollments disappear only after a complete, error-free, nonempty pull.
- Status: implemented
- Verified by: `test_lti_launch.py::test_second_launch_for_the_same_course_never_calls_resolve_course_ref`, `test_instructor_relaunch_inside_the_cooldown_skips_roster_and_content`, `test_instructor_launch_reconciles_stale_enrollments`, `test_empty_roster_pull_skips_reconciliation`, `test_roster_pull_failure_skips_reconciliation`; `test_course_sync_cache.py`.

### AUTH-REQ-004: Hand off one signed session to the SPA
- Rule: mint an HS256 JWT with sub, institution_id, app_role, authenticated role/audience, iat/exp/jti and optional course/display name. Configured TTL defaults to 3600 seconds. Redirect in a fragment; capture in sessionStorage and scrub the fragment. Backend bearer validation owns authorization. Browser decoding is only display/routing state.
- Acceptance: student navigation enters `/course`; staff enter `/class`; missing or expired API bearer returns 401. No refresh route is implemented; expiry requires a fresh LMS launch.
- Status: implemented
- Verified by: static `security/jwt.py`, `deps.py::get_current_user`, `apps/web/src/lib/auth/session.ts`, `routes/launch.tsx`. Dedicated browser expiry/signature tests are absent; mocked launch success is covered in `test_lti_launch.py`.

### AUTH-REQ-005: Keep proposal generation off the launch model path
- Rule: skill seeding on staff launch is disabled by default. When enabled and outside the skill cooldown, wake the worker; do not run the proposer inline. Failures do not reject a valid launch.
- Acceptance: default launch makes no proposer/model call; enabled launch queues work; students do not seed.
- Status: implemented
- Verified by: `test_lti_launch.py::test_instructor_launch_queues_skill_proposal_when_enabled`, `test_instructor_launch_default_off_makes_no_proposer_or_model_calls`, `test_skill_seed_failure_does_not_block_the_launch`.

### AUTH-REQ-006: Converge Blackboard roster and launch identities with guarded reconciliation
- Rule: Blackboard roster reads use REST user `uuid`, which matches validated LTI launch `sub` (and NRPS `user_id`), rather than membership `userId`, REST user `id` or `userName`. Within an institution, launch-first, roster-first, repeated sync and returning launch resolve one user per person. Exact aliases and identifiers own resolution; email or name alone never joins established users. Existing conflicting aliases are not reassigned. This is the automatic resolver rule. A separately reviewed, maintainer-run WI-24 repair may plan an exact, proved legacy-to-canonical alias reassignment; it never changes this resolver or merges by email/name. The local-only repair design retains the legacy user UUID as an unenrolled shell, reserves `wi24-retired:<legacy-users.id>` as its retired LMS marker after collision checks, and preserves the original identifier and mapping in private backup and an in-database merge audit. This manual data-repair exception is implemented and locally proved by the reviewed repair script/runbook, but remains unreleased until Fred FG-7a/FG-7b; no hosted repair has run. Consent/DSR ambiguity on either anchor refuses a non-converged pair without changing governance records or policies.
- Reconciliation: retain removals, including a genuinely removed instructor, only after every roster page was fetched successfully and the nonempty roster was fully resolved and enrolled. A partial, malformed, empty or failed pull, or any per-member failure, removes nobody. Warnings contain counts only, never identifiers, URLs, names, email addresses or exception payloads. A missing roster UUID stops the sync without substituting REST ID, username or email.
- Historical data: a pre-fix REST-ID user and its history remain intact; a complete successful sync enrolls the UUID/launch user and removes the legacy user's stale enrollment. No evidence is moved or histories merged. H01(b) repair is locally prepared for ITO and awaits the human gates; the known legacy 40-event history remains on its old user and is absent from the canonical roster view until that repair.
- Acceptance: student-first then instructor sync; instructor-first then student launch; repeated sync; returning launch; different people sharing names/email; cross-institution isolation; UUID/sub equality; legacy REST-ID enrollment removal with unchanged history; failed/partial/malformed/empty pulls removing nobody; member-write failure removing nobody; genuinely removed instructor losing enrollment after a complete successful sync; missing UUID stopping sync.
- Status: done-awaiting-confirmation; implementation and local checks complete under APPROVAL-06 rev 2, Lane I and Fred's confirmed reconciliation amendment (2026-10-25). Live Blackboard acceptance remains FG-5.
- Verified by: dedicated `services/api/tests/test_identity_convergence_lane_i.py` (31 scenarios), updated launch regressions, and the disposable real Postgres/PostgREST check `services/api/tests/identity_lane_i_postgrest.py`; identity evidence below. Real Blackboard acceptance remains a Fred gate.

### AUTH-REQ-007: Require existing course enrollment on student reads
- Rule: For a validated student, the inventoried course-scoped GET handlers require the existing bank course/enrollment guard for the requested or resource-resolved course. Missing enrollment, unavailable course and another institution return the same 404 before content, learning-state retrieval or existing GET side effects. Identity and institution come from the validated token; UUID shape or a session course claim is insufficient. Enrolled responses, existing processing and staff branches remain unchanged. Reuse the existing guard without extending its semantics or introducing another gate.
- Scope: Course metadata/memory; Twin/next-up/assigned plan; content/modules/Diagnostic status and question retrieval; Study cards/deck; Test next-item/set list/set detail/results; Lesson retrieval; Tutor conversation list/detail; and reward summary. The five existing GETs that can also write or wake work (Diagnostic questions, Study deck, Test next-item, Test set detail and Lesson retrieval) gain admission before that processing; their allowed processing is unchanged. Bank status already has this guard. The new full-history endpoint retains its own stronger student-role/institution/enrollment checks.
- Resource resolution: Tutor detail retains its existing owned-conversation lookup before checking that conversation's course, then reads messages/attachments. Do not change the shared ownership helper or its mutation callers. A function-local module import in Diagnostic may avoid the existing Bank/Diagnostic import cycle; only the guard branch and necessary imports are permitted.
- Acceptance: Each fixed GET covers enrolled success, non-enrolled 404 and foreign-institution 404. Denied requests perform no protected processing, generation, scheduling, exposure writes or worker calls. Staff behavior, response fields and enrolled learning behavior remain unchanged. Strict AST comparison permits only the exact student admission branches and necessary imports. Mutation methods are outside this amendment.
- Status: done-awaiting-confirmation; local integration complete, hosted deployment and live acceptance pending.
- Verified by: `services/api/tests/test_wi26_student_read_admission.py` (116 route/import cases) and `services/api/tests/wi26_student_scope_local.py` (exact student-branch/import AST proof). The merged API suite passes 1,014 tests; no deployed acceptance claimed.

## API contract

| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |
| GET /lti/login; POST /lti/login | Begin OIDC, query/form login hints | Public initiation | 302 to configured platform; creates signed cookie |
| POST /lti/launch | Validate form id_token/state and establish session | Platform signature + signed state | 302; validation statuses above; course resolution failure 502 |
| GET /lti/jwks | Tool public signing keyset | Public | Public RSA key only |
| GET /courses/{course_id} | Course metadata | Session; student enrollment via AUTH-REQ-007, existing staff gate | 404 for unavailable/outside-institution course or non-enrolled student |

Course metadata lives in `routers/courses.py`; backend UUID path dependencies return 404 for malformed IDs. Session authorization is reused by the other feature contracts.

## Data
Service-role launch writes institutions, users, user_profiles, lms_identity_aliases, courses and enrollments; course cache/sync stamps are persisted. These privileged writes depend on validated platform claims. Profiles and aliases do not all have their own institution_id column: ownership is inherited through the user relation (schema exception below). Browser RLS is defined in 0002 and 0015: self/course staff/institution admin boundaries apply to identities/enrollments; courses/skills have institution-level reads. RLS cannot substitute for API authorization because `db/supabase.py` uses the service role. This spec does not assert that an lti_launches audit row is written by the route.

## AI usage (if any)
No model call is required for authentication. Staff proposal wake-up delegates to the skills worker; roster/course lookup uses Blackboard REST. Names/email are retained in protected profiles, not passed to a model by the auth handler. Broad sanitization coverage remains partial elsewhere.

## Edge cases and known limits
- Unknown roles default to student; roster mapping treats explicit Student as student and other roles as instructor. These mappings differ deliberately in source and need real Blackboard role acceptance.
- Context label, rather than context ID, resolves the course. A launch without a label can yield a session without a course.
- Reconciliation does not run after any member resolution/enrollment failure. Writes before a failure may have enrolled successfully resolved members; no enrollment is removed. Roster fetching completes before any member is resolved.
- Signed state is stateless and not consumed server-side. Expiry/nonce checks are present; single-use replay storage is not.
- Frontend session parsing does not verify JWT signature or exp; API validation rejects invalid/expired sessions. No revocation list or refresh mechanism is implemented.
- Staff launch still awaits roster REST calls. Best-effort failure handling is not a whole-request deadline (WI-16).

## Contradictions requiring planner resolution

| Locations at source revision | Finding | Proposed resolution (not implemented here) |
| --- | --- | --- |
| `services/api/app/lti/claims.py:16` (EXPECTED_VERSION); `services/api/app/lti/routes.py:230` (message checks) | Expected LTI version exists as a constant, but launch does not enforce version equality. | Decide whether to enforce 1.3.0 and add rejection tests before claiming full LTI claim validation. |
| `AGENTS.md:33` (every persisted row carries institution_id); `packages/db/migrations/0001_init.sql:90` (user_profiles definition); `services/api/app/db/supabase.py:178` (profile write) | Profiles derive tenancy through user_id instead of a row-local institution column. | Document the deliberate relational exception centrally or plan a forward migration; do not rewrite applied SQL. |
| `apps/web/src/routes/launch.tsx:373` (error copy: Blackboard or Canvas); `services/api/app/lti/routes.py:240` (fixed blackboard connector type) | UI names Canvas despite only Blackboard implementation. | Narrow copy through an authorized UI task or implement/test a second connector separately. |

## Evidence and verification limits

WI-08 / APPROVAL-05 rev 2, Lane P. Source reviewed at `4f3ec29d3f827a1db92e90c4f395947d37744479` on 2026-10-25. `implemented` means present in that source, with the evidence stated per requirement; it is not a claim of deployed acceptance. `partial` identifies an explicit gap. Planned behavior is not inferred from archived plans.

- Local: `cd services/api && uv run pytest -q` — **431 passed**, 30 dependency deprecation warnings, 28.45s.
- Local: `cd services/worker && uv run pytest -q` — **117 passed**, 0.68s.
- Both processes used committed `services/conftest.py`: dotenv disabled, inherited application settings replaced, IPv4/IPv6/DNS blocked. Tests use mocked boundaries; no hosted data or provider calls.
- No browser acceptance, live LTI/Blackboard check, RLS replay, deployment, migration, lint/typecheck/build claim is made by this documentation-only lane. UI evidence is static source review unless stated otherwise.

## Identity investigation and lineage

Lane I preserves Lane P's AUTH-REQ-001–005 baseline from commit `2062784`, with only the explicitly approved identity/reconciliation amendments to AUTH-REQ-002/003 above. AUTH-REQ-006 is the next unused ID. Implementation base: integrated main `5afe69518bf51c728a76753527f1682d64041d71`. Requirements/work lineage: APPROVAL-06 rev 2 H01(a), H01(b), handover WI-08; Fred's confirmed UUID/reconciliation policy on 2026-10-25 supersedes additive-retention proposals.

[Anthology's user-ID documentation](https://docs.blackboard.com/docs/blackboard/lti/1.3/lti-subsystems/ags/ags-grades) identifies REST user `uuid`, launch `sub` and NRPS `user_id` as the matching identity. Current source before this change projects membership `userId` and expanded REST `user.id`, omitting `user.uuid`; `resolve_user` discovers aliases by email; roster reconciliation deletes absent students even when a member failed. These are source findings, not new hosted observations. No real identifier values were collected or reported. The unused `lti_launches` table and diagnostic alias sources are not used as launch provenance.

## Identity verification — 2026-10-25

Implementation: `cbc9a0676f805d1b562535bce7351fd3a5ccef5e`, branch `codex/identity-convergence`, worktree `.`, integrated base `5afe69518bf51c728a76753527f1682d64041d71`. Spec-first commit: `a618de3`. REQ/WI lineage: AUTH-REQ-002/003/006, handover WI-08, APPROVAL-06 H01(a)/(b). This identity entry supplements Lane P's retained evidence above; it does not replace or upgrade that earlier verification.

| Check | Result / scope |
| --- | --- |
| Focused API tests | `cd services/api && uv run pytest -q tests/test_identity_convergence_lane_i.py tests/test_lti_launch.py tests/test_blackboard_content.py tests/test_course_sync_cache.py`: **103 passed**, 26 dependency deprecation warnings. The dedicated file contributes 31 scenarios. |
| Full API suite | `cd services/api && uv run pytest -q`: **579 passed**, 30 dependency deprecation warnings, 27.94s, on implementation `cbc9a06`. |
| Worker suite | `cd services/worker && uv run pytest -q`: **117 passed**, 0.62s. No worker source changes. |
| New-test lint | `cd services/api && uv run ruff check tests/test_identity_convergence_lane_i.py tests/identity_lane_i_postgrest.py`: passed. |
| Existing-file lint comparison | Whole-file Ruff retains **17 findings**, matching integrated base `5afe695` by diagnostic code/message; **zero new findings**. Whole-file Ruff is not globally green. Unrelated findings remain outside this lane's scope. |
| Real persistence check | `cd services/api && PYTHONPATH=. uv run python tests/identity_lane_i_postgrest.py`: passed against disposable local Supabase Postgres **17.6** and PostgREST **14.15**. Exercises the real resolver/select/upsert/delete queries, both identity orders, repeated sync/returning resolution, shared name/email, tenant isolation, failed/empty/member-failed preservation, legacy and departed-instructor enrollment removal, and unchanged evidence. Both test containers are removed on exit. |
| Scope and whitespace | `git diff --check`: passed. AST source comparison against `5afe695` confirms only `resolve_user`, `_sync_roster` and `get_roster` changed in the three owned runtime files, plus roster-specific URL imports. Launch handling, tenancy/role mapping, other functions and all migration files are unchanged. |

The offline tests cover UUID expansion and a fully paginated success, omitted/null/empty terminal paging forms, failed first/later pages, partial HTTP status, malformed/missing results or paging, repeated continuation, foreign continuation origin, absent/empty UUID, member resolution/enrollment failure, removal failure and counts-only warnings with no traceback/identifier/exception-body leakage. The existing mocked launch identity fixture now uses exact identifiers rather than simulating the superseded email-discovery policy.

The initial focused run had one failing **synthetic fixture**: the same user/course key was incorrectly reused across institutions, causing the fixture's upsert to overwrite its first enrollment. Separate institution-owned users corrected the fixture; the final 103-test run passes. Initial standalone local schema setup omitted the referenced skills table; the committed disposable harness creates all fixture dependencies in order and passes. No migration or application behavior was changed to accommodate either fixture correction.

Limits: the local persistence fixture uses committed identity/evidence table definitions in an isolated schema; it is **not** a full migration, RLS, deployment or real Blackboard acceptance test. Offline pytest processes use committed dotenv/network isolation. The local persistence harness bypasses application credentials and binds only to hard-coded loopback port 55436. Frontend lint/typecheck/build/browser checks were not rerun because this lane changes no frontend source or OpenAPI schema; coordinator owns combined integration checks. No hosted access/write, identity repair, schema migration, deployment, push or message to another chat was performed. H01(b) remains planned with ITO; legacy history, including the previously reported 40-event history, is not merged or made visible under the canonical learner by this code fix.

## APPROVAL-07 local verification boundary

At integrated source `8e51040f1dda4235f9b12ad344da4cd81442e1e9`, reviewed staff guards, H history/error states, M repair tooling and student-read admission are locally integrated. Full API: 1,014; worker: 117; frontend/tour unit: 33; Study component: four. Web lint/typecheck/build and configuration inventory pass. Final integrated synthetic browser verification passes 1,474 assertions; real LTI acceptance is not inferred. Earlier revision-specific evidence retains its recorded attribution. Hosted 0038/0039 application, release, real-pair repair or safe refusal, and live acceptance are separate human gates; this record upgrades no live result.

## Change log

| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-25 | Record merged local verification and supersede stale implementation-pending findings; retain hosted gates and bounded summary/statistics limits | APPROVAL-07 coordinator integration; no new behavior | AUTH-REQ-006/007 |
| 2026-10-25 | Require existing enrollment admission on inventoried student GETs; preserve staff, mutations and enrolled processing | APPROVAL-07 Amendment 7; coordinator spec before follow-up implementation | AUTH-REQ-007; WI-26 |
| 2026-10-25 | Write full source-backed feature spec; identify limits and contradictions | APPROVAL-05 rev 2 Lane P; handover WI-08 | AUTH-REQ-001 through AUTH-REQ-005 |
| 2026-10-25 | Specify UUID/subject convergence, exact identity resolution and complete-pull-only enrollment removal, including instructors; preserve legacy evidence without repair | APPROVAL-06 rev 2 Lane I; Fred confirmed reconciliation amendment; P baseline lineage `2062784` | AUTH-REQ-002, AUTH-REQ-003, AUTH-REQ-006 |
| 2026-10-25 | Record implementation, dedicated regression and disposable local persistence evidence; retain live acceptance and legacy repair limits | APPROVAL-06 rev 2 Lane I; implementation `cbc9a06` | AUTH-REQ-002, AUTH-REQ-003, AUTH-REQ-006 |

| 2026-10-25 | Distinguish automatic exact-alias conflict protection from planned operator-reviewed historical repair; retain legacy UUID/provenance with a checked retired LMS marker | APPROVAL-07 WI-24; coordinator local-design review before script implementation; Fred repair gates remain | AUTH-REQ-006, WI-24 |
