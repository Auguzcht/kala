---
id: WI-01
title: <imperative title>
status: planned
owner: unassigned
requirements: []          # e.g. [TUTOR-REQ-003]
depends_on: []
reason: ""                # required when blocked or deferred
next_action: ""           # required when blocked
tests:
  - id: WI-01-T01
    kind: manual          # unit | integration | e2e | manual | static
    path: ""              # only when the test file exists
---

# WI-01: <title>

## Current state
One paragraph. What is true right now, with the revision you checked.

## What
The change, in observable terms.

## Where
Files and services touched.

## How
Approach and any constraint (migration order, flags, rollback).

## Testing

### WI-01-T01: <scenario name>
- Preconditions:
- Action:
- Expected result:

## Evidence
(append entries using the format in contract.md section 5)

## Delivery
| Fact | Value |
| --- | --- |
| Merged | |
| Migrations applied | |
| API / worker deployed (alias version, CodeSha256 prefix) | |
| Web deployed (Vercel deployment) | |
| Confirmed by | |
