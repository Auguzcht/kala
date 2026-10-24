---
id: WI-20
title: Adopt a standard frontend test runner so component tests run without external fixtures
status: planned
owner: unassigned
requirements: [TUTOR-REQ-001, STUDY-REQ-003, STUDY-REQ-005]
depends_on: []
tests:
  - id: WI-20-T01
    kind: integration
---

# WI-20: Adopt a standard frontend test runner

## Current state

Study component tests depend on an external matching React/react-test-renderer fixture and Node's experimental VM modules. Tutor tests use a custom hook/module harness. Neither provides a standard browser integration suite. Existing coverage and its limits remain valid; no dependencies are added by this work item.

## What

Adopt a standard frontend test runner (for example, Vitest) so component tests run from a clean checkout using locked repository dependencies and a documented command, without external fixtures.

## Where

The web application's test configuration and existing tutor, API-error/schema and Study component tests.

## How

Choose and review the runner after the integration freeze. Preserve existing behavioral assertions while replacing custom harnesses and document which browser/API boundaries remain mocked. Add dependencies only in that separately approved implementation.

## Testing

### WI-20-T01: Run component checks from a clean checkout

- Preconditions: install locked repository dependencies; no external renderer fixture, .env or live credentials.
- Action: run the documented frontend test command.
- Expected result: tutor, error-contract and Study regression tests pass without external fixture paths or live network calls.
- Result: not-run; runner adoption remains planned.

## Evidence

- Date: 2026-10-25 (Asia/Manila)
- Source: [APPROVAL-02 section 5](../approval-02.md), reaffirmed by [APPROVAL-03](../approval-03.md).
- Environment: local static test-harness review.
- Result: planned; no implementation or dependency changes.

## Delivery

Planned work item only. Runner implementation, deployment and confirmation: pending.
