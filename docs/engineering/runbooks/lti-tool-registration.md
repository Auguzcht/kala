---
runbook: lti-tool-registration
applies_to: [dev-hosted, prod]
who_runs_it: Learn administrator with API / ITO maintainer
time_needed: "[Fred to confirm]"
last_verified: "unverified; source review at 4f3ec29 on 2026-10-25, Lane R"
status: in-progress
---

# Runbook 08 — register Kala on Learn

## When to use it

Connect the environment's Learn instance to the application from [04](anthology-developer-app.md) and API from [06](terraform-apply.md). Human administrators execute these steps. This WI-06 draft is source checked; exact console fields and a real two-role launch remain unverified.

## Before you start

- Complete [03](blackboard-learn-instance.md), 04, 06 and the public tool endpoints. Complete [09](vercel-web.md) before the end-to-end launch.
- Have Learn system-admin access, the LTI Application/client ID and separate REST application record, approved test course/users, and backend configuration custody from [secrets.md](../secrets.md).
- Obtain platform issuer, OIDC authorization URL, OAuth token URL and platform JWKS from the administrator. The source default issuer is Blackboard's issuer host, not the EC2 instance host; confirm the actual platform registration rather than guessing it.

## Steps

1. In Learn's system administration area, open **LTI Tool Providers** and register an LTI 1.3 tool using the Application/client ID. This path comes from [the README](../../../infra/blackboard/README.md); exact current menu labels and registration buttons: [Fred to confirm]. Check that Learn resolves the intended application and public API endpoints.
2. Review the tool record's client ID, issuer and endpoints against the portal record. Distinguish the **tool** JWKS at `/lti/jwks` from the **platform** JWKS that Kala uses to validate Learn signatures. Stop on any environment mismatch.
3. Save the registration and obtain its Deployment ID. Put it into the configured deployment allowlist through [05](secrets-manager.md). Source splits that setting on commas; configure explicit allowed deployment IDs. An empty list skips the allowlist check in current code and is not an accepted final configuration.
4. Have the administrator approve launch data release required for course context and intended role mapping. Exact Learn privacy controls for names/emails/roles and institutional privacy approval: [Fred to confirm]. Identity comes from the validated launch; never add client-side role or institution overrides.
5. Create a course tool placement / course link that launches the API's LTI target, then make it available in the synthetic test course. Exact placement type, target-link fields and new-window/iframe choice: [Fred to confirm]. Source validates `LtiResourceLinkRequest`; do not promise Deep Linking or AGS workflows merely because the console offers them.
6. In Learn's REST API integration administration, register/allow the separate REST application from 04 and its approved service/integration user. Exact menu, privilege set and course access: [Fred to confirm]. The backend connector exchanges REST key/secret using client credentials and reads courses, memberships and content. A successful LTI launch alone does not prove this access.
7. API maintainer verifies the effective backend settings by presence and environment match only. Include platform endpoints, LTI client/deployment, signing-key readiness and REST configuration as defined in the catalogue. The configured SPA origin must be correct in both Lambda/Terraform and the frontend build. Use 05/06/09 for changes; no secret payloads in evidence.
8. Launch freshly from Learn as each role and follow [10](first-launch-smoke.md). Source flow is `/lti/login` → platform authorization → form POST `/lti/launch` → SPA `/launch` with a session fragment. Never copy the fragment, launch JWT, state cookie, authorization header or full browser address to reports. The institution is resolved server-side from issuer plus deployment; the course and role must match the test enrollment.

## Verify it worked

Check public `/lti/jwks` returns an RSA public keyset without private fields. Do not POST a fabricated launch as a production acceptance test. A real student launch opens the correct course; an instructor launch shows the intended cohort. Record only time, environment, role, source/deployed revision and sanitized result. Check roster/content using synthetic data. Signed state, nonce, issuer/audience, expiry and deployment checks are visible in source/tests, not independently verified against Learn by this draft.

## Undo / roll back

The Learn administrator can hide/disable the newly created course placement while preserving its registration and evidence. If replacing a working registration, retain its approved configuration privately until the new one passes. Revert the coordinated portal/Learn/backend configuration as one reviewed operation. A new deployment ID can resolve a different institution row; do not edit tenant rows or copy data as a rollback shortcut. Exact restoration path: [Fred to confirm].

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `invalid state`, state/nonce mismatch | Stale launch, blocked cross-site cookie, origin mismatch | Relaunch from Learn over HTTPS; inspect cookie policy locally without copying cookies. Source uses a Secure, HttpOnly, SameSite=None state cookie with 600s lifetime. |
| Invalid launch signature / audience / issuer | Wrong platform JWKS, issuer or LTI client | Compare administrator-provided registration privately; do not disable validation. |
| `unknown deployment` (403) | Allowlist does not include this registration | Confirm the administrator's Deployment ID and perform the reviewed settings refresh. |
| Course resolution or roster fails after authentication | REST integration, course mapping or rate limit | Check separate REST permissions; use [12](incident-response.md). Respect Retry-After rather than relaunching repeatedly. |
| SPA opens at wrong host or direct deep link 404s | Effective frontend origin or missing SPA rewrite | Follow 09; changing only the secret may be shadowed by Lambda environment. |

## Sources and evidence gaps

[Routes](../../../services/api/app/lti/routes.py), [security primitives](../../../services/api/app/lti/security.py), [claims](../../../services/api/app/lti/claims.py), [launch tests](../../../services/api/tests/test_lti_launch.py), [REST connector](../../../services/api/app/lms/blackboard.py), [quota incident](../../archive/bugs/blackboard-rest-quota-exhaustion.md). Historic ngrok registrations are not current endpoint evidence. Current placement screenshots, permission settings, deployment mapping and two-role launch results: [Fred to confirm].

## History

| Date | Change to this runbook | Why |
| --- | --- | --- |
| 2026-10-25 | Draft registration exchange, placement and validation checks | APPROVAL-05 rev 2, Lane R, WI-06. |
