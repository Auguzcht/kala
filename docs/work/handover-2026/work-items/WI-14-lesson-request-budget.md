---
id: WI-14
title: Bound inline lesson generation
status: planned
owner: unassigned
requirements: []
depends_on: []
tests:
  - id: WI-14-T01
    kind: integration
---

# WI-14: Bound inline lesson generation

## Current state
Lesson outline and step generation still run on the API request path and can exceed the Lambda wall. Queued lesson checks do not bound teaching-content generation.

Source: [accepted endpoint audit](../evidence/audit-endpoints.md) at `e9de105`, 2026-10-24; no new runtime observation. Requirements are not assigned yet; the owning full spec must be written or amended before implementation. This is a planned finding, not a completed fix.

## What
Choose an async or whole-request deadline design for outline plus steps. Preserve ready-lesson replay and null-check compatibility.

## Where
[services/api/app/learn/lessons.py](<../../../../services/api/app/learn/lessons.py>) and the affected feature's future spec/tests. No code changes in Lane D.

## How
Design after freeze in the owning lane, preserving existing contracts unless separately approved. [APPROVAL-01 sections 3 and 5](../approval-01.md) records the scope boundary.

## Testing

### WI-14-T01: Verify the designed bound and safe behavior
- Preconditions: isolated configuration and mocked dependencies (ITO-approved test environment for logging).
- Action: exercise the slow/failure case described above.
- Expected result: On a slow mocked outline/step path, the chosen bounded behavior completes without relying on a Lambda kill.
- Result: not-run; behavior implementation is planned.

## Evidence
- Date: 2026-10-24 (Asia/Manila)
- Revision: `e9de105` / Lane D documentation only
- Environment: local static source audit
- Result: not-run (scenario); source finding preserved by APPROVAL-01

## Delivery
Merged: no. Deployed: no. Hosted migrations: none. Confirmation: pending implementation and named verification.
