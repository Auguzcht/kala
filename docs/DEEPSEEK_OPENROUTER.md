# DeepSeek instructions — OpenRouter interim model provider

Backend is done and tested (49/49 passing, includes 9 new provider-dispatch
tests). This is purely an env-configuration + verification task, no more
code should be needed unless the live test below turns something up.

## Why

Real Bedrock model access is scoped for once this runs under the school's
AWS org account (not yet). Until then, every model call needs to route
through OpenRouter's free tier instead. `ai/bedrock.py` now dispatches on
`AI_PROVIDER` and every caller (router.py, rag.py, skill_proposer.py,
learn/items.py, diagnostic.py) is completely unchanged either way.

## Do this

1. Add to `services/api/.env`:
   ```
   AI_PROVIDER=openrouter
   OPENROUTER_API_KEY=<the real key>
   ```
   The model IDs (`OPENROUTER_MODEL_FAST/DEFAULT/REASONING/PREMIUM`,
   `OPENROUTER_EMBED_MODEL`) already have working defaults in `config.py`,
   only set them in `.env` if you want to override a specific tier.

2. Restart the API (env is read at startup, same rule as always).

3. **Run one live verification before trusting this for the demo**, free
   model availability rotates and the specific models here were only
   confirmed as of when this was wired in:
   - Trigger any converse call (easiest: launch as instructor on a course
     with no skills, which fires skill proposal) and confirm it actually
     returns proposals instead of an error in the log.
   - Trigger any embed call (same launch does this too, via ingest/dedup)
     and confirm `len(embedding) == 1024` reaches Postgres without the
     dimension-mismatch error in `diagnostic.py`'s ingest path.
   - If either model ID has rotated out of OpenRouter's free tier, check
     `https://openrouter.ai/collections/free-models` (chat) or
     `https://openrouter.ai/collections/embedding-models` (embeddings) for
     a current replacement and update the corresponding `.env` var, no code
     change needed, the model ID is the only thing that changes.

## What NOT to do

- Don't change `ai/router.py`, `ai/rag.py`, `ai/skill_proposer.py`,
  `learn/items.py`, or `routers/diagnostic.py`. They're provider-agnostic on
  purpose, only `ai/bedrock.py` and `config.py` know which provider is active.
- Don't remove or "clean up" the Bedrock code paths in `bedrock.py`, they're
  what this switches back to once real AWS org access lands, that's the whole
  point of the dispatch design.
- Don't hardcode a specific OpenRouter model ID anywhere outside `config.py`.
  If a free model rotates out, the fix should always be a one-line `.env`
  change, never a code change.

## Known risk, not a bug to fix, just be aware

OpenRouter's free-tier models have real availability risk (roughly 85-90%
uptime observed, not enterprise SLA). Every caller already degrades
gracefully on a model failure (best-effort skill proposal, deterministic
fallback items in the learn loop), so a flaky model shows up as those
existing fallback paths firing, not a crash. Worth one full rehearsal run
specifically to see what that degraded state looks like on stage, rather
than discovering it live during the actual demo.
