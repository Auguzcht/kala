# APPROVAL-03: tutor acceptance and local integration

Decision source: Fred's explicit approval in the coordinating chat, 2026-10-24.
This supplements [APPROVAL-02](approval-02.md); this decision controls the push gate.

1. Lane T at `b605a3b` is approved. Merge to local main after F.
2. Implement APPROVAL-02 section 5: one shared committed conftest.py that disables dotenv, supplies fake test-only configuration including a generated JWT signing key, and blocks network sockets. `cd services/api && uv run pytest` must work in a fresh clone with no .env. Replace the Study runner and T's scratch runner. Existing test bodies may change only in imports. Add the planned frontend-runner work item.
3. On merged local main run and report counts for the full API suite, worker suite, 14 tutor/error/schema frontend tests, four Study component tests, web lint, typecheck, build and config_inventory --check. Inspect `git diff --stat e9de105..main` for migration and infra/terraform changes.
4. If all checks pass, stop and report the final local main SHA. **Do not push. Fred deploys the backend first, then pushes.** No agent deployment is authorized.

Coordinator scope finding, 2026-10-25 (not an additional user approval): the approved D archive move previously removed `infra/terraform/lambda.tf.NOTE.md`; this is a documentation path under infra/terraform. Report it explicitly rather than claiming zero paths changed there. No decision to undo that approved archive move is implied.
