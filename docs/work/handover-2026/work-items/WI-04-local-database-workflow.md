---
id: WI-04
status: planned
owner: ITO
---

# Local database workflow and hosted drift review

Lane DB owns the existing local replay/relocation/schema/types workflow and hosted drift review under [database policy](../../../engineering/database.md). Hosted PostgreSQL-major confirmation and the approved workflow gates remain separate from application release. Every future db:* package script stays strictly local. Applied migration bytes, including comments and numeric names, remain immutable.

## Accepted FG-6 grant finding — 2026-10-27

Owner: **ITO**, Lane DB drift check. Fred accepted 0038/0039 and FG-6 with a pre-existing SELECT-grant difference on 14 tables versus the local replay. Anon SELECT differs on generated_items, guided_lesson_steps, guided_lessons, ingest_jobs, item_exposures, item_reviews, lms_identity_aliases, quiz_set_attempts, quiz_set_items, quiz_sets, srs_state, tutor_attachments, tutor_conversations and tutor_messages. Authenticated SELECT also differs on ingest_jobs.

At least the tutor_conversations difference predates 0038, whose SQL changes policies only. Manual 0001–0036 application and Supabase default grants are the likely cause, not a fully proved grant history. All inspected public tables have RLS enabled and no anon/public policies; all 36 public policies, including 0038's 22, and all 20 application functions match the replay. No grant changes are authorized now.

Reconcile grant origins and intended access during the existing maintainer-supplied drift check. Propose any remediation separately with affected privileges, role tests and human approval. Do not change grants, run hosted queries, repair migration history or apply SQL merely because this finding is assigned. The local receipt remains local only, not retained. Hosted authenticated-role acceptance is FG-9, not a prerequisite reopened by this accepted finding.

## Verified by

- [Fred's FG-6 acceptance and exact scope](../evidence/fg6-fg8-acceptance-2026-10-27.md)
