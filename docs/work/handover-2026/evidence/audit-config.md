> Durable copy of accepted 2026-10-24 evidence at base `e9de105`, preserved under [APPROVAL-01](<../approval-01.md>). Findings describe that audit revision, not integrated fixes or live recovery. Repository links are adapted for archive moves; original source line labels are retained. Raw scratch manifests, scripts, dumps and JSON are intentionally not promoted.

# AUDIT REPORT

Task / brief ID: BRIEF-04 / WI-05 — secrets and configuration inventory, names only.

Branch and worktree: `codex/config-inventory` at `/Users/fred/.codex/worktrees/c15f/kala`.

Base revision: `e9de105d7f3074ec39f54e32b1f2b5e2bda669ed`; local `origin/main` matched at the start. No fetch, reset, commit, push, merge, or deployment occurred. The initially detached checkout was given the requested branch.

Files changed: none in the repository. All artifacts in this directory are scratch audit outputs. Final Git cleanliness is recorded below and in `worktree-state.json`.

REQ / WI IDs touched: WI-05 audited; no requirements, implementation, or repository documentation changed.

## Results and complete artifacts

Static audit completed under Fred's revised stop rule. No contradiction blocks completion of this audit as written. The prior visual-rule stop was resolved by Fred: DESIGN.md governs. No visual work was performed.

| Scope | Result |
| --- | --- |
| API Settings fields | 43 |
| Worker Settings fields | 25 |
| Unique backend field aliases | 47 |
| Duplicated worker/API fields | 21; all aliases and defaults match exactly |
| Runtime names | 54: 47 backend aliases, 1 bootstrap-only name, 4 browser references including DEV, 2 Edge Function names |
| Terraform inputs | 8 |
| Makefile settings | 5 |
| Total scoped inventory rows | 67 |
| Source fallback/initializer present | 57 rows |
| No source fallback/initializer | 10 rows |
| Default safe to publish | 35 yes, 0 no, 32 unknown |
| Requested JS/TS environment reference occurrences | 8 |
| Terraform Lambda environment assignments | 5 across 2 Lambda resources |
| Extractor source files read | 241; manifest contains names and SHA-256 only |
| Unsupported/dynamic environment accesses found in requested scan | 0 |

The 32 unknown publication classifications comprise 22 existing defaults/initializers needing explicit review and 10 rows without a source default. A safe empty credential sentinel is not evidence of runtime usability. No default literal values are included in output artifacts. Classification is deliberately conservative for nonempty strings. `DEV` has no source default because Vite supplies it; it is not a deployer-provided setting.

Complete inventory and safety reasons: [inventory.md](#preserved-full-names-only-inventory), machine-readable inventory.json (historical scratch artifact `inventory.json`, not promoted).

Every duplicated field, both aliases, exact-match results, and API/worker line numbers: [duplicates.md](#preserved-apiworker-parity-table), duplicates.json (historical scratch artifact `duplicates.json`, not promoted). Default equality uses Python AST structure, preserving literal types and contents without exporting the contents; quote style and formatting do not affect equality.

Source-only extractor proposal: config_inventory.py (historical scratch artifact `config_inventory.py`, not promoted). It is outside the repository and is not an installed production script. It uses AST parsing for Python, structural HCL scanning for the current Terraform source, and direct reference scanning for JS/TS. It does not import application code, evaluate Terraform, execute Make recipes, follow dotenv paths, load credentials, or contact services. Its strict read allowlist excludes environment files, JSON payload files, tfvars, and state files. It rejects symlinks/out-of-tree source paths. A production implementation would still need normal review before placement at `scripts/config_inventory.py`.

## Secret shadowing: conditional static proof

| Name | Terraform assignment | Config consumer | Result |
| --- | --- | --- | --- |
| KALA_SECRETS_ARN | `infra/terraform/lambda.tf:17` and `:53` | API bootstrap `services/api/app/config.py:17`; worker bootstrap `services/worker/app/config.py:23` | Selects the secret before loading its payload; actual payload membership unknown |
| FRONTEND_URL | `infra/terraform/lambda.tf:18` | API `services/api/app/config.py:40` | Environment value wins if a payload member has this name |
| WORKER_FUNCTION_ARN | `infra/terraform/lambda.tf:19` and `:54` | API `services/api/app/config.py:108`; worker `services/worker/app/config.py:95` | Environment value wins if a payload member has this name |

Precedence is established by `os.environ.setdefault` at `services/api/app/config.py:26` and `services/worker/app/config.py:32`. `get_settings` calls the loader before Settings initialization at API lines 259–261 and worker lines 133–135. Settings are cached. AWS_REGION is read during bootstrap at API line 23 and worker line 29, before secret JSON population; its later Settings default does not establish the bootstrap client's region.

Terraform declares a secret container at `infra/terraform/secrets.tf:5`, with its name at line 6. It does not declare an `aws_secretsmanager_secret_version` payload resource in that file. No payload key membership is statically established. `FRONTEND_URL` and `WORKER_FUNCTION_ARN` are therefore conditional shadow candidates supported by the supplied pack's backend catalogue, not confirmed current payload duplicates or proof of deployed drift. See shadowing.json (historical scratch artifact `shadowing.json`, not promoted).

A final scan of every Terraform `.tf` file found no `aws_secretsmanager_secret_version` or `secret_string` marker. The only JSON encoding marker was in `infra/terraform/iam.tf:70`. Marker evidence is in payload-static-scan.json (historical scratch artifact `payload-static-scan.json`, not promoted); this scan does not establish any hosted payload contents.

## Findings and proposed resolutions

| Finding and exact sources | Proposed resolution for later approval |
| --- | --- |
| Supplied pack, “Where each kind of value is stored” and backend heading propose `kala/<env>/app`; current Terraform secret name is `kala/app` at `infra/terraform/secrets.tf:6`; BRIEF-04 task 3 itself references `kala/app`. | Describe the current name accurately and explicitly label environment-scoped naming as proposed. No infrastructure renaming in WI-05. This does not block a names-only audit. |
| Supplied pack backend table groups LTI_AUTH_LOGIN_URL, LTI_AUTH_TOKEN_URL, LTI_KEYSET_URL as API and worker. API declares all at `services/api/app/config.py:242–244`; worker declares only LTI_AUTH_TOKEN_URL at `services/worker/app/config.py:122`. | Split into individual rows with exact declaration consumers. The catalogue labels configuration declarations, not proof of execution paths. |
| Supplied pack backend table groups BEDROCK_MODEL_* and BEDROCK_EMBED_MODEL as API and worker. API declares model fields at `services/api/app/config.py:45–54`; worker declares only BEDROCK_EMBED_MODEL at `services/worker/app/config.py:46`. | Expand all names and use exact consumer lists. |
| Supplied pack local-development store row omits worker dotenv; worker Settings declares env-file loading at `services/worker/app/config.py:38`. | Add `services/worker/.env` to the proposed local store table. This audit did not open or create it. |
| Bootstrap KALA_SECRETS_ARN is outside Settings fields but read at API line 17 / worker line 23. Lambda owns it at `infra/terraform/lambda.tf:17,53`. | Give bootstrap its own inventory row; include an explicitly commented optional placeholder, with local instructions to keep it unset. |
| Supplied pack browser table lists three VITE names; source also references DEV at `apps/web/src/lib/api/parse-response.ts:30,35` and `apps/web/src/routes/__root.tsx:19`. | Include DEV as a Vite built-in in the inventory, but exclude it from examples and Vercel user configuration. |
| Edge names AWS_PROXY_SECRET and AWS_ENDPOINT_URL occur at `supabase/functions/aws-proxy/index.ts:15–16`; the supplied pack has a store row but no per-name Edge inventory. | Add a names-only Edge table with consumer, secrecy, and ownership notes. |
| `docs/engineering/secrets.md`, `scripts/config_inventory.py`, and worker `.env.example` do not exist at this base. API and web examples exist; their contents were not read. | Add the missing files and review/rewrite existing examples only after implementation authorization. Existing example coverage remains unknown. |
| Root CLAUDE.md expects scoped guides, but `services/api/CLAUDE.md`, `services/worker/CLAUDE.md`, and `infra/CLAUDE.md` were absent. Root AGENTS.md and docs/README.md are also absent; the supplied routing pack is not installed. | Record as handover documentation work; do not install the pack during this audit. |

No repository document drift was silently resolved in code. The prior cross-audit visual discrepancy was reported by the planner at root CLAUDE.md:96 and apps/web/src/styles/DESIGN.md:39, and explicitly resolved by Fred in favor of DESIGN.md. The other planner resolutions (36 migrations superseding old setup, historical INC-002 with live recovery unverified) require no configuration-audit action.

## Complete proposed file changes, not applied

| Intended repository path | Scratch proposal | Coverage |
| --- | --- | --- |
| scripts/config_inventory.py | config_inventory.py (historical scratch artifact `config_inventory.py`, not promoted) | Source-only extractor; produces names, consumers, defaults present, publication safety, source references, reasons, and metadata |
| docs/engineering/secrets.md | secrets-inventory.proposed.md (historical scratch artifact `secrets-inventory.proposed.md`, not promoted) | 47 individual backend names; bootstrap; browser; Edge; Terraform; Make; store ownership; supplied account/exposure sections preserved as unverified claims |
| services/api/.env.example | api-env-example.proposed.txt (historical scratch artifact `api-env-example.proposed.txt`, not promoted) | All 43 Settings aliases plus KALA_SECRETS_ARN: 44 unique names |
| services/worker/.env.example | worker-env-example.proposed.txt (historical scratch artifact `worker-env-example.proposed.txt`, not promoted) | All 25 Settings aliases plus KALA_SECRETS_ARN: 26 unique names |
| apps/web/.env.example | web-env-example.proposed.txt (historical scratch artifact `web-env-example.proposed.txt`, not promoted) | All 3 VITE settings; DEV excluded |

Examples are complete placeholder templates with every assignment commented. Users fill and uncomment selected settings; omitted settings retain source defaults. Numeric/boolean/credential placeholders are labeled without copying any default or credential values. Each group has a one-line explanatory comment. KALA_SECRETS_ARN stays commented to avoid accidental hosted retrieval during local development. These templates have not been validated as a runnable environment, and are intentionally not applied.

The proposed secret table keeps the supplied columns: Name, Secret?, Consumed by, Issued by, Rotate how. The draft does not assert that all catalogue names live in the JSON secret. Names matching Lambda environment entries are explicitly Terraform-owned. Rotation ownership is proposed for review; no actual rotation or current-key validation occurred. Accounts and exposure history are copied only from the supplied pack and labeled unverified, including their status.

## Commands run and results

- `pwd`, `git status --short`, `git branch --show-current`, `git rev-parse HEAD`, `git rev-parse origin/main`: correct assigned checkout, initially clean and detached, base matched local origin/main.
- `git switch -c codex/config-inventory`: succeeded. No existing branch reset.
- Read root CLAUDE.md and the Supabase SKILL.md. Attempted reads of the three missing scoped guides reported “No such file or directory.”
- `rg --files` for repository source/instruction discovery. An initial read-only AGENTS filename search also listed other managed-worktree paths; no other worktree file was opened or modified.
- Read-only Python AST/name probes of the two config modules, Terraform source, frontend references, Edge references, and Makefile: succeeded; printed names and structural metadata only.
- Read-only JSON inspection of root/package.json and apps/web/package.json: neither contains a db:* script at this base. No db script was executed or proposed. This does not authorize hosted CLI commands or later script changes.
- Read-only names/line probes of docs/BACKEND.md, docs/SUPABASE.md, services/api/README.md, services/worker/README.md, and infra/terraform/README.md: configuration-name references only were printed. No secret payload or environment file was opened.
- `python3 <scratch>/config_inventory.py --root /Users/fred/.codex/worktrees/c15f/kala --out <scratch>`: succeeded after the final scratch proposal update. Results are in summary.json (historical scratch artifact `summary.json`, not promoted).
- Independent artifact verification: 11 checks passed; verification.json (historical scratch artifact `verification.json`, not promoted). Checked unique scoped names, forbidden-file absence from the extractor manifest, all 241 source hashes unchanged, all 21 duplicate comparisons, complete/unique/placeholder-only examples, all 47 backend rows, no default-value output column, Python syntax, and unknown actual payload membership.
- Final `git status --porcelain=v1 --untracked-files=all`, `git diff --quiet`, `git diff --cached --quiet`, HEAD/branch checks: see worktree-state.json; repository remains clean.

Spec changes made: none.

Evidence added: scratch artifacts only, all in this directory. source-read-manifest.json (historical scratch artifact `source-read-manifest.json`, not promoted) covers the extractor's 241 source reads, not the separate instruction/docs/package/status probes. It contains paths and source hashes only.

## Limitations, gates, and resource state

This is static proof of source declarations and precedence, not runtime proof. No application imports or startup, unit tests, lint, typecheck, build, local database, Docker commands, cloud CLI, network fetch, Secrets Manager/KMS access, hosted drift inspection, Blackboard observation, or production operation was performed. No `.env` or `.env.example` file, `secret.json`, terraform.tfvars, state, credential store, token, student record, or hosted payload was read. Existing example contents and actual secret memberships remain unknown by design. Unknown default safety classifications require a deliberate publication review; no unsafe literal was discovered or exported.

All required static audit work is complete. Implementation, repository file moves/edits, commits, pushes, merges, deployments, and later gated brief parts remain deferred. Planner approval and continuation are required before repository implementation; no additional approval is requested for already resolved audit points.

Scratch resources: this directory only; retained for review. Docker/local databases: none created, started, stopped, or removed. No running server or port binding was changed. Main checkout, existing Kala Audit chat, other worktrees/chats, and the user's Vite server were left untouched. No other chat was messaged.

Secrets printed: none (confirmed). No student personal data or user/session tokens were printed.


## Preserved full names-only inventory

# Static configuration inventory (names only)

A default means a source fallback/initializer. Lambda assignments are consumers, not defaults. Make defined expressions count as initializers. Unknown safety requires review; no literal values are exported. An empty credential sentinel can be safe to publish while unusable for runtime. DEV is supplied by Vite and has no source default.

| Namespace | Name | Consumers | Has default | Default safe to publish | Source | Classification reason |
| --- | --- | --- | --- | --- | --- | --- |
| make | ACCOUNT | Makefile | yes | unknown | Makefile:6 | Computed Make expression; never executed; conditional assignment |
| make | AWS | Makefile | yes | yes | Makefile:4 | Static tool selector or region identifier; conditional assignment |
| make | ECR | Makefile | yes | unknown | Makefile:7 | Computed Make expression; never executed; defined expression |
| make | REGION | Makefile | yes | yes | Makefile:3 | Static tool selector or region identifier; conditional assignment |
| make | TF | Makefile | yes | yes | Makefile:5 | Static tool selector or region identifier; conditional assignment |
| runtime | AI_PROVIDER | api, worker | yes | unknown | services/api/app/config.py:63, services/worker/app/config.py:52 | Nonempty string needs explicit publication review; value omitted |
| runtime | AWS_ENDPOINT_URL | edge | no | unknown | supabase/functions/aws-proxy/index.ts:16 | No source fallback |
| runtime | AWS_PROXY_SECRET | edge | no | unknown | supabase/functions/aws-proxy/index.ts:15 | No source fallback |
| runtime | AWS_REGION | api, api bootstrap, worker, worker bootstrap | yes | yes | services/api/app/config.py:109, services/api/app/config.py:23, services/worker/app/config.py:45, services/worker/app/config.py:29 | Region identifier; Bootstrap environment read occurs before secret payload loading |
| runtime | BANK_REASONING_EFFORT | worker | yes | unknown | services/worker/app/config.py:93 | Nonempty string needs explicit publication review; value omitted |
| runtime | BANK_REASONING_MAX_TOKENS | worker | yes | yes | services/worker/app/config.py:94 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | BEDROCK_EMBED_MODEL | api, worker | yes | yes | services/api/app/config.py:54, services/worker/app/config.py:46 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | BEDROCK_MODEL_CHAT | api | yes | yes | services/api/app/config.py:52 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | BEDROCK_MODEL_DEFAULT | api | yes | yes | services/api/app/config.py:46 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | BEDROCK_MODEL_FAST | api | yes | yes | services/api/app/config.py:45 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | BEDROCK_MODEL_PREMIUM | api | yes | yes | services/api/app/config.py:53 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | BEDROCK_MODEL_REASONING | api | yes | yes | services/api/app/config.py:47 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | DEV | web Vite built-in | no | unknown | apps/web/src/lib/api/parse-response.ts:30, apps/web/src/lib/api/parse-response.ts:35, apps/web/src/routes/__root.tsx:19 | Vite-provided built-in; no source default |
| runtime | EMBED_PROVIDER | api, worker | yes | yes | services/api/app/config.py:227, services/worker/app/config.py:53 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | FRONTEND_URL | api, Terraform Lambda api | yes | yes | services/api/app/config.py:40, infra/terraform/lambda.tf:18 | Loopback development URL; Explicit Lambda environment assignment; expression not exported |
| runtime | KALA_SECRETS_ARN | api bootstrap, worker bootstrap, Terraform Lambda api, Terraform Lambda worker | no | unknown | services/api/app/config.py:17, services/worker/app/config.py:23, infra/terraform/lambda.tf:17, infra/terraform/lambda.tf:53 | Bootstrap environment read occurs before secret payload loading; Explicit Lambda environment assignment; expression not exported |
| runtime | LMS_REST_BASE_URL | api, worker | yes | yes | services/api/app/config.py:249, services/worker/app/config.py:113 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | LMS_REST_CLIENT_ID | api, worker | yes | yes | services/api/app/config.py:250, services/worker/app/config.py:114 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | LMS_REST_CLIENT_SECRET | api, worker | yes | yes | services/api/app/config.py:251, services/worker/app/config.py:115 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | LMS_VERIFY_TLS | api, worker | yes | yes | services/api/app/config.py:241, services/worker/app/config.py:121 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | LTI_AUTH_LOGIN_URL | api | yes | yes | services/api/app/config.py:242 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | LTI_AUTH_TOKEN_URL | api, worker | yes | yes | services/api/app/config.py:243, services/worker/app/config.py:122 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | LTI_CLIENT_ID | api | yes | yes | services/api/app/config.py:240 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | LTI_DEPLOYMENT_IDS | api | yes | yes | services/api/app/config.py:245 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | LTI_ISSUER | api | yes | unknown | services/api/app/config.py:239 | Nonempty string needs explicit publication review; value omitted |
| runtime | LTI_KEYSET_URL | api | yes | yes | services/api/app/config.py:244 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | LTI_TOOL_PRIVATE_KEY_PEM | api | yes | yes | services/api/app/config.py:246 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | OPENAI_API_KEY | api, worker | yes | yes | services/api/app/config.py:228, services/worker/app/config.py:97 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | OPENAI_BASE_URL | api, worker | yes | unknown | services/api/app/config.py:229, services/worker/app/config.py:98 | Nonempty string needs explicit publication review; value omitted |
| runtime | OPENAI_EMBED_MODEL | api, worker | yes | unknown | services/api/app/config.py:236, services/worker/app/config.py:99 | Nonempty string needs explicit publication review; value omitted |
| runtime | OPENROUTER_API_KEY | api, worker | yes | yes | services/api/app/config.py:107, services/worker/app/config.py:55 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | OPENROUTER_BASE_URL | api, worker | yes | unknown | services/api/app/config.py:110, services/worker/app/config.py:56 | Nonempty string needs explicit publication review; value omitted |
| runtime | OPENROUTER_EMBED_MODEL | api, worker | yes | unknown | services/api/app/config.py:215, services/worker/app/config.py:59 | Nonempty string needs explicit publication review; value omitted |
| runtime | OPENROUTER_MODEL_BANK | worker | yes | unknown | services/worker/app/config.py:90 | Nonempty string needs explicit publication review; value omitted |
| runtime | OPENROUTER_MODEL_CHAT | api | yes | unknown | services/api/app/config.py:147 | Nonempty string needs explicit publication review; value omitted |
| runtime | OPENROUTER_MODEL_CHAT_FALLBACK | api | yes | unknown | services/api/app/config.py:162 | Nonempty string needs explicit publication review; value omitted |
| runtime | OPENROUTER_MODEL_DEFAULT | api, worker | yes | unknown | services/api/app/config.py:125, services/worker/app/config.py:75 | Nonempty string needs explicit publication review; value omitted |
| runtime | OPENROUTER_MODEL_FALLBACK | api | yes | unknown | services/api/app/config.py:186 | Nonempty string needs explicit publication review; value omitted |
| runtime | OPENROUTER_MODEL_FAST | api, worker | yes | unknown | services/api/app/config.py:113, services/worker/app/config.py:72 | Nonempty string needs explicit publication review; value omitted |
| runtime | OPENROUTER_MODEL_ITEM | api, worker | yes | unknown | services/api/app/config.py:179, services/worker/app/config.py:87 | Nonempty string needs explicit publication review; value omitted |
| runtime | OPENROUTER_MODEL_PREMIUM | api | yes | unknown | services/api/app/config.py:176 | Nonempty string needs explicit publication review; value omitted |
| runtime | OPENROUTER_MODEL_REASONING | api | yes | unknown | services/api/app/config.py:166 | Nonempty string needs explicit publication review; value omitted |
| runtime | OPENROUTER_MODEL_REASONING_FALLBACK | api | yes | unknown | services/api/app/config.py:172 | Nonempty string needs explicit publication review; value omitted |
| runtime | OPENROUTER_PROVIDER_ORDER | api | yes | unknown | services/api/app/config.py:203 | Nonempty string needs explicit publication review; value omitted |
| runtime | SESSION_TTL_SECONDS | api | yes | yes | services/api/app/config.py:41 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | SKILL_SEED_ON_LAUNCH | api | yes | yes | services/api/app/config.py:42 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | SUPABASE_JWT_SECRET | api | yes | yes | services/api/app/config.py:37 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | SUPABASE_SERVICE_KEY | api, worker | yes | yes | services/api/app/config.py:36, services/worker/app/config.py:42 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | SUPABASE_URL | api, worker | yes | yes | services/api/app/config.py:35, services/worker/app/config.py:41 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | TRACER_K | worker | yes | yes | services/worker/app/config.py:129 | Empty sentinel or nonsecret scalar; usability is separate |
| runtime | VITE_API_BASE_URL | web | no | unknown | apps/web/src/lib/api/client.ts:6 | No source fallback |
| runtime | VITE_SUPABASE_ANON_KEY | web | no | unknown | apps/web/src/lib/supabase/client.ts:5 | No source fallback |
| runtime | VITE_SUPABASE_URL | web | no | unknown | apps/web/src/lib/supabase/client.ts:4 | No source fallback |
| runtime | WORKER_FUNCTION_ARN | api, worker, Terraform Lambda api, Terraform Lambda worker | yes | yes | services/api/app/config.py:108, services/worker/app/config.py:95, infra/terraform/lambda.tf:19, infra/terraform/lambda.tf:54 | Empty sentinel or nonsecret scalar; usability is separate; Explicit Lambda environment assignment; expression not exported |
| terraform | api_image_uri | Terraform input | no | unknown | infra/terraform/variables.tf:17 | No Terraform default |
| terraform | assume_role_arn | Terraform input | yes | yes | infra/terraform/variables.tf:11 | Empty sentinel or nonsecret scalar; usability is separate |
| terraform | budget_alert_email | Terraform input | yes | yes | infra/terraform/variables.tf:38 | Empty sentinel or nonsecret scalar; usability is separate |
| terraform | env | Terraform input | yes | unknown | infra/terraform/variables.tf:6 | Nonempty string needs explicit publication review; value omitted |
| terraform | frontend_url | Terraform input | no | unknown | infra/terraform/variables.tf:27 | No Terraform default |
| terraform | region | Terraform input | yes | yes | infra/terraform/variables.tf:1 | Region identifier |
| terraform | worker_image_uri | Terraform input | no | unknown | infra/terraform/variables.tf:22 | No Terraform default |
| terraform | worker_schedule | Terraform input | yes | unknown | infra/terraform/variables.tf:32 | Nonempty string needs explicit publication review; value omitted |


## Preserved API/worker parity table

# API/worker duplicates

| Field | API alias | Worker alias | Alias matches | Default matches | API source | Worker source |
| --- | --- | --- | --- | --- | --- | --- |
| ai_provider | AI_PROVIDER | AI_PROVIDER | yes | yes | services/api/app/config.py:63 | services/worker/app/config.py:52 |
| aws_region | AWS_REGION | AWS_REGION | yes | yes | services/api/app/config.py:109 | services/worker/app/config.py:45 |
| bedrock_embed_model | BEDROCK_EMBED_MODEL | BEDROCK_EMBED_MODEL | yes | yes | services/api/app/config.py:54 | services/worker/app/config.py:46 |
| embed_provider | EMBED_PROVIDER | EMBED_PROVIDER | yes | yes | services/api/app/config.py:227 | services/worker/app/config.py:53 |
| lms_rest_base_url | LMS_REST_BASE_URL | LMS_REST_BASE_URL | yes | yes | services/api/app/config.py:249 | services/worker/app/config.py:113 |
| lms_rest_client_id | LMS_REST_CLIENT_ID | LMS_REST_CLIENT_ID | yes | yes | services/api/app/config.py:250 | services/worker/app/config.py:114 |
| lms_rest_client_secret | LMS_REST_CLIENT_SECRET | LMS_REST_CLIENT_SECRET | yes | yes | services/api/app/config.py:251 | services/worker/app/config.py:115 |
| lms_verify_tls | LMS_VERIFY_TLS | LMS_VERIFY_TLS | yes | yes | services/api/app/config.py:241 | services/worker/app/config.py:121 |
| lti_auth_token_url | LTI_AUTH_TOKEN_URL | LTI_AUTH_TOKEN_URL | yes | yes | services/api/app/config.py:243 | services/worker/app/config.py:122 |
| openai_api_key | OPENAI_API_KEY | OPENAI_API_KEY | yes | yes | services/api/app/config.py:228 | services/worker/app/config.py:97 |
| openai_base_url | OPENAI_BASE_URL | OPENAI_BASE_URL | yes | yes | services/api/app/config.py:229 | services/worker/app/config.py:98 |
| openai_embed_model | OPENAI_EMBED_MODEL | OPENAI_EMBED_MODEL | yes | yes | services/api/app/config.py:236 | services/worker/app/config.py:99 |
| openrouter_api_key | OPENROUTER_API_KEY | OPENROUTER_API_KEY | yes | yes | services/api/app/config.py:107 | services/worker/app/config.py:55 |
| openrouter_base_url | OPENROUTER_BASE_URL | OPENROUTER_BASE_URL | yes | yes | services/api/app/config.py:110 | services/worker/app/config.py:56 |
| openrouter_embed_model | OPENROUTER_EMBED_MODEL | OPENROUTER_EMBED_MODEL | yes | yes | services/api/app/config.py:215 | services/worker/app/config.py:59 |
| openrouter_model_default | OPENROUTER_MODEL_DEFAULT | OPENROUTER_MODEL_DEFAULT | yes | yes | services/api/app/config.py:125 | services/worker/app/config.py:75 |
| openrouter_model_fast | OPENROUTER_MODEL_FAST | OPENROUTER_MODEL_FAST | yes | yes | services/api/app/config.py:113 | services/worker/app/config.py:72 |
| openrouter_model_item | OPENROUTER_MODEL_ITEM | OPENROUTER_MODEL_ITEM | yes | yes | services/api/app/config.py:179 | services/worker/app/config.py:87 |
| supabase_service_key | SUPABASE_SERVICE_KEY | SUPABASE_SERVICE_KEY | yes | yes | services/api/app/config.py:36 | services/worker/app/config.py:42 |
| supabase_url | SUPABASE_URL | SUPABASE_URL | yes | yes | services/api/app/config.py:35 | services/worker/app/config.py:41 |
| worker_function_arn | WORKER_FUNCTION_ARN | WORKER_FUNCTION_ARN | yes | yes | services/api/app/config.py:108 | services/worker/app/config.py:95 |
