# Feature registry

One folder per feature: `docs/features/<slug>/README.md`, written from `engineering/documentation/templates/feature-spec.md`. A row here does not prove the feature has shipped. The spec's requirement statuses and the evidence do.

Status as of the 2026-10-24 scaffold snapshot (`e9de105` era). Each spec author re-verifies against current `main`.

| Slug | REQ prefix | Area | Code anchors | Status |
| --- | --- | --- | --- | --- |
| [lti-auth](lti-auth/README.md) | `AUTH` | LTI 1.3 login, launch, JWKS, tenant resolution, session token, role routing | `services/api/app/lti/`, `app/security/jwt.py`, `apps/web/src/routes/launch.tsx` | active |
| [lms-ingest](lms-ingest/README.md) | `INGEST` | Blackboard REST connector, async course walk, ingest jobs, content chunks, embeddings | `app/lms/`, `routers/ingest_jobs.py`, worker `jobs/ingest_walk.py`, `embed_backfill.py` | active |
| [skills](skills/README.md) | `SKILL` | Skill proposals, tagging to skills and Bloom's levels, instructor review | `app/tagging.py`, worker `tagger.py`, `skill_proposer.py`, `SkillReviewPanel.tsx` | active |
| [question-bank](question-bank/README.md) | `BANK` | Item generation, bank build, dedupe, embeddings, saturation | `app/bank/`, worker `jobs/bank_build.py`, `item_generation.py`, `embed_bank_items.py` | active |
| [diagnostic](diagnostic/README.md) | `DIAG` | Diagnostic questions and submit, evidence writes | `routers/diagnostic.py`, `features/diagnostic/` | active |
| [lessons](lessons/README.md) | `LESSON` | Guided lessons, lesson checks matched to steps | `routers/lessons.py`, `learn/lessons.py`, worker `assign_lesson_checks.py` | active |
| [study](study/README.md) | `STUDY` | Flashcards, card memory, SRS, due rules, review sessions | `routers/flashcards.py`, `learn/srs.py`, `features/flashcards/`, `skill-hub/StudyBrowser.tsx` | active |
| [practice-tests](practice-tests/README.md) | `TEST` | Test sets, attempts, retakes, XP rule, recap | `routers/practice.py`, `learn/xp.py`, `features/practice/`, `TestBrowser.tsx` | active |
| [tutor](tutor/README.md) | `TUTOR` | RAG tutor, conversations, attachments, post-answer dock chat | `routers/tutor.py`, `app/ai/rag.py`, `features/tutor/` | active |
| [twin](twin/README.md) | `TWIN` | Mastery tracer, readiness, student twin view | `app/twin/`, worker `reconcile_mastery.py`, `readiness_snapshot.py`, `features/twin/` | active |
| [instructor-insights](instructor-insights/README.md) | `INSTR` | Roster, heatmap, at-risk list, student sheet, decisions, plan | `routers/dashboard.py`, `features/instructor/`, `features/plan/` | active, partial |
| [gamification](gamification/README.md) | `GAME` | XP, streaks, celebrations | `routers/gamification.py`, `features/gamification/` | active |
| [ai-platform](ai-platform/README.md) | `AI` | Provider router, model tiers, de-identification, concurrency, errors | `services/api/app/ai/`, worker `model_errors.py` | active |
| [tour](tour/README.md) | `TOUR` | Student and instructor guided tours (never write data) | `components/shell/*Tour*` | active |
| [admin](admin/README.md) | `ADMIN` | Institution admin console | none yet | planned |
| [research](research/README.md) | `RES` | Researcher portal, grants, consented anonymized views, exports | migration `0003_research.sql` only | planned |
| [grade-passback](grade-passback/README.md) | `AGS` | LTI Assignment and Grade Services | none yet | planned |

Cross-cutting rules (tenancy, RLS, de-identification) live in [engineering/security-and-privacy.md](../engineering/security-and-privacy.md), not repeated in each spec.

## Spec completeness

All rows above describe feature areas, not proof of complete specifications. Full specs remain planned in WI-08. S/T/F own the minimal `lms-ingest`, `tutor`, `ai-platform` and `study` specs for APPROVAL-01; Lane D does not create or edit them. In this isolated lane they may be absent until integration. The sanitizer remains partial (emails and `name:` patterns only). AGS grade passback is **planned**, independent of legacy REST gradebook routes.

Historical design and local-guide rationale is preserved in [the disposition map](../work/handover-2026/evidence/migration-map.md), [guide knowledge](../work/handover-2026/evidence/local-guide-knowledge.md) and [design notes](../design/handover-findings.md). These are source material for full specs, not substitute feature requirements.
