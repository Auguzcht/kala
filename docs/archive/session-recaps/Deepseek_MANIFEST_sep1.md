> Archived: 2026-10-24 (Asia/Manila), under APPROVAL-01. Historical source: `docs/Deepseek_MANIFEST_sep1.md` at base `e9de105` / ignored main-only input.
> Replacement: [docs/work/handover-2026/evidence/migration-map.md](<../../work/handover-2026/evidence/migration-map.md>). This original is evidence, not current policy; old commands and next-step queues are not authorization to execute them. Source line references below and in audits refer to the original, before this header.

# Scoped changes — drag-and-replace manifest

Every file in this zip mirrors its path inside `apps/web`, `services/api`,
`packages/db`, and the repo root. Drop each one into the same relative path
in your actual project, overwriting where a file already exists.

## ⚠️ One manual deletion required (not a zip-able change)

Delete this file — it no longer exists in the updated repo and nothing
replaces it at that path:

```
apps/web/src/features/instructor/components/StudentDrillDown.tsx
```

Its job is now split across `LearnerRecord.tsx` and `LearnerSheet.tsx`,
both included below.

## New files (create these paths)

```
packages/db/migrations/0009_teacher_loop.sql
services/api/app/twin/cohort.py
services/api/app/ai/prescriber.py
apps/web/src/features/instructor/CLAUDE.md
apps/web/src/features/instructor/components/CohortStats.tsx
apps/web/src/features/instructor/components/CohortCharts.tsx
apps/web/src/features/instructor/components/RosterTable.tsx
apps/web/src/features/instructor/components/LearnerRecord.tsx
apps/web/src/features/instructor/components/LearnerSheet.tsx
apps/web/src/features/instructor/components/DecisionCenter.tsx
apps/web/src/features/plan/CLAUDE.md
apps/web/src/features/plan/index.ts
apps/web/src/features/plan/api/plan.api.ts
apps/web/src/features/plan/hooks/use-plan.ts
apps/web/src/features/plan/schema/plan.schema.ts
apps/web/src/features/plan/components/InstructorPlan.tsx
docs/DEMO_SCRIPT.md
docs/COMPONENT_AUDIT.md
```

## Modified files (overwrite these paths)

```
services/api/app/routers/dashboard.py       — appended cohort + recommendation endpoints, added imports
services/api/app/routers/twin.py            — appended GET /courses/{id}/plan
apps/web/src/features/instructor/index.ts               — new exports
apps/web/src/features/instructor/schema/instructor.schema.ts — new zod shapes
apps/web/src/features/instructor/api/instructor.api.ts       — new fetch functions
apps/web/src/features/instructor/hooks/use-instructor.ts     — new hooks + optimistic decide
apps/web/src/components/shell/InstructorShell.tsx        — tour steps repointed at new anchors
apps/web/src/routes/class/index.tsx                      — rebuilt class overview
apps/web/src/routes/class/student.$uid.tsx                — now renders LearnerRecord, not StudentDrillDown
apps/web/src/routes/course/index.tsx                      — added <InstructorPlan> card
CLAUDE.md                                                 — points at the two new docs
docs/UI_AND_MODULES.md                                    — documents the teacher decision loop
```

## After copying, run

```
pnpm --filter web typecheck
```

I parsed every file with the TypeScript compiler for syntax errors and
compiled every Python file, but I could not run a full `tsc --noEmit` or
`pnpm lint` in this sandbox (no `node_modules`). Three small issues were
already caught and fixed on review — a duplicate import in `RosterTable`, a
missing `ReactNode` import in `DecisionCenter`, and a missing type import in
`use-instructor.ts` — so the files here already include those fixes. Still
run typecheck before you record; that's the safety net I couldn't pull.
