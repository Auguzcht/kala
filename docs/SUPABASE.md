# Supabase setup and data governance

This is the source of truth for the Supabase side of Kala. The migrations in `packages/db/migrations` were validated on PostgreSQL 16 with pgvector: all three apply cleanly, and the RLS behavior below was tested (student sees only own rows, instructor sees their course, other tenants see nothing, PII is not cross-readable, researchers get only consented pseudonymized rows and are blocked from raw tables).

## What Supabase stores (and what it does not)

Identity originates from the LMS through the LTI launch. Supabase never stores LMS passwords and is not the content system of record. It stores three things:

1. A thin, pseudonymous mirror of identity so learning evidence can be anchored: `institutions` (the tenant, resolved from LTI `iss` + `deployment_id`), `users` (a pseudonymous anchor whose `id` equals the JWT `sub`), and `user_profiles` (the small amount of PII, kept separate so it can be purged). Plus `lti_launches` as a security log.
2. The academic mirror and the learning-intelligence layer: `courses`, `enrollments`, `skills`, `content_items` (chunks + embeddings for RAG), `assessments`, the append-only `evidence_events`, and the derived `mastery_state`, `readiness_snapshots`, `recommendations`. This is the digital twin, the thing the LMS cannot produce.
3. Governance and audit: `consents`, `researchers`, `researcher_grants`, `data_subject_requests`, and the immutable `audit_log`.

The LMS stays the source of truth for content and official grades. Supabase is the source of truth for learning evidence.

## Roles and RLS

RLS is enabled on all 18 tables with a default-deny posture. Roles come from the JWT `app_role` claim: `student`, `instructor`, `admin`, `researcher`. The backend uses the `service_role` key for writes and bypasses RLS; the policies govern the authenticated client path as defense in depth. Summary:

- Students read only their own evidence, mastery, readiness, recommendations, and profile, and record their own consent and data-subject requests.
- Instructors read data for the courses they teach (enforced by `teaches()`), not the whole institution.
- Admins read identifiable operational data within their own institution, including the audit log and launch log.
- Researchers cannot read base tables at all. They read only the three anonymized views.
- `anon` has no access to anything.

Writes to `evidence_events`, `mastery_state`, and the other derived tables are performed by the backend service role, never by the client, so students cannot forge evidence.

## Researcher access (their own dashboard, only them)

External researchers use a separate portal with their own authentication, not an LTI launch. Their token carries `app_role='researcher'` and `sub` equal to their `researchers.id`. Three gates are enforced inside the database, in the view bodies:

1. `app_role` must be `researcher`.
2. an active, unexpired `researcher_grant` must exist for the institution.
3. only rows for students who granted research consent are included.

`research_mastery_anon` and `research_evidence_anon` expose pseudonyms only (no names, emails, or LMS ids). `research_cohort_daily` is aggregate-only with k-anonymity: groups with fewer than 10 attempts are hidden. Institutions themselves (via admins) see identifiable data for their own students; external researchers never do.

## SOC 2 / ISO 27001 alignment

- Access control and least privilege (SOC 2 CC6, ISO A.9): default-deny RLS on every table, role-scoped policies, `anon` revoked, writes through the service role.
- Audit logging (CC7, A.12.4): immutable `audit_log` written by security-definer triggers on consent, grants, data-subject requests, and enrollments; `UPDATE`/`DELETE` are blocked by trigger for all roles including the service role.
- Integrity of records (A.12): `evidence_events`, `lti_launches`, and `audit_log` are append-only and tamper-resistant.
- Data minimization and PII separation (A.8, privacy): PII lives only in `user_profiles`; everything analytical uses the pseudonym.
- Consent and data-subject rights (privacy, PDPA): `consents` is versioned and gates all research use; `data_subject_requests` records export and erasure.
- Encryption: Supabase encrypts at rest and in transit by default. Keep secrets in Supabase Vault; if you later need column-level encryption for a field, use pgsodium.
- Access reviews (CC6): `researcher_grants` carry an expiry and a status, so access lapses by default.

## Setup steps

1. Create the Supabase project (choose the region closest to the pilot, matching your AWS region where practical). Run `pnpm setup` or `pnpm install` first in this repo; the root workspace already pulls in the Supabase CLI, so the local binary is available without a separate global install.
2. In the SQL editor or CLI, ensure `pgcrypto` and `vector` are enabled (migration `0001` does this).
3. Set the JWT secret so the backend can mint Supabase-compatible tokens: use the project JWT secret for HS256, or configure third-party (asymmetric) auth if you prefer. The backend must include `sub`, `institution_id`, `app_role`, and `role: authenticated` in every minted token.
4. Confirm the `authenticated` role has usage on the `auth` schema and execute on `auth.uid()` and `auth.jwt()` (Supabase sets this up by default).
5. Run the migrations in order: `0001_init.sql`, `0002_rls.sql`, `0003_research.sql`.
6. Seed the pilot institution row (MMCM) with its LMS issuer and deployment id.
7. Set the embedding dimension. `content_items.embedding` is `vector(1024)`; change it to match your embedding model before you index at scale.

## Edge functions and AWS

You do not need edge functions for the core build. The primary AWS connection is FastAPI on Lambda talking to Supabase with the service-role key (or a direct Postgres connection). The scheduled worker (EventBridge) recomputes the twin and re-embeds content by reading and writing Supabase directly.

An optional edge function is included at `supabase/functions/aws-proxy` for the event-driven case: if you would rather have Supabase push an event to AWS the moment data changes (for example, re-embed on content change) instead of polling, wire that function to a Supabase Database Webhook, or call your AWS endpoint from a trigger using `pg_net`. Use SigV4 or IAM auth in production rather than the shared-secret placeholder.

## Retention and erasure

Erasure uses crypto-shredding: on an approved erasure request, purge the `user_profiles` row (and any stored raw content tied to the user). Evidence remains under a pseudonymous `users.id` with no way back to a person, which preserves the research dataset while honoring the request. Set retention windows per institution agreement; the append-only tables are the records you retain.

## Are we ready to build?

Yes. With the scaffold, the masterplan, the finalized stack, and this validated schema, development can start now. What remains are setup and provisioning actions, not open questions:

- Create the Supabase project and run the three migrations (above).
- Stand up the Blackboard developer environment (your own AMI in the AWS org account, or the hosted sandbox), with Canvas as the fallback.
- Enable Bedrock and confirm the exact model ids available in your region.
- Register the LTI 1.3 tool and the REST application in the Anthology Developer Portal.

Two decisions are intentionally deferred and are already tracked in the masterplan open-decisions log: the mastery tracer (BKT versus Elo with recency decay) and the final embedding model and its dimension. Neither blocks the first task, which is the auth spine: the FastAPI LTI launch handler that mints the Supabase token and wires it to the RLS you see here. Everything that handler needs is defined.
