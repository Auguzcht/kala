---
id: WI-17
title: Define explicit Bedrock timeout and retry policy
status: planned
owner: unassigned
requirements: []
depends_on: []
tests:
  - id: WI-17-T01
    kind: integration
---

# WI-17: Define explicit Bedrock timeout and retry policy

## Current state
At the audited base, Bedrock clients use inherited SDK timeout/retry settings. Lane T may add an opt-in deadline for tutor only; default/global policy stays deferred by approval.

Source: [accepted endpoint audit](../evidence/audit-endpoints.md) at `e9de105`, 2026-10-24; no new runtime observation. Requirements are not assigned yet; the owning full spec must be written or amended before implementation. This is a planned finding, not a completed fix.

## What
Choose explicit SDK connect/read/retry policy with ITO and provider owners. Do not alter non-tutor defaults in the pre-freeze tutor lane.

## Where
[services/api/app/ai/bedrock.py](<../../../../services/api/app/ai/bedrock.py>) and the affected feature's future spec/tests. No code changes in Lane D.

## How
Design after freeze in the owning lane, preserving existing contracts unless separately approved. [APPROVAL-01 sections 3 and 5](../approval-01.md) records the scope boundary.

## Testing

### WI-17-T01: Verify the designed bound and safe behavior
- Preconditions: isolated configuration and mocked dependencies (ITO-approved test environment for logging).
- Action: exercise the slow/failure case described above.
- Expected result: Mocked SDK calls demonstrate the chosen attempt/time limit, and non-tutor callers are assessed explicitly before changing their defaults.
- Result: not-run; behavior implementation is planned.

## Evidence
- Date: 2026-10-24 (Asia/Manila)
- Revision: `e9de105` / Lane D documentation only
- Environment: local static source audit
- Result: not-run (scenario); source finding preserved by APPROVAL-01

## Delivery
Merged: no. Deployed: no. Hosted migrations: none. Confirmation: pending implementation and named verification.
