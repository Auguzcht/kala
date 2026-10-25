# Provider availability and 0037 read-only pre-checks

Checked on 2026-10-25, Asia/Manila. Database snapshot time: 2026-10-25T07:45:04.058917+08:00. Source base:25c91418ead3cf6cc6ceb5bdad679b9a0a994ae8. Operator: coordinator, directly authorized by Fred to check model state and run pre-checks before Fred applies0037. No model generation, hosted write, migration application, secret update, deployment or push occurred.

## Actual model routing

Study hint and Explain call useTutorAsk in apps/web/src/features/flashcards/components/FlashcardDeck.tsx:171–172 and663–682. Test dock follow-up uses the same hook in apps/web/src/features/practice/components/PracticePanel.tsx:278. askTutor posts /tutor/ask in apps/web/src/features/tutor/api/tutor.api.ts:24. Tutor backend selects task=chat in services/api/app/routers/tutor.py:473–476; ai/router.py:24 resolves the chat model.

Test's already-generated explanation is rendered from question.explanation at PracticePanel.tsx:178–179. Generation uses the item role in services/api/app/learn/items.py:303. Reading that stored explanation makes no new model call. Its fast appearance cannot benchmark a fresh hint/Tutor request.

Read-only AWS CLI checks found the live API alias still on version6. Its environment overrides only FRONTEND_URL, KALA_SECRETS_ARN and WORKER_FUNCTION_ARN. The current secret bundle contains no model-role overrides. Config defaults are unchanged from published4f3ec29, whose deployed source was previously verified. Thus chat selects inclusionai/ling-3.0-flash-vl with nex-agi/nex-n2.5-mini:free fallback; item/default selects deepseek/deepseek-v4.1-flash:floor. AI_PROVIDER is OpenRouter; EMBED_PROVIDER is OpenAI. Cached Lambda settings can lag future secret updates; no refresh is claimed.

## Current OpenRouter metadata

Used the current runtime key in process memory; never printed it, its label, raw secret payload or provider body. GET/auth/key and GET/credits both returned200. Key is not a free-tier account, has no configured spend cap or expiry. Account totals:5 USD credits,2.371717341 USD usage; remaining **2.628282659 USD** at inspection. This confirms the reported approximate2.63 USD balance; exhausted credits are not established as the cause.

| Model | Endpoint metadata result | Conclusion |
| --- | --- | --- |
| inclusionai/ling-3.0-flash-vl | HTTP200; one current endpoint, DeepInfra | Still listed and served; not retired. Metadata does not prove a successful completion for this account. |
| nex-agi/nex-n2.5-mini:free | HTTP200; endpoints=[] | No serving endpoint at inspection; not a usable fallback then. This does not establish permanent retirement. |
| nex-agi/nex-n2.5-mini | HTTP200; one current endpoint, Nex AGI | Paid fallback candidate on a different serving provider. Advertised prompt/completion prices0.025/0.10 USD per million tokens. Not completion-tested in this task. |
| deepseek/deepseek-v4.1-flash:floor | HTTP200; multiple endpoints including Relace | Current item/default role remains available; no need to reroute interactive hints to the batch item role. |

Sources: [Ling endpoint metadata](https://openrouter.ai/api/v1/models/inclusionai/ling-3.0-flash-vl/endpoints), [free Nex endpoint metadata](https://openrouter.ai/api/v1/models/nex-agi/nex-n2.5-mini:free/endpoints), [paid Nex endpoint metadata](https://openrouter.ai/api/v1/models/nex-agi/nex-n2.5-mini/endpoints), [OpenRouter error documentation](https://openrouter.ai/docs/api/reference/errors-and-debugging). These were read during this task; public catalog metadata and account read APIs are not live-generation acceptance.

CloudWatch filtered read over the preceding12 hours returned three matching primary429 rows, at UTC2026-10-24 16:42:22,17:39:23 and17:40:15, attempting the free fallback. Only allowlisted timestamp/model/status/fallback fields were retained. Pagination remained, so this is not an exhaustive event count. Old deployed logs do not establish the fallback's exact response status. The evidence shows primary rate limiting plus a currently unroutable fallback, not insufficient account credit.

## Proposed FG-1 configuration for Fred

No new wiring is needed. In kala/app Fred can set OPENROUTER_MODEL_CHAT_FALLBACK to nex-agi/nex-n2.5-mini (without :free), retaining the existing primary and shared chat route. This changes only the chat-role fallback. The separate reasoning-role fallback remains unchanged and needs its own review if changed later. Provider/model roles are distinct from their actual serving provider: primary currently DeepInfra, proposed fallback Nex AGI.

This is a concrete configuration proposal, not an applied change. APPROVAL-06 FG-1 reserves hosted model configuration/runtime refresh to Fred. Save the previous secret-version and alias mapping privately, update the single setting, then initialize fresh API instances through the approved release procedure. Once0037 passes, the planned FG-4 make deploy refresh can publish the integrated source and updated settings together. Retest hint, Explain and Tutor through Fred's Blackboard session; capture stage/status/timing only. Recovery is the previously recorded compatible alias/approved secret version, leaving additive0037 in place. No successful live answer or model performance guarantee is claimed.

## 0037 pre-check results

Target host: jcufmpxjlgdfzefvulvz.supabase.co, matching the runtime configuration. Pinned repo CLI:2.114.0 through pnpm exec. One-off hosted SELECTs use the CLI Management API, authorized by Fred's current request; no db:* package script was changed or used. SQL is wrapped in BEGIN READ ONLY and ROLLBACK. No connection strings, keys or request bodies are recorded.

| Check | Result |
| --- | --- |
| Reviewed0037 SHA-256 | 82c9297ea08b4c16c3ba03bb2cc64eb222e67dd4276e9b4f7a8db22efe873450; matches runbook |
| PostgreSQL | 17.6 (major17) |
| pinned_at column | Absent |
| RLS | Enabled; FORCE ROW LEVEL SECURITY false, as observed |
| Owner-read policy | tutor_conversations_read; SELECT to authenticated; user_id=auth.uid() |
| service_role SELECT / UPDATE | Both true |
| Existing conversation count | 1 |
| Grants snapshot | anon/authenticated/postgres/service_role each have DELETE,INSERT,REFERENCES,SELECT,TRIGGER,TRUNCATE,UPDATE. Snapshot only; no grants changed. |
| 0035 function markers | All four conflict-rule/qualified-returning checks true |
| 0036 columns | generated_items.embedding vector(1024), embedded_at timestamptz; guided_lesson_steps.embedding vector(1024), as expected |

The target-table pre-checks pass. Full metadata snapshot for post-apply comparison is local/gitignored .tmp/0037-prechecks.json; it contains schema/grant metadata and the count only, never conversation content.

### Baseline evidence limit

Hosted supabase_migrations.schema_migrations contains one timestamped entry,20261010215929; it does not list numeric0001–0036 or0037. This differs from the historical expected33 numeric records in docs/runbooks/0034-apply.md:22. docs/runbooks/0036-apply.md:3 records manual SQL-editor application; current0035 function markers and0036 columns match. Treat that history table as an incomplete application record, not proof that the schema lacks those changes. No full hosted schema dump, drift inspection, repair, history marking or replay was performed. Full0001–0036 baseline parity is not certified by this scoped check; record manual baseline provenance before application. Do not rerun older SQL to fill the history table.

## Fred's apply/post-check step

Follow [0037-apply.md](../../../runbooks/0037-apply.md), preserving the unchanged reviewed file. Before applying, confirm the intended project and existing manual baseline. Apply the complete file once. Then compare column/RLS/policy/grants/service privileges against the saved snapshot; expect nullable timestamptz with no default, count1 unless concurrent use explains a difference, and pinned_count0 before new API pinning. Stop on an unexpected change. Recovery keeps the additive column and previous compatible API; no DROP or old-migration edit. Application/post-checks remain pending Fred.

## AUDIT REPORT

```text
Task / brief ID: Fred's model-state review and0037 pre-check request
Branch and worktree: main; .
Base revision:25c91418ead3cf6cc6ceb5bdad679b9a0a994ae8
Files changed: this evidence and acceptance/integration evidence only
REQ / WI IDs touched: AI-REQ-002; TUTOR-REQ-001/003; WI-01/21; FG-1/FG-3
Commands run and results: source trace; read-only AWS alias/config/secret and
  sanitized CloudWatch metadata; OpenRouter key/credits/endpoint GETs;
  pinned Supabase CLI read-only metadata/count/privilege queries; checksum.
  Target-table checks pass; baseline-history limitation recorded.
  Runtime suites not rerun: no runtime or test code changed.
Spec changes made: none; existing routing preserved
Evidence added: this report; gitignored pre-check snapshot; acceptance update
Anything not done, and why: hosted config, generation smoke, migration apply,
  post-checks and deployment remain Fred gates; no push or history repair
Risks or questions for planner: primary429; free fallback no endpoints;
  paid candidate not completion-tested; manual baseline provenance required
Secrets printed: none (confirmed)
```
