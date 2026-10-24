---
id: WI-15
title: Bound content upload work
status: planned
owner: unassigned
requirements: []
depends_on: []
tests:
  - id: WI-15-T01
    kind: integration
---

# WI-15: Bound content upload work

## Current state
Storage, PDF extraction, sequential chunk writes and pending embedding work can exceed the API wall. The 12-second slice checks before starting a chunk and does not cancel an in-flight embed/update.

Source: [accepted endpoint audit](../evidence/audit-endpoints.md) at `e9de105`, 2026-10-24; no new runtime observation. Requirements are not assigned yet; the owning full spec must be written or amended before implementation. This is a planned finding, not a completed fix.

## What
Design bounded or asynchronous upload work. Lane S owns only the approved correction to the misleading comment near diagnostic.py:304; this planned item owns the later behavior design.

## Where
[services/api/app/routers/diagnostic.py](<../../../../services/api/app/routers/diagnostic.py>) and the affected feature's future spec/tests. No code changes in Lane D.

## How
Design after freeze in the owning lane, preserving existing contracts unless separately approved. [APPROVAL-01 sections 3 and 5](../approval-01.md) records the scope boundary.

## Testing

### WI-15-T01: Verify the designed bound and safe behavior
- Preconditions: isolated configuration and mocked dependencies (ITO-approved test environment for logging).
- Action: exercise the slow/failure case described above.
- Expected result: A large mocked PDF and stalled embedding cannot run past the approved whole-request budget; uploaded/stored progress has an explicit recovery contract.
- Result: not-run; behavior implementation is planned.

## Evidence
- Date: 2026-10-24 (Asia/Manila)
- Revision: `e9de105` / Lane D documentation only
- Environment: local static source audit
- Result: not-run (scenario); source finding preserved by APPROVAL-01

## Delivery
Merged: no. Deployed: no. Hosted migrations: none. Confirmation: pending implementation and named verification.
