> Archived: 2026-10-24 (Asia/Manila), under APPROVAL-01. Historical source: `docs/DEEPSEEK_SEPT1_CLOSEOUT.md` at base `e9de105` / ignored main-only input.
> Replacement: [docs/work/handover-2026/evidence/migration-map.md](<../../work/handover-2026/evidence/migration-map.md>). This original is evidence, not current policy; old commands and next-step queues are not authorization to execute them. Source line references below and in audits refer to the original, before this header.

# Sept 1 closeout: verified gaps and ordered task briefs

Written Aug 30. Two days to the demo. Every claim below was checked against the
tree, not against a progress log. Ordering is by "what breaks the demo if it is
missing," not by phase number.

Verification state at time of writing: `uv run pytest` in `services/api` is
127 passed **only when `SUPABASE_JWT_SECRET` is set in the environment**.
Without it, 6 LTI launch tests fail with `InvalidKeyError: HMAC key must not be
empty`. CI does not set it, and CI runs pytest with `continue-on-error: true`,
so CI has been reporting green regardless. Fix that first (Task 0).

---

## Reality check against the assumption "terraform and docker aren't set up"

They are written. They have never been applied or built.

| Thing | State |
|---|---|
| `infra/terraform/*.tf` | 11 files, ~380 lines. ECR (2 repos), Lambda x2 (container image), API Gateway HTTP API with Mangum proxy route, EventBridge Scheduler, Secrets Manager, IAM least-privilege, CloudWatch log groups, error alarm, optional budget. Written, never applied. |
| `services/api/Dockerfile` | Lambda python:3.12 base, `CMD ["app.main.handler"]`, matches the Mangum handler in `main.py`. Never built. |
| `services/worker/Dockerfile` | Same shape. Never built. |
| ECR push pipeline | **Missing.** `api-ci.yml` and `worker-ci.yml` lint and import-check only. No `docker build`, no ECR login, no push. |
| Terraform remote state | **Missing.** Local state only. Acceptable for a two-day demo, but back up `terraform.tfstate` off-machine. |
| `services/worker/app/handler.py` | **A stub.** Returns `{"ok": True, "processed": 0}` and three comments. This is the single largest gap between the architecture diagram and the running system. |

Two ordering traps in the terraform as written:

1. `lambda.tf` needs `var.api_image_uri` to point at an image that already
   exists, but `ecr.tf` creates the repo in the same apply. A single
   `terraform apply` fails. Use the two-phase apply in Task 2.
2. `secrets.tf` creates an empty secret. The Lambda reads `KALA_SECRETS_ARN`
   at cold start. Populate the secret value before the first invoke or every
   request 500s.

---

## Status against the 10 training-plan phases

| Phase | Verified state |
|---|---|
| 1. Onboarding, requirements | Done |
| 2. Foundation, env setup (Phase 0) | Done. Monorepo, Supabase + pgvector, CI to Vercel, Blackboard AMI up |
| 3. Auth spine, LTI 1.3 (Phase 1) | Done. Launch, JWKS, nonce/state, tenant resolve, session mint, RLS, NRPS roster |
| 4. LMS ingest and skill tagging (Phase 2) | Done in the backend. **No UI trigger anywhere.** `POST /courses/{id}/ingest` is curl-only, while four empty states in the app tell the user to "run the ingest pass" |
| 5. Learn loop (Phase 3) | Done and then some. SRS, guided lessons, derived XP, parallelized generation |
| 6. Twin and instructor insight (Phase 4) | Done. Heatmap, at-risk, drill-down, bento twin |
| 7. MLOps: worker, IaC, observability | **Partial and the weakest area.** IaC written but unapplied, images unbuilt, no deploy pipeline, worker is a stub |
| 8. Security, privacy, compliance | Mostly done. RLS + `verify_rls.py`, `deidentify.py` before model calls, research views with k-anonymity and consent gates. Missing: the de-identified cue appears on exactly one screen, and there is no audit-log surface |
| 9. MVP integration, rehearsal, Cintana submission | Not started. No backup demo video, no rehearsal script |
| 10. Post-demo: pilot, evaluation, handover | AGS passback is wired for the diagnostic only (`diagnostic.py:229` calls `connector.post_grade`). Researcher SQL views exist (`0003_research.sql`), no router, no portal. No SUS instrument |

---

## Task 0. CI honesty and test env (10 minutes, no DeepSeek needed)

Do this by hand before anything else. Two edits to `.github/workflows/api-ci.yml`:

```yaml
      - name: Tests
        env:
          SUPABASE_JWT_SECRET: ci-test-secret
        run: uv run pytest
```

Delete the `continue-on-error: true` line and the stale comment claiming
`services/api` has no test suite. There are 127 tests. A green check that
cannot go red is worse than no check, and a judge or adviser who looks at the
repo will see the comment.

Add the same env var to `services/api/.env.example` with a note that the tests
need it set.

---

## Task 1. Verify the model provider path (30 minutes, do this before any deploy)

This is the highest-risk external dependency left and it is not code.

`config.py` has an `AI_PROVIDER` switch: `bedrock` or `openrouter`, with an
independent `EMBED_PROVIDER`. The OpenRouter defaults are free-tier models
(`nvidia/nemotron-3.5-lightning:free`, `minimax/minimax-m3:free`). Free-tier
models rate-limit and get retired without notice. Running the Sept 1 demo on
them is a live coin flip.

Do all three tonight:

1. On the personal AWS account, open the Bedrock console in
   `ap-southeast-1` and request model access. Confirm the exact model IDs
   available there and write them into
   `BEDROCK_MODEL_FAST/DEFAULT/REASONING/PREMIUM/EMBED`. Not every Claude model
   is offered in every region. If the ones you want are not in Singapore,
   switch `region` in `terraform.tfvars` and `AWS_REGION` to a region that has
   them before applying, since changing region after apply means a full
   teardown.
2. Put $5 of credit on the OpenRouter account and switch the model IDs off the
   `:free` suffixes. This is demo insurance and costs less than a coffee.
3. Run one real generation through each path and record which one you are
   demoing on. The pitch says Bedrock. If you demo on OpenRouter, say so in the
   architecture slide as "provider-swappable model router, Bedrock in the
   school org account, external provider in the personal dev account." That is
   a stronger engineering story than pretending, and the abstraction is real.

---

## Task 2. Deploy the backend to the personal account (60 to 90 minutes)

Do this by hand, not with DeepSeek. Terraform errors are faster to read than to
prompt around.

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# edit: region, env=demo, frontend_url=<your vercel url>, budget_alert_email=<your email>
# leave assume_role_arn empty (personal account), leave the image URIs as-is for now

terraform init

# Phase A: create only the things that do not depend on an image existing.
terraform apply \
  -target=aws_ecr_repository.api \
  -target=aws_ecr_repository.worker \
  -target=aws_secretsmanager_secret.app

# Populate the secret BEFORE the first Lambda invoke.
# secrets.json holds the same keys services/api/.env.example lists.
aws secretsmanager put-secret-value \
  --secret-id kala/app \
  --secret-string file://secrets.json

# Build and push both images (linux/amd64 matters if you are on Apple silicon).
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=$(terraform output -raw region 2>/dev/null || echo ap-southeast-1)
aws ecr get-login-password --region $REGION \
  | docker login --username AWS --password-stdin $ACCOUNT.dkr.ecr.$REGION.amazonaws.com

docker build --platform linux/amd64 -t kala-api ../../services/api
docker tag kala-api $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/kala-api:latest
docker push $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/kala-api:latest

docker build --platform linux/amd64 -t kala-worker ../../services/worker
docker tag kala-worker $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/kala-worker:latest
docker push $ACCOUNT.dkr.ecr.$REGION.amazonaws.com/kala-worker:latest

# Phase B: now the image URIs resolve.
terraform apply
terraform output api_base_url
```

Then, and this is the part that is easy to forget: the LTI tool registration in
Blackboard points at the old backend URL. Update the redirect URI to
`<api_base_url>/lti/launch` and the JWKS URL to match, then re-test a launch
end to end. **Do not change the API Gateway URL again after this point.** Every
re-apply that recreates the API changes the URL and silently breaks the LTI
registration, which is the worst possible thing to discover on stage.

Save `terraform.tfstate` somewhere off the laptop.

Cost note: the Blackboard Learn AMI on EC2 is billing continuously. Check the
instance type and confirm the budget alarm email is set, because a personal
card plus a large instance plus two days is a real number.

---

## Task 3. Make the worker real (DeepSeek, ~90 minutes)

This is the biggest credibility gap. The architecture diagram in the masterplan
shows EventBridge driving a worker that recomputes the twin and re-embeds
content. The handler currently returns a hardcoded zero. If anyone opens
`services/worker/app/handler.py` during judging, the MLOps story collapses.

It does not need to be sophisticated. It needs to be real, idempotent, and
visible in CloudWatch.

### DeepSeek brief

> Context: this is the Kala monorepo. `services/worker` is a Lambda container
> triggered by EventBridge Scheduler on a 15 minute cadence. It currently has a
> stub handler. `services/api/app` has the real implementations you should
> reuse rather than reinvent: `app/db/supabase.py` (PostgREST client with
> `select`, `insert`, `update`, `delete`), `app/twin/tracer.py` (mastery
> recompute from evidence), `app/ai/bedrock.py` (`embed`), `app/ai/chunking.py`,
> `app/ai/concurrency.py` (thread-pool fan-out helper), `app/config.py`
> (pydantic settings, reads secrets from Secrets Manager when
> `KALA_SECRETS_ARN` is set).
>
> Task: implement `services/worker/app/handler.py` as three idempotent jobs
> that run in sequence and return a real counts dict.
>
> 1. `recompute_twins()`: find every `(user_id, course_id, skill_id)` that has
>    an `evidence_events` row newer than the matching `mastery_state.updated_at`,
>    and re-run the tracer for those only. Never recompute the whole table.
>    Scope every query by `institution_id`.
> 2. `reembed_stale_content()`: find `content_items` whose `updated_at` is newer
>    than the newest embedding row that references them, re-chunk, re-embed, and
>    upsert. Cap the batch (start at 50 items) so a single invocation cannot run
>    past the 120 second Lambda timeout. Use the concurrency helper for the
>    embedding fan-out.
> 3. `sync_grades()`: leave a clearly marked no-op that returns 0 with a comment
>    naming the connector method it will call. Do not fake it.
>
> Requirements:
> - Every job wrapped so one failure does not abort the others. Log the
>   exception, count it, keep going. Return
>   `{"twins_recomputed": n, "items_reembedded": n, "grades_synced": 0, "errors": [...]}`
>   so the return value is readable in the CloudWatch log line.
> - Structured logging with `logging.getLogger(__name__)` at INFO for each job's
>   start, count, and duration. This is what makes the observability story
>   demonstrable.
> - Idempotent: running it twice in a row must produce the same state and a
>   second-run count of zero.
> - Do not import from `services/api` across the package boundary. Either vendor
>   the small pieces you need into `services/worker/app/` or, better, extract
>   the shared bits into `packages/` if the workspace already supports it.
>   Say which you did and why.
> - Add `services/worker/tests/test_handler.py` with fakes for the DB and embed
>   calls, covering: no stale rows produces zero counts; one stale row produces
>   one recompute; a raising job does not abort the other two.
>
> Do not change the API service. Do not change the Dockerfile CMD.

After it lands: `terraform apply` the new worker image, then invoke it once
manually and screenshot the CloudWatch log line. That screenshot is your MLOps
slide.

---

## Task 4. Student onboarding tour (DeepSeek, ~45 minutes)

Highest value per hour of anything on this list, because it doubles as the demo
script and it holds up when you are nervous.

`driver.js` is already a dependency and already implemented in
`InstructorShell.tsx` (line 59). `DESIGN.md` line 72 specifies the student path
and explicitly says the same script runs the conference walkthrough. It was
never built for the student side.

### DeepSeek brief

> Read `apps/web/src/components/shell/InstructorShell.tsx` and copy its
> Driver.js pattern exactly, including the `overlayColor: "rgba(14,27,51,0.35)"`
> and `showProgress: true` options, so the two tours feel identical.
>
> Add the equivalent tour to `apps/web/src/components/shell/CourseShell.tsx`
> for the student path, in this order, matching `DESIGN.md` line 72:
> Workspace (the "Next up" panel, explaining that the recommendation comes from
> the student's own evidence) → Diagnostic → Practice → Tutor → Twin.
>
> Requirements:
> - Fires once on first visit, persisted per user so it does not repeat. Use the
>   existing zustand store in `src/stores/` if one fits, not localStorage
>   directly, and follow whatever persistence pattern InstructorShell uses.
> - A "Take the tour" control so it can be replayed on demand. Put it in the
>   TopBar. This is the one you will actually press during the demo.
> - Respect `prefers-reduced-motion` (DESIGN.md line 73).
> - Copy rules from DESIGN.md: student-facing text uses plain topic language.
>   No "Bloom's taxonomy," no "RAG," no "server-side," no raw "your twin"
>   framing on the first step. Write it as direction, not description:
>   "Start here. One question per skill builds your baseline," not "This is the
>   diagnostic page."
> - Anchor steps to the side rail nav items, which are stable across pages.

---

## Task 5. Grounding chips and the de-identified cue (DeepSeek, ~40 minutes)

`DESIGN.md` names seven signature elements. Number 6 is grounding chips: "RAG
answers carry 'grounded in [content item]' chips, the not-a-black-box,
responsible-AI story." It is not implemented anywhere. The word "grounded"
appears only in code comments.

This is the responsible-AI slide made visible, and Cintana's judging criteria
reward exactly this. It is cheap.

### DeepSeek brief

> The tutor endpoint (`services/api/app/routers/tutor.py`, with retrieval in
> `app/ai/rag.py`) retrieves chunks to ground its answer. First check whether
> the response schema already returns the source chunk IDs or titles. If it does
> not, add them: return a `sources` array of
> `{ contentItemId, title, moduleRef }` on the tutor answer, then regenerate the
> frontend types with `pnpm --filter web gen:api` (the `pregen:api` hook
> regenerates the OpenAPI schema first, so this one command does the whole
> chain).
>
> Then, in `apps/web/src/features/tutor/components/TutorChat.tsx`, render the
> sources as small chips under each assistant answer. Follow DESIGN.md exactly:
> hairline border, low radius (2 to 4px), mono type for the label, ink or slate
> text. Not pills, not colored fills. The chip reads "Grounded in: <title>".
> If sources come back empty, render nothing rather than an empty container.
>
> Separately, add the quiet "de-identified before model call" cue to the tutor
> input area. Copy the exact treatment from
> `features/instructor/components/StudentDrillDown.tsx` line 52 so the cue is
> consistent across the product. Right now it appears on one screen out of
> eleven, which reads as an accident rather than a policy.
>
> Add a unit test on the backend that the tutor response includes sources when
> retrieval returned chunks.

---

## Task 6. Diagnostic migrated to the shared study shell (DeepSeek, ~30 minutes)

The shared `StudySessionShell` + `AnswerableCard` refactor was completed and
adopted by Practice, Flashcards, Lessons, and Tutor. Diagnostic is the one
holdout: `DiagnosticPanel.tsx` still uses raw `Card`/`CardContent` and its own
answer rows, and its header comment still calls it a "worked-example
component," which is scaffold language sitting in the first screen a new student
sees.

### DeepSeek brief

> Read `apps/web/src/components/study/StudySessionShell.tsx` and
> `AnswerableCard.tsx`, then read how
> `features/practice/components/PracticePanel.tsx` consumes them, since Practice
> was the reference migration.
>
> Migrate `features/diagnostic/components/DiagnosticPanel.tsx` to the same two
> components. Behavior that must not change: one question per skill, self-paced,
> server-side grading, the client never claims correctness, and the diagnostic
> is a fixed baseline instrument so questions must not regenerate (see
> `tests/test_diagnostic_idempotency.py`, which must still pass).
>
> While you are in there, disable the choice buttons during the in-flight
> request, not only after a result lands. Practice already had this exact
> double-submit window and it was fixed there; check how, and match it.
>
> Rewrite the stale file header comment. Delete the "worked-example component"
> framing.
>
> Verify with `pnpm --filter web typecheck && pnpm --filter web build` and the
> backend suite with `SUPABASE_JWT_SECRET=test uv run pytest`.

---

## Task 7. The admin surface, which is also your demo recovery tool (DeepSeek, ~60 minutes)

Currently there is no `/admin` route. `session.ts` has `role: "student" |
"instructor" | "admin"`, `map_role()` handles admin on the backend, and
`launch.tsx` routes admins to the class dashboard as a fallback. Masterplan 9.3
defines an admin journey that does not exist in the app.

Separately, `POST /courses/{id}/ingest` has no UI trigger, and four empty states
tell the user to "run the ingest pass" with no way to do it. If ingest needs
re-running during the demo, right now that is a terminal and a curl in front of
judges.

One screen fixes both.

### DeepSeek brief

> Add `apps/web/src/routes/admin.tsx` and `routes/admin/index.tsx`, guarded to
> `role === "admin"` using the same guard pattern as `routes/course.tsx` and
> `routes/class.tsx` (redirect to `/unauthorized` on role mismatch). Update
> `routes/launch.tsx` so admins land on `/admin` instead of the class dashboard.
>
> The page has three panels, in the instrument-panel style from DESIGN.md
> (hairline borders, low radius, mono figures, no new colors):
>
> 1. **Connector health.** Which LMS connector is active, whether the last
>    roster pull and content pull succeeded, and when. If the backend does not
>    already expose this, add a small `GET /courses/{id}/connector-status`
>    endpoint that reports last-sync timestamps from existing tables. Do not
>    invent new state to store.
> 2. **Ingest and coverage.** Counts of content items, chunks embedded, skills,
>    and how many skills are approved versus proposed, using the existing
>    `GET /courses/{id}/modules` and dashboard skill endpoints. Plus a "Run
>    ingest" button that calls `POST /courses/{id}/ingest`, shows a spinner
>    while running (the `Spinner` component exists in `components/ui/`), and
>    reports the resulting counts. Confirm before firing, since it is expensive
>    and hits the model provider.
> 3. **Adoption.** Per course: students launched, students with any evidence,
>    total evidence events, last activity. Aggregate only, no per-student rows
>    and no names. Admins are an institutional role, not a surveillance role,
>    and the research framing depends on that line holding.
>
> Do not add XP, badges, or streaks to this page. See the gamification note
> below.
>
> Reuse `InstructorShell` for the chrome rather than writing a third shell.

---

## Gamification, per persona

The current system is student-only and correctly built: XP, streaks, and badges
derived purely from `evidence_events` and `mastery_state`, no writable balance,
recomputed on read (`app/learn/xp.py`). Keep that exactly as it is.

For the other two personas, do not extend the same mechanic. Giving instructors
XP and badges for using an analytics tool is the thing that makes teachers
distrust ed-tech, and it is not defensible in the research write-up. Give each
persona the feedback loop that matches what they actually control:

- **Students** keep XP, streaks, and badges, because they control their own
  effort and spacing, and the reward is tied to evidence that moved mastery.
- **Instructors** get *cohort movement*, not points: "Class mastery moved +0.06
  on Applying this week," "3 students moved out of the needs-support list," "2
  skills still have no evidence." Their reward is seeing the class change, which
  is the thing the LMS structurally cannot show them. One tile on the class
  dashboard. Already computable from `mastery_state` deltas.
- **Admins** get *coverage and adoption*, not points: percent of courses
  ingested, percent of skills approved, percent of enrolled students who have
  launched at least once. Their job is rollout health.

That is one honest sentence per persona in the pitch and it costs one tile each.
It also gives you a real answer if a judge asks "why don't teachers get badges,"
which is a question worth being ready for.

---

## Frontend design gaps not covered above

Ordered by how visible they are in a demo:

1. **Mobile.** `CourseShell` renders a fixed 56px rail and `pl-14` at every
   breakpoint, with `max-w-7xl` content. There is no breakpoint treatment
   anywhere in the shell. DESIGN.md's quality floor says responsive to mobile,
   and the heatmap is called out as needing a small-screen strategy that also
   does not exist. If a judge opens Kala on a phone this is the first thing they
   see. Minimum fix: collapse the rail to a bottom bar under `sm`, and let the
   heatmap scroll horizontally with a sticky first column.
2. **Duplicate identity chip.** `CourseShell` renders the user's initials twice,
   once at the bottom of the rail (line 108) and once in the top bar (line 124).
   Remove the top bar one and make the rail chip a real popover with the user's
   name, role, course, and sign out. That popover was already deferred once.
3. **Home page grid.** Five quick links in a `lg:grid-cols-4` grid leaves an
   orphan on the second row. Either make it five columns at `lg`, or drop
   Diagnostic from quick links once the baseline is complete, which is better
   product behavior anyway, since a finished diagnostic is not a thing you
   return to.
4. **Home twin snapshot uses `flex-wrap` with a `min-w-72 flex-1` card**, which
   is the exact equal-stretch pattern that was already rejected and rebuilt on
   the Twin page. Same fix: a real grid.
5. **Signature element motion.** DESIGN.md line 61 specifies a pulse on the twin
   when an evidence event updates a node, and line 64 specifies rows sliding
   into the evidence ledger. Both were previously noted as unimplemented.
   Motion primitives exist in `components/motion/` and are barely used. These
   two are the "the instrument is live" moment in the demo and they are worth
   more than any new feature at this point.

---

## What to cut

You cannot do all of this in one night. Recommended cut, in order of what
survives:

**Do tonight, non-negotiable:** Task 0, Task 1, Task 2. Without a deployed
backend on a URL that the LMS points at, nothing else matters.

**Do tonight if the deploy goes cleanly:** Task 3 (worker) and Task 4 (student
tour). The worker closes the biggest gap between the story and the system. The
tour is your demo script.

**Tomorrow (Aug 31):** Task 5 (grounding chips), Task 6 (diagnostic), then the
mobile shell and the popover from the design list. Then record the backup demo
video, which the training plan lists as a Phase 9 deliverable and which does not
exist yet. Record it early enough that you can re-record once.

**Cut to post-demo:** Task 7 (admin surface), the researcher portal, the SUS
instrument, AGS passback beyond the diagnostic. These are all Phase 10 items in
the training plan, which is explicitly the post-demo phase. Do not spend
Sept 1 hours on them. Name them in the pitch as the pilot roadmap, which is
where they belong anyway.
