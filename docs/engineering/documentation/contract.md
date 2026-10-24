# Documentation contract

Adapted for Kala from a production spec-led workflow. It is deliberately smaller: one maintainer team, one LMS, one institution.

## 1. Identifiers

| ID | Meaning | Example | Scope |
| --- | --- | --- | --- |
| Feature slug | Folder name of a feature spec | `practice-tests` | Repo |
| `<PFX>-REQ-001` | One requirement in a feature spec | `TEST-REQ-004` | Feature. Prefix list in `features/README.md` |
| `WI-01` | One work item | `WI-03` | Initiative |
| `WI-01-T01` | One test scenario for a work item | `WI-03-T02` | Work item |
| `ADR-001` | One decision record | `ADR-007` | Repo |
| `INC-001` | One incident record | `INC-001` (the 0034 submit failure) | Repo |
| Migration number | `0037_<name>.sql` | `0037_admin_roles.sql` | Repo |

Rules:

1. IDs are never reused. A removed requirement keeps its heading with `Status: retired` and a reason.
2. Reordering text never renumbers IDs.
3. `depends_on` in a work item controls order. Numbers do not.
4. Historical labels from session recaps (Checkpoint 1, Case 7, bug 12, section 10.4) are kept where they appear and mapped once in the owning work item. Do not rename history.

## 2. Status vocabulary

| Status | Meaning | Required with it |
| --- | --- | --- |
| `planned` | Defined, not started | Nothing |
| `in-progress` | Being built or verified | Owner |
| `blocked` | Cannot move | `reason` and `next_action` |
| `deferred` | Deliberately out of current delivery | `reason` and who decided |
| `done-awaiting-confirmation` | Built, automated checks pass, evidence recorded, only a named manual check remains | Evidence entry |
| `confirmed-done` | Accepted | Confirmation date and source, latest passing evidence for every scenario |

Merged, deployed and released are separate facts recorded in the work item's Delivery section. "Merged" is never "done".

## 3. Profiles

- **Light** (default for Kala): one `docs/work/<initiative>/README.md`, or one file per item in `work-items/`, holding goal, requirements touched, current state, scenarios, evidence and delivery.
- **Full**: add `design.md` when a change touches tenancy, auth, RLS, the evidence log, shared contracts or more than one service.

## 4. How a behavior change happens

1. Find the feature spec through `docs/README.md`.
2. Write the change in the spec: new or amended `REQ`, with acceptance stated as something observable. Add a change-log line: date, reason, decision source, affected IDs.
3. Create or update the work item. Link the `REQ` IDs. Write the test scenarios.
4. Implement against the spec. Tests reference the `REQ` or `WI-..-T..` ID in their name or docstring.
5. Record evidence for the actual revision and environment.
6. Record merge, deploy and release separately.

## 5. Evidence entries

Append only. A later failure is never hidden by an earlier pass.

```yaml
- scenarios: [WI-03-T01, WI-03-T02]
  revision: e9de105          # or base revision + "working tree: <paths>"
  date: 2026-10-18
  environment: dev-hosted    # local | dev-hosted | prod (see engineering/environments.md)
  result: pass               # pass | fail | skipped | not-run
  source: scripts/smoke_retake.py output, CloudWatch log group /aws/lambda/kala-api
  limitations: Run as one test student only
```

## 6. Spikes and proofs

A spike answers one question with a time limit. File it as `docs/work/<initiative>/evidence/spike-<topic>.md` with: Question, Method, Result, Decision (link the ADR if one was made), Limits. A spike never changes a spec by itself. If it changes intent, write the ADR and amend the spec.

## 7. What the checker can and cannot prove

`scripts/docs_check.py` (if present) verifies links, front matter, ID format, status words and that every `REQ` is referenced by at least one `WI` or marked `deferred`. It cannot prove the spec is true, that tests are meaningful or that anything is deployed.
