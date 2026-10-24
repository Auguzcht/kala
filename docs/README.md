# Kala documentation guide

This page decides where every kind of information lives and which document wins when two disagree. If a document is not reachable from this page, it is not an authority.

## Task router

| I want to... | Read, in this order |
| --- | --- |
| Understand what a feature does today | [features/README.md](features/README.md) -> that feature's `README.md` -> its source and tests |
| Change how a feature behaves | Feature spec -> [engineering/documentation/contract.md](engineering/documentation/contract.md) section 4 -> update the spec -> open or update a work item -> implement |
| Fix a bug | Feature spec (confirm intended behavior) -> fix -> add an evidence entry to the work item or the feature's evidence log |
| Set up a laptop for development | [engineering/local-development.md](engineering/local-development.md) |
| Stand Kala up in a new environment from zero | [engineering/environments.md](engineering/environments.md) -> [engineering/runbooks/README.md](engineering/runbooks/README.md), in the listed order |
| Find out where a secret lives or how to rotate it | [engineering/secrets.md](engineering/secrets.md) -> [engineering/runbooks/key-rotation.md](engineering/runbooks/key-rotation.md) |
| Change the database schema | [engineering/database.md](engineering/database.md) (write migration, `pnpm db:reset`, `pnpm db:schema`, `pnpm db:types` on the local Docker stack) |
| Apply a migration to a hosted project | [engineering/database.md](engineering/database.md) -> runbook 02 |
| Plan infrastructure, cost or sign-off | [engineering/infrastructure-requirements.md](engineering/infrastructure-requirements.md) |
| Deploy the API or worker | [engineering/runbooks/deploy-backend.md](engineering/runbooks/deploy-backend.md) |
| See what is unfinished | [work/README.md](work/README.md) |
| Know why something was decided | [decisions/README.md](decisions/README.md) |
| Read old plans or session recaps | [archive](archive/README.md) (history only, not policy) |

## Where information belongs

| Location | Holds | Does not hold |
| --- | --- | --- |
| `features/<feature>/README.md` | Durable intended behavior: requirements (`REQ`), contracts, roles, edge cases, change log | Progress, to-do lists, dates of work |
| `engineering/` | How to build, test, run, deploy, secure and operate Kala | Feature behavior |
| `engineering/runbooks/` | Step-by-step procedures a person executes, with checks | Background essays |
| `work/<initiative>/` | Work items (`WI`), status, blockers, evidence of tests and deploys | Durable behavior (link to the spec instead) |
| `decisions/` | One short record per decision (`ADR-001`), with date, reason and source | Tasks |
| `archive/` | Superseded documents, each with a header pointing to its replacement | Anything current |
| Source and tests | Actual implementation and observed behavior | Intent |

## Precedence when documents disagree

1. The feature spec states intent.
2. Tests and code state observed behavior.
3. A disagreement between 1 and 2 is a finding. Record it in the relevant work item and resolve it deliberately.
4. Anything in `archive/`, old recaps, PATCH notes or chat history has no authority.

## Status words

Only these: `planned`, `in-progress`, `blocked`, `deferred`, `done-awaiting-confirmation`, `confirmed-done`. Definitions are in [engineering/documentation/contract.md](engineering/documentation/contract.md).

## Installation boundary

WI-03 installs the router, templates, archives and focused knowledge extracts. [APPROVAL-01](work/handover-2026/approval-01.md) plus section 5 controls the parallel lane scopes. [Link-check evidence](work/handover-2026/evidence/docs-link-check.md) separates absent cross-lane files, not-yet-authored specs/runbooks, historical missing references and unexpected broken links. Full specs and full operational runbooks remain WI-06/WI-07/WI-08 work; a registry row is not a completed document.

Retained legacy design/setup documents are reachable as source material through the [82-file disposition map](work/handover-2026/evidence/migration-map.md). Their authority claims are superseded by this router and the approved feature specs. Visual authority remains [DESIGN.md](../apps/web/src/styles/DESIGN.md). [F08/F09](design/handover-findings.md) are recorded findings, with no CSS changes.

## Change log

| Date | Change | Source |
| --- | --- | --- |
| 2026-10-24 | Install the documentation framework, preserve accepted audit/recap evidence, archive only approved rows, and record six planned findings | APPROVAL-01 including confirmed section 5; WI-02 and WI-03 |
