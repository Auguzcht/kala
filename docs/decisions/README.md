# Decision records

One file per decision: `ADR-001-<slug>.md`, from `../engineering/documentation/templates/adr.md`. Never edit an accepted decision. Supersede it with a new one.

## Seed list (from the Checkpoint 1 and 1.1 session record, to be written in WI-09)

| ID | Decision |
| --- | --- |
| ADR-001 | A tenant is an LMS deployment, resolved from `iss` + `deployment_id` |
| ADR-002 | One session token minted by the API, read by RLS, used for both API and direct Supabase reads |
| ADR-003 | Practice attempt identity is server-owned (`quiz_set_attempts.id`), not the client session ID |
| ADR-004 | First attempt earns 2 XP per answer plus 10 if correct. Retakes earn 0 XP and do not move mastery |
| ADR-005 | A new answer to a finished attempt returns 409. An exact retry with the same idempotency key returns the saved snapshot |
| ADR-006 | AI help in Test only after grading, through the dock. No inline Explain more |
| ADR-007 | Study list hides answers by default |
| ADR-008 | The tour never writes student data |
| ADR-009 | Duplicate thresholds: bank 0.94, in-lesson variety 0.85, lesson check floor 0.35 |
| ADR-010 | Course ingest is asynchronous through the worker, never in the request path (31.8 s walk against the 30 s wall) |
| ADR-011 | Anything that kicks the worker from a request is debounced and leased (account concurrency cap shared with the API) |
| ADR-012 | Model provider: OpenRouter for generation, OpenAI for embeddings, Bedrock path retained (confirm current reality before writing) |
| ADR-013 | Offline or self-hosted AI option (pending answer to the supervisor's question) |
| ADR-014 | No declarative schema. Migrations are the only database authority. `schema.sql` and types are generated from a local Docker replay |
| ADR-015 | Full transfer: ITO provisions every account. No data, keys or accounts migrate from the developer's personal setup |

## Preserved recap decisions (WI-03)

- [ADR-016: legacy flashcard XP rollout gate](ADR-016-legacy-flashcard-xp.md). Grandfathering outcome remains a human decision.
- [ADR-017: feedback by persona](ADR-017-persona-feedback.md). No new dashboard feature is authorized.

ADR-001 through ADR-015 above remain a **seed list**, not authored or accepted records. In particular, ADR-012 live provider configuration and ADR-013 offline/self-hosted model suitability are unverified. See [recap evidence](../work/handover-2026/evidence/recap-knowledge.md).
