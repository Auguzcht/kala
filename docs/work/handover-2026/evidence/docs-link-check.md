# Documentation link check — 2026-10-24

Scope: all `docs/**/*.md`, plus root/folder agent guides. Local static filesystem/Markdown heading check at base `e9de105` plus Lane D changes. No external URL fetch, server, app import or network call.

## Result

- 96 docs files plus 31 root/folder agent guides checked.
- 650 local Markdown links checked; 6 external links not fetched.
- 46 unresolved link occurrences under docs/ plus 13 in agent guides; 31 distinct absent targets.
- **Zero unexpected broken targets.** The checker exits 0 only because every unresolved target is explicitly classified as excluded cross-lane work or not-yet-authored documentation. This is not a claim that all links resolve.

## Missing destinations by responsibility

| Category | Unique absent targets | Link occurrences |
| --- | ---: | ---: |
| full spec not yet authored (WI-08) | 13 | 23 |
| cross-lane file excluded from D | 6 | 23 |
| full runbook not yet authored (WI-06/07) | 11 | 12 |
| engineering policy not yet authored (WI-08) | 1 | 1 |

The six excluded files belong to S/T/F/C/DB and are intentionally not authored by D. Full feature specs remain WI-08, full runbooks WI-06/WI-07. `engineering/security-and-privacy.md` is a remaining cross-cutting authoring gap. No placeholder or invented feature requirement closes these gaps. The two existing runbook extracts (database setup and deploy backend) are partial and unverified, so link existence does not imply operational completeness.

## Every unresolved link occurrence

| Source | Target | Classification |
| --- | --- | --- |
| `apps/web/src/features/auth/CLAUDE.md:1` | `docs/features/lti-auth/README.md` | full spec not yet authored (WI-08) |
| `apps/web/src/features/bank/CLAUDE.md:1` | `docs/features/question-bank/README.md` | full spec not yet authored (WI-08) |
| `apps/web/src/features/courses/CLAUDE.md:1` | `docs/features/lti-auth/README.md` | full spec not yet authored (WI-08) |
| `apps/web/src/features/diagnostic/CLAUDE.md:1` | `docs/features/diagnostic/README.md` | full spec not yet authored (WI-08) |
| `apps/web/src/features/flashcards/CLAUDE.md:1` | `docs/features/study/README.md` | cross-lane file excluded from D |
| `apps/web/src/features/gamification/CLAUDE.md:1` | `docs/features/gamification/README.md` | full spec not yet authored (WI-08) |
| `apps/web/src/features/instructor/CLAUDE.md:1` | `docs/features/instructor-insights/README.md` | full spec not yet authored (WI-08) |
| `apps/web/src/features/lessons/CLAUDE.md:1` | `docs/features/lessons/README.md` | full spec not yet authored (WI-08) |
| `apps/web/src/features/plan/CLAUDE.md:1` | `docs/features/instructor-insights/README.md` | full spec not yet authored (WI-08) |
| `apps/web/src/features/practice/CLAUDE.md:1` | `docs/features/practice-tests/README.md` | full spec not yet authored (WI-08) |
| `apps/web/src/features/skill-hub/CLAUDE.md:1` | `docs/features/study/README.md` | cross-lane file excluded from D |
| `apps/web/src/features/tutor/CLAUDE.md:1` | `docs/features/tutor/README.md` | cross-lane file excluded from D |
| `apps/web/src/features/twin/CLAUDE.md:1` | `docs/features/twin/README.md` | full spec not yet authored (WI-08) |
| `docs/README.md:14` | `docs/engineering/secrets.md` | cross-lane file excluded from D |
| `docs/README.md:14` | `docs/engineering/runbooks/key-rotation.md` | full runbook not yet authored (WI-06/07) |
| `docs/README.md:15` | `docs/engineering/database.md` | cross-lane file excluded from D |
| `docs/README.md:16` | `docs/engineering/database.md` | cross-lane file excluded from D |
| `docs/archive/incidents/INC-002-tutor-30s.md:2` | `docs/features/tutor/README.md` | cross-lane file excluded from D |
| `docs/engineering/environments.md:37` | `docs/engineering/secrets.md` | cross-lane file excluded from D |
| `docs/engineering/local-development.md:15` | `docs/engineering/secrets.md` | cross-lane file excluded from D |
| `docs/engineering/local-development.md:15` | `docs/engineering/database.md` | cross-lane file excluded from D |
| `docs/engineering/runbooks/02-database-setup.md:15` | `docs/engineering/database.md` | cross-lane file excluded from D |
| `docs/engineering/runbooks/README.md:7` | `docs/engineering/runbooks/aws-account-bootstrap.md` | full runbook not yet authored (WI-06/07) |
| `docs/engineering/runbooks/README.md:9` | `docs/engineering/runbooks/blackboard-learn-instance.md` | full runbook not yet authored (WI-06/07) |
| `docs/engineering/runbooks/README.md:10` | `docs/engineering/runbooks/anthology-developer-app.md` | full runbook not yet authored (WI-06/07) |
| `docs/engineering/runbooks/README.md:11` | `docs/engineering/runbooks/secrets-manager.md` | full runbook not yet authored (WI-06/07) |
| `docs/engineering/runbooks/README.md:12` | `docs/engineering/runbooks/terraform-apply.md` | full runbook not yet authored (WI-06/07) |
| `docs/engineering/runbooks/README.md:14` | `docs/engineering/runbooks/lti-tool-registration.md` | full runbook not yet authored (WI-06/07) |
| `docs/engineering/runbooks/README.md:15` | `docs/engineering/runbooks/vercel-web.md` | full runbook not yet authored (WI-06/07) |
| `docs/engineering/runbooks/README.md:16` | `docs/engineering/runbooks/first-launch-smoke.md` | full runbook not yet authored (WI-06/07) |
| `docs/engineering/runbooks/README.md:17` | `docs/engineering/runbooks/key-rotation.md` | full runbook not yet authored (WI-06/07) |
| `docs/engineering/runbooks/README.md:18` | `docs/engineering/runbooks/incident-response.md` | full runbook not yet authored (WI-06/07) |
| `docs/engineering/runbooks/README.md:19` | `docs/engineering/runbooks/blackboard-instance-ops.md` | full runbook not yet authored (WI-06/07) |
| `docs/engineering/runbooks/deploy-backend.md:17` | `docs/engineering/secrets.md` | cross-lane file excluded from D |
| `docs/features/README.md:9` | `docs/features/lti-auth/README.md` | full spec not yet authored (WI-08) |
| `docs/features/README.md:10` | `docs/features/lms-ingest/README.md` | cross-lane file excluded from D |
| `docs/features/README.md:11` | `docs/features/skills/README.md` | full spec not yet authored (WI-08) |
| `docs/features/README.md:12` | `docs/features/question-bank/README.md` | full spec not yet authored (WI-08) |
| `docs/features/README.md:13` | `docs/features/diagnostic/README.md` | full spec not yet authored (WI-08) |
| `docs/features/README.md:14` | `docs/features/lessons/README.md` | full spec not yet authored (WI-08) |
| `docs/features/README.md:15` | `docs/features/study/README.md` | cross-lane file excluded from D |
| `docs/features/README.md:16` | `docs/features/practice-tests/README.md` | full spec not yet authored (WI-08) |
| `docs/features/README.md:17` | `docs/features/tutor/README.md` | cross-lane file excluded from D |
| `docs/features/README.md:18` | `docs/features/twin/README.md` | full spec not yet authored (WI-08) |
| `docs/features/README.md:19` | `docs/features/instructor-insights/README.md` | full spec not yet authored (WI-08) |
| `docs/features/README.md:20` | `docs/features/gamification/README.md` | full spec not yet authored (WI-08) |
| `docs/features/README.md:21` | `docs/features/ai-platform/README.md` | cross-lane file excluded from D |
| `docs/features/README.md:22` | `docs/features/tour/README.md` | full spec not yet authored (WI-08) |
| `docs/features/README.md:23` | `docs/features/admin/README.md` | full spec not yet authored (WI-08) |
| `docs/features/README.md:24` | `docs/features/research/README.md` | full spec not yet authored (WI-08) |
| `docs/features/README.md:25` | `docs/features/grade-passback/README.md` | full spec not yet authored (WI-08) |
| `docs/features/README.md:27` | `docs/engineering/security-and-privacy.md` | engineering policy not yet authored (WI-08) |
| `docs/work/handover-2026/README.md:26` | `docs/features/lms-ingest/README.md` | cross-lane file excluded from D |
| `docs/work/handover-2026/README.md:27` | `docs/features/tutor/README.md` | cross-lane file excluded from D |
| `docs/work/handover-2026/README.md:27` | `docs/features/ai-platform/README.md` | cross-lane file excluded from D |
| `docs/work/handover-2026/README.md:28` | `docs/features/study/README.md` | cross-lane file excluded from D |
| `docs/work/handover-2026/README.md:29` | `docs/engineering/secrets.md` | cross-lane file excluded from D |
| `docs/work/handover-2026/README.md:31` | `docs/engineering/database.md` | cross-lane file excluded from D |
| `docs/work/handover-2026/README.md:50` | `docs/engineering/database.md` | cross-lane file excluded from D |

## Method and limits

The task-owned Python checker scans inline Markdown links/images and reference-link definitions outside fenced code, resolves relative paths, validates Markdown heading fragments, and checks numeric source-line anchors against file length. It retains line locations for every finding. It does not fetch external URLs, validate bare paths/backticked examples, execute scripts, resolve templated paths, or prove that historic source-line claims still describe current behavior. It is a targeted local check, not a complete CommonMark parser or a feature-conformance test. Audit line labels retain original e9de105 numbering even when archive headers add lines.

Temporary/worktree links have been adapted to repository-relative evidence/archive destinations, including source links in the accepted inventory. Deleted patch proof uses Git history references; generated local-only exports/caches and unpromoted scratch metadata are named historical artifacts without false live links. Zero absolute local Markdown link targets remain under docs/.

Exact command (exit 0 with categorized expected gaps):

```sh
python3 /Users/fred/.codex/visualizations/2026/10/24/01a16e82-b88c-7ee1-b65d-be93d8bef6db/lane-d/check_docs_links.py
```

The full categorized result is preserved above; helper code/JSON is external task scratch and is not copied into the repository. No live smoke, Blackboard or hosted check was run.
