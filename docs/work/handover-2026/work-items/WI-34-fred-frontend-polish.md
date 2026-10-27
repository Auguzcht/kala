---
id: WI-34
status: in-progress
owner: Fred; coordinator for specs/privacy audit/final checks
---

# Fred's direct frontend polish

Source base eb9409a8dc5617f01f9dc20d888775009894ec78; branch codex/fred-polish. Brief: [APPROVAL-09](../approval-09.md). Intended behavior is TUTOR-REQ-017/018, TWIN-REQ-003/010/011, INSTR-REQ-010 presentation and DESIGN-REQ-001/002. Sent-message edit remains deferred, TUTOR-REQ-015 / WI-29.

Coordinator specifies first and prepares the workspace; Fred writes UI code. Web server runs only from this worktree on5173. Existing web configuration uses the deployed API; local interactions can write hosted rows. No second local API is currently needed. If started later with existing env, it also uses hosted Supabase.

Fred classifies Hello Clyde as course material under Amendment1: one embedded AWS101 chunk, all reported own-history/attachment/profile/memory and ownership-mismatch counts zero; no cross-user data reported. Attribution remains limited because request retrieval results are not retained. Queries were prepared and not run by Codex; sanitizer/cache/hosted changes stay prohibited, with only the separate Amendment1 prompt literal/test exception allowed. A cross-user finding stops all work. Course names and ordinary personal names are not comprehensively removed by the existing sanitizer; do not infer source from a greeting alone.

After Fred finishes, coordinator reviews the bounded diff and runs affected browser/E3/web/docs checks, then reports and stops. Fred separately delegates any final push. No code implementation, final acceptance, hosted query or data repair is inferred from setup/specification work.

## Verified by

- [Input trace and unresolved classification](../evidence/approval-09-privacy-trace.md)
- [Prepared COUNT query, not executed](../evidence/approval-09-clyde-counts.sql)

Amendment1 grants the separate _SYSTEM-only backend branch codex/no-name-greeting under TUTOR-REQ-019, with E1 AST/19-guard proof and full API/enrollment tests. This narrow grant supersedes the backend stop only for that literal and existing test extension. Combined integration waits for Fred's frontend completion/checks; no deploy or push is delegated.

Preparation: frontend specs223aa36 committed before edits; web5173/PID40695/HTTP200 verified. Separate prompt candidate65e539a passes API1016, enrollment116, E1 and19-guard proof; it remains unmerged until Fred's UI checks pass. No frontend application edits were made by Codex.
