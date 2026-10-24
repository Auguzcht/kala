---
id: WI-19
title: Extend de-identification coverage deliberately
status: planned
owner: unassigned
requirements: []
depends_on: []
tests:
  - id: WI-19-T01
    kind: integration
---

# WI-19: Extend de-identification coverage deliberately

## Current state
The existing sanitizer covers emails and explicit name: patterns only. Arbitrary names and other identifiers remain outside coverage; de-identification status is partial.

Source: [accepted endpoint audit](../evidence/audit-endpoints.md) at `e9de105`, 2026-10-24; no new runtime observation. Requirements are not assigned yet; the owning full spec must be written or amended before implementation. This is a planned finding, not a completed fix.

## What
Specify threat/coverage boundaries and evaluate broader minimization without modifying stored rows. Lane T applies the existing sanitizer at every tutor model boundary but does not expand it.

## Where
[services/api/app/ai/deidentify.py](<../../../../services/api/app/ai/deidentify.py>) and the affected feature's future spec/tests. No code changes in Lane D.

## How
Design after freeze in the owning lane, preserving existing contracts unless separately approved. [APPROVAL-01 sections 3 and 5](../approval-01.md) records the scope boundary.

## Testing

### WI-19-T01: Verify the designed bound and safe behavior
- Preconditions: isolated configuration and mocked dependencies (ITO-approved test environment for logging).
- Action: exercise the slow/failure case described above.
- Expected result: A documented fixture matrix measures identifiers removed and false positives; unsupported patterns are explicit and model-bound copies remain separate from stored rows.
- Result: not-run; behavior implementation is planned.

## Evidence
- Date: 2026-10-24 (Asia/Manila)
- Revision: `e9de105` / Lane D documentation only
- Environment: local static source audit
- Result: not-run (scenario); source finding preserved by APPROVAL-01

## Delivery
Merged: no. Deployed: no. Hosted migrations: none. Confirmation: pending implementation and named verification.
