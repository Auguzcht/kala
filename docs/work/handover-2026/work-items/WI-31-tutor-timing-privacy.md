---
id: WI-31
status: planned
owner: ITO; Fred executes FG-1b configuration and deployment
---

# Tutor diagnostics privacy, model swap and latency follow-ups

FG-L under APPROVAL-08 Amendment2 stopped on actual returned field user_id_prefix. No raw values are retained; raw data is local only, not retained. That original attempt produced no stage/model/status aggregates. The identifying field remains in the current timing logger and remains an ITO privacy finding.

A future named diagnostics lane must review/remove that field without changing provider routing, persistence or response semantics and prove logging allowlist/privacy with synthetic tests. T2's E1 scope does not authorize a logging change. Do not paste/query/share raw records to reproduce the finding. Fred subsequently delegated aggregate-only inspection that projects no individual log rows; that does not authorize raw-row access or fix the logger.

## FG-1b decision and evidence boundary — 2026-10-27

Decision by Fred: prepare a swap of the chat primary and fallback, before his APPROVAL-09 backend deployment. Execution belongs to Fred. Follow the [FG-1b procedure](../../../engineering/runbooks/fg1b-chat-model-swap.md) for exact keys, targets, consumers, entry-count checks, post-deploy aggregates and rollback.

Small-sample basis from the delegated aggregate incident investigation:

| Observation | Count | Limit |
| --- | --- | --- |
| Ling primary HTTP 429s | 4 | Three followed by Nex fallback; one by a different global fallback on another call path. This is not four confirmed Tutor requests. |
| Ling-primary Tutor requests reaching the chat deadline | 2 | No fallback recorded. A slow primary can exhaust the shared attempt budget. |
| Nex fallbacks completing successfully | 3 of 3 | Small incident sample, not a controlled benchmark or availability guarantee. |

No individual log row or identifying field is retained here. Raw data is local only, not retained. Later aggregate results supplement the original stopped attempt; they do not rewrite it as a successful raw-log review.

Paid-model cost note: Fred reported $2.63 remaining, not independently checked during this preparation. The provider account is replaced at institutional cutover. No billing/key/account change is part of FG-1b.

## Still planned for ITO

- A primary-attempt limit that reserves time for fallback, with a separately approved routing/deadline design and tests. The setting swap alone does not implement that limit.
- Streaming, with its own API/frontend/runtime review. This task enables no streaming.
- Remove identifying timing metadata and verify the logging allowlist without exposing historical raw records.

## Acceptance and delivery

Fred confirms the secret entry counts, performs deployment and asks 3–5 Tutor questions, one hint and one Explain more. Only afterward, run aggregate timing p50/max (`chat_ms`, `handler_ms`), fallback and 429 counts for the new-runtime test window. Rollback is the inverse swap followed by human redeployment.

Preparation only: no secret edit, deploy, hosted application write or new verification query executed for FG-1b. No performance improvement or completion is claimed. This work item stays planned for its remaining ITO work.


## Delegated execution and retained timeout trace

After the preparation report, Fred explicitly delegated the AWS CLI edit. Account identity and absence of both chat-name overrides on API latest/live were checked. The two approved target models were saved in `kala/app`, then read back and compared in memory. Entry count: **26 before, 27 after**; one of the two approved keys was absent and added. Every other entry was verified unchanged. No secret value was printed or saved. No Lambda refresh, deploy or live performance acceptance is inferred from that edit.

The retained pre-swap aggregate receipt at source `eb9409a8` covers 15 Tutor timing records: 10 primary successes, 3 fallback successes and 2 timeouts. Primary-success chat p50/max: 9,274.69 / 20,933.37 ms; handler: 10,985.11 / 22,099.07 ms. Fallback-success chat p50/max: 7,039.63 / 8,877.08 ms; handler: 7,798.78 / 9,501.36 ms. Timeout chat p50/max: 21,684.10 / 21,976.39 ms; handler: 23,022.83 / 23,023.07 ms, with retrieval max 923.36 ms. These counts indicate the model stage dominated those two requests; they do not prove post-swap performance. `chat_ms` may span both attempts. No raw records are retained in the repository.
