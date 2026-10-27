---
runbook: fg1b-chat-model-swap
applies_to: [dev-hosted]
who_runs_it: Fred
time_needed: "5–10 minutes for the setting edit, plus deployment and live sampling"
last_verified: "source reviewed at eb9409a8 on 2026-10-27; execution pending"
status: planned
---

# FG-1b: swap the chat primary and fallback

## Scope and decision

Fred approved preparation on 2026-10-27. Fred edits the existing `kala/app` secret in `ap-southeast-1` before the APPROVAL-09 backend deployment. Codex prepares this procedure only. No secret payload was retrieved for this preparation. This is an application-setting change through Secrets Manager, not KMS key management or a Terraform apply.

The small sample motivating the decision is four primary HTTP 429s and two chat deadline hits for Ling, while three of three observed Nex fallbacks succeeded. It is not a controlled benchmark or a model-availability verdict. Nex is paid, the balance is low (Fred reported $2.63), and the provider account will be replaced at institutional cutover. Current balance was not independently queried. Cost and latency require live acceptance.

## Configuration inventory and consumers

Names and owners are catalogued in [secrets.md](../secrets.md). The exact chat setting names are `OPENROUTER_MODEL_CHAT` and `OPENROUTER_MODEL_CHAT_FALLBACK`. Both are API settings. This confirms the supported keys, not their current presence in the hosted bundle.

| Feature | Reads these two chat settings? | Source |
| --- | --- | --- |
| Tutor, including saved conversations | Yes, via `POST /tutor/ask`, `task="chat"` | [tutor.py](../../../services/api/app/routers/tutor.py), [model router](../../../services/api/app/ai/router.py) |
| Study hint, Explain more and follow-up chat | Yes, through the same stateless Tutor endpoint | [FlashcardDeck.tsx](../../../apps/web/src/features/flashcards/components/FlashcardDeck.tsx), [use-tutor.ts](../../../apps/web/src/features/tutor/hooks/use-tutor.ts) |
| Test follow-up chat | Yes, through the same endpoint | [PracticePanel.tsx](../../../apps/web/src/features/practice/components/PracticePanel.tsx) |
| Guided lesson hints and step/check follow-up chat | Yes, through the same endpoint | [LessonChat.tsx](../../../apps/web/src/features/lessons/components/LessonChat.tsx) |
| Guided lesson outline and teaching content | No. Outline uses `OPENROUTER_MODEL_REASONING` and `OPENROUTER_MODEL_REASONING_FALLBACK`. Step prose uses reasoning primary with `OPENROUTER_MODEL_FALLBACK` as the global fallback. | [learn/lessons.py](../../../services/api/app/learn/lessons.py) |
| Worker jobs, including lesson-check generation and bank assignment | No. Worker settings do not declare either chat key. Item/tagging/bank/embedding settings are separate. | [worker configuration](../../../services/worker/app/config.py), [worker handler](../../../services/worker/app/handler.py) |

The swap does not fix inline lesson-content generation. It does not change a primary-attempt limit, the request deadline, retries, routing code or streaming.

## Fred's steps before deployment

1. In the existing AWS account, region `ap-southeast-1`, open Secrets Manager and the existing `kala/app` secret. Use the private value-editing flow. Do not share its JSON, screenshots or credentials.
2. Privately record the entry count and whether the two named keys already exist. Confirm Lambda environment variables do not override those names. Environment variables take precedence over the secret. An override needs separate review; this procedure does not change Lambda settings.
3. Set only these two entries:

   | Key | Approved target model identifier |
   | --- | --- |
   | `OPENROUTER_MODEL_CHAT` | `nex-agi/nex-n2.5-mini` |
   | `OPENROUTER_MODEL_CHAT_FALLBACK` | `inclusionai/ling-3.0-flash-vl` |

   Model identifiers are public configuration, not credentials. Every other entry stays unchanged. If a named key is absent, add only that named key and account for that addition in the entry count.
4. Privately compare every other entry before saving, then confirm the entry count after saving. It must stay equal if both keys existed, or increase by exactly the number of the two named keys added. Keep credential values out of reports.
5. Do this **before** the approved APPROVAL-09 `make deploy`. From the final reviewed source revision Fred runs that deployment using [deploy-backend.md](deploy-backend.md). A secret save alone does not refresh cached settings in warm Lambda environments. Verify the new API version, `live` alias, image/source mapping, worker completion and health under that runbook. Codex does not deploy or advance an alias.

## Verification after Fred deploys

Fred asks three to five Tutor questions, requests one Study hint and one Explain more, and records only the sample counts, success/timeout outcomes and approximate test window. These normal student actions can write learning/application rows. They are human acceptance, not an agent read-only probe.

After Fred confirms the new runtime and sample window, Codex runs aggregate-only CloudWatch Logs Insights queries on the discovered API Lambda group (previously `/aws/lambda/kala-api`). Use the post-deployment test window, allow for log arrival, and record its bounds. Do not fetch individual messages or project raw logs, correlation IDs, names, user identifiers or bodies. The retained `user_id_prefix` logging finding remains open in WI-31; aggregate projection does not remove it from the underlying logs.

Timing aggregates (milliseconds):

```text
filter @message like /tutor_timing/
| stats count(*) as requests,
    count(chat_ms) as chat_samples, count(handler_ms) as handler_samples,
    pct(chat_ms, 50) as chat_p50_ms, max(chat_ms) as chat_max_ms,
    pct(handler_ms, 50) as handler_p50_ms, max(handler_ms) as handler_max_ms
```

Fallback counts, including timeout/error outcomes separately:

```text
filter @message like /tutor_timing/
| parse @message /['"]outcome['"]:\s*['"](?<outcome_tag>[a-z_]+)['"]/
| parse @message /['"]fallback_used['"]:\s*(?<fallback_tag>True|False|true|false)/
| stats count(*) as requests by fallback_tag, outcome_tag
```

Primary 429 count after the swap (one diagnostic family only, avoiding duplicate counts from fallback warnings):

```text
filter @message like /tutor_provider_error/
| parse @message /"stage":\s*"(?<stage_tag>[^"]+)"/
| parse @message /"model":\s*"(?<model_tag>[^"]+)"/
| parse @message /"http_status":\s*(?<status_tag>[0-9]+)/
| filter stage_tag = "chat" and model_tag = "nex-agi/nex-n2.5-mini" and status_tag = "429"
| stats count(*) as primary_429_count
```

Report request counts, p50/max for `chat_ms` and `handler_ms`, fallback count, primary 429 count and success/timeout counts. `chat_ms` spans the chat stage, potentially both attempts; it is not primary-call latency alone. Report denominators for missing timing fields. These queries aggregate logged API chat requests, including hints/Explain, not just saved Tutor conversations. Background/other user traffic can enter the window, so do not assert an exact match to Fred's sample. Missing timing events, a Lambda kill or an empty result are not proof of zero failures. Normalize an empty 429 result to zero only after log arrival and successful query completion are confirmed.

Queries are prepared, not executed by this task. No post-swap improvement or acceptance is claimed. Compare with the small pre-swap sample in WI-31 without treating it as a performance guarantee.

## Rollback by Fred

If live acceptance fails, Fred sets `OPENROUTER_MODEL_CHAT` back to `inclusionai/ling-3.0-flash-vl` and `OPENROUTER_MODEL_CHAT_FALLBACK` back to `nex-agi/nex-n2.5-mini`. All other entries remain unchanged. Confirm entry counts and repeat the approved backend deployment so the restored settings reach a new runtime. Then repeat the same small live sample and aggregate checks. This does not revert the APPROVAL-09 application source.

## Outstanding work

WI-31 keeps the primary-attempt limit, streaming and removal of identifying timing metadata with ITO. The slow-primary path can still consume the shared budget before fallback becomes possible. WI-14 separately owns lesson-content request deadlines/background generation.
