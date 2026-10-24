# APPROVAL-05 Lane X: tutor provider investigation

Date: 2026-10-25 (Asia/Manila). Status: `done-awaiting-confirmation` for coordinator review; production recovery remains unverified. Work item: WI-01. Related requirements: TUTOR-REQ-001, AI-REQ-001 and AI-REQ-002. The initial investigation changed no production code. The subsequent approved diagnostics implementation and its separate validation are appended below.

## Finding and limits

**Confirmed failure mode:** three observed stateless `/tutor/ask` requests completed retrieval, received HTTP **429** from the primary OpenRouter chat model `inclusionai/ling-3.0-flash-vl`, attempted `nex-agi/nex-n2.5-mini:free`, and ended in `provider_error`. The fallback failure's status and reason are absent from the emitted application logs. **Underlying root cause remains unknown**: the evidence does not establish which account/provider limit caused the primary 429, or why the fallback failed. It does not establish exhausted credits, invalid keys, or a request-shape regression.

Fred reports an OpenRouter balance of **$2.63**. Do not characterize it as empty. The confirmed fallback is a `:free` variant; a nonzero account balance does not identify the reason for its failure. Changing the configured model remains Fred's decision. The initial submission made no provider requests or secret reads. A subsequent explicit authorization allowed one current-key metadata GET, documented below; no generation or embedding request was made.

One recorded tutor request timed out in chat and is consistent with the application's 503 `tutor_timeout` response. Its relationship to the reported console 503 is unconfirmed without a matching sanitized browser route/time/code. Five other tutor requests succeeded in the same query window. This is intermittent failure evidence, not proof that every live path currently fails or has recovered.

## Authority, base, and collection boundary

- Read the complete attachment APPROVAL-05 rev 2, AGENTS.md, docs/README.md, the relevant local CLAUDE.md guides, the tutor/AI platform/Study specs, and APPROVAL-01 through APPROVAL-04. Read the committed APPROVAL-05 amendment via `git show main:docs/work/handover-2026/approval-05.md` after coordinator notification. The practice-tests spec is absent at the audited base; no requirements were invented from that missing file.
- Branch: `codex/tutor-provider-502`; worktree: `/Users/fred/.codex/worktrees/9a3f/kala`; source base: `4f3ec29d3f827a1db92e90c4f395947d37744479`. `git merge-base --is-ancestor cab26de 4f3ec29` succeeded. The only diff from `cab26de` is the initiative README and deployment-evidence document. The already-created branch was selected after confirming its ref equals that base.
- Initial work was source-only. Fred subsequently authorized read-only CLI collection, now recorded in APPROVAL-05 section 6 on main at `0e7602e`. That supersedes the original Fred-only CloudWatch collection assignment. No production implementation or rebase onto a future spec commit is implied.
- Initial submission wrote only this evidence file and the uniquely named new investigation test file. The later approved implementation adds only the explicitly released paths and a second uniquely named new test file, listed below. No overlap with B/U/coordinator-owned files was needed. No pre-existing test, tutor.py, spec, migration, infrastructure, dev server, or other worktree was edited.
- CLI JSON was captured inside local Python subprocesses and parsed in memory. Raw messages were never printed or saved. Initial output was limited to timestamps, classified event/outcome/stage, opaque Lambda request IDs, model/provider names, HTTP status, timing scalars, counts, and selected non-secret Lambda metadata. The initial investigation read no secret payload. The subsequent key-status exception below did read the secret payload into process memory; this document does not claim otherwise. No dotenv read, hosted write, deploy, push, migration, key rotation, or live generation/embedding call occurred.

## Sanitized CloudWatch evidence

Read-only `aws logs start-query` / `get-query-results` against `/aws/lambda/kala-api`, region `ap-southeast-1`. Window: **2026-10-24 14:53:13–17:53:13 UTC**, or **2026-10-24 22:53:13–2026-10-25 01:53:13 Manila**. Query ID: `7ef20e96-1fd4-4397-8c6d-a4fdcfbee97f`. Query completed; 23 matching events, below the 100-row limit. The filter covered tutor timing, provider errors, OpenRouter, embeddings, chat requests, ModelUnavailable and status markers. The 23 events include nine tutor timing lines, six generic tutor provider error lines, three fallback warning lines, and five other matched timing events. No raw event text is reproduced here.

All nine tutor timing records below are stateless. Durations are milliseconds, rounded to two decimals. `retrieval_ms` combines embedding and the database match call; these are not separate embedding measurements. These request IDs are Lambda correlation IDs obtained from CloudWatch's `@requestId`, not upstream provider request IDs.

| Completion UTC, 2026-10-24 | Lambda request ID | Outcome | Retrieval ms | Chat ms | Handler ms | Role / fallback |
| --- | --- | --- | ---: | ---: | ---: | --- |
| 16:42:00.126 | `93404a51-6f60-4c15-bbf4-5579735303bf` | success | 4015.82 | 10718.69 | 14735.47 | chat / no |
| 16:42:22.444 | `4b0a5d13-94c2-4e44-87f2-82150ae8cb31` | provider_error | 561.79 | 1965.32 | 2528.97 | chat_fallback / yes |
| 16:44:40.224 | `467c2a85-f413-4d90-902d-c8ac6ebee637` | success | 1425.39 | 6788.83 | 8215.71 | chat / no |
| 16:50:27.384 | `69234076-37d9-42f5-914c-3eb646fad52b` | success | 768.87 | 7820.87 | 8591.59 | chat / no |
| 16:51:03.112 | `3c5a30a0-cb92-4760-8b24-4ff12d18ceb4` | success | 686.01 | 12551.88 | 13239.46 | chat / no |
| 16:52:42.363 | `70cc7d3e-8198-407a-a159-dbd1a80c9dca` | success | 465.07 | 7305.37 | 7771.51 | chat / no |
| 16:53:24.568 | `e39f8af6-904a-4706-b181-76636a6430c5` | timeout | 345.17 | 22677.07 | 23023.55 | chat / no |
| 17:39:23.621 | `5de14dd3-bb75-47d2-845e-4acbcc09277c` | provider_error | 2110.59 | 2407.09 | 4519.90 | chat_fallback / yes |
| 17:40:15.079 | `ce4d2e46-76b3-4ec1-8d31-b46b6851b664` | provider_error | 632.25 | 1868.53 | 2502.19 | chat_fallback / yes |

For each `provider_error` row, the same Lambda request ID has a fallback warning recording primary model `inclusionai/ling-3.0-flash-vl`, **status 429**, and fallback model `nex-agi/nex-n2.5-mini:free`, plus two generic provider failure events. The timings, provider role, and source flow together show retrieval completed and the second chat attempt failed. They do **not** reveal the second attempt's HTTP status. For these three failures an embedding outage is excluded as the failing stage; this does not exclude an embedding failure in other requests outside the observed set.

Read-only `aws lambda get-function-configuration --qualifier live` used an explicit JMESPath projection, never complete configuration or Environment output. The selected metadata reports API **version 6**, **timeout 30 seconds**, and no direct Lambda environment overrides for AI_PROVIDER, EMBED_PROVIDER, OPENROUTER_MODEL_CHAT, OPENROUTER_MODEL_CHAT_FALLBACK, OPENROUTER_EMBED_MODEL, or OPENAI_EMBED_MODEL. Null here means no direct override, **not** an unset effective setting. Provider/model settings in the secret bundle were not inspected; the later exception extracted only the credential needed for key metadata. Logs independently establish the primary and fallback used in the three failures. The CLI is available via the main checkout's existing AWS executable; no CLI installation or setup script was run. An initial invocation rejected the CLI-v2-only pager flag; retry without it succeeded and no raw CLI error was emitted.

## Subsequent authorized current-key metadata check

After initial submission `a309ddd`, Fred's delegated authorization expressly extended the earlier no-secret-read boundary: read the current OpenRouter credential from `kala/app` into process memory solely for the official current-key metadata endpoint. Before the request, the [official OpenRouter current-key documentation](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-api-key) was checked and confirmed **GET https://openrouter.ai/api/v1/key**, using bearer authentication. This is an account/key metadata endpoint, not a model completion or embedding endpoint.

Collection date: **2026-10-25 Manila**, after the initial CloudWatch collection and before 01:59:45 Manila. `aws secretsmanager get-secret-value` ran with captured subprocess stdout/stderr; its payload was decoded in memory, and only OPENROUTER_API_KEY was extracted for the fixed HTTPS destination. The request used no proxy, disabled redirects, retained TLS verification and had a 15-second timeout. No raw response, key label/hash, headers, credential, or exception text was emitted or persisted. No provider/model configuration fields were extracted from the bundle. The process exited after outputting only allowlisted scalar metadata.

| Allowlisted metadata | Observed value |
| --- | ---: |
| Credential read available | true |
| Metadata endpoint HTTP status | **200** |
| is_free_tier | false |
| Has per-key spend limit | false |
| Has expiry | false |
| Disabled field available in response | false |
| Free-model daily limit | 50 |
| Free-model daily remaining | **50** |
| Free-model daily used | **0** |
| Key usage | 2.155158467 |
| Key daily usage | 0.001704348 |
| Key weekly usage | 0.001704348 |
| Key monthly usage | 1.772073308 |

The current bundle credential authenticated successfully to this metadata endpoint. No disabled flag was returned, so do not report a returned `disabled=false`. No per-key spend limit or expiry was configured according to this response. The free-model allowance was not exhausted at collection time. This endpoint's key usage is not an account credit balance, and the check does not independently verify Fred's $2.63 balance.

This snapshot does **not** prove model capacity, successful generation, the fallback's earlier failure status, historical quota state, or that a warm v6 Lambda uses the same current key: settings/secret loading is cached. No key identity comparison was emitted, and no rotation history was checked. Primary HTTP 429 remains confirmed from earlier logs; the reason for it and the fallback failure remains unknown. No recovery claim, config/model change or operational action follows from this metadata check alone.

## Exact source error mapping and fallback policy

Source anchors at the initial audited revision `4f3ec29`: [bedrock.py](../../../../services/api/app/ai/bedrock.py) (`converse` at 68, `_can_fallback` at 149, embedding dispatch at 159, Bedrock chat at 195, Bedrock embedding at 222, OpenRouter chat at 266, OpenRouter embedding at 480, OpenAI embedding at 589); [errors.py](../../../../services/api/app/ai/errors.py); [main.py](../../../../services/api/app/main.py) (handlers at 52 and 60). Line numbers here describe that initial snapshot; later diagnostics shift the provider-file lines.

| Provider stage | Conversion to ModelUnavailableError | Application response / fallback |
| --- | --- | --- |
| OpenRouter chat | Every caught `httpx.HTTPStatusError`; original HTTP status retained. This is a predicate over every non-2xx response rejected by `raise_for_status`, including redirects, not a finite allowlist of error statuses. Any other caught `httpx.HTTPError` gets `status_code=None`. HTTP 404 also sets `model_not_found=True`. | Unrecovered typed error becomes 502. The outer `converse` permits one fallback only for the exact statuses listed below, with budget/config guards. |
| OpenRouter embedding | Same HTTP/transport conversion, status retention, and 404 flag as above. | 502, **no embedding fallback** for any status. A chat fallback never runs when retrieval raises first. |
| OpenAI embedding | Same HTTP/transport conversion and 404 flag. | 502, **no embedding fallback** for any status. |
| Bedrock chat | Every exception raised inside the runtime/client/converse try block except `TutorTimeout` becomes ModelUnavailableError. No HTTP metadata is extracted; status remains None. | 502; no application model fallback in the Bedrock dispatch branch. TutorTimeout is re-raised. Parsing after that try block is outside the conversion. |
| Bedrock embedding | No exception conversion in `_bedrock_embed`. | SDK/parse errors propagate; they do not automatically use the ModelUnavailableError handler. No application embedding fallback. |

The three HTTP-backed paths do not wrap arbitrary JSON decoding, response-shape, or vector-processing errors as ModelUnavailableError. A 2xx response with an invalid body is not covered by the HTTP-error conversion. HTTPX timeouts are converted to ModelUnavailableError unless the tutor's independent elapsed-time guard wins first.

| Original failure status | OpenRouter chat model fallback eligible? | Embedding fallback |
| --- | --- | --- |
| None (transport error, including HTTPX timeout) | yes | never |
| 404, 408, 429, 500, 502, 503, 504 | yes, exactly these seven numeric statuses | never |
| 401, 402, 403 | **no**; same student-safe 502 after conversion | never |
| Every other status, including 400, 409, 422, other redirects, 501, 529 | no | never |

Eligibility is not a guarantee of a retry. The fallback must exist and differ from the primary. Tutor fallback is skipped below six seconds remaining. Only 429 and 503 use a 1.5-second backoff; that sleep must still leave six seconds. One fallback attempt is made, without another fallback loop. At or below the three-second response reserve, an OpenRouter primary ModelUnavailableError becomes TutorTimeout before status/config checks, even for normally non-retriable failures. An eligible retry skipped for insufficient budget also becomes TutorTimeout. These cases return application 503, not provider status passthrough.

Separate from model fallback, OpenRouter chat has one capability downgrade: a structured request receiving 404 with a recognized unsupported-parameter message can retry the **same model** without `response_format`. Tutor prose requests do not pass `response_format`, so this branch does not apply to the five reported surfaces. Provider routing within a single OpenRouter request also sends `allow_fallbacks=True` when an order preference exists; this is distinct from Kala's second-model retry.

## Logging defect

At the initial audited revision, Lane T's budgeted paths avoid logging raw provider error bodies, but discard diagnosis fields. This is the confirmed observability defect addressed by the subsequently approved implementation below. The table records pre-fix behavior.

| Emitted application event | Provider | Model | HTTP status | Failure stage | Explicit application request_id |
| --- | --- | --- | --- | --- | --- |
| Budgeted OpenRouter chat / OpenRouter embedding / OpenAI embedding failure | absent | absent | absent | `provider_call`, not embed/chat | absent |
| Budgeted Bedrock chat failure | bedrock | absent | absent | chat | absent |
| OpenRouter fallback warning | OpenRouter in fixed event name | primary and fallback | primary only | implicit in source branch | absent |
| tutor_timing | role only, not provider | absent | absent | combined stage durations | absent |
| main ModelUnavailableError handler | emits no diagnostic event | absent | absent | absent | absent |

`ModelUnavailableError` already carries provider/model/status in memory; `stage` and correlation metadata are not attributes of that exception. CloudWatch's `@requestId` supplied correlation in this collection despite its absence from application event fields. Upstream provider request IDs are not recorded. Non-budgeted HTTP failures still log response body prefixes and transport exception strings; no such raw bodies were collected into this evidence or output. A future fix must not restore that unsafe logging to tutor.

## Source defaults and configuration limits

Source: [config.py](../../../../services/api/app/config.py) at 62, 147–174 and 185–236; [router.py](../../../../services/api/app/ai/router.py) at 66–80 and 83–141.

| Source setting | Declared default / behavior |
| --- | --- |
| AI_PROVIDER | `bedrock`; actual observed failing chat path is OpenRouter |
| OPENROUTER_MODEL_CHAT | `inclusionai/ling-3.0-flash-vl` |
| OPENROUTER_MODEL_CHAT_FALLBACK | `nex-agi/nex-n2.5-mini:free`; also confirmed in live fallback warnings |
| OPENROUTER_MODEL_REASONING_FALLBACK | `nex-agi/nex-n2.5-mini:free` |
| OPENROUTER_MODEL_FALLBACK (global) | `deepseek/deepseek-v4.1-flash:floor`; chat uses its role-specific nonempty fallback first |
| EMBED_PROVIDER | empty string; uses AI_PROVIDER when empty |
| OPENROUTER_EMBED_MODEL | `nvidia/nemotron-3-embed-1b:free` |
| OPENAI_EMBED_MODEL | `text-embedding-3-small` |
| OPENROUTER_PROVIDER_ORDER | `Relace`, used as a preference with provider fallthrough |

A nearby config comment says EMBED_PROVIDER defaults to OpenAI; the actual Field default is empty. With OpenRouter selected and no embedding override in either settings source, dispatch would use the OpenRouter embedding model. That contradiction is a static finding, not proof of live embedding configuration. Existing benchmark, retirement, and availability comments are historical source claims; this lane did not verify current provider availability or change any model.

## Preliminary frontend request comparison

Read-only comparison at base `4f3ec29`, **preliminary until provider-path recovery**. All rows POST JSON through [askTutor](../../../../apps/web/src/features/tutor/api/tutor.api.ts) at 18 and [useTutorAsk](../../../../apps/web/src/features/tutor/hooks/use-tutor.ts) at 29. Every body has `course_id`, `question`, `style`. Only persistent Tutor supplies `conversation_id`. No row supplies institution, role, skill, history, or attachment fields in the ask body. The server retrieves history and attachments for an owned conversation. Files use a separate upload route.

| Surface / source | question field | style | conversation_id |
| --- | --- | --- | --- |
| Study hint, FlashcardDeck.tsx:652 | Recall-card hint instruction plus quoted card prompt; asks not to reveal the answer | eli5 | omitted |
| Study Explain more, FlashcardDeck.tsx:665 | `Explain this in more detail: ` plus card prompt; no back/answer supplied | detail | omitted |
| Study dock, FlashcardDeck.tsx:675 | Flashcard instruction, prompt, back label or unavailable marker, shown side, student's current question; separated by blank lines | default (hook supplies it) | omitted |
| Review missed dock | **Same FlashcardDeck handler as Study dock**; card prompt/back derived from saved practice results for the exact missed item IDs | default | omitted |
| Test dock, PracticePanel.tsx:603 | Review instruction, item prompt, options, selected label, correct label, correctness, student's current question | default | omitted |
| Tutor chat, TutorChat.tsx:220 | Current question only; first creates a conversation when needed | default unless a chip requests another supported style | present, resolved conversation ID |
| Lesson check hint, LessonChat.tsx:210 | Check-scoped instruction and question, current grading state, hint instruction | eli5 | omitted |
| Lesson check Explain more | Same check context with answer-explanation instruction | default | omitted |
| Lesson check follow-up, LessonChat.tsx:254 | Same check context plus current question | default | omitted |
| Lesson dock follow-up, LessonChat.tsx:274 | Current question only | default | omitted |
| Exported useAskTutor / useAskInConversation hooks | Plain current question; conversation-aware hook supplies its argument | default or requested style | omitted / present respectively; no current component call sites found for these hooks |

Review missed reaches FlashcardDeck through [SkillHub](../../../../apps/web/src/features/skill-hub/components/SkillHub.tsx) at 192 and [the skill route](../../../../apps/web/src/routes/course/skill.$skillId.tsx) at 101. FlashcardDeck at 125–148 maps saved question results to prompt, correct answer text, and stored explanation. There is no separate Review-missed `/tutor/ask` serializer.

The endpoint always performs RAG before chat: [tutor.py](../../../../services/api/app/routers/tutor.py) at 379–424 and [rag.py](../../../../services/api/app/ai/rag.py) at 12. Every surface selects the same `chat` role and 2048 answer-token ceiling. `eli5` and `detail` append different system text, not different models. Stateless follow-ups render local turns but send no prior turn history. Different prompt sizes or the detail instruction can affect latency, but do not explain the observed upstream 429 by themselves.

The sanitizer boundary remains partial: email patterns and explicit `name:` / `姓名:` patterns only. Current question, RAG query, built course/attachment context, system text, and persistent history receive sanitized copies before providers; stored originals remain unchanged. This source comparison does not prove sanitizer correctness for every UI shape. The requested per-shape mocked payload tests remain deferred until recovery under APPROVAL-05 section 1.5.

## Stored Test explanation versus live help; possible 503 route

Test's submitted-answer explanation is supplied by the `submit_practice` database RPC and returned as `review_result['explanation']` in [practice.py](../../../../services/api/app/routers/practice.py) at 843–887. Saved results also expose stored explanations. Migration 0035 at 202 and 290–300 shows generated-item explanation copied into the saved answer result. This is read-only SQL inspection; no SQL was authored or executed. Displaying Test feedback and Review-missed card backs does not make an inline provider call. Asking a dock follow-up does. Comparing initial Test feedback speed with live Study Explain more mixes these two different paths.

Two explicit application 503 paths exist in the audited API source:

1. `POST /tutor/ask`: TutorTimeout maps in main.py at 52 to `{detail: 'The tutor took too long to respond. Please try again.', code: 'tutor_timeout'}`. It can arise from a stage deadline or skipped fallback. The observed timing event at 16:53:24.568 UTC shows `outcome=timeout`, `provider_role=chat`, no fallback, and about 23 seconds total; that fits the 26-second budget minus the three-second reserve. Only this ask handler emits tutor_timing, so its route is inferable. A source-mapped upstream **503** that survives as ModelUnavailableError becomes application **502**, not application 503.
2. `POST /practice/{course_id}/set`: insufficient queued jobs returns 503 with `practice set could not be queued; please try again` (practice.py at 214 and 317).

The browser entry could also be an infrastructure response. No route/status access-log evidence was obtained tying the console observation to one of these. Safe browser method, path without query, timestamp and `code` are needed to identify it conclusively; no full HAR or tokens are needed.

The available tutor timing data show successful live requests taking roughly 7.8–14.7 seconds and the timeout spending 22.7 seconds in chat. **No row records UI action or style**, so none can honestly be labelled the Explain-more latency measurement. After recovery, correlate one manually triggered Explain-more action with a sanitized timestamp/request ID, record retrieval/chat/handler stages, and then assess the smallest non-infrastructure improvement. A shorter card-explanation instruction is a candidate for a later spec-reviewed comparison, not a cause-backed fix or promised latency reduction. No streaming work is proposed.

## Evidence still needed and proposed next gate

CloudWatch CLI collection is complete for the authorized window; Fred does not need to repeat that query. Remaining account evidence, supplied as safe scalar metadata rather than screenshots of bodies/keys:

- OpenRouter Activity around **00:42:20–00:42:23**, **01:39:22–01:39:24**, and **01:40:13–01:40:16 Manila, 2026-10-25**: primary and fallback model, selected upstream provider, each HTTP status, concise error category (rate limit, quota, billing, auth, capacity, model unavailable), and upstream request ID if present. The fallback status is the critical missing value. The Lambda IDs above may not be searchable in OpenRouter; use times/model names for correlation.
- Whether either provider key was rotated, revoked, deleted or disabled on Oct 25, with approximate time and deployed update confirmation, **never key material**. The current bundle key's authentication and per-key quota snapshot is now recorded above; historical status and the credentials used by warm Lambda invocations remain unverified. The reported $2.63 balance is already recorded.
- Only if failures implicate embedding or that path still fails after chat recovery: OpenAI key enabled/disabled and billing/quota health. These three observed requests completed embedding, so an OpenAI billing incident is not established here.
- Safe browser route/method/time and optional `code` for the unexplained 503, and later a fresh successful click-through of Study hint, Explain more, Study/Review-missed/Test docks and persistent Tutor. This lane makes no new live calls.

If evidence confirms key/account billing configuration, the recovery is operational: Fred updates the setting in `kala/app` or corrects account funding/quota as indicated, with no application-code deploy required; this lane neither performs nor claims that recovery. The observed 429 alone does not justify rotation or adding credit. A fallback-model change is a separate explicit config decision for Fred.

Initial proposal, subsequently accepted in the coordinator's spec commit: **AI-REQ-002: Provider failure diagnostics for tutor**, status `planned` at spec release:

> Every failed tutor embedding/chat provider attempt records an error event with stage (`embed` or `chat`), provider, attempted model, HTTP status (nullable for transport failures), and opaque request_id. Log neither request/response bodies, credentials, tokens nor identity data. Preserve the generic student-safe 502 contract for 401, 402 and 403; classify them distinctly at error level without adding fallback. Keep the current fallback allowlist and TUTOR-REQ-001 deadline behavior. Correlate primary and fallback attempts without losing the fallback failure's metadata.

Suggested acceptance: mocked primary/fallback and embed failures retain all fields for 401/402/403/429/503 and transport exceptions; no sensitive marker reaches emitted events; 401/402/403 do not retry; 503 tutor_timeout and successful-answer persistence behavior stay unchanged; default non-tutor behavior remains unchanged. Suggested AI-platform change-log row: `2026-10-25 | Specify privacy-safe tutor provider failure diagnostics before implementation | APPROVAL-05 rev 2 and confirmed CLI evidence | AI-REQ-002; TUTOR-REQ-001 compatibility`.

Coordinator subsequently approved this narrow logging/error-handling direction and then released implementation against spec commit `11d69de`. The lane rebased onto that named commit before editing production code. Fallback policy, model selection, timeouts, and retry behavior remain unchanged. Coordinator owns both specs; this lane did not edit them. No new Tutor REQ number is claimed, avoiding B/U's allocations.

Coordinator granted the additional path **services/api/app/ai/request_budget.py**, only to initialize one opaque random UUID per RequestBudget and expose it to existing budgeted provider calls. This gives embedding, primary chat and fallback chat the same internal request_id without student data, client-supplied headers, a middleware change, or editing tutor.py. CloudWatch's existing @requestId continues to link those events to the Lambda invocation; the generated ID is an internal correlation ID, not an upstream provider ID. Tests assert stable IDs across stages/attempts and distinct IDs across requests. Non-budgeted calls retain existing behavior. No errors.py or other helper-path grant was needed. tutor.py remains off limits to X.

## Offline verification

New test file: [test_provider_investigation_approval05_lane_x.py](../../../../services/api/tests/test_provider_investigation_approval05_lane_x.py). It exercises HTTP/transport metadata for OpenRouter chat and both HTTP embedding providers, exact fallback status eligibility (including all numeric statuses 100–599), role fallback/backoff behavior, and HTTP-level `/tutor/ask` 502-versus-503 mapping at retrieval/chat failures. All outbound boundaries are mocked. Existing committed shared isolation disables dotenv and IPv4/IPv6/DNS; no scratch isolation or existing test edits.

- Initial focused run before adding the three transport variants: `cd services/api && uv run pytest tests/test_provider_investigation_approval05_lane_x.py tests/test_bedrock_provider_dispatch.py tests/test_request_budget.py tests/test_tutor.py`: **121 passed**, two dependency deprecation warnings.
- `uv run ruff check --fix tests/test_provider_investigation_approval05_lane_x.py`: fixed only new-file import spacing; a prior dict-construction lint finding was corrected in that file. Final `uv run ruff check tests/test_provider_investigation_approval05_lane_x.py`: **passed**.
- Final full API suite with all 69 new test cases: `cd services/api && uv run pytest`: **500 passed**, 30 dependency deprecation warnings, 27.82 seconds.
- Final new-file whitespace, link-target and scope review is performed before the investigation commit; only the two owned files are included.
- Worker, web lint/typecheck/build and browser checks were not run for the initial investigation: no production/web/worker code changed in that submission. Later diagnostics verification is recorded below. No integration, merge, push or deploy is claimed.

## Approved AI-REQ-002 diagnostics implementation

Implementation base: coordinator spec commit **11d69de**, containing the accepted AI-REQ-002 and WI-01 follow-up. Both investigation commits and the key-status evidence were preserved through the required rebase. Ownership release explicitly grants bedrock.py, optional router.py/main.py changes only as needed, and request_budget.py for correlation. No router.py or main.py edit proved necessary.

- **request_budget.py:** initialize one internal UUIDv4 per budget. The monotonic start, deadline, reserve, timeout calculations, fallback flags, cancellation and persistence semantics are unchanged.
- **bedrock.py:** observe failures at the five provider leaf functions (OpenRouter chat, both HTTP embeddings, Bedrock chat and embedding) only when a budget is supplied. Emit an ERROR event with JSON metadata: `stage`, `provider`, `model`, `http_status`, `request_id`, and a fixed `error_code`. HTTP 401/402/403 classify respectively as `unauthorized`, `payment_required`, and `forbidden`. Unavailable status is JSON null. Known Bedrock SDK status metadata can be extracted safely without rendering SDK messages.
- The observer re-raises the existing exception. Previously converted errors stay converted; previously unwrapped SDK, JSON and response-shape errors stay unwrapped. TutorTimeout bypasses provider-error diagnostics and preserves the existing deadline path. No student response changes or additional retries are introduced.
- The fallback's own leaf call emits its attempted model and failure status under the same budget ID as the primary. Old generic budgeted error lines are replaced. Non-budgeted calls bypass the observer and retain their existing behavior, including their existing logging; broader logging cleanup is outside this approved scope.
- Added [test_provider_diagnostics_approval05_lane_x.py](../../../../services/api/tests/test_provider_diagnostics_approval05_lane_x.py) and extended only X's own new investigation test. These cover sensitive-marker exclusion from body/exception/prompt, HTTP and transport fields, distinct auth/payment categories, primary/fallback correlation and statuses, stable/different UUIDs, SDK status metadata, preserved unwrapped exceptions, preserved TutorTimeout and non-budgeted diagnostics. Existing fallback/deadline/persistence regressions are unchanged.

Validation after implementation:

- `cd services/api && uv run ruff check app/ai/bedrock.py app/ai/request_budget.py tests/test_provider_investigation_approval05_lane_x.py tests/test_provider_diagnostics_approval05_lane_x.py`: **passed**.
- Focused provider, request-budget and tutor suite including both new X files: **139 passed**, two dependency deprecation warnings, 26.70 seconds.
- `cd services/api && uv run pytest`: **515 passed**, 30 dependency deprecation warnings, 27.66 seconds. This includes all 431 pre-existing cases plus 69 X investigation cases and 15 X diagnostics cases.
- `git diff --check`: **passed**. Evidence link-target check: **14 local targets valid**. Final scope review includes exactly this evidence file, bedrock.py, request_budget.py, and the two new X test files. The production diff changes no fallback decision, model setting, HTTP client timeout, retry configuration, or application error handler.
- Web, worker, browser, hosted generation and deployment checks are not run: the change is confined to API diagnostic logging/correlation, and live generation calls remain unauthorized. Logging verification does not demonstrate provider recovery.

Secrets printed: **none**. Raw production/provider messages emitted or persisted: **none**.
