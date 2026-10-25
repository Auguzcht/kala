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

## Current operating boundary

Use the current feature specifications for requirements, engineering for procedures and decisions for accepted rationale. Requirements marked partial/planned and runbooks marked execution-unverified are explicit limits, not completed capabilities. Agents must not infer acceptance from a registry row or a past successful check.

Visual authority remains [DESIGN.md](../apps/web/src/styles/DESIGN.md). The [environment boundary](engineering/environments.md), [database policy](engineering/database.md), [secrets catalogue](engineering/secrets.md), [security limits](engineering/security-and-privacy.md) and [release runbook](engineering/runbooks/deploy-backend.md) carry operational constraints. The local database workflow is not yet installed; do not run future db:* commands as if present. Applied migration files are immutable and a human applies hosted SQL after review. Human deployment and live acceptance are separate from local verification.

Work items track delivery, not requirements. The handover initiative starts with its closeout record and does not define operational authority. Consult records only when the task explicitly names them. Do not read docs/archive/** or docs/work/**/evidence/** by default.

## Change log

| Date | Change | Source |
| --- | --- | --- |
| 2026-10-24 | Install the documentation framework, preserve accepted audit/recap evidence, archive only approved rows, and record six planned findings | APPROVAL-01 including confirmed section 5; WI-02 and WI-03 |

## Historical sources

These links preserve provenance only. Required rules, commands and limits are stated above; do not read the records unless the task explicitly names them.

- [archive](archive/README.md)
- [Link-check evidence](work/handover-2026/evidence/docs-link-check.md)
- [82-file disposition map](work/handover-2026/evidence/migration-map.md)
