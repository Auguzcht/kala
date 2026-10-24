> Durable copy of accepted 2026-10-24 evidence at base `e9de105`, preserved under [APPROVAL-01](<../approval-01.md>). Findings describe that audit revision, not integrated fixes or live recovery. Repository links are adapted for archive moves; original source line labels are retained. Raw scratch manifests, scripts, dumps and JSON are intentionally not promoted.

# Tutor CloudWatch queries — historical, not executed

```text
BRIEF-01 Part A — maintainer-only CloudWatch investigation (not executed)
Use /aws/lambda/kala-api (Terraform lambda.tf:1-4), narrow the console time
range to Fred's observed request, and correlate request IDs. AWS log times
are UTC; Fred's timezone is Asia/Manila (UTC+08:00). No failure timestamp is
assumed. These queries intentionally do not display raw @message, request
bodies, user data, response bodies, tokens, or provider error bodies.

Q1. Duration/memory and invocation identifiers
fields @timestamp, @requestId, @duration, @billedDuration, @maxMemoryUsed, @memorySize, @logStream
| filter @type = "REPORT"
| sort @timestamp desc
| limit 100

Q2. Lambda timeout and fatal-runtime signals
fields @timestamp, @requestId, @logStream
| filter @message like /Task timed out after|Status: timeout|Runtime.ExitError|Runtime.OutOfMemory|signal: killed|Process exited before completing request|INIT_REPORT.*Status: error|Runtime.ImportModuleError/
| sort @timestamp desc
| limit 100
Interpretation: timeout confirms an invocation exhausted the execution budget,
not which upstream consumed it. Correlate its request ID and timestamp with
the observed tutor request before attributing it to /tutor/ask. Memory near
the limit is supporting evidence only; a fatal memory/runtime line is stronger.

Q3. Provider HTTP-status failures (no upstream body displayed)
filter @message like /OpenRouter chat request failed|OpenRouter embedding request failed|OpenAI embedding request failed|OpenRouter model id no longer exists/
| parse @message /(?<operation>OpenRouter chat request failed|OpenRouter embedding request failed|OpenAI embedding request failed|OpenRouter model id no longer exists)/
| parse @message /status=(?<providerStatus>[0-9]+)/
| stats count(*) as events by bin(5m), operation, providerStatus
An absent status for the retired-model line denotes the separately logged
404 branch; do not interpret a blank parsed value as success.

Q4. Transport failures, by operation and invocation
fields @timestamp, @requestId, @logStream
| filter @message like /OpenRouter request errored|OpenRouter embedding request errored|OpenAI embedding request errored|bedrock converse failed/
| parse @message /(?<operation>OpenRouter request errored|OpenRouter embedding request errored|OpenAI embedding request errored|bedrock converse failed)/
| display @timestamp, @requestId, @logStream, operation
| sort @timestamp desc
| limit 100
The matched operation confirms the dependency failed. It does not distinguish
DNS from read timeout without inspecting a sanitized exception type. HTTPX
ReadTimeout may have an empty message; the application does not log its class.

Q5. Fallback attempts (an attempt is not evidence of eventual success/failure)
fields @timestamp, @requestId, @logStream
| filter @message like /OpenRouter primary unavailable/
| parse @message /status=(?<primaryStatus>[^)]+)\)/
| display @timestamp, @requestId, @logStream, primaryStatus
| sort @timestamp desc
| limit 100
Transport failures use status=None. Compare Q2-Q4 for the SAME invocation;
multiple endpoints share these provider log strings.

Q6. Generic application exception counts (normally HTTP 500, not direct 502)
filter @message like /Error in ASGI application|Exception in ASGI application|httpx.HTTPStatusError|httpx.ReadTimeout|KeyError:|IndexError:|JSONDecodeError/
| stats count(*) as exception_lines by bin(5m)
This counts log lines, not distinct requests or causes. The tutor has no
stage timing logs; a DB-stall timeout may have only the Lambda timeout signal.

Q7. Follow one identified invocation without exposing full messages
fields @timestamp, @requestId, @duration, @maxMemoryUsed, @memorySize, @logStream
| filter @requestId = "REPLACE_WITH_OBSERVED_LAMBDA_REQUEST_ID"
| parse @message /(?<operation>OpenRouter primary unavailable|OpenRouter chat request failed|OpenRouter request errored|OpenRouter embedding request failed|OpenRouter embedding request errored|OpenAI embedding request failed|OpenAI embedding request errored|bedrock converse failed|Task timed out after|Runtime.ExitError|Runtime.OutOfMemory)/
| parse @message /status=(?<providerStatus>[0-9]+)/
| display @timestamp, @requestId, @duration, @maxMemoryUsed, @memorySize, operation, providerStatus, @logStream
| sort @timestamp asc
Application log discovery of @requestId depends on the deployed Lambda log
format. If it is missing, correlate a narrow time window within @logStream;
that is weaker evidence and must not be presented as an exact join.

Q8. OPTIONAL existing API Gateway access-log group — only if Fred already has one
fields @timestamp, requestId, routeKey, httpMethod, path, status, integrationStatus, integrationLatency
| filter (path = "/tutor/ask" or routeKey = "POST /tutor/ask" or routeKey = "ANY /{proxy+}")
| filter status >= 500
| sort @timestamp desc
| limit 100
Adjust field names to the existing log format, which is not established in
this repository. Terraform apigw.tf:27-32 does NOT configure access logging.
The proxy routeKey alone cannot isolate the tutor, so require path or Fred's
observed Gateway request ID when routeKey is ANY /{proxy+}. Do not infer
logs exist or propose an infrastructure change in this audit. Generic status
alone cannot establish Lambda timeout, crash, or a particular provider failure.

Confirmation strings already present in source:
- OpenRouter chat request failed (model=..., status=...)
- OpenRouter model id no longer exists (model=...)
- OpenRouter request errored (model=...)
- OpenRouter primary unavailable (model=..., status=...); retrying with fallback model=...
- OpenAI embedding request failed (model=..., status=...)
- OpenAI embedding request errored (model=...)
- OpenRouter embedding request failed / errored
- bedrock converse failed (model=...)
Platform strings depend on runtime/log format: Task timed out after ...;
REPORT ... Status: timeout; Runtime.ExitError; Runtime.OutOfMemory; signal: killed.
Do not copy the remainder of provider-body or traceback log lines into reports.
```
