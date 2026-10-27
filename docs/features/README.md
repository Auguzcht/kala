# Feature registry

One folder per feature: `docs/features/<slug>/README.md`, written from `engineering/documentation/templates/feature-spec.md`. A row here does not prove the feature has shipped. The spec's requirement statuses and the evidence do.

Registry checked for DOCS-HYGIENE on 2026-10-25. Active means an implemented area, not a complete or fully accepted spec.

| Slug | REQ prefix | Area | Code anchors | Status |
| --- | --- | --- | --- | --- |
| [lti-auth](lti-auth/README.md) | `AUTH` | LTI 1.3 login, launch, JWKS, tenant resolution, session token, role routing | `services/api/app/lti/`, `app/security/jwt.py`, `apps/web/src/routes/launch.tsx` | active |
| [lms-ingest](lms-ingest/README.md) | `INGEST` | Blackboard REST connector, async course walk, ingest jobs, content chunks, embeddings | `app/lms/`, `routers/ingest_jobs.py`, worker `jobs/ingest_walk.py`, `embed_backfill.py` | active |
| [skills](skills/README.md) | `SKILL` | Skill proposals, tagging to skills and Bloom's levels, instructor review | `app/tagging.py`, worker `tagger.py`, `skill_proposer.py`, `SkillReviewPanel.tsx` | active |
| [question-bank](question-bank/README.md) | `BANK` | Item generation, bank build, dedupe, embeddings, saturation | `app/bank/`, worker `jobs/bank_build.py`, `item_generation.py`, `embed_bank_items.py` | active |
| [diagnostic](diagnostic/README.md) | `DIAG` | Diagnostic questions and submit, evidence writes | `routers/diagnostic.py`, `features/diagnostic/` | active |
| [lessons](lessons/README.md) | `LESSON` | Guided lessons, lesson checks matched to steps | `routers/lessons.py`, `learn/lessons.py`, worker `assign_lesson_checks.py` | active |
| [study](study/README.md) | `STUDY` | Flashcards, card memory, SRS, due rules, review sessions | `routers/flashcards.py`, `learn/srs.py`, `features/flashcards/`, `skill-hub/StudyBrowser.tsx` | active |
| practice-tests (full spec not authored) | `TEST` | Test sets, attempts, retakes, XP rule, recap | `routers/practice.py`, `learn/xp.py`, `features/practice/`, `TestBrowser.tsx` | active |
| [tutor](tutor/README.md) | `TUTOR` | RAG tutor, conversations, attachments, post-answer dock chat | `routers/tutor.py`, `app/ai/rag.py`, `features/tutor/` | active |
| [twin](twin/README.md) | `TWIN` | Mastery tracer, readiness, student twin view | `app/twin/`, worker `reconcile_mastery.py`, `readiness_snapshot.py`, `features/twin/` | active |
| [instructor-insights](instructor-insights/README.md) | `INSTR` | Roster, heatmap, at-risk list, student sheet, decisions, plan | `routers/dashboard.py`, `features/instructor/`, `features/plan/` | active, partial |
| [gamification](gamification/README.md) | `GAME` | XP, streaks, celebrations | `routers/gamification.py`, `features/gamification/` | active |
| [ai-platform](ai-platform/README.md) | `AI` | Provider router, model tiers, de-identification, concurrency, errors | `services/api/app/ai/`, worker `model_errors.py` | active |
| [tour](tour/README.md) | `TOUR` | Student tour hidden pending side-effect-free reads; instructor walkthrough retained | `components/shell/*Tour*` | active |
| admin (spec not authored) | `ADMIN` | Institution admin console | none yet | planned |
| research (spec not authored) | `RES` | Researcher portal, grants, consented anonymized views, exports | migration `0003_research.sql` only | planned |
| grade-passback (spec not authored) | `AGS` | LTI Assignment and Grade Services | none yet | planned |

Cross-cutting rules (tenancy, RLS, de-identification) live in [engineering/security-and-privacy.md](../engineering/security-and-privacy.md), not repeated in each spec.

## Spec completeness

All rows above describe feature areas, not proof of complete specifications. Current specs disclose partial/planned requirements and verification limits; Practice/Test still lacks a complete standalone spec. Missing planned specs are labeled rather than linked to absent files. The sanitizer remains partial (emails and `name:` patterns only). AGS grade passback is **planned**, independent of legacy REST gradebook routes.

The Practice/Test contract is not yet a complete feature spec. Current delivery and XP boundaries are in [Study mode boundaries](study/README.md#learning-surface-boundaries) and [ADR-016](../decisions/ADR-016-legacy-flashcard-xp.md). Do not infer a complete acceptance contract from code anchors. Historical design rationale is source material, not substitute requirements.

## Historical sources

These links preserve provenance only. Required rules, commands and limits are stated above; do not read the records unless the task explicitly names them.

- [guide knowledge](../work/handover-2026/evidence/local-guide-knowledge.md)
- [the disposition map](../work/handover-2026/evidence/migration-map.md)
