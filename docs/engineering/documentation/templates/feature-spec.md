---
feature: <slug>
req_prefix: <PFX>
owner_role: <role who decides intent, e.g. product owner / OAICI>
status: active            # active | planned | retired
code:
  web: apps/web/src/features/<name>/
  api: services/api/app/routers/<name>.py
  worker: []
  db: [packages/db/migrations/00xx_<name>.sql]
tests: []
---

# <Feature name>

## Purpose
Two or three sentences. Who uses it and what it gives them that the LMS cannot.

## Actors and permissions
| Actor (app_role) | Can | Cannot |
| --- | --- | --- |
| student | | |
| instructor | | |

## Requirements

### <PFX>-REQ-001: <short observable statement>
- Rule: what must be true.
- Acceptance: what a tester sees or what a query returns.
- Status: implemented | partial | planned | retired
- Verified by: test path or scenario ID, or "manual: docs/engineering/testing.md row N"

## API contract
| Method and path | Purpose | Auth | Notes (idempotency, error codes) |
| --- | --- | --- | --- |

## Data
Tables written and read, which writes are service-role only, which RLS policies apply.

## AI usage (if any)
Which model tier, what is sent (after de-identification), timeouts, fallback, cost notes.

## Edge cases and known limits

## Change log
| Date | Change | Reason and decision source | IDs affected |
| --- | --- | --- | --- |
