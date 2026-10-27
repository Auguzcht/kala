---
id: WI-34
status: in-progress
owner: Fred; coordinator for specs/privacy audit/final checks
---

# Fred's direct frontend polish

Source base eb9409a8dc5617f01f9dc20d888775009894ec78; branch codex/fred-polish. Brief: [APPROVAL-09](../approval-09.md). Intended behavior is TUTOR-REQ-017/018, TWIN-REQ-003/010/011, INSTR-REQ-010 presentation and DESIGN-REQ-001/002. Sent-message edit remains deferred, TUTOR-REQ-015 / WI-29.

Coordinator specifies first and prepares the workspace; Fred writes UI code. Web server runs only from this worktree on5173. Existing web configuration uses the deployed API; local interactions can write hosted rows. No second local API is currently needed. If started later with existing env, it also uses hosted Supabase.

Privacy classification of Hello Clyde is pending Fred's scoped COUNT results. Queries are prepared, not run; no backend/sanitizer/prompt or hosted change. A cross-user finding stops all work. Course names and ordinary personal names are not comprehensively removed by the existing sanitizer; do not infer source from a greeting alone.

After Fred finishes, coordinator reviews the bounded diff and runs affected browser/E3/web/docs checks, then reports and stops. Fred separately delegates any final push. No code implementation, final acceptance, hosted query or data repair is inferred from setup/specification work.

## Verified by

- [Input trace and unresolved classification](../evidence/approval-09-privacy-trace.md)
- [Prepared COUNT query, not executed](../evidence/approval-09-clyde-counts.sql)
