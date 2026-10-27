# APPROVAL-09 Amendment1 — prompt-only no-name greeting

Base: eb9409a8dc5617f01f9dc20d888775009894ec78 (main). Branch codex/no-name-greeting, separate managed worktree. TUTOR-REQ-019 and its change log were committed first at e784d01 before implementation. Source/test changes are exactly two added string-continuation lines in the existing _SYSTEM constant and two assertions in the existing small-talk test.

New prompt instruction: “Never address the student by name. Treat any names in course material as people in the material, not the student.” No other prompt string, import, signature, function, guard, model setting, provider routing or persistence changes.

## Classification provenance

Fred reports one embedded AWS101 chunk containing the name; prior history, attachments, own display name and memory tables have zero matches; attachment ownership mismatches zero, no cross-user data. Classification: **course material**. The found source is not proof of retrieval in that request because per-request retrieval results are not retained. Ordinary names in course material reach the model under the existing sanitizer, which removes emails and explicit name: patterns only. Codex ran no hosted query and retained no user identifiers or raw content. This prompt instruction is not a sanitizer fix or a guarantee of live model compliance.

## E1 proof

Both source modules parse _SYSTEM as exactly one module-level string Constant. Replacing only that value with an identical sentinel makes their complete AST dumps equal, excluding source positions. This proves every other executable node, import, guard and signature in tutor.py is unchanged.

All19 previously guarded functions are AST-identical to the approved base. The seven other router files are additionally byte-identical:

| Router | Identical guarded functions |
| --- | --- |
| courses | get_course, memory_summary |
| twin | get_twin, next_up, learning_plan |
| diagnostic | get_content, list_modules, get_diagnostic_status, get_diagnostic |
| flashcards | skill_cards, deck |
| gamification | summary |
| practice | next_item, list_sets, get_set, get_set_results |
| lessons | get_lesson |
| tutor | list_conversations, get_conversation |

The existing test captures the actual provider-bound system prompt for default/detail variants and now asserts both no-name/material-person rules. Every prior safety, style and small-talk assertion remains. It is a mocked-provider contract test, not a prediction that the live provider always follows the rule.

## Checks

- `uv run pytest` from services/api: **1,016 passed**,30 existing dependency warnings; dotenv disabled, generated test signing key and IPv4/IPv6/DNS blocked by committed conftest.
- `uv run pytest tests/test_wi26_student_read_admission.py`: **116 passed**.
- E1 full-module AST and19-function comparison: **PASS**.
- Source diff: only _SYSTEM in the application, plus the two test assertions; no unrelated backend path, migration, config, secret or infrastructure change.
- Docs checker/unit and whitespace checks run before the candidate commit. No frontend checks or combined-branch acceptance is inferred from these API results.

## Integration boundary

Do not merge this branch until Fred finishes APPROVAL-09 frontend work and its lint/typecheck/build, affected browser suites, E3 and docs checks pass. Coordinator then integrates both with the Tutor spec retaining frontend REQ-017/018 and prompt REQ-019. Fred runs make deploy for the backend and separately delegates frontend publication. No deploy, push, hosted action, sanitizer change or sent-message edit is delegated to Codex. Live greeting acceptance follows the new human deployment, not this local test run.

```text
AUDIT REPORT
Task / brief ID: APPROVAL-09 Amendment1; E1; TUTOR-REQ-019
Branch and worktree: codex/no-name-greeting; separate managed worktree
  (local only, not retained)
Base revision: eb9409a8dc5617f01f9dc20d888775009894ec78
Files changed:
  docs/features/tutor/README.md
  services/api/app/routers/tutor.py
  services/api/tests/test_tutor_small_talk_approval08.py
  docs/work/handover-2026/evidence/approval-09-no-name-greeting.md
REQ / WI IDs touched: TUTOR-REQ-019; AUTH-REQ-007 preserved; WI-34
Commands run and results: full API1016; enrollment116; E1/19 guards pass;
  docs/unit/whitespace checked before commit as recorded in final response.
Spec changes made: REQ-019 and change log first at e784d01.
Evidence added: this prompt-only implementation report; Fred-provided
  course-material classification, without raw hosted rows.
Anything not done, and why: combined merge awaits Fred's frontend edits
  and checks; no deployment/publication or live greeting check.
Risks or questions for the planner: material names still pass the limited
  sanitizer; prompt compliance is not proven by mocked tests.
Secrets printed: none (confirmed).
```
