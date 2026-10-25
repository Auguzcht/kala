# Security and privacy boundary

These rules apply to every feature. [AGENTS.md](../../AGENTS.md) is the agent entry point; feature specs identify incomplete enforcement. This page consolidates current requirements and limits without changing behavior.

## Identity, tenancy and authorization

Blackboard LTI 1.3 is the login boundary. Resolve institution from validated issuer and deployment, and user/role from validated launch/session data. Never trust client-supplied tenant or role. Every persisted learning row carries institution identity; tenant RLS is required. User ownership and course enrollment checks remain necessary inside a tenant. A service-role success does not establish RLS or course-level authorization.

[AUTH-REQ-005–008](../features/lti-auth/README.md) describe launch, enrollment and roster identity/reconciliation. Successful complete non-empty roster fetches reconcile removals; failed/partial fetches remove nobody. Legacy REST-id duplicate users retain their history without enrollment after successful reconciliation; history repair is planned, not an automatic merge.

[Instructor insights](../features/instructor-insights/README.md) records partial course guards and the direct recommendation status-policy gap. [Skills](../features/skills/README.md) records incomplete course authorization on review routes. Do not treat validated staff role, UI filtering or the UUID fix as full course isolation. Gradebook staff/course guards are scoped in [INGEST-REQ-001](../features/lms-ingest/README.md#ingest-req-001-lms-gradebook-read-and-write-routes-are-restricted-to-staff-who-teach-the-course). These known gaps require scoped follow-up and do not authorize bypasses.

## Model and logging boundary

De-identify model-bound copies before provider calls, while preserving authorized learning records. The existing sanitizer handles emails and explicit `name:` / `姓名:` patterns only. Arbitrary names and other personal information can remain. It is partial protection, never comprehensive anonymization. [AI-REQ-001 and AI-REQ-002](../features/ai-platform/README.md) define Tutor sanitization and metadata-only diagnostics; their scope does not prove every non-Tutor caller is safe.

Log status, stage, counts and opaque request identifiers as authorized. Never log credentials, tokens, prompts, request/response bodies or student identity. Keep roster names in authorized instructor views; model payloads use pseudonyms/numeric allowlists where implemented. Do not export real student data to reproduce bugs. [Incident response](runbooks/incident-response.md) provides bounded metadata-only queries.

## Credentials and operational authority

[secrets.md](secrets.md) is the names/stores/owners catalogue. Never print, paste, log or commit values or read environment files into chat. Only public `VITE_*` configuration reaches the browser. Test-only settings and generated JWT material in `services/conftest.py` must never run an application or deployment.

Agents do not deploy, apply hosted migrations, rotate keys or write hosted learning data. A named human reviews and executes the current runbook. A narrow explicit user delegation applies only to its named operation. Use [environments](environments.md), [database policy](database.md) and [backend release procedure](runbooks/deploy-backend.md). Confirm institutional retention, incident contacts and privacy governance before cutover; these are open handover decisions, not completed controls.

## Verification limits

Mocked suites, synthetic browser tests and health checks do not prove live LTI, tenant isolation, provider recovery or persistence. Record the actual environment, revision, human verifier and result separately. [First-launch smoke](runbooks/first-launch-smoke.md) requires real role-based acceptance using approved synthetic accounts.

## Change log

- 2026-10-25 — DOCS-HYGIENE: consolidate existing golden rules and disclosed gaps into the truth layer; no new security implementation or acceptance claim.
