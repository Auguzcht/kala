# APPROVAL-07 coordinator baseline and dispatch

2026-10-25. Runtime/publication baseline: `da765cbd27bd06c53c04ef3698c9410b503eb94a`, after DOCS-HYGIENE and TOUR-REFRESH. Local coordinator requirements are committed before lane implementation; no hosted interaction, push or deployment is authorized to agents in this round.

## Lane ownership and release

| Lane | Branch | Initial phase | Serialized / forbidden paths |
| --- | --- | --- | --- |
| SEC / WI-26 | `codex/wi26-course-authorization` | Full route/direct-read/RLS inventory, then guard-only fixes and local policy proof under INSTR-REQ-009 / TWIN-REQ-009 | Router guards first; diagnostic only three explicitly amended routes. Never change helper/defaults, preview or queue logic. Hand router ownership to H only after SEC merge. |
| H / WI-25 | `codex/wi25-evidence-history` | Query, shared-ledger frontend and optional index after TWIN-REQ-010 / INSTR-REQ-010 commit | No dashboard/twin router edits until SEC merges and coordinator releases route phase; no shared spec/generated type edits. |
| M / WI-24 | `codex/wi24-identity-repair` | All-reference/constraint/trigger inventory, own runbook design before script, local synthetic proof | Script/tests/fixtures/repair runbook/WI-24 only; no application code or hosted connection. Stop before FG-7a. |

All three run on GPT-6.1 sol in separate managed worktrees/chats. The coordinator alone edits shared specs and generated OpenAPI/API types. SEC spec commit `cf9f2b3`; H spec commit `9c24a85`; APPROVAL-07 recorded at `d75284e`, amendments at `b938c96`. WI-24/25/26 remain open, with ITO as work-item owner, until actual delivery and live acceptance; no identity repair or security completion is inferred from local tests.

## Resolved blocking contradictions

- Brief named nonexistent evidence `occurred_at`; source `0001_init.sql:184` and current API use `created_at`. Fred's Amendment 1 authorizes `(created_at DESC, id DESC)` and preservation of both `createdAt` response and exact stored timestamps during repair. Only index schema changes are allowed for H.
- Brief's outside-course 403 test contradicted the existing helper's 404 and existence-hiding pattern. Amendment 2 requires role denial 403 and course/learner/institution denial 404, including gradebook consistency. INGEST-REQ-001 was amended before implementation.
- Refresh is in the required inventory but was outside the diagnostic edit restriction. Amendment 3 adds only refresh-route guard calls to the two gradebook guard edits; all other diagnostic behavior stays unchanged, proved by AST/diff. Staff guards in other unowned router files are explicitly in SEC scope. Any fix needing more than guards or another active lane's file stops.

## Integration and human gates

Merge SEC, H, then M after green reports, preserving existing migration bytes. Run full API/worker/frontend/browser/tour suites, lint/typecheck/build, docs policy and migration checksums. Any 0038 policy tightening or 0039 index must run locally first with exact runbooks. No earlier approval to push carries through this round.

Fred runs FG-6 reviewed migrations; FG-8 deploy/alias/worker/push/Vercel; FG-7a counts-only dry run; planner reviews; FG-7b apply/post-checks/recompute; FG-9 live click-through. Before each gate the coordinator supplies name, exact steps, expected result and rollback. Repair rollback exists before FG-7a. No worktree cleanup or confirmed-done status precedes the actual closing evidence. If SEC is not green, flag it explicitly for Fred's release decision.

## Immutable migration baseline

SHA-256 of original bytes at the published baseline. All 37 current files match exactly before this round. The only possible new files this round are authorized numeric 0038 (policy tightening) and 0039 (index only). Historical path comments, including 0036, remain untouched.

| File under packages/db/migrations | SHA-256 |
| --- | --- |
| `0001_init.sql` | `bed15c8b58df5ba6814a0005e67defa2745b0105be78d513594d7f27c4b74014` |
| `0002_rls.sql` | `9a6059760d337fa2a43cf73c91db7d866467faf85066d3aed5d51180aa707dfc` |
| `0003_research.sql` | `17d4439e055517eab43e38a278df8b0be99c455468339f60df7d2630c3027cde` |
| `0004_rag.sql` | `c5cb082ff8d89d42a40f4855f21e308174a1d01227b7536a870ee05865ee227f` |
| `0005_learn_items.sql` | `811055624eb088505e142d41e96fbf61cc40b52efa82bfa7fed86fa9b0b7b5c8` |
| `0006_module_scope.sql` | `d71064f81f39eb690cfb72a17086c9166489ea7bbe0438811a62d405b8909876` |
| `0007_skill_proposals.sql` | `8684ed5c32f61bf5c15daadb1263f94f1e86c3be32bc532833cd07aece470f18` |
| `0008_learn_loop_v2.sql` | `bf3b573673de77d0c6905eea368f1f9f4494297b4258e38ce1653ccad7e5ac18` |
| `0009_teacher_loop.sql` | `790eff8ccf7d617044134b0d0f1f42ea6184e56dff58bc95229e73e855635fd6` |
| `0010_tutor_sessions.sql` | `17ac3cfbaec8a490c9445a7769469e56a6c69056f7a775dfa117a9c1a4d2243f` |
| `0011_tutor_attachments.sql` | `a810cb0bda689c37ae219dd51ec9590cdd39753b56cca095496be57052a34e48` |
| `0012_quiz_sets.sql` | `019312a6a931c2738077ab15bd7a7f89ca927dbbe3a55ca1058bb9e80f7aef47` |
| `0013_quiz_set_attempts.sql` | `2f69ff2d5f1a17badbd3418f84cc00e983703039783b303faf09c598028ca6c6` |
| `0014_content_tag_attempted.sql` | `d343f0fb479a134d17155169a6ccf220502fc07c90993b7e876bf60945e03d31` |
| `0015_lms_identity_aliases.sql` | `eb9e7cb3b026b4163d0b36679568b772f9d49afd45a86181d5c4c06944c6d506` |
| `0016_lms_course_resolution_cache.sql` | `47612526a9d0d54d2612a0ec8bebf72391ac051bb776edf369c2a97848933a74` |
| `0017_ingest_jobs.sql` | `7422d13fcfeb227786d724b922ede5e33ed82c6ce459a23fbbbba61ca8147870` |
| `0018_ingest_job_dedupe_and_backoff.sql` | `e944472ad9d5f9439b22ef2524a6ab81ef77c38907624e0a7ebd134d4c1bc118` |
| `0019_async_item_generation.sql` | `11ca0c75f38e8428b8c15e47a158f97d757f54c2ed3103433c47bf13e3105759` |
| `0020_async_lesson_checks.sql` | `e26b52ae741d6556c775c00b4893faee4c5d52462f08329e61a4c6314b83eeb3` |
| `0021_question_bank.sql` | `6e4321105382dbbf90b58a5a080fad7e4e07b8f53b7f0deeb68ef7d4ae43d3a0` |
| `0022_embedding_tags.sql` | `5d941603b704f6dcc7e7d9bcb35c6efbcc3516fc085b4b2acfd6566e8f8fbab5` |
| `0023_course_scoped_staff_reads.sql` | `80ce90cab174e7c76f9d7e3af85609fa1bec93adc425d4086d5dd111269f16ef` |
| `0024_bank_saturation.sql` | `e1ff601f6ca46d4695aecd36054429b58639dc9aedffb01062ae71a2d4d9408f` |
| `0025_reject_approved_skill_retire_bank_items.sql` | `3ad9e644622b47351b5fedab33bf09800036a96faad349d2d03edea28c6f524e` |
| `0026_card_memory.sql` | `1e18ee6fc09f07b2900073439a4f973cfe164ba9a93b144eaef70201465d2765` |
| `0027_item_reviews.sql` | `352b0559a63dcda2691986a6d22256231481fa278b4a91747f3867a71f446102` |
| `0028_practice_item_reviews.sql` | `f8ae4ed6305b91d3b2aea1f5574a696e46ba3b9eaa8e40980585161ea0dbd9a3` |
| `0029_card_memory_session_modes.sql` | `2df0665bdc966a51b09605181e28593e828e08d81f2956f0e06444f2f01bf81d` |
| `0030_card_memory_daily_cap_accounting.sql` | `cf661628f8ae78d8a0f765b539c4c01189c8ab95c2ba0a820c4c8e7006ed9404` |
| `0031_atomic_practice_submit.sql` | `e97fd3a32ab98aa3eae77a52c636be14ec05a2140525e0238b3a805acf6938f7` |
| `0032_practice_answer_recap.sql` | `7ea6b8cc5f7f6fd7fb5d84d7eaaf5a5258ac776ec78b9655efef4c173b953a64` |
| `0033_bulk_practice_set_exposures.sql` | `5922be3dac86a541695bb9675566db15efe95b83cefa651f0e72206e7eff4369` |
| `0034_attempt_aware_practice.sql` | `2f20a8e9bdc7351d9f7763aa3a80bc5a1eac3203c2fc02f715c8de1ad6ce88c6` |
| `0035_fix_submit_practice_ambiguity.sql` | `8eb3dad5f15ba590b25cf632a0c5b5f2ec3f868b46864ab085df141defb1d448` |
| `0036_bank_lesson_embeddings.sql` | `8de747c633647e732c7181aca35c24cd6e57e70055c8b502b9d6a24e67d20ac9` |
| `0037_tutor_conversation_pin.sql` | `82c9297ea08b4c16c3ba03bb2cc64eb222e67dd4276e9b4f7a8db22efe873450` |

## Frontend denial-state finding for H/U

Static review under Amendment 2: `RosterTable.tsx` only consumes data/isLoading and defaults missing students to an empty array; `AtRiskList.tsx` similarly defaults absent flags to an empty list. A failed 404 can therefore look like an empty class or no support concerns. `CohortStats.tsx` keeps its skeleton when data is absent even after an error. `LearnerRecord.tsx`, `StudentDrillDown.tsx` and Heatmap show an error state rather than crash, but their generic “Check your connection” copy does not distinguish a non-disclosing 404. These are source findings, not a fresh browser reproduction. Recorded for H/U as requested; no API denial or frontend behavior is changed by this note. H owns history callers, not a general dashboard redesign. Live URL refusal remains an FG-9 case, and no UI completion is claimed.
