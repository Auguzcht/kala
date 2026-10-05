# AWS101 item-generation routing benchmark

Run: `2026-10-05T19:54:04.434750+00:00`; course: `ae4e7680-f94b-4652-b3f6-b9c32f4420de`; schema: `{items: [...]}`; batch size: 5; cap: `max_completion_tokens=8192` (the current OpenRouter name for the requested 8192 cap).

No production code, Terraform, or data were changed by the benchmark, and no migration was applied. The requested migration text-only edit is recorded separately. Context was read-only similarity matches at SIM_THRESHOLD 0.544, with the existing production prompt, banned phrases, and validator imported.

## OpenRouter parameter check

The current API documentation names `max_completion_tokens` (and marks `max_tokens` deprecated), `provider` for routing preferences, `reasoning.effort` / `reasoning_effort` for effort, and `reasoning.exclude` for excluding reasoning output. See [OpenRouter chat completions API docs](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion). The benchmark therefore sent `max_completion_tokens: 8192`; the requested `max_tokens=8192` is the same generation cap.

## Results

| Variant | Model / mode | p50 | p95 | Max | >75s | >90s | Validator pass | Reasoning tokens (total / median) | Provider served | Cost/batch USD | Finish reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|
| A | deepseek/deepseek-v4.1-flash:floor floor default | 48858 ms | 55724 ms | 55938 ms | 0 | 0 | 100.0% (50/50) | 26105 / 2582.5 | `{"InferenceNet": 10}` | 0.0012068142 | `{"stop": 10}` |
| B | deepseek/deepseek-v4.1-flash default default | 21965 ms | 44102 ms | 46982 ms | 0 | 0 | 100.0% (50/50) | 18199 / 1831.5 | `{"AtlasCloud": 4, "CoreWeave": 1, "DeepInfra": 5}` | 0.0017475298000000001 | `{"stop": 10}` |
| C | deepseek/deepseek-v4.1-flash:nitro nitro default | 6720 ms | 12011 ms | 12830 ms | 0 | 0 | 100.0% (50/50) | 19425 / 1431.0 | `{"Together": 10}` | 0.0039624132 | `{"stop": 10}` |
| D | deepseek/deepseek-v4.1-flash:nitro nitro effort=low | 6020 ms | 8247 ms | 8347 ms | 0 | 0 | 100.0% (50/50) | 13195 / 1224.5 | `{"Together": 10}` | 0.0030336132 | `{"stop": 10}` |
| E | deepseek/deepseek-v4.1-flash:nitro nitro exclude=true | 8800 ms | 11580 ms | 13261 ms | 0 | 0 | 100.0% (50/50) | 23610 / 2331.5 | `{"Together": 10}` | 0.0038185284 | `{"stop": 10}` |

D/E gate: **D and E are flagged if validator pass rate is below 95%; speed is not recommended when that happens.**

Best B/C by p95: **C**. Recommended variant: **D**. Recommended p95 under 75 seconds: **True**.
