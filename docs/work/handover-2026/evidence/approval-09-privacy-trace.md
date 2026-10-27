# APPROVAL-09 — Hello Clyde input trace, read-only

Source boundary: eb9409a8dc5617f01f9dc20d888775009894ec78. Fred reports that a Tutor conversation on the Hanna Sato account greeted the user as Clyde. This report contains no hosted reads, captured model payload, private identifier or user message. No backend, prompt, sanitizer, cache or privacy fix is authorized here.

## Result and classification boundary

**Origin not yet classified.** Source inspection does not establish which input contained the name for this request. No cross-user leak has been demonstrated, and this is not a claim that one is ruled out. Fred must run the scoped count query privately and return counts only. A cross-user leak finding stops all APPROVAL-09 work immediately. No name match alone proves identity leakage or the exact retrieved model input.

The current code has no Clyde literal in production application source. Ordinary proper names survive the sanitizer. Course material, this user's prior turns/current question, and owned attachment filenames/text can therefore supply the name. A generated name with no matching retained input is also possible; do not force an unsupported classification into one of the three requested outcomes.

## Every model-bound input

| Input and source at the boundary | Can a person's name reach the provider? | Sanitizer / scope |
| --- | --- | --- |
| System and style strings: services/api/app/routers/tutor.py:61 and:77; passed at:484 | No dynamic person/profile input; static tutor/small-talk/teaching instructions. No Clyde literal found | app/ai/router.py:107–113 sanitizes the system string in budgeted Tutor calls. No prompt change made |
| Current question: tutor.py:458–462 and:479–481 | Yes, ordinary proper names survive | strip_pii before embedding/retrieval; safe_context on assembled prompt; router.answer sanitizes text again |
| History: tutor.py:446–456 | Yes, in either this user's question or Kala's earlier reply | Last10 messages of an owned conversation; strip_pii per message, then router.answer again. A prior generated name can recur |
| Retrieved chunks: tutor.py:458–464; ai/rag.py:13–27; immutable0004_rag.sql:17–18 | Yes, names embedded in course text survive | Institution/course-scoped vector query; returned chunk_text joins into safe_context, then router.answer. Retrieval is course-wide, not limited by the conversation's optional skill_id |
| Attachments: tutor.py:466–477 | Yes, both filename and extracted text may carry ordinary names | Ready attachments of the already-owned conversation, per-file/total bounded text; safe_context and router.answer sanitize assembled text. Upload ownership is checked before metadata/storage writes |
| Memory/summary | No separate personal memory or summary enters this Tutor call | _ask has no memory/summary lookup. courses.py:40–77 memory/summary computes card/SRS counts, not a free-text conversation memory. It is not called by _ask |
| Profile/display name | No direct profile/display-name value is passed by this call path | CurrentUser uses validated token identifiers/role, not profile text (deps.py:145–149). Frontend TutorChat.tsx:97 uses displayName for UI initials only. safe_context emits an eight-character subject identifier, not a display name |
| Primary/fallback handoff | Same already-sanitized system/messages can reach either provider | ai/router.py:104–124 constructs the budgeted call; ai/bedrock.py:153–202 reuses its request for fallback. There is no separate unsanitized fallback prompt |
| Embedding provider | The question can carry ordinary names to the embedding provider | ai/rag.py sanitizes the query before embed; this is separate from the chat provider. The name-removal limitation is the same |

app/ai/deidentify.py:10–20 removes emails and explicit name:/姓名: patterns only. It does not remove an ordinary greeting, a standalone person name, student IDs, all profile-like text or every form of personal data. Repeated sanitization does not make it comprehensive.

## Ownership and retrieval boundaries

_owned_conversation (tutor.py:137–152) filters conversation id, validated user id and institution id before history/attachment reads. Message and attachment reads subsequently filter by that conversation id. RAG passes current institution and the owned conversation's course (or the stateless request course) to match_content_items. The RPC's SQL has explicit institution/course predicates. Direct profile, display-name and cross-user-memory reads are absent from this model-input path.

These source guards do not certify the incident's actual launch identity, database ownership, historical prompt or browser cache. The previously retained student-mutation admission limitation is not silently fixed or reclassified here. No live LTI flow, current token, other user's conversation or provider log is inspected by Codex.

## Counts Fred can return — no rows

Prepared query: docs/work/handover-2026/evidence/approval-09-clyde-counts.sql. **Not run.** Fred privately fills institution, the validated account's user id, its conversation id and the first offending assistant-message id. The query searches only that conversation's course material, prior owned history, own attachments and own profile, plus schema metadata. It never searches another user's text. An attachment ownership-integrity count examines metadata only and emits no identifiers/content.

The offending answer is excluded from the prior-history window, avoiding the circular conclusion that the name was an input just because it now appears in the reported answer. Same-timestamp user-message counts are a bounded diagnostic; paired persistence and equal timestamps do not reconstruct the original request exactly. Present-day corpus/profile/attachment counts cannot prove what was retrieved at incident time. There is no invented memory table or SQL helper.

- Require owned_conversation_count=1 and incident_message_count=1. Otherwise stop and privately validate scope; do not infer absence or read foreign content.
- A positive course chunk count supports the **course material** candidate. It is shared course context, not a direct user-profile input. Record that proper names in course material can reach the model, but this count alone does not prove the chunk was one of the five retrieved.
- A positive prior-history/current-question count supports **this user's own history/input**. Split user and assistant counts to distinguish a name the user supplied from one Kala previously generated. This does not establish the origin of the first occurrence.
- Own attachments are a separate owned-input candidate; do not mislabel them as a cross-user leak or ordinary course material merely to fit a category.
- Any ownership mismatch or evidence of foreign private context means **cross-user leak investigation / immediate stop and report**. A count of zero outside a valid target is not proof of safety. Do not expand the search to other users' content.
- If all candidate counts are zero, or more than one input could explain the name, classification remains unresolved. Fred/planner review is required before any fix or further access.

The prepared source audit is complete; incident classification is pending Fred's counts and planner review. No fix, hosted action or repair was performed.
