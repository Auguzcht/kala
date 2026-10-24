---
runbook: vercel-web
applies_to: [dev-hosted, prod]
who_runs_it: Vercel project owner and API / ITO maintainer
time_needed: "[Fred to confirm]"
last_verified: "unverified; source review at 4f3ec29 on 2026-10-25, Lane R"
status: in-progress
---

# Runbook 09 — publish the web application

## When to use it

Create an institutional SPA deployment or update approved public build settings. WI-07 draft; the human project owner publishes and the infrastructure owner approves backend-origin changes. This lane does not deploy or edit Vercel configuration.

## Before you start

Have the approved source/repository access, institutional Vercel team/domain owner, [02](02-database-setup.md)'s database and [06](terraform-apply.md)'s API. Obtain only public browser configuration through [secrets.md](../secrets.md). Team/project identity, Git integration and production-branch policy: [Fred to confirm].

## Steps

1. In the institutional Vercel team, import the approved Git repository. Select the Vite application rooted at `apps/web`. Source scripts support a production build using `pnpm build` there and output `dist`. Exact dashboard root/build/install settings for this monorepo and locked pnpm version: [Fred to confirm]. Check the plan uses the reviewed revision and root workspace lockfile.
2. Set only the public browser settings listed in the catalogue for the intended deployment environment. Check API/database hosts match that environment and never place a service credential in a public variable. Vite embeds these values at build time; a change requires a new build/deployment. Current Vercel environment scopes and approved values: [Fred to confirm].
3. Run web lint, typecheck and build locally as listed in [local-development.md](../local-development.md), without dumping environment files. The human deploys the approved source through the team's reviewed Git/dashboard workflow. Exact publication control and approver: [Fred to confirm]. No push/deploy is authorized by this draft.
4. Confirm SPA rewrites from [apps/web/vercel.json](../../../apps/web/vercel.json) are active: all application paths resolve to `index.html`. Verify `/launch` and a real course deep link can load directly without 404, using approved synthetic sessions privately. Do not edit hosting files as a workaround under this lane.
5. Configure/verify the approved HTTPS domain privately with the domain owner. Exact DNS records, certificate status and rollback record: [Fred to confirm]. Do not register a temporary preview origin as the final production origin.
6. Coordinate the exact deployed SPA origin with the backend owner. Both Gateway and FastAPI CORS and the launch redirect must agree. `FRONTEND_URL` is declared in Lambda environment by Terraform, so changing only the secret bundle cannot override it. Follow [05](secrets-manager.md)/[06](terraform-apply.md) for reviewed changes and [07](deploy-backend.md) for release verification. No ad hoc origin wildcard.
7. Have the named tester launch from Learn via [08](lti-tool-registration.md), then complete [10](first-launch-smoke.md). Confirm the SPA consumes the session fragment without copying the full URL, token, local storage or headers into evidence.

## Verify it worked

Record verifier/date/environment, frontend revision and deployment identifier privately, endpoint hosts, direct-route outcome, no CORS failure, and student/instructor smoke results. A Vercel successful-build badge does not prove LTI or API compatibility. No Vercel project was inspected by Lane R.

## Undo / roll back

The human project owner selects the approved previous deployment only after checking backend/schema/config compatibility. Previous builds retain their embedded public settings. Restore coordinated backend origins if needed through infrastructure review; moving the web domain alone is insufficient. Exact Vercel promotion/rollback controls and DNS TTL expectations: [Fred to confirm].

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Deep link 404s | Wrong root or rewrite not applied | Verify committed Vite rewrite and project root. |
| Old API host still used | Build-time variables unchanged in deployed build | Set intended environment scope and have owner rebuild. |
| Learn redirects to wrong site / CORS denial | Effective backend origin mismatch | Check Terraform-owned Lambda origin and Gateway/FastAPI CORS. |

## Sources

[Web README](../../../apps/web/README.md), [Vercel rewrite](../../../apps/web/vercel.json), [API settings](../../../services/api/app/config.py), [Gateway](../../../infra/terraform/apigw.tf), [launch route](../../../apps/web/src/routes/launch.tsx). Current dashboard settings and live acceptance: [Fred to confirm].

## History

| Date | Change to this runbook | Why |
| --- | --- | --- |
| 2026-10-25 | Draft build, origin and launch checks | APPROVAL-05 rev 2, Lane R, WI-07. |
