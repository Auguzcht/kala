---
id: WI-18
title: Decide API Gateway access logging with ITO
status: planned
owner: unassigned
requirements: []
depends_on: []
tests:
  - id: WI-18-T01
    kind: manual
---

# WI-18: Decide API Gateway access logging with ITO

## Current state
Repository Terraform does not configure API Gateway access logs. Hosted log availability has not been inspected; Lambda logs alone cannot establish every integration failure.

Source: [accepted endpoint audit](../evidence/audit-endpoints.md) at `e9de105`, 2026-10-24; no new runtime observation. Requirements are not assigned yet; the owning full spec must be written or amended before implementation. This is a planned finding, not a completed fix.

## What
ITO decides whether and how to add access logs, retention, fields and privacy controls. This is an infrastructure change requiring its own explicit task.

## Where
[infra/terraform/apigw.tf](<../../../../infra/terraform/apigw.tf>) and the affected feature's future spec/tests. No code changes in Lane D.

## How
Design after freeze in the owning lane, preserving existing contracts unless separately approved. [APPROVAL-01 sections 3 and 5](../approval-01.md) records the scope boundary.

## Testing

### WI-18-T01: Verify the designed bound and safe behavior
- Preconditions: isolated configuration and mocked dependencies (ITO-approved test environment for logging).
- Action: exercise the slow/failure case described above.
- Expected result: An ITO-approved environment records request/status/integration evidence with appropriate retention and without request bodies, tokens or student text.
- Result: not-run; behavior implementation is planned.

## Evidence
- Date: 2026-10-24 (Asia/Manila)
- Revision: `e9de105` / Lane D documentation only
- Environment: local static source audit
- Result: not-run (scenario); source finding preserved by APPROVAL-01

## Delivery
Merged: no. Deployed: no. Hosted migrations: none. Confirmation: pending implementation and named verification.
