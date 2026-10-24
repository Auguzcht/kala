# Secrets and configuration inventory

**Names only. Secret and setting values never belong in this file.**

No values or actual payload membership are asserted. Backend configuration catalogue; this is not evidence that every name is stored in Secrets Manager. Account details and historical exposure entries come from the supplied pack and are not independently verified. The later Lane S incident is separately attributed to its reporting agent.


## Inventory contract (WI-05)

Approved by APPROVAL-01 on 2026-10-24. This is development tooling and documentation; it changes no runtime configuration.

- Read only the two Python configuration modules, browser source, Edge Function source, Terraform `.tf` source and Makefile. Never read environment files, secret payloads, credentials, tfvars, state, or remote services.
- Print names, consumers, whether a source default exists and whether that default is safe to publish (yes/no/unknown). Never print default values. Empty sentinels can be safe to publish without being usable configuration. Nonempty strings are unknown unless explicitly recognized as harmless; credential-like defaults are never safe.
- Compare all duplicated API/worker aliases and defaults without disclosing defaults. Report unsupported or dynamic syntax rather than silently assuming complete coverage.
- Keep the tables and examples complete for the declared names. Examples use commented placeholders; fill and uncomment only the settings needed, leaving omitted defaults in source.
- Treat Lambda/secret overlap as conditional until a maintainer establishes actual payload membership.

Run from the repository root:

```sh
python3 scripts/config_inventory.py
python3 scripts/config_inventory.py --format json --check
python3 -B -m unittest discover -s scripts -p test_config_inventory.py -v
```

`--check` fails on unsupported source syntax or differing duplicated aliases/defaults. The dedicated tests check document/example coverage as well. The script does not open this document or the examples. The source scan is not runtime, hosted-state, or secret-membership verification.

The scanner supports the repository's literal `Field` aliases, Terraform inputs and literal Lambda environment maps, direct browser environment accesses, and `Deno.env.get` calls. It ignores JS comments and string text while scanning template expressions. It is not a full TypeScript or Terraform parser; regex literals containing an environment-access spelling can be conservatively counted as references. Dynamic aliases, dynamic environment lookups, heredocs and computed Lambda maps require review and cause `--check` to fail. Extend the dedicated tests when source syntax changes.

## Where each kind of value is stored

| Kind | Store | Per environment |
| --- | --- | --- |
| Backend runtime secrets | AWS Secrets Manager JSON, referenced by `KALA_SECRETS_ARN`; payload contents unknown | Current Terraform names one `kala/app` secret; isolation strategy requires maintainer review |
| Non-secret backend settings | Source defaults, Terraform-owned Lambda entries, or maintainer-managed JSON | Per deployment; precedence documented below |
| Browser config | Vercel environment variables | Per Vercel environment |
| Local development | `services/api/.env`, `services/worker/.env`, `apps/web/.env.local` | Per laptop; keep bootstrap secret ARN unset for local-only operation |
| Edge Function secrets, if aws-proxy is used | Supabase Edge Function configuration | Per project; not inspected |
| Human accounts | Institution password manager; owner: ITO | Per environment |
| Terraform state | Backend selected and approved by ITO; actual backend/state not inspected | Per environment |

## Backend secrets and settings

| Name | Secret? | Consumed by | Issued by | Rotate how |
| --- | --- | --- | --- | --- |
| `AI_PROVIDER` | no | api, worker | Application configuration | n/a (configuration change through review) |
| `AWS_REGION` | no | api, worker | Lambda runtime or local configuration | n/a (configuration change through review) |
| `BANK_REASONING_EFFORT` | no | worker | Application configuration | n/a (configuration change through review) |
| `BANK_REASONING_MAX_TOKENS` | no | worker | Application configuration | n/a (configuration change through review) |
| `BEDROCK_EMBED_MODEL` | no | api, worker | Application configuration | n/a (configuration change through review) |
| `BEDROCK_MODEL_CHAT` | no | api | Application configuration | n/a (configuration change through review) |
| `BEDROCK_MODEL_DEFAULT` | no | api | Application configuration | n/a (configuration change through review) |
| `BEDROCK_MODEL_FAST` | no | api | Application configuration | n/a (configuration change through review) |
| `BEDROCK_MODEL_PREMIUM` | no | api | Application configuration | n/a (configuration change through review) |
| `BEDROCK_MODEL_REASONING` | no | api | Application configuration | n/a (configuration change through review) |
| `EMBED_PROVIDER` | no | api, worker | Application configuration | n/a (configuration change through review) |
| `FRONTEND_URL` | no | api | Application configuration | n/a (configuration change through review) |
| `LMS_REST_BASE_URL` | no | api, worker | LMS / Developer Portal administrator | n/a (configuration change through review) |
| `LMS_REST_CLIENT_ID` | no | api, worker | LMS / Developer Portal administrator | n/a (configuration change through review) |
| `LMS_REST_CLIENT_SECRET` | yes | api, worker | LMS / Developer Portal administrator | Provider-specific replacement and revocation runbook; maintainer-run |
| `LMS_VERIFY_TLS` | no | api, worker | LMS / Developer Portal administrator | n/a (configuration change through review) |
| `LTI_AUTH_LOGIN_URL` | no | api | LTI registration administrator | n/a (configuration change through review) |
| `LTI_AUTH_TOKEN_URL` | no | api, worker | LTI registration administrator | n/a (configuration change through review) |
| `LTI_CLIENT_ID` | no | api | LTI registration administrator | n/a (configuration change through review) |
| `LTI_DEPLOYMENT_IDS` | no | api | LTI registration administrator | n/a (configuration change through review) |
| `LTI_ISSUER` | no | api | LTI registration administrator | n/a (configuration change through review) |
| `LTI_KEYSET_URL` | no | api | LTI registration administrator | n/a (configuration change through review) |
| `LTI_TOOL_PRIVATE_KEY_PEM` | yes | api | Institutional key custodian | Reviewed key-pair rollover with JWKS overlap; maintainer-run |
| `OPENAI_API_KEY` | yes | api, worker | OpenAI account administrator | Provider-specific replacement and revocation runbook; maintainer-run |
| `OPENAI_BASE_URL` | no | api, worker | Application configuration | n/a (configuration change through review) |
| `OPENAI_EMBED_MODEL` | no | api, worker | Application configuration | n/a (configuration change through review) |
| `OPENROUTER_API_KEY` | yes | api, worker | OpenRouter account administrator | Provider-specific replacement and revocation runbook; maintainer-run |
| `OPENROUTER_BASE_URL` | no | api, worker | Application configuration | n/a (configuration change through review) |
| `OPENROUTER_EMBED_MODEL` | no | api, worker | Application configuration | n/a (configuration change through review) |
| `OPENROUTER_MODEL_BANK` | no | worker | Application configuration | n/a (configuration change through review) |
| `OPENROUTER_MODEL_CHAT` | no | api | Application configuration | n/a (configuration change through review) |
| `OPENROUTER_MODEL_CHAT_FALLBACK` | no | api | Application configuration | n/a (configuration change through review) |
| `OPENROUTER_MODEL_DEFAULT` | no | api, worker | Application configuration | n/a (configuration change through review) |
| `OPENROUTER_MODEL_FALLBACK` | no | api | Application configuration | n/a (configuration change through review) |
| `OPENROUTER_MODEL_FAST` | no | api, worker | Application configuration | n/a (configuration change through review) |
| `OPENROUTER_MODEL_ITEM` | no | api, worker | Application configuration | n/a (configuration change through review) |
| `OPENROUTER_MODEL_PREMIUM` | no | api | Application configuration | n/a (configuration change through review) |
| `OPENROUTER_MODEL_REASONING` | no | api | Application configuration | n/a (configuration change through review) |
| `OPENROUTER_MODEL_REASONING_FALLBACK` | no | api | Application configuration | n/a (configuration change through review) |
| `OPENROUTER_PROVIDER_ORDER` | no | api | Application configuration | n/a (configuration change through review) |
| `SESSION_TTL_SECONDS` | no | api | Application configuration | n/a (configuration change through review) |
| `SKILL_SEED_ON_LAUNCH` | no | api | Application configuration | n/a (configuration change through review) |
| `SUPABASE_JWT_SECRET` | yes | api | Supabase project administrator | Planned signing-key migration; assess session and legacy-key impact first |
| `SUPABASE_SERVICE_KEY` | yes | api, worker | Supabase project administrator | Provider-specific replacement and revocation runbook; maintainer-run |
| `SUPABASE_URL` | no | api, worker | Supabase project administrator | n/a (configuration change through review) |
| `TRACER_K` | no | worker | Application configuration | n/a (configuration change through review) |
| `WORKER_FUNCTION_ARN` | no | api, worker | Terraform output / maintainer | n/a (configuration change through review) |

## Bootstrap settings

| Name | Secret? | Consumed by | Issued by | Rotate how |
| --- | --- | --- | --- | --- |
| `KALA_SECRETS_ARN` | no (resource identifier) | api, worker bootstrap | Terraform secret resource | Update reference through review; payload membership unknown |

`AWS_REGION` is also read during bootstrap before payload loading. `FRONTEND_URL` and `WORKER_FUNCTION_ARN` are Terraform-owned environment entries; matching payload names would be shadowed. Current Terraform declares the secret name `kala/app`; the supplied pack proposes `kala/<env>/app`. Document current naming and defer any naming migration to explicit infrastructure authorization.

## Browser config (Vercel)

| Name | Notes |
| --- | --- |
| `VITE_API_BASE_URL` | Public API base URL |
| `VITE_SUPABASE_ANON_KEY` | Public client key; authorization depends on database policies; never substitute a service credential |
| `VITE_SUPABASE_URL` | Public Supabase project URL |
| `DEV` | Vite-provided built-in, not a user-supplied setting; omit it from examples and Vercel settings |

## Edge Function config (only if aws-proxy is used)

| Name | Notes |
| --- | --- |
| `AWS_PROXY_SECRET` | Secret; consumer: aws-proxy; institution owns issuance and coordinated rotation |
| `AWS_ENDPOINT_URL` | Endpoint configuration; consumer: aws-proxy; no source fallback |

## Terraform input catalogue

| Name | Notes |
| --- | --- |
| `api_image_uri` | Has source default: no; runtime payload membership not implied |
| `assume_role_arn` | Has source default: yes; runtime payload membership not implied |
| `budget_alert_email` | Has source default: yes; runtime payload membership not implied |
| `env` | Has source default: yes; runtime payload membership not implied |
| `frontend_url` | Has source default: no; runtime payload membership not implied |
| `region` | Has source default: yes; runtime payload membership not implied |
| `worker_image_uri` | Has source default: no; runtime payload membership not implied |
| `worker_schedule` | Has source default: yes; runtime payload membership not implied |

## Makefile configuration catalogue

| Name | Notes |
| --- | --- |
| `ACCOUNT` | Make-only setting; see static inventory for classification |
| `AWS` | Make-only setting; see static inventory for classification |
| `ECR` | Make-only setting; see static inventory for classification |
| `REGION` | Make-only setting; see static inventory for classification |
| `TF` | Make-only setting; see static inventory for classification |

## Accounts (names only; handover pack, unverified)

ITO creates institutional accounts and replacement credentials. Personal access is revoked after approved cutover evidence.

| Account | Purpose | Current holder (dev-hosted) | New holder (prod) |
| --- | --- | --- | --- |
| AWS root and IAM admin | Infrastructure | Student developer (personal) | ITO |
| Anthology Developer Portal | LTI and REST application registration | Student developer | ITO |
| Blackboard Learn administrator and test users | Testing | Student developer | ITO |
| Supabase organization | Database | Student developer | ITO |
| Vercel | Web hosting | Student developer | ITO |
| OpenRouter, OpenAI | Models and billing | Student developer | ITO or finance |
| GitHub repository | Source | Unknown; confirm with Fred | ITO organization |

## Exposure log (source attributed; remediation status unverified)

| Date | What | How | Action | Status |
| --- | --- | --- | --- | --- |
| 2026-10-18 | Supabase service key, LMS REST secret | Printed in an agent chat, per supplied pack | Rotate before handover | open, per supplied pack |
| 2026-10-24 | AWS IAM key and console password, OpenRouter, OpenAI, Blackboard app secret, Blackboard user passwords | Pasted in a planning chat, per supplied pack | Rotate AWS key now, rest at cutover, per supplied pack | open, per supplied pack |
| 2026-10-24 | Personal OpenRouter API key; OpenAI embeddings API key; Blackboard Developer application key and application secret; AWS IAM console password, CLI access key ID and secret access key; Blackboard Learn passwords for administrator, two student accounts and instructor account | Lane S reports that a parent-chat tool response emitted an existing credential-bearing preview once; identities confirmed from its existing context without reopening the source | Rotate at cutover, per APPROVAL-02 section 6; no rotation performed by agents | open; agent-reported exposure, remediation unverified |

[APPROVAL-02](../work/handover-2026/approval-02.md) section 6 sets rotation at cutover and supersedes the timing recommendation in the historical pack row above. Credential identifiers are listed for incident completeness; no values or new hosted-state verification are recorded. Lane S reports that it stopped the lookup and did not use or copy values into files or commits.

Secret loaders run during cached settings initialization; secret rotation and process/version refresh need maintainer-run validation. This document supplies names and handover ownership only, not a credential-rotation procedure or runtime proof.

## Change log

| Date | Change | Decision source | IDs affected |
| --- | --- | --- | --- |
| 2026-10-24 | Install names-only static inventory, exact consumer tables and complete placeholder examples | APPROVAL-01, Lane C and amendment A2; accepted BRIEF-04 audit | WI-05 |
| 2026-10-24 | Record names-only Lane S tool-preview exposure and cutover rotation decision | APPROVAL-02 section 6; Lane S incident follow-up | WI-05 |
