# APPROVAL-04: bounded test cleanup and repeated verification

Decision source: Fred's explicit approval in the coordinating chat, 2026-10-25.
This supplements [APPROVAL-03](approval-03.md).

1. Apply the prepared `proposed-test-cleanup-wait.patch` to `services/api/tests/test_request_budget.py`, test-only. Preserve the response-time assertion, unfinished-at-deadline-return assertion and eventual-completion assertion. No other test-body edits.
2. Approve after the fact `addopts = "--confcutdir=.."` in both services' pyproject.toml files. Record this acceptance in integration evidence.
3. On main, run the focused test twenty times in a shell loop and report the pass count. Then run the full API suite twice on main, once more in a fresh clone using `cd services/api && uv run pytest`, and the worker suite once.
4. If all checks pass, stop and report the final main SHA. **Do not push. Fred deploys the backend first, then pushes.** No agent deployment is authorized.

Only the fixed worker-cleanup sleep is replaced by a one-second bounded wait. The production deadline and its test response-time bound are unchanged.
