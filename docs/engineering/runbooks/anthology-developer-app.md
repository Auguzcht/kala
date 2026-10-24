---
runbook: anthology-developer-app
applies_to: [dev-hosted, prod]
who_runs_it: Institutional Developer Portal owner and Learn administrator
time_needed: "[Fred to confirm]"
last_verified: "unverified; source review at 4f3ec29 on 2026-10-25, Lane R"
status: in-progress
---

# Runbook 04 — register the Anthology application

## When to use it

Prepare the LTI client registration and REST application for a new environment. This WI-06 draft documents maintainer-only registration; it does not authorize an agent to create applications or handle credentials.

## Before you start

- Obtain an institutional Developer Portal account, Learn administrator and the test environment from [03](blackboard-learn-instance.md).
- Obtain the approved API base from [06](terraform-apply.md) for final registration and a key custodian for the tool signing key. Credential names/stores are in [secrets.md](../secrets.md).
- The registry's early step 04 can collect metadata before 06. Any placeholder registration remains unusable until the real public endpoints are saved. Whether the current portal permits placeholders: [Fred to confirm]. Do not submit invented URLs merely to complete a form.

## Steps

1. Sign in to the institutional account at the Developer Portal (host `developer.anthology.com`, from the repository README). Open its application-registration area. Exact menu labels, account entitlement and required organization fields: [Fred to confirm]. Check account ownership before creating anything.
2. Create the environment's application using the administrator-approved name/description: [Fred to confirm]. Enable/configure LTI 1.3 through the portal's supported flow. Record the Application ID as the LTI client ID in the private environment inventory, keeping it distinct from the REST application key. Whether one current portal record supplies both registrations or requires separate records: [Fred to confirm].
3. Enter the public tool endpoints using the real API base:

   | Portal field / purpose | Tool path | Check |
   | --- | --- | --- |
   | Redirect URI | `/lti/launch` | Matches the URL allowed for form-post launches. |
   | OIDC initiation / login | `/lti/login` | Public HTTPS API route, not the SPA. |
   | Tool public JWKS | `/lti/jwks` | Public RSA signing keyset, no private material. |

   Exact portal field names, any target-link URI field and multiple-redirect support: [Fred to confirm]. Source supports these routes; portal acceptance has not been observed by Lane R.
4. Obtain the REST application key and secret through the approved portal workflow and save them directly to the institutional password manager. Store the LTI client ID and REST key under their separate names from the catalogue. Never paste credentials or screenshots containing them into repository evidence. Check only that each required field is set.
5. Have the Learn administrator enable the REST integration on the specific Learn instance in [08](lti-tool-registration.md). Portal registration alone grants no course access. Associated integration user, role privileges, consent settings and exact system-admin console path: [Fred to confirm].
6. Obtain the platform endpoints from the Learn administrator. Source uses the configured OAuth token URL for the REST client-credentials exchange as well as the LTI configuration; confirm it belongs to this Learn instance. Record endpoint hosts only in shared evidence. Set backend configuration through [05](secrets-manager.md), never browser variables.
7. Revisit any provisional registration after 06 and replace placeholder endpoints with the approved API endpoints before first launch. Recheck that the API/tool JWKS, portal record and Learn registration refer to the same client and environment. Continue with 08.

## Verify it worked

The institutional owner can reopen the application record, the three public tool endpoints match the API, and the Learn administrator recognizes the intended LTI client and REST application. Complete actual launch and roster/content checks in [10](first-launch-smoke.md). Record date, verifier, environment and sanitized pass/fail outcomes. No application or credentials were accessed by Lane R.

## Undo / roll back

Before use, the portal owner may disable only the new unused application after administrator approval. After use, coordinate replacement with both the Learn registration and backend settings; disabling a shared app breaks both launch and REST consumers. Exact portal disable/revoke controls and consumer inventory: [Fred to confirm]. See [11](key-rotation.md) for credential replacement gates.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Unknown client / redirect rejected | Wrong Application ID or API redirect | Compare the private portal and Learn records with `/lti/launch`. |
| REST 401/403 after successful launch | REST key/secret or Learn integration privileges differ | Have the portal owner and Learn administrator verify the separate REST setup; do not swap in the LTI ID by guesswork. |
| No application creation option | Account entitlement or changed portal flow | Stop; Fred supplies current institutional access and screenshots with sensitive fields hidden. |

## Sources and evidence gaps

[Blackboard README](../../../infra/blackboard/README.md), [connector](../../../services/api/app/lms/blackboard.py), [LTI routes](../../../services/api/app/lti/routes.py), [settings](../../../services/api/app/config.py). No archived session record located in the repo supplies the full Developer Portal click path or current field screenshots. These are explicit Fred verification gaps, not completed setup evidence.

## History

| Date | Change to this runbook | Why |
| --- | --- | --- |
| 2026-10-25 | Draft portal and separate LTI/REST checks | APPROVAL-05 rev 2, Lane R, WI-06. |
