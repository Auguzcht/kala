# APPROVAL-02: implementation review and integration gates

Decision source: Fred's explicit approval in the coordinating chat, 2026-10-24.
This supplements [APPROVAL-01](approval-01.md). Later approval controls where the two differ.

1. Lane C and Lane D are approved. Merge C, then D to main. Documentation/tooling only; no deploy.
2. Lane S (`49fb07a`) is approved. Merge after D.
3. Lane F (`8e06e6a`) is approved on conditions, within F's paths:
   - Add native flip cards in Study fresh selection (`include_flashcards`) as STUDY-REQ-004 and the Preparing empty-state fix as STUDY-REQ-005 in the Study spec, with rationale and a change-log line citing APPROVAL-02. Name tests accordingly. Revert either if it cannot be justified as fixing the same caught-up-while-cards-remain defect class.
   - Record the external renderer fixture dependency as a known limitation. Add no dependencies now.
   - Merge after S once these conditions are met.
4. Lane T must finish granted TutorChat work, then rerun the full API suite and web lint, typecheck and build, and return a refreshed AUDIT REPORT. Add to TUTOR-REQ-001's known limits that on Lambda an abandoned synchronous call can resume when the warm environment serves the next request. **Do not merge T until Fred approves the refreshed report.**
5. Coordinator integration commit, after S, F and T are on main and before push:
   - Commit one shared test isolation in conftest.py so `cd services/api && uv run pytest` passes in a fresh clone without .env. Disable dotenv, set fake test-only environment values including a generated JWT signing key, and block network sockets. Replace run_study_checks.py and T's scratch runner with it. Do not edit test bodies beyond imports.
   - Run full API suite, worker suite, web lint, typecheck and build on merged main. Report counts. Push only if all pass; fast-forward only.
   - Add a planned work item: Adopt a standard frontend test runner (e.g. Vitest) so component tests run without external fixtures.
6. Report the names, never values, of credentials in Lane S's tool-output exception and add them to the exposure log. Rotation happens at cutover.
7. Lane DB stays gated on the hosted Postgres major.

**No deploy until Fred confirms the integrated report.** Merge, push, deployment and live verification are distinct facts. This approval does not authorize a T merge, an early integration commit, or a deployment.
