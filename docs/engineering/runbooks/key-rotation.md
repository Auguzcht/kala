---
runbook: key-rotation
applies_to: [dev-hosted, prod]
who_runs_it: Named credential custodian with ITO service owners
time_needed: "[Fred to confirm]"
last_verified: "unverified; source review at 4f3ec29 on 2026-10-25, Lane R"
status: in-progress
---

# Runbook 11 — coordinate credential replacement

## When to use it

Prepare approved cutover rotation or respond to a confirmed exposure. WI-07 draft, executed only by credential custodians. [APPROVAL-02](../../work/handover-2026/approval-02.md) sets standing exposure-log rotation timing at cutover; current incident owners may approve an earlier emergency replacement. Agents never rotate credentials. No zero-downtime claim is supported for every credential class.

## Before you start

Use [secrets.md](../secrets.md) as the sole credential/store/owner and exposure inventory. Identify every actual consumer privately, including both Lambdas, local copies and any optional proxy. Choose named owners, window, revocation deadline and recovery policy: [Fred to confirm]. Never reopen historical pasted credentials to perform an inventory.

## Steps

1. Custodian verifies the incident/cutover scope, old credential status and provider-specific replacement controls privately. Record credential **names**, owner, presence/status and timing only. Current dashboard paths and support for overlapping valid credentials: [Fred to confirm]. Stop if an overlap assumption has not been verified.
2. For independent model-provider/REST credentials, create a replacement through the owner's approved provider process, store it privately, and update all intended consumers through [05](secrets-manager.md). Validate billing/entitlement and the selected model or REST integration, not just presence. Keep the previous credential only if uncompromised and explicitly allowed during the transition.
3. Refresh API and worker through the reviewed release/configuration procedure; cached warm settings do not automatically pick up secret updates. Check Lambda environment overrides. Run [10](first-launch-smoke.md)'s relevant synthetic paths before declaring the new credential in use. Exact consumer-refresh/revocation sequence: [Fred to confirm].
4. **Session-signing/database key gate:** [jwt.py](../../../services/api/app/security/jwt.py) uses the configured HS256 secret for sessions; [LTI state](../../../services/api/app/lti/security.py) also uses it. Changing it affects active sessions/state and may affect related project keys. Exact Supabase-supported replacement, legacy-key impact, active-session handling and rollback: [Fred to confirm]. Stop for an approved signing migration/relaunch plan; this runbook does not silently change algorithms or promise seamless overlap.
5. **LTI tool-signing gate:** source exposes one RSA public key with fixed `kid` `kala-tool-key-1`. It does not implement multi-key overlap. Do not follow the catalogue's proposed JWKS-overlap wording as an existing capability. Exact platform JWKS-cache behavior, maintenance window, coordinated portal/Learn update and any required code work: [Fred to confirm]. Stop before replacing this key until a tested rollover plan is approved.
6. For AWS human/CLI access and Learn user passwords, the account administrator uses institutional identity/password policy and verifies replacement access privately before removing old grants. Exact temporary-access, MFA/recovery and revocation procedures: [Fred to confirm]. Do not create root access keys or copy personal credentials to ITO.
7. After verified cutover, custodians revoke old credentials, validate rejection through an approved private method, and update the names-only exposure status through its owning lane. Record verifier/date, consumer checks and revocation result. No credential values or authentication payloads in the record.

## Verify it worked

All intended consumers demonstrably use the replacement, relevant synthetic flows pass, old credentials are revoked and custody belongs to the institution. Record partial failures honestly. No provider/account was queried and no credential was generated or rotated by Lane R.

## Undo / roll back

Never reactivate an exposed/revoked credential. If replacement fails, stop affected operations and have the custodian issue another valid replacement or follow the approved service recovery plan. A compromised key is not a rollback artifact. Exact per-provider emergency recovery: [Fred to confirm].

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Some calls still fail after rotation | Missed consumer, cached settings or override | Verify both Lambda refreshes and effective setting names privately. |
| Users suddenly lose sessions | Session signing changed | Follow approved relaunch/maintenance plan; do not weaken JWT verification. |
| LTI service signatures fail | Platform key cache / fixed-key rollover | Stop and use the approved coordinated key plan. |

## History

| Date | Change to this runbook | Why |
| --- | --- | --- |
| 2026-10-25 | Draft replacement process and explicit signing-key gates | APPROVAL-05 rev 2, Lane R, WI-07. |
