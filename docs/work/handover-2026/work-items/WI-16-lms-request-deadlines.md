---
id: WI-16
title: Add whole-request deadlines to LMS paths
status: planned
owner: unassigned
requirements: []
depends_on: []
tests:
  - id: WI-16-T01
    kind: integration
---

# WI-16: Add whole-request deadlines to LMS paths

## Current state
Launch, roster pagination and recursive content reads have per-call timeouts but no cumulative request deadline. Cold OAuth/JWKS plus DB/LMS calls can exceed the request wall.

Source: [accepted endpoint audit](../evidence/audit-endpoints.md) at `e9de105`, 2026-10-24; no new runtime observation. Requirements are not assigned yet; the owning full spec must be written or amended before implementation. This is a planned finding, not a completed fix.

## What
Define a shared budget and safe pagination/caching/recovery behavior. Keep tenant, course and staff authorization independent of timeout handling.

## Where
[services/api/app/lti/routes.py](<../../../../services/api/app/lti/routes.py>) and the affected feature's future spec/tests. No code changes in Lane D.

## How
Design after freeze in the owning lane, preserving existing contracts unless separately approved. [APPROVAL-01 sections 3 and 5](../approval-01.md) records the scope boundary.

## Testing

### WI-16-T01: Verify the designed bound and safe behavior
- Preconditions: isolated configuration and mocked dependencies (ITO-approved test environment for logging).
- Action: exercise the slow/failure case described above.
- Expected result: Slow mocked OAuth/JWKS and multi-page LMS responses terminate within the approved budget and return a clear response without exposing another course.
- Result: not-run; behavior implementation is planned.

## Evidence
- Date: 2026-10-24 (Asia/Manila)
- Revision: `e9de105` / Lane D documentation only
- Environment: local static source audit
- Result: not-run (scenario); source finding preserved by APPROVAL-01

## Delivery
Merged: no. Deployed: no. Hosted migrations: none. Confirmation: pending implementation and named verification.
