---
runbook: incident-response
applies_to: [dev-hosted, prod]
who_runs_it: Fred / ITO incident lead with service owners
time_needed: "[Fred to confirm]"
last_verified: "unverified; source review at 6e21eed on 2026-10-25, Lane R"
status: in-progress
---

# Runbook 12 — triage a production failure

## When to use it

Classify an outage or failed learning path before choosing recovery. WI-07 draft; a named human performs live checks and any operational action. Agents do not deploy, write hosted data, rotate keys or change infrastructure. Immediate incident owner, escalation contacts, severity criteria and response targets: [Fred to confirm].

## Before you start

Obtain read access to the intended AWS log groups and selected metadata, and have the Learn/database/provider owners available through [credential custody](../secrets.md). Record the user's observed time in Asia/Manila and convert to UTC for logs. Collect route/mode, HTTP status, duration and request identifier where available; no request text, full URLs with fragments, tokens, HAR exports, raw provider bodies or full configuration output.

## Steps

1. Incident lead records impact and scope: launch, one learning path, all tutor asks, roster/ingest, or the whole API. Check public health with bounded status-only output and inspect selected API `live` version/image and worker update metadata as in [07](deploy-backend.md). Health success does not establish providers or database work. Do not repeatedly submit learning writes as probes.
2. In CloudWatch Logs Insights select `/aws/lambda/kala-api`, set a narrow time range around the observation, and use the metadata-only queries below. Source declares a 30-day retention for API and worker groups. Keep identifiers privately; share sanitized aggregates and status/stage evidence only.

   ```text
   fields @timestamp, @requestId, @duration, @maxMemoryUsed, @memorySize
   | filter @type = "REPORT"
   | sort @timestamp desc
   | limit 100
   ```

   For runtime failure signals, do not display the matched message:

   ```text
   fields @timestamp, @requestId, @logStream
   | filter @message like /Task timed out after|Status: timeout|Runtime.ExitError|Runtime.OutOfMemory|Runtime.ImportModuleError/
   | display @timestamp, @requestId, @logStream
   | sort @timestamp desc
   | limit 100
   ```

3. For Tutor, distinguish the source's responses before attributing a cause:

   | Observation | What source supports | Next check |
   | --- | --- | --- |
   | 502 with the student-safe model-unavailable detail | `ModelUnavailableError` reached the API handler; embedding or chat dependency failed | Provider/configuration checks below. |
   | 503 with `code: tutor_timeout` | The 26-second handler budget expired before an answer | Stage timings and dependency latency. |
   | Generic 503 near the Lambda wall | Could be runtime/Gateway failure | Correlate actual REPORT/timeout and request time; status alone is insufficient. |
   | Answer returned but conversation not saved | Persistence can fail after an answer while response remains 200 | Check persistence warning and storage, without repeating the ask automatically. |

   These refer specifically to Tutor; launch can also return 502 for Learn/course-resolution failures.
4. Extract only Tutor timing aggregates; do not show full log messages:

   ```text
   filter @message like /tutor_timing/
   | parse @message /'mode': '(?<mode>[^']+)'/
   | parse @message /'outcome': '(?<outcome>[^']+)'/
   | parse @message /'handler_ms': (?<handlerMs>[0-9.]+)/
   | stats count(*) as requests, avg(handlerMs) as averageMs, max(handlerMs) as maximumMs by mode, outcome
   ```

   The parsing reflects the base source's Python-dict log format and has not been run against CloudWatch by Lane R. Deployed formatter/request-ID discovery and exact stage extraction: [Fred to confirm]. A missing field is a logging/parsing gap, not zero latency. A timed-out synchronous call may continue/resume in a warm Lambda; response return does not guarantee remote cancellation.
5. Confirm the deployed logging version; an older release can lack the timing and provider fields below. At refreshed source 6e21eed, merged Lane X diagnostics wrap budgeted embed/chat failures and emit JSON after `tutor_provider_error`: `stage`, `provider`, `model`, `http_status`, `request_id`, `error_code`. Stages are embed/chat; model/status can be null if unavailable, and TutorTimeout is deliberately excluded. The request ID is the budget identifier, not automatically a Lambda request-ID join. Have Fred extract only these metadata fields or aggregates after verifying the deployed formatter; never display raw @message/provider bodies. Code presence and mocked tests are not proof these new logs are deployed; integration evidence leaves deployment/acceptance at Fred gates.
6. The inspected Study/Tutor incident included primary HTTP 429. The recovery checklist is to check rate limits/credits, configure a paid fallback on a different provider (no :free), refresh Lambda instances and retest the hint under the maintainer. The secret setting was verified on 2026-10-25, and Fred confirms live alias v7 at 00:04 UTC followed the 00:01 UTC secret change, completing runtime refresh; successful live Hint/Explain/dock responses remain unconfirmed. This supersedes the initial unclassified-cause snapshot; recovery remains pending. Other failure events still require their own evidence. Ask the provider owners to check key validity, rotation/revocation, billing/credits, model availability and rate limits privately. Embedding happens before chat, so one embedding outage can break all tutor paths. Record provider/model **names**, HTTP status and stage only if actually observed. In the base fallback policy, transport failures and 404/408/429/500/502/503/504 can qualify for chat fallback; 401/403/402 do not. Fallback also depends on remaining budget and does not establish embedding recovery. A default free-model slug is not proof of the deployed fallback; the owner confirms effective configuration privately.
7. Check dependency-specific evidence without guessing fixes. For Learn 429, honor Retry-After and stop relaunch/refresh bursts; a past quota incident established that repeated calls can worsen the outage; stop the burst and wait for the reported limit window. For SQLSTATE 42702 on practice submit, review [0035](../../runbooks/0035-apply.md) and installed schema with the DB owner. Never edit/reapply immutable migrations or infer RLS correctness from service-role access. For ingest/worker failures use `/aws/lambda/kala-worker` with a narrow window and sanitized job/status metadata; exact current worker failure queries: [Fred to confirm].
8. Incident lead classifies cause and approves a concrete recovery: provider owner corrects key/credits/config if operational; deployment owner uses 07 for a compatible image recovery; DB owner reviews a forward fix. No deploy is needed merely to replenish provider credits. No automatic model switch, timeout increase or infrastructure change is authorized. Record required approvals and a named owner.
9. After recovery, perform relevant synthetic checks in [10](first-launch-smoke.md), including both tutor modes for a tutor incident. Record observed pass/fail, time and deployed revision; retain earlier failures. Update incident evidence through its owning lane. A later historical success never establishes current recovery.

## Verify it worked

Reproduce the affected path once safely under the named tester, confirm dependency health and record sustained observation window: [Fred to confirm]. INC-002 remains historical with live recovery unverified. APPROVAL-06 reports primary rate limiting; FG-1 live recovery remains unverified. The 37th migration is merged locally; Fred reported [0037](../../runbooks/0037-apply.md) applied with read-only checks passed on dev-hosted on 2026-10-25. Deployment/publication and live acceptance still require their own results; agents perform none of these hosted actions. This lane performed no live investigation.

## Undo / roll back

Undo only the incident lead's approved operational change using its service runbook; never revive compromised credentials or revert migrations. Preserve logs and sanitized timeline. Do not enable logging of bodies/PII to diagnose a provider. Recovery rollback owner/procedure per incident: [Fred to confirm].

## Troubleshooting and observability limits

| Gap | Consequence | Response |
| --- | --- | --- |
| Gateway access logging absent from Terraform | Cannot assume route-level access logs exist | [WI-18](../../work/handover-2026/work-items/WI-18-api-gateway-access-logs.md) is planned; request ITO decision separately. |
| Error alarm lacks source notification action | Alarm declaration does not prove paging | Confirm notification/escalation privately. |
| Diagnostics may not yet be deployed; nullable metadata | Local wrappers do not prove live stage/status availability | Confirm deployed version and ask Fred for metadata-only evidence; never infer missing fields. |
| Partial sanitizer | Logs/model-bound text must not be treated as anonymous | Do not copy payloads; see [AI-REQ-001](../../features/ai-platform/README.md). |

## History

| Date | Change to this runbook | Why |
| --- | --- | --- |
| 2026-10-25 | Draft privacy-safe triage and recovery gates | APPROVAL-05 rev 2, Lane R, WI-07. |
| 2026-10-25 | Replace stale logging/cause snapshot with merged diagnostics and FG-1/FG-3/FG-4 limits | APPROVAL-06 rev 2; source 6e21eed. |

## Historical sources

These links preserve provenance only. Required rules, commands and limits are stated above; do not read the records unless the task explicitly names them.

- [integration evidence](../../work/handover-2026/evidence/approval-06-integration.md)
- [historical queries](../../work/handover-2026/evidence/tutor-cloudwatch-queries.md)
- [quota incident](../../archive/bugs/blackboard-rest-quota-exhaustion.md)
- [INC-002](../../archive/incidents/INC-002-tutor-30s.md)
