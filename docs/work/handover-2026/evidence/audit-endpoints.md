> Durable copy of accepted 2026-10-24 evidence at base `e9de105`, preserved under [APPROVAL-01](<../approval-01.md>). Findings describe that audit revision, not integrated fixes or live recovery. Repository links are adapted for archive moves; original source line labels are retained. Raw scratch manifests, scripts, dumps and JSON are intentionally not promoted.

KALA HANDOVER — BRIEF-01 PART A ENDPOINT REACHABILITY AUDIT
2026-10-24, Asia/Manila. Audit-only; no repository file edits.

Worktree: .
Branch: codex/endpoint-reachability
Base/HEAD/local origin/main when first checked: e9de105d7f3074ec39f54e32b1f2b5e2bda669ed
Branch was created from the assigned detached checkout. No fetch/reset/pull,
commit/push/merge/deployment, hosted operation, or secret-file read occurred.

All conclusions below are STATIC SOURCE FINDINGS unless explicitly marked
as published platform documentation. No live endpoint, CloudWatch, browser,
LTI launch, local Postgres, or Docker reproduction was performed. INC-002 is
historical evidence; this report makes no claim that live tutor 502s are fixed.
Fred must correlate observed failures with CloudWatch. Existing main/Kala Audit
worktrees, Vite :5173 and unrelated resources were untouched.

RESULTS AND PRIORITY FINDINGS
- 60 distinct application method/path pairs in 12 routers, all mounted by
  services/api/app/main.py:83-94. 42 frontend API call sites map to 42 of them;
  there are zero method/path mismatches at this revision.
- 18 application routes have no SPA API wrapper. Four are external LTI
  protocol endpoints, health is used by a local check script, three are
  instructor-only unconsumed maintenance/review routes, and ten are legacy/
  otherwise unconsumed HTTP entries. "Dead" here means no in-repo HTTP caller
  was found, not proof that Fred or an external client never uses it.
- One additional matched wrapper, createIntervention, is exported through a
  hook but has no screen caller. Thus wrapper presence is not UI reachability.
- Nine server-side model/LMS endpoint paths can exceed the requested 29s
  risk threshold. Login redirect is listed separately to avoid counting a
  browser redirect as a synchronous remote HTTP call.
- Tutor has no cumulative deadline. OpenRouter permits a 25s primary then
  a 25s fallback; RAG and DB operations precede/follow them. API Lambda is
  configured for 30s. The current dedicated chat role mitigates a historical
  model selection issue but does not bound this full chain or prove recovery.
- GET deck is stateful: claiming/serving fresh cards writes schedules and
  studied exposure before any rating. Completed ratings move due dates;
  Reload refetches selection, not an unconditional replay of the same cards.
- A concrete additional deck defect exists: the Flashcards landing-page
  counts peek uses limit=0, while backend clamps it to 1 and can claim a
  card. Tracked-but-unreviewed cards (reps=0) are then excluded from both
  normal due and fresh top-up selection. No runtime reproduction is claimed.
- Staff-intended legacy LMS routes, including grade PATCH, use only
  get_current_user, not require_role. Inventory labels do not imply a staff
  authorization gate that is absent in code. This merits a later scoped
  authorization review; no route was invoked or modified.

1. FULL BACKEND INVENTORY
Paths are complete APIRouter prefix + decorator paths, as wired by main.py.
Auth column lists dependencies, not a proof of all resource authorization.
get_current_user verifies the Kala HS256 bearer session locally (deps.py:136-153;
security/jwt.py:46-53); require_role delegates to it and restricts app_role
(deps.py:156-162). UUID validation dependencies are NOT auth dependencies.

Method | Full path | Router file:line | Handler | Auth dependency
--- | --- | --- | --- | ---
GET | /lti/login | services/api/app/lti/routes.py:201 | login_get | none; OIDC redirect and signed state creation (not bearer auth)
POST | /lti/login | services/api/app/lti/routes.py:206 | login_post | none; OIDC redirect and signed state creation (not bearer auth)
POST | /lti/launch | services/api/app/lti/routes.py:211 | launch | none as Depends; signed state/cookie, RS256 launch JWT, nonce/message/deployment checks in body
GET | /lti/jwks | services/api/app/lti/routes.py:366 | jwks | none
GET | /courses/{course_id}/bank/status | services/api/app/routers/bank.py:26 | bank_status | get_current_user
GET | /courses/{course_id} | services/api/app/routers/courses.py:18 | get_course | get_current_user
GET | /courses/{course_id}/memory/summary | services/api/app/routers/courses.py:33 | memory_summary | get_current_user
GET | /dashboard/{course_id}/heatmap | services/api/app/routers/dashboard.py:96 | heatmap | require_role('instructor', 'admin')
GET | /dashboard/{course_id}/at-risk | services/api/app/routers/dashboard.py:214 | at_risk | require_role('instructor', 'admin')
GET | /dashboard/{course_id}/students/{user_id}/twin | services/api/app/routers/dashboard.py:262 | student_twin | require_role('instructor', 'admin')
GET | /dashboard/{course_id}/skills/proposed | services/api/app/routers/dashboard.py:292 | list_proposed_skills | require_role('instructor', 'admin')
GET | /dashboard/{course_id}/skills/auto-matched | services/api/app/routers/dashboard.py:315 | list_auto_matched_skills | require_role('instructor', 'admin')
PATCH | /dashboard/{course_id}/skills/{skill_id}/review | services/api/app/routers/dashboard.py:340 | review_proposed_skill | require_role('instructor', 'admin')
POST | /dashboard/{course_id}/skills/{skill_id}/reject-approved | services/api/app/routers/dashboard.py:377 | reject_approved_skill | require_role('instructor', 'admin')
PATCH | /dashboard/{course_id}/skills/{skill_id}/detach | services/api/app/routers/dashboard.py:404 | detach_auto_matched_skill | require_role('instructor', 'admin')
GET | /dashboard/{course_id}/roster | services/api/app/routers/dashboard.py:450 | course_roster | require_role('instructor', 'admin')
GET | /dashboard/{course_id}/stats | services/api/app/routers/dashboard.py:474 | course_stats | require_role('instructor', 'admin')
GET | /dashboard/{course_id}/students/{user_id}/record | services/api/app/routers/dashboard.py:486 | student_record | require_role('instructor', 'admin')
GET | /dashboard/{course_id}/students/{user_id}/recommendations | services/api/app/routers/dashboard.py:566 | list_recommendations | require_role('instructor', 'admin')
POST | /dashboard/{course_id}/students/{user_id}/recommendations | services/api/app/routers/dashboard.py:590 | generate_recommendations | require_role('instructor', 'admin')
PATCH | /dashboard/{course_id}/recommendations/{rec_id} | services/api/app/routers/dashboard.py:666 | decide_recommendation | require_role('instructor', 'admin')
POST | /dashboard/{course_id}/students/{user_id}/interventions | services/api/app/routers/dashboard.py:726 | create_intervention | require_role('instructor', 'admin')
GET | /courses/{course_id}/roster | services/api/app/routers/diagnostic.py:139 | get_roster | get_current_user
GET | /courses/{course_id}/content | services/api/app/routers/diagnostic.py:148 | get_content | get_current_user
GET | /courses/{course_id}/assessments | services/api/app/routers/diagnostic.py:161 | get_assessments | get_current_user
POST | /courses/{course_id}/skills/propose | services/api/app/routers/diagnostic.py:170 | propose_course_skills | require_role('instructor', 'admin')
POST | /courses/{course_id}/ingest | services/api/app/routers/diagnostic.py:184 | ingest_course | get_current_user
GET | /courses/{course_id}/ingest/status | services/api/app/routers/diagnostic.py:221 | ingest_status | get_current_user
POST | /courses/{course_id}/content/upload | services/api/app/routers/diagnostic.py:232 | upload_course_content | require_role('instructor', 'admin')
POST | /courses/{course_id}/content/retag | services/api/app/routers/diagnostic.py:352 | reset_tagging | require_role('instructor', 'admin')
GET | /courses/{course_id}/modules | services/api/app/routers/diagnostic.py:374 | list_modules | get_current_user
PATCH | /courses/{course_id}/assessments/{column_id}/grade | services/api/app/routers/diagnostic.py:429 | post_grade | get_current_user
GET | /courses/{course_id}/diagnostic/status | services/api/app/routers/diagnostic.py:488 | get_diagnostic_status | get_current_user
GET | /courses/{course_id}/diagnostic | services/api/app/routers/diagnostic.py:510 | get_diagnostic | get_current_user
POST | /courses/{course_id}/diagnostic/submit | services/api/app/routers/diagnostic.py:648 | submit_diagnostic | get_current_user
GET | /flashcards/{course_id}/skills/{skill_id}/cards | services/api/app/routers/flashcards.py:61 | skill_cards | get_current_user
GET | /flashcards/{course_id}/deck | services/api/app/routers/flashcards.py:142 | deck | get_current_user
POST | /flashcards/{course_id}/review | services/api/app/routers/flashcards.py:443 | review | get_current_user
GET | /gamification/{course_id}/summary | services/api/app/routers/gamification.py:14 | summary | get_current_user
GET | /health | services/api/app/routers/health.py:6 | health | none
GET | /lessons/{course_id}/skill/{skill_id} | services/api/app/routers/lessons.py:28 | get_lesson | get_current_user
POST | /lessons/{course_id}/steps/{step_id}/check | services/api/app/routers/lessons.py:56 | submit_check | get_current_user
GET | /practice/{course_id}/next | services/api/app/routers/practice.py:177 | next_item | get_current_user
POST | /practice/{course_id}/set | services/api/app/routers/practice.py:214 | create_set | get_current_user
POST | /practice/{course_id}/set/from-items | services/api/app/routers/practice.py:332 | create_set_from_items | get_current_user
GET | /practice/{course_id}/sets | services/api/app/routers/practice.py:527 | list_sets | get_current_user
GET | /practice/{course_id}/sets/{set_id} | services/api/app/routers/practice.py:572 | get_set | get_current_user
POST | /practice/{course_id}/sets/{set_id}/retake | services/api/app/routers/practice.py:658 | start_practice_retake | get_current_user
GET | /practice/{course_id}/sets/{set_id}/results | services/api/app/routers/practice.py:699 | get_set_results | get_current_user
POST | /practice/{course_id}/submit | services/api/app/routers/practice.py:843 | submit | get_current_user
POST | /tutor/conversations | services/api/app/routers/tutor.py:157 | create_conversation | get_current_user
GET | /tutor/conversations | services/api/app/routers/tutor.py:181 | list_conversations | get_current_user
GET | /tutor/conversations/{conversation_id} | services/api/app/routers/tutor.py:196 | get_conversation | get_current_user
POST | /tutor/conversations/{conversation_id}/attachments | services/api/app/routers/tutor.py:233 | upload_attachment | get_current_user
DELETE | /tutor/conversations/{conversation_id}/attachments/{attachment_id} | services/api/app/routers/tutor.py:290 | delete_attachment | get_current_user
DELETE | /tutor/conversations/{conversation_id} | services/api/app/routers/tutor.py:308 | delete_conversation | get_current_user
POST | /tutor/ask | services/api/app/routers/tutor.py:343 | ask | get_current_user
GET | /courses/{course_id}/twin | services/api/app/routers/twin.py:17 | get_twin | get_current_user
GET | /courses/{course_id}/next-up | services/api/app/routers/twin.py:27 | next_up | get_current_user
GET | /courses/{course_id}/plan | services/api/app/routers/twin.py:64 | learning_plan | get_current_user


FastAPI defaults add four framework routes (main.py:29); these are distinct
from the 60 application routes. Static framework behavior, not boot proof:

Method(s) | Path | Source | Auth
--- | --- | --- | ---
GET, HEAD | /openapi.json | FastAPI default, main.py:29 | none
GET, HEAD | /docs | FastAPI default, main.py:29 | none
GET, HEAD | docs/oauth2-redirect | FastAPI default, main.py:29 | none
GET, HEAD | /redoc | FastAPI default, main.py:29 | none

CORS middleware can handle browser preflight OPTIONS (main.py:75-81);
this is middleware behavior rather than another declared application endpoint.
API Gateway proxies ANY /{proxy+} (apigw.tf:21-25). ingest_jobs.py and
item_generation_jobs.py contain queue helpers, not APIRouters/routes.
Canvas connector code is not wired by get_lms_connector (deps.py:165-167).

2. FULL FRONTEND CALL INVENTORY
42 application call sites. Method defaults to GET unless RequestInit supplies
it. URL query expressions remain visible; matching strips query strings and
normalizes camelCase identifiers to backend parameter placeholders. Calling
API source and screen consumers are both recorded. Screens are statically
traced via named hook calls, not proof of a mounted/running UI. Shared session
screens also appear within SkillHub takeover (SkillHub.tsx:187-243).

Method | Path pattern | Calling API file:line / function | Screen consumers (source basenames; full paths in JSON/TSV)
--- | --- | --- | ---
GET | /courses/${courseId}/bank/status | apps/web/src/features/bank/api/bank.api.ts:6 / fetchBankStatus | components/shell/CourseShell.tsx, features/diagnostic/components/DiagnosticPanel.tsx, features/flashcards/components/FlashcardDeck.tsx, features/lessons/components/LessonChat.tsx, features/practice/components/PracticePanel.tsx, features/skill-hub/components/SkillHub.tsx, features/skill-hub/components/StudyBrowser.tsx, features/skill-hub/components/TestBrowser.tsx, routes/course/lessons.tsx, routes/course/practice.tsx
GET | /courses/${courseId} | apps/web/src/features/courses/api/courses.api.ts:5 / fetchCourse | components/shell/TopBar.tsx, routes/course/index.tsx, routes/launch.tsx
GET | /courses/${courseId}/diagnostic | apps/web/src/features/diagnostic/api/diagnostic.api.ts:15 / fetchDiagnostic | features/diagnostic/components/DiagnosticPanel.tsx
GET | /courses/${courseId}/diagnostic/status | apps/web/src/features/diagnostic/api/diagnostic.api.ts:21 / fetchDiagnosticStatus | components/shell/CourseShell.tsx, routes/course/index.tsx
POST | /courses/${courseId}/diagnostic/submit | apps/web/src/features/diagnostic/api/diagnostic.api.ts:29 / submitDiagnostic | features/diagnostic/components/DiagnosticPanel.tsx
GET | /flashcards/${courseId}/deck?${params.toString()} | apps/web/src/features/flashcards/api/flashcards.api.ts:23 / fetchFlashcardDeck | features/flashcards/components/FlashcardDeck.tsx, routes/course/flashcards.tsx
GET | /flashcards/${courseId}/skills/${skillId}/cards | apps/web/src/features/flashcards/api/flashcards.api.ts:33 / fetchFlashcardMembership | features/flashcards/components/FlashcardDeck.tsx, features/skill-hub/components/StudyBrowser.tsx
POST | /flashcards/${courseId}/review | apps/web/src/features/flashcards/api/flashcards.api.ts:79 / reviewFlashcard | features/flashcards/components/FlashcardDeck.tsx
GET | /gamification/${courseId}/summary | apps/web/src/features/gamification/api/gamification.api.ts:8 / fetchGamificationSummary | features/gamification/components/GamificationSummary.tsx, features/practice/components/PracticePanel.tsx, features/twin/components/TwinBody.tsx
GET | /dashboard/${courseId}/heatmap | apps/web/src/features/instructor/api/instructor.api.ts:36 / fetchHeatmap | features/instructor/components/Heatmap.tsx, routes/launch.tsx
GET | /dashboard/${courseId}/at-risk | apps/web/src/features/instructor/api/instructor.api.ts:41 / fetchAtRisk | features/instructor/components/AtRiskList.tsx, features/instructor/components/LearnerRecord.tsx, features/instructor/components/LearnerTriage.tsx, features/instructor/components/StudentDrillDown.tsx, routes/launch.tsx
GET | /dashboard/${courseId}/students/${userId}/twin | apps/web/src/features/instructor/api/instructor.api.ts:46 / fetchStudentTwin | features/instructor/components/StudentDrillDown.tsx
GET | /dashboard/${courseId}/skills/proposed | apps/web/src/features/instructor/api/instructor.api.ts:51 / fetchProposedSkills | features/instructor/components/SkillReviewPanel.tsx, routes/class/index.tsx, routes/launch.tsx
PATCH | /dashboard/${courseId}/skills/${skillId}/review | apps/web/src/features/instructor/api/instructor.api.ts:60 / reviewProposedSkill | features/instructor/components/SkillReviewPanel.tsx
POST | /courses/${courseId}/skills/propose | apps/web/src/features/instructor/api/instructor.api.ts:68 / proposeSkills | features/instructor/components/SkillReviewPanel.tsx
GET | /dashboard/${courseId}/skills/auto-matched | apps/web/src/features/instructor/api/instructor.api.ts:73 / fetchAutoMatchedSkills | features/instructor/components/AutoMatchedSection.tsx, routes/launch.tsx
PATCH | /dashboard/${courseId}/skills/${skillId}/detach | apps/web/src/features/instructor/api/instructor.api.ts:81 / detachAutoMatchedSkill | features/instructor/components/AutoMatchedSection.tsx
GET | /dashboard/${courseId}/roster | apps/web/src/features/instructor/api/instructor.api.ts:90 / fetchRoster | features/instructor/components/RosterTable.tsx
GET | /dashboard/${courseId}/stats | apps/web/src/features/instructor/api/instructor.api.ts:95 / fetchCohortStats | features/instructor/components/CohortCharts.tsx, features/instructor/components/CohortStats.tsx
GET | /dashboard/${courseId}/students/${userId}/record | apps/web/src/features/instructor/api/instructor.api.ts:100 / fetchLearnerRecord | components/shell/InstructorShell.tsx, features/instructor/components/LearnerRecord.tsx, features/instructor/components/LearnerTriage.tsx
GET | /dashboard/${courseId}/students/${userId}/recommendations | apps/web/src/features/instructor/api/instructor.api.ts:110 / fetchRecommendations | features/instructor/components/DecisionCenter.tsx
POST | /dashboard/${courseId}/students/${userId}/recommendations | apps/web/src/features/instructor/api/instructor.api.ts:119 / generateRecommendations | features/instructor/components/DecisionCenter.tsx
PATCH | /dashboard/${courseId}/recommendations/${recId} | apps/web/src/features/instructor/api/instructor.api.ts:137 / decideRecommendation | features/instructor/components/DecisionCenter.tsx
POST | /dashboard/${courseId}/students/${userId}/interventions | apps/web/src/features/instructor/api/instructor.api.ts:155 / createIntervention | none; exported useCreateIntervention has no screen call
GET | /lessons/${courseId}/skill/${skillId} | apps/web/src/features/lessons/api/lessons.api.ts:10 / fetchLesson | features/lessons/components/LessonChat.tsx
POST | /lessons/${courseId}/steps/${stepId}/check | apps/web/src/features/lessons/api/lessons.api.ts:19 / submitStepCheck | features/lessons/components/LessonChat.tsx
GET | /courses/${courseId}/plan | apps/web/src/features/plan/api/plan.api.ts:5 / fetchPlan | features/plan/components/InstructorPlan.tsx
POST | /practice/${courseId}/set${query} | apps/web/src/features/practice/api/practice.api.ts:28 / fetchPracticeSet | features/practice/components/PracticePanel.tsx, features/skill-hub/components/TestBrowser.tsx
GET | /practice/${courseId}/sets/${setId} | apps/web/src/features/practice/api/practice.api.ts:41 / fetchPracticeSetById | features/practice/components/PracticePanel.tsx, features/skill-hub/components/TestBrowser.tsx
GET | /practice/${courseId}/sets/${setId}/results${query} | apps/web/src/features/practice/api/practice.api.ts:52 / fetchPracticeSetResults | features/flashcards/components/FlashcardDeck.tsx, features/practice/components/PracticePanel.tsx
POST | /practice/${courseId}/sets/${setId}/retake | apps/web/src/features/practice/api/practice.api.ts:58 / startRetake | features/practice/components/PracticePanel.tsx
GET | /practice/${courseId}/sets${query} | apps/web/src/features/practice/api/practice.api.ts:68 / fetchPracticeSets | components/shell/CourseShell.tsx, features/skill-hub/components/TestBrowser.tsx
POST | /practice/${courseId}/submit | apps/web/src/features/practice/api/practice.api.ts:84 / submitPracticeAttempt | features/practice/components/PracticePanel.tsx
POST | /tutor/ask | apps/web/src/features/tutor/api/tutor.api.ts:24 / askTutor | features/flashcards/components/FlashcardDeck.tsx, features/lessons/components/LessonChat.tsx, features/practice/components/PracticePanel.tsx, features/tutor/components/TutorChat.tsx
POST | /tutor/conversations | apps/web/src/features/tutor/api/tutor.api.ts:40 / createTutorConversation | features/tutor/components/TutorChat.tsx
GET | /tutor/conversations?course_id=${encodeURIComponent(courseId)} | apps/web/src/features/tutor/api/tutor.api.ts:48 / listTutorConversations | components/shell/TutorSidebar.tsx, features/tutor/components/TutorChat.tsx
GET | /tutor/conversations/${conversationId} | apps/web/src/features/tutor/api/tutor.api.ts:53 / fetchTutorConversation | features/tutor/components/TutorChat.tsx
DELETE | /tutor/conversations/${conversationId} | apps/web/src/features/tutor/api/tutor.api.ts:58 / deleteTutorConversation | components/shell/TutorSidebar.tsx
POST | /tutor/conversations/${conversationId}/attachments | apps/web/src/features/tutor/api/tutor.api.ts:71 / uploadTutorAttachment | features/tutor/components/TutorChat.tsx
DELETE | /tutor/conversations/${conversationId}/attachments/${attachmentId} | apps/web/src/features/tutor/api/tutor.api.ts:82 / deleteTutorAttachment | features/tutor/components/TutorChat.tsx
GET | /courses/${courseId}/twin | apps/web/src/features/twin/api/twin.api.ts:5 / fetchTwin | components/shell/CourseShell.tsx, features/flashcards/components/FlashcardDeck.tsx, features/skill-hub/components/SkillHub.tsx, features/twin/components/TwinView.tsx, routes/course/flashcards.tsx, routes/course/index.tsx, routes/course/lessons.tsx, routes/course/practice.tsx, routes/course/skills.tsx, routes/launch.tsx
GET | /courses/${courseId}/next-up | apps/web/src/features/twin/api/twin.api.ts:10 / fetchNextUp | routes/course/index.tsx, routes/course/practice.tsx, routes/launch.tsx


Additional network mechanisms outside the 42 application API wrappers:
- lib/api/client.ts:52 is the shared fetch implementation for all 42 calls,
  not an additional endpoint. It appends VITE_API_BASE_URL and bearer auth.
- components/ai-elements/prompt-input.tsx:81-84 fetches a supplied blob URL to
  convert an attachment to data. No fixed Kala backend route applies.
- lib/supabase/client.ts:1 imports the SDK; no feature calls of a Supabase
  client were found. Client construction is not a table/auth endpoint call.
- LTI redirects and platform form posts are external protocol traffic listed
  in backend inventory, not SPA fetches. No axios/XMLHttpRequest/EventSource/
  WebSocket/sendBeacon endpoint caller was found under apps/web/src.
- Call-site fallback: flashcards.api.ts:37-39 only falls back from membership
  GET on an API 404 to GET /flashcards/{course_id}/deck?limit=50&skill_id=...
  with mode omitted. Both paths exist. A permission/unknown-skill 404 also
  enters this fallback; it does not prove route absence.

3A. FRONTEND CALLS WITH NO MATCHING BACKEND ROUTE

Result | Evidence
--- | ---
none | 42/42 static method/path matches; independent raw fetch/client search found no additional application API client

This establishes route-shape reachability only. It does not prove deployed
revision, VITE_API_BASE_URL, query/body schema, CORS, permissions or database
availability. No API success/failure status was observed in this audit.

3B. BACKEND ROUTES WITH NO FRONTEND WRAPPER
The brief's four categories do not cover externally invoked LTI protocol
routes. Those are explicitly marked external LTI, rather than falsely marked
as dead, worker-used or script-used. No worker HTTP calls to Kala API were
found: the worker uses its own LMS/provider/DB clients and queued table rows.

Method | Path | Classification | Exact route source | Use evidence / limit
--- | --- | --- | --- | ---
GET | /lti/login | external LTI protocol | services/api/app/lti/routes.py:201 | Blackboard/browser OIDC entry; infra/blackboard/README.md:9. Not a SPA fetch.
POST | /lti/login | external LTI protocol | services/api/app/lti/routes.py:206 | Alternate platform OIDC entry; lti/routes.py:206. Not dead.
POST | /lti/launch | external LTI protocol | services/api/app/lti/routes.py:211 | Platform form_post launch; infra/blackboard/README.md:9; not a SPA fetch.
GET | /lti/jwks | external LTI protocol | services/api/app/lti/routes.py:366 | Public tool key discovery configured for Blackboard; infra/blackboard/README.md:9.
GET | /courses/{course_id}/memory/summary | dead / unconsumed in repo | services/api/app/routers/courses.py:33 | Read-only memory endpoint; no wrapper, script or worker HTTP caller found.
POST | /dashboard/{course_id}/skills/{skill_id}/reject-approved | instructor-only; UI-unconsumed | services/api/app/routers/dashboard.py:377 | require_role staff gate; existing tests test_dashboard_routes.py:19,35 exercise it. No component caller.
GET | /courses/{course_id}/roster | dead / unconsumed in repo | services/api/app/routers/diagnostic.py:139 | Legacy LMS REST preview, tests only. JWT required; NOT restricted to instructor role.
GET | /courses/{course_id}/content | dead / unconsumed in repo | services/api/app/routers/diagnostic.py:148 | Legacy LMS tree preview, tests only. JWT required; NOT restricted to instructor role.
GET | /courses/{course_id}/assessments | dead / unconsumed in repo | services/api/app/routers/diagnostic.py:161 | Legacy LMS grade-column preview, tests only. JWT required; NOT restricted to instructor role.
POST | /courses/{course_id}/ingest | dead / unconsumed HTTP entry in repo | services/api/app/routers/diagnostic.py:184 | Maintainer/intended enqueue entry, documented and tested; worker consumes ingest_jobs directly, not this HTTP route.
GET | /courses/{course_id}/ingest/status | dead / unconsumed HTTP entry in repo | services/api/app/routers/diagnostic.py:221 | Tests exercise it. scripts/poll_ingest.py:92 reads Supabase directly, not this endpoint.
POST | /courses/{course_id}/content/upload | instructor-only; UI-unconsumed | services/api/app/routers/diagnostic.py:232 | Staff course authorization gate; tested by test_course_content_upload.py. No in-repo HTTP script caller found.
POST | /courses/{course_id}/content/retag | instructor-only; UI-unconsumed | services/api/app/routers/diagnostic.py:352 | Staff course authorization gate; documented/tested maintenance route. No in-repo HTTP script caller found.
GET | /courses/{course_id}/modules | dead / unconsumed in repo | services/api/app/routers/diagnostic.py:374 | DB metadata route; no frontend wrapper, worker HTTP use or script call found.
PATCH | /courses/{course_id}/assessments/{column_id}/grade | dead / unconsumed in repo | services/api/app/routers/diagnostic.py:429 | LMS write-through; tests only. get_current_user, not require_role. Staff intent is NOT an auth guarantee.
GET | /health | used by scripts | services/api/app/routers/health.py:6 | check_stack.sh:28,66-69 requests API_HEALTH_URL (default local /health); script not executed.
GET | /practice/{course_id}/next | dead / legacy HTTP surface | services/api/app/routers/practice.py:177 | Existing route tests; SPA uses async POST /set. Still reachable and can generate a model answer inline.
POST | /practice/{course_id}/set/from-items | dead / legacy HTTP surface | services/api/app/routers/practice.py:332 | Tested study-to-test bridge, but no current frontend wrapper or script caller found.


Matched but dormant UI wrapper:
POST /dashboard/{course_id}/students/{user_id}/interventions — instructor-only.
API: instructor.api.ts:144-159; hook use-instructor.ts:206-220; barrel export
instructor/index.ts:27. No component/route invocation of useCreateIntervention
or createIntervention found. It is not counted among the 18 absent wrappers.
Tests alone are not categorized as production callers. scripts/smoke_live.py
and smoke_retake.py use already-matched practice endpoints. poll_ingest.py
queries PostgREST directly; it does not call the ingest status API.
No route should be removed based solely on this static classification.

3C. MODEL/LMS REQUEST PATHS AND TIME RISK
Platform source configuration: infra/terraform/lambda.tf:11 sets API timeout
30s, memory 1024MB; worker timeout is 120s at :48. apigw.tf:4 is HTTP API,
:15 AWS_PROXY, :18 payload v2, and integration :14-19 omits timeout_milliseconds.
The HTTP API maximum integration timeout is 30s, not the REST/WebSocket 29s
figure. An omitted value does not prove the currently deployed integration
setting, so its exact live timeout is unverified. The brief's 29s threshold
is retained as a conservative audit flag, not asserted as this API's limit.
Published AWS quota: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-quotas.html
Integration API/defaults: https://docs.aws.amazon.com/apigatewayv2/latest/api-reference/apis-apiid-integrations-integrationid.html

Important timing semantics: HTTPX scalar timeouts apply to network phases/
inactivity, not to total elapsed request time. Therefore sums below are
illustrative serial stall budgets demonstrating overrun, NOT finite true
worst-case wall-clock guarantees. No route-wide cancellation/deadline exists.
Source: https://www.python-httpx.org/advanced/timeouts/
Bedrock clients are constructed with no explicit Config timeout/retry override
(ai/bedrock.py:156-160). SDK default connect/read timeouts are 60s; legacy
retry defaults can allow five total attempts (four retries), while environment/
shared SDK configuration can override them. Actual deployed retry count is
not established from this repo. Application-level Bedrock retries: zero;
OpenRouter fallback wrapper is bypassed on the Bedrock branch.
Sources: https://docs.aws.amazon.com/botocore/latest/reference/config.html
https://docs.aws.amazon.com/boto3/latest/guide/retries.html

Method | Full path | Sources | External time path | Timeouts | Retries and fallbacks | Can exceed 29s
--- | --- | --- | --- | --- | --- | ---
POST | /tutor/ask | tutor.py:343,372-442; ai/rag.py:11-18; ai/router.py:71-107 | RAG embedding -> PostgREST RPC -> chat; persistent mode adds ownership/history/attachments and post-answer persistence. | OpenAI embedding 20s OR OpenRouter embedding 25s OR Bedrock SDK; DB 60s per call; OpenRouter chat 25s per HTTP attempt. | Embedding: 0 application retries. Chat: at most 1 cross-model fallback; 1.5s backoff only on 429/503; no structured retry for tutor. No shared request deadline. | YES. Generation alone permits 25+25 seconds; one DB wait permits 60. Serial stall illustration: OpenAI stateless 131.5s, persistent 431.5s, before overhead; NOT total wall-clock maxima.
GET | /lessons/{course_id}/skill/{skill_id} | routers/lessons.py:28-46; learn/lessons.py:78-169,172-325 | Ready lesson: DB only. Fresh/reclaimed: RAG -> outline -> up to 6 concurrent step generations -> sequential DB/queue persistence. Fresh shell retrieves RAG twice. | Embedding 20/25s or SDK; DB 60s; outline/steps OpenRouter 25s per HTTP attempt. | Outline: up to 1 cross-model fallback, then one-step deterministic fallback. Each step: 2 outer attempts; each can use 1 model fallback. Outline uses reasoning-specific fallback, steps omit it and use GLOBAL fallback. | YES. Outline <=2 and longest step <=4 chat HTTP attempts along dependency path: nominal 154.5s including maximum 1.5s backoffs, plus RAG/DB. Concurrency prevents multiplying that path by all six steps, but does not add a deadline.
GET | /practice/{course_id}/next | routers/practice.py:177-211; learn/items.py:228-264,298-397 | Bank-on branch: selection DB only. Legacy bank-off branch: RAG -> generated MCQ -> DB persist. | Embedding 20/25s or SDK; DB 60s; chat 25s each. | MCQ: 1 validation retry; each converse may retry structured-output 404 once and may use one distinct-model fallback. With source-default item/fallback equal, cross-model retry skipped: up to 4 completion POSTs total. Overrides permitting distinct fallback can allow 8. No repeated validation retry for ModelUnavailableError. | YES. Source-default nominal generation stall budget up to 100s (4x25), plus embedding/RPC/DB; configured distinct fallback can increase it. No total deadline.
POST | /courses/{course_id}/content/upload | routers/diagnostic.py:89-124,232-350 | Optional Storage upload, sequential DB chunk inserts, then _embed_pending across pending course chunks. | Storage 30s; DB 60s each; embedding 20/25s or SDK; EMBED_SLICE_SECONDS=12. | Embedding has no application retry; errors counted and next chunk may continue. Loop checks 12s deadline BEFORE a chunk; in-flight embed/update is not cancelled. | YES. Storage alone can consume 30; one embedding can exceed 12; prior PDF extraction/chunk inserts and pending query are outside that deadline. No finite input-independent count of DB calls.
POST | /lti/launch | lti/routes.py:211-363; lti/security.py:30-49; lms/blackboard.py:269-346 | JWT verification may fetch platform JWKS; uncached course resolution uses Blackboard; instructor roster sync after cooldown may paginate and persist rows. Skill proposals are queued, not modeled inline. | JWKS library default 30s (PyJWT 2.13.0 lock/source); Blackboard OAuth and REST each 15s; DB 60s each. | No explicit LMS retry. Cached JWKS normally 0 fetches; cold/expired set fetch and unknown-kid forced refresh can yield up to 2 fetches. Roster and content helper work is not a retry loop. | YES. One cold JWKS fetch can exhaust 30s; OAuth+one REST can approach 30 before DB; multi-page roster has no whole-request deadline. _seed_course_skills helper is unused by current launch.
GET | /courses/{course_id}/roster | routers/diagnostic.py:139-145; lms/blackboard.py:303-346 | DB course-ref lookup -> cached OAuth token or token POST -> all roster pages. | DB 60s; OAuth 15s; each roster GET 15s. | 0 explicit retries; follows nextPage to exhaustion. A 429 is raised, not slept/retried. | YES. Nominal 15*(P + cold-token flag) seconds + DB; P is unbounded by route.
GET | /courses/{course_id}/content | routers/diagnostic.py:148-158; lms/blackboard.py:426-442 | DB course-ref lookup -> OAuth if needed -> recursive content metadata tree. include_attachments=False; no PDF downloads on this route. | DB 60s; OAuth 15s; root and each children GET 15s. | 0 explicit retries; recursive traversal has no total request-time budget. | YES. Nominal 15*(tree-request count + cold-token flag) seconds + DB, with no fixed tree size.
GET | /courses/{course_id}/assessments | routers/diagnostic.py:161-167; lms/blackboard.py:561-580 | DB course-ref lookup -> OAuth if needed -> one gradebook-column GET. | DB 60s; OAuth 15s; REST GET 15s. | 0 explicit retries; this implementation reads one gradebook response, not all pages. | YES. Cold OAuth + REST can consume 30 seconds before DB/response overhead.
PATCH | /courses/{course_id}/assessments/{column_id}/grade | routers/diagnostic.py:429-443; lms/blackboard.py:582-592 | DB course-ref lookup -> OAuth if needed -> grade PATCH to Blackboard. | DB 60s; OAuth 15s; PATCH 15s. | 0 explicit retries. No model fallback. | YES. Cold OAuth + PATCH can consume 30 seconds before DB/response overhead. Audit did not invoke this write route.
GET/POST | /lti/login | lti/routes.py:167-208 | Browser redirect to platform authorization URL, not server-to-server LMS HTTP. | No upstream request/timeout in this handler; signed-state work local. | No retry. | No server-to-server model/LMS time path here; common cold settings initialization is separate.


Async boundary findings (not extra model/LMS-in-request rows):
- POST /courses/{course_id}/skills/propose queues worker_state and kicks worker
  (diagnostic.py:170-181). POST /courses/{course_id}/ingest enqueues ingest_jobs
  (:184-218); no LMS/model walk remains inline. get_diagnostic queues missing
  items, and POST /practice/{course_id}/set queues legacy missing practice
  items. Bank-enabled branches select reusable rows. Lesson check generation
  is queued, but lesson outline/teaching content above is still inline.
- Worker invocation is asynchronous for the WORK, but the SDK invoke API call
  still occurs synchronously (bank/kick.py:32-35,76-79). SDK defaults and DB
  debounce operations can themselves outlast a 30s request. Swallowing an
  exception is not cancellation. No hosted calls were used to assess this.
- DB-only endpoints also inherit 60s per PostgREST operation; being absent
  from the model/LMS table does not prove they fit the Lambda budget.
- Current code imports AI helpers that are not reachable from route bodies;
  imports/comments alone were not counted as inline generation.

HTTP ERROR CLAIMS CHECK
main.py:51-63 explicitly maps ModelUnavailableError to application HTTP 502
with flat {detail: ...}. That is a valid Lambda response, not a Lambda crash.
ItemGenerationError also maps to 502 (:66-71). Generic unhandled Python or
PostgREST exceptions normally become application 500 through ASGI/Mangum,
not automatically 502. Lambda execution timeout/crash, malformed integration
response, invocation rejection and API integration timeout are distinct
platform outcomes. AWS documents function error/malformed responses as 502
and invocation rejection as 500; HTTP API troubleshooting requires integration
error evidence. The brief's blanket "502 or 503 when timeout/crash" is a
hypothesis, not a diagnostic rule. INC-002's old 503 observation is historical,
not a guarantee of current status. We did not reproduce it or change infra.
Sources: https://docs.aws.amazon.com/lambda/latest/dg/services-apigateway-errors.html
https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-troubleshooting-lambda.html

4. POST /tutor/ask — FULL CURRENT REQUEST/RESPONSE TRACE
Frontend: tutor/api/tutor.api.ts:18-34 calls shared api() as POST, sending
course_id, question, style, and optional conversation_id. No timeoutMs is
passed for tutor, so no AbortController deadline is created (client.ts:43-49).
useTutorAsk is used by FlashcardDeck/LessonChat/PracticePanel; TutorChat uses
conversation-aware send. Providers QueryClient query retry=1 (providers.tsx:9)
does not mean POST mutation automatically retries. Tutor mutations declare
no retry; manual retry is a separate user request. API Gateway does not retry
Lambda invocations (AWS Lambda API Gateway error documentation above).

1. Cold module/config path, if applicable: main.py:74 -> get_settings() ->
   config.py:14-28 may call Secrets Manager get_secret_value when the ARN
   is set. This is conditional initialization, not a repeated per-turn step.
   No explicit SDK deadline/retry policy; standard SDK config applies.
   Local Settings can read .env; this audit did NOT import app or Settings.
2. FastAPI Pydantic validates Ask body/style (tutor.py:327-340); missing/invalid
   body generally yields 422. Depends(get_current_user) validates bearer
   signature/audience/expiry locally (deps.py:136-153; jwt.py:46-53). No
   session introspection HTTP, OAuth call, LMS request, or model call here.
   Bad bearer results in 401. CurrentUser derives identity/tenant/role from
   signed claims, not request body.
3. Handler ask (:343-369) delegates to _ask (:372). No stream/async job path.
4a. Stateless (no conversation_id): rag.retrieve receives raw question,
    institution and request course_id (:376-378). One embedding call,
    then one PostgREST RPC match_content_items (rag.py:11-18). Construct
    context; safe_context strips limited PII patterns; append style prompt;
    answer(task='chat') returns one non-streaming answer (:379-382).
4b. Persistent: GET tutor_conversations scoped by conversation ID, user and
    institution (:124-138); absent yields 404. GET up to 10 prior messages
    descending then reverse into chronological history (:387-395). RAG uses
    the owned conversation's course_id (:397-400), not body course_id.
    GET ready tutor_attachments (:402-405), cap extracted text at 8,000 chars
    per file and joined block at 16,000 (:413-417). safe_context processes
    current context/question. answer(task='chat',history=...) (:420-426).
5. Model role selection: ai/router.py:15-39,94-106; OpenRouter source default
   chat is inclusionai/ling-3.0-flash-vl (config.py:147-149), role fallback
   nex-agi/nex-n2.5-mini:free (:162-165). Bedrock selects BEDROCK_MODEL_CHAT.
   These are SOURCE DEFAULTS; provider and model choices in deployed secrets
   are unknown. _ANSWER_MAX_TOKENS=2048 (router.py:50) bounds generated tokens,
   not wall time. Strip reasoning from returned text (:107).
6. OpenRouter /chat/completions (:440-443) has scalar timeout 25s (:248).
   _openrouter_converse converts HTTP/transport errors to ModelUnavailableError
   (:279-351). converse allows one fallback when a distinct configured fallback
   exists and status is None/404/408/429/500/502/503/504 (:104-138). Sleep 1.5s
   only for 429 or 503. If fallback fails, it propagates. Tutor passes no
   response_format; the structured-output downgrade retry does NOT apply.
   Provider preference is sent with allow_fallbacks=True (:413-426), so upstream
   provider reroutes are possible; their internal attempt count is not in repo.
7. Persistent success only: one bulk POST tutor_messages with both turns
   (:428-433), then PATCH tutor_conversations timestamp and first-turn title
   (:434-440), before returning {answer, conversationId}. Stateless success
   returns {answer}. No post-answer storage call in stateless mode. The message
   insert and timestamp patch are separate HTTP operations, not one transaction;
   a later failure can cause an error response after some persistence succeeded.
8. FastAPI serializes JSON; Mangum wraps API Gateway payload v2. Frontend api()
   checks status then JSON and Zod response schema. Non-OK throws API status/body
   error; 401 clears session and navigates to session-expired (client.ts:66-72).

Every outbound request in the steady-state tutor handler:

When | External call | Timeout | Retry count | Source
--- | --- | --- | --- | ---
persistent only, before RAG | GET /rest/v1/tutor_conversations | 60s scalar | 0 application retries | tutor.py:124-138
persistent only, before RAG | GET /rest/v1/tutor_messages (limit 10) | 60s scalar | 0 | tutor.py:387-395
both modes | POST embeddings: OpenAI /embeddings OR OpenRouter /embeddings OR Bedrock invoke_model | 20s / 25s scalar / SDK default 60s connect+read | 0 app retries; Bedrock SDK policy inherited | bedrock.py:141-151,184-189,460-490,548-595
both modes, after embed | POST /rest/v1/rpc/match_content_items | 60s scalar | 0 | rag.py:13-18; db/supabase.py:87-93
persistent only, after RAG | GET /rest/v1/tutor_attachments (ready only) | 60s scalar | 0 | tutor.py:402-405
both modes | POST OpenRouter /chat/completions OR Bedrock converse | 25s scalar / SDK default 60s connect+read | OpenRouter max 1 cross-model fallback + 1.5s on 429/503; Bedrock 0 app retries, SDK inherited | bedrock.py:104-138,163-179,440-443
persistent success only | POST /rest/v1/tutor_messages (both turns) | 60s scalar | 0 | tutor.py:428-433
persistent success only | PATCH /rest/v1/tutor_conversations | 60s scalar | 0 | tutor.py:434-440
cold initialization, separate from steady state | Secrets Manager get_secret_value, if configured | SDK inherited, not explicitly bounded | 0 app retries; SDK inherited | config.py:14-28; main.py:74


There is NO Blackboard/LMS call and NO Storage object download in /tutor/ask.
Attachments use extracted_text already in PostgREST; upload/extraction has a
separate endpoint. Stateless has 1 DB operation, persistent has 6 DB operations.
OpenAI-embedding nominal serial stall illustrations: stateless 20+60+25+25+1.5
=131.5s; persistent 20+6*60+25+25+1.5=431.5s, ignoring overhead. OpenRouter
embedding adds 5s to these illustrations. These are not true elapsed upper
bounds because of HTTPX inactivity semantics; actual Lambda execution is
cut at its configured 30s. A successful model answer can still lose its
response if subsequent DB writes consume the remaining budget.

Additional boundary finding: rag.retrieve embeds the raw question before
safe_context runs (tutor.py:376-381; rag.py:12). In persistent mode, raw prior
message content becomes history (:387-395) without safe_context processing.
safe_context only handles the newly constructed context/question (:420-425)
and strips emails and explicit 'name:' patterns (ai/deidentify.py:10-17), not
arbitrary names. This is a static gap against root CLAUDE.md's de-identify
before every model call rule (:34). No real student payload was tested.
Proposed resolution for a later approved work item: cover embedding input and
persisted history at the model boundary, with explicit de-identification tests.

4A. RANKED 502 HYPOTHESES — NOT A LIVE DIAGNOSIS
Ranking reflects explicit current code paths, not observed production rates.
If Fred observes ~30s elapsed with a generic Gateway response, move cumulative
execution timeout to rank 1; if body is the app's flat {detail:...}, dependency
failure is stronger. Do not infer a cause from status alone.

Order | Hypothesis | Confirming evidence/log signature | Limit
--- | --- | --- | ---
1 | Chat provider unavailable: timeout, transport, 404 retired model, 429, 5xx; fallback absent/equal/exhausted | OpenRouter request errored / chat request failed / model id no longer exists; optional primary unavailable then fallback error in SAME invocation; app ModelUnavailableError handler returns 502. Bedrock alternative: bedrock converse failed. | Fallback-warning alone is not failure; source defaults are not deployed settings. Correlate request ID and elapsed time.
2 | Embedding provider fails before chat starts | OpenAI embedding request failed/errored or OpenRouter embedding request failed/errored in correlated invocation; handler maps typed error to 502. | Embedding has no cross-provider rescue. Bedrock embed does not wrap errors here and normally causes 500 or a platform timeout, not the same typed 502.
3 | Cumulative Lambda timeout during RAG, DB, primary, fallback, or persistence | REPORT Status: timeout or Task timed out after 30... for the observed invocation; often duration near 30,000ms. | Confirms execution timeout only. No tutor stage timers exist. A 60s DB timeout cannot fire before a 30s Lambda kill. Raised to #1 for ~30s generic failures.
4 | Runtime process crash/OOM or cold initialization failure | Runtime.ExitError / Runtime.OutOfMemory / signal: killed / INIT_REPORT Status:error / Runtime.ImportModuleError; memory report supports OOM. | No source evidence it is happening. ASGI traceback alone usually means app 500, not process crash/502.
5 | API integration invocation/response failure outside normal Mangum path | Existing Gateway integration-error data must name invocation/response-format failure; match Gateway request with Lambda records or absence of invocation. | No application log line can prove a pre-invocation Gateway failure. Terraform has no API access-log destination. Exact status/mapping is unverified; do not assert every failure is 502/503.


PostgREST HTTPStatusError/ReadTimeout, malformed upstream JSON/shape and ordinary
Python exceptions can also break tutor, but usually produce app 500 unless
they exhaust the Lambda deadline or crash the process. They are not established
direct 502 causes. Missing auth is 401, invalid request is 422, bad conversation
is 404; neither frontend/backend path mismatch nor those guards explain a 502.

4B. CLOUDWATCH QUERIES
Complete ready-to-run, privacy-preserving queries and interpretation notes are
in [tutor-cloudwatch-queries.md](<tutor-cloudwatch-queries.md>). They cover duration/memory,
timeouts/fatal runtimes, provider status/transport errors, fallback attempts,
ASGI exceptions, per-invocation correlation and optional EXISTING Gateway logs.
They have NOT been run. No tutor-specific stage timer or response-status logger
exists in source; practice_submit_timing (main.py:32-47) is practice-only.
Current Terraform does not establish API access logging. The audit proposes no
infrastructure/deployment change. Fred retains responsibility for live evidence.

5. STUDY DECK END STATE — EXACT CONDITIONS
A. FlashcardDeck (normal sequential session; file in features/flashcards/components)
- mode defaults to 'review' (FlashcardDeck.tsx:95), requests 20 cards (:125).
  SkillHub supplies studyMode ?? 'review' (SkillHub.tsx:192-197); StudyBrowser
  can start 'all' through its primary/Study all actions (:200-213).
- Data/loading/error and missed-question states are checked before normal
  empty/completion displays. Empty branch is exactly:
  `if (!data || data.cards.length === 0)` (FlashcardDeck.tsx:316).
  Bank loading/no-material/preparing/error guards precede the caught-up view
  (:317-358). A remainingToday===0 membership-loading guard precedes it (:359).
- Daily-limit predicate is exactly:
  `mode === "review" && remainingToday === 0 &&
   (membership.data?.counts.new ?? 0) > 0` (:313-315).
  If true within the empty branch, show 'Daily new card limit reached'
  (:362-368), not 'All caught up'.
- Normal empty-state title uses exactly:
  `const allCaughtUp = data ? data.stats.tracked > 0 : false` (:370)
  `title={allCaughtUp ? "All caught up" : "No cards yet"}` (:373).
  This checks tracked-count, not mastery, not all-known, and not reps>0.
- 'Reload deck' appears on bank availability error (:350-355), in the final
  empty branch (:383-388; changes to 'Checking cards…' while fetching), and
  on normal completion ComposeDock (:398-434). Loading/no-material/preparing/
  daily-limit views do not offer that normal empty-state Reload button.
- End-of-deck is `currentIndex + 1 >= queueLength` -> setDeckDone(true)
  (:578-583). Marking false appends the card to the local session queue
  (:475-479,491-494); it must be reached again before that queue can finish.
  First rating posts a review; repeats already in postedRatingIdsRef are
  local only (:496-514). A first 'Still learning' then later local 'Got it'
  does NOT replace the first server rating. Failed mutation rolls UI back
  (:559-572). Study completion can render optimistically while save is pending;
  that display is not by itself proof of a saved review.
- Missed-test review normally returns through onReviewDone instead of the
  standard completion/reload view (:398-415,554-556). It sources cards from
  selected test results, not the regular deck selector (:125-167).
- reloadDeck resets local index/phase/done/ratings/session cards and calls
  `refetch()` (:596-610). It does NOT itself POST a rating or clear SRS state.
  It also does not reset offset or change mode to 'all'. New response sessionId
  changes responseSessionKey and initializes returned sessionCards (:200-216).
  Empty server result takes the empty branch on re-render. This is a rendered
  component-state transition, not a navigation call to an 'All caught up' route.
- Empty-view Reload instead calls refreshEmptyDeck (:586-593); it fetches and
  can toast that nothing is due. Neither action guarantees replay of old cards.

B. SkillHub StudyBrowser (browse view; no schedule writes on native membership GET)
- Uses membership GET (:38), not deck GET, except compatibility fallback below.
  `if (cards.length === 0)` (:69), then loading/no-material/preparing/error
  checks (:70-97). Bank-error branch has 'Reload deck' (:94).
- Empty title's exact predicate is:
  `data?.isFallback === true && (data.fallbackTracked ?? 0) > 0` (:98),
  selecting 'All caught up' vs 'No cards yet' (:101). Only the fallback caught-
  up empty view offers Reload (:107). Native successful membership empty
  response alone does not use tracked count to claim caught up.
- With nonempty membership, `dueNow = cards.filter(isDueNow).length` (:113),
  where `state !== "new" && (card.due || card.state === "due")` (:299-301).
  `hasNewCards = counts.new > 0` (:118). Primary label is 'Review due (N)'
  if dueNow>0, otherwise Start/Continue studying when new cards exist, otherwise
  'All caught up' (:120-124). It is disabled exactly when
  `dueNow === 0 && !hasNewCards` (:204). This is a button label within the
  browse view, not the empty view title. Membership still lists known/future
  cards; Study all remains available (:209-213).
- `startWithAll = dueNow === 0 && hasNewCards` (:119). Primary invokes
  onStart(startWithAll ? 'all' : 'review') (:203). Therefore not every finished
  StudyBrowser session can follow the empty-review-queue story: mode='all'
  reselects the stable pool, independent of due status.
- If membership GET returns 404, flashcards.api.ts:33-66 falls back to the old
  due/new deck endpoint, sets isFallback and fallbackTracked. This fallback
  is stateful because it calls the selector; the native membership GET
  (routers/flashcards.py:61-126) is side-effect-free.

C. Why completion -> Reload can show All caught up, and where 'seen' comes from
1. A review-mode GET serves due studied cards first (flashcards.py:244-284).
   srs.is_due returns False for missing schedule or reps=0 (srs.py:156-168),
   due_cards requires due_at<=now and excludes graduated rows (:299-317).
2. Fresh study top-up uses bank/serving.py:45-53, explicitly removing all
   already-tracked item IDs. Selected fresh cards are atomically claimed by
   claim_study_cards RPC (flashcards.py:297-302), ensure_tracked (:308-312),
   and record_exposure(studied=True) (:313-315). Exposure writes
   last_studied_at (bank/serving.py:106-128). This happens on SERVE, before
   flip/rating. 'Seen' can refer to schedule tracking or exposure telemetry;
   they are distinct from a counted review or mastery.
3. POST review calls RPC review_flashcard (flashcards.py:476-487). Migration
   0027_item_reviews.sql:142-175 computes was_due, guards first session rating,
   counts miss/due success, increments reps, and moves due_at into the future.
   First good at default ease advances to box1, approximately 61.44h; first
   miss becomes box0/ease2300, approximately 9.2h. These are scheduler-source
   examples, not observed database values. Early good leaves schedule unchanged.
   A local requeued success does not override first-miss scheduling.
4. The hook deliberately leaves the active deck query uninvalidated while
   reviewing (use-flashcards.ts:35-56); only gamification, counts-peek key
   [...,0], and membership are invalidated. Thus the completion view still
   holds the old session list until explicit Reload.
5. Reload fetches current selection again. Finished cards are now future-due
   or graduated and tracked, so they are neither currently due nor fresh. If
   there are no additional eligible fresh/due cards, server returns empty
   cards plus tracked>0, and FlashcardDeck shows All caught up after the
   higher-priority guards. If fresh cards remain, another deck may appear;
   if cap is exhausted and new membership remains, Daily new card limit
   reached may appear. It is NOT unconditional after every completed deck.
6. mode='all' is different: flashcards.py:192-241 selects the full eligible
   pool in stable user/course/item hash order and offset pages, claims with
   exemption=True, records exposure, and returns it regardless of due status.
   Reload keeps mode/offset and can replay that group. Cards can disappear
   only if pool/eligibility/data changes; mere completion does not require an
   empty response. No mastery writes are made by flashcard self-rating.

D. Additional static defects and documentation drift to record for Part B triage
- Counts-only peek contradiction: routes/course/flashcards.tsx:20 says
  'limit=0 returns ... counts without fetching cards' and :21 calls it.
  Backend flashcards.py:160 uses `10 if limit is None else max(1, limit)`;
  the subsequent fresh selection/claim/exposure runs normally (:292-315).
  It therefore can allocate one card and spend daily allowance on landing-
  page load. Invalidation of the [...,0] query after ratings can repeat this.
  Proposed resolution: define a side-effect-free count/read contract, then
  restore that contract in a separately approved fix; do not silently reinterpret
  limit=0 as desired new behavior.
- Served but unreviewed cards can fall through normal review selection:
  claim creates reps=0 schedule (0030:82-101); bank top-up excludes tracked
  IDs (serving.py:46-53), while is_due rejects reps=0 (srs.py:163-164).
  Reloading/abandoning an unfinished session can therefore strand new cards
  outside normal review until Study all/test path rates them. Membership
  continues to call them New (srs.card_state:179-180). With an exhausted
  fresh pool and nonzero tracked count, FlashcardDeck may say All caught up
  although some cards have never been rated. Proposed resolution: planner
  should define how claimed/unreviewed cards re-enter review, with counts,
  cap accounting and selector predicates aligned. This is source-derived,
  not database/runtime reproduction.
- Deck docstring says 'Answer keys never leave the server' (flashcards.py:153),
  but back label/explanation are intentionally returned (:321-346,394-408);
  frontend schema explicitly requires back (flashcards.schema.ts:18-25).
  Proposed resolution: describe the deliberate Study vs Test response policy
  precisely; do not remove Study backs based on the stale docstring.
- Upload comment claims a large PDF cannot time out (diagnostic.py:303-308),
  while sequential chunk writes and non-cancelling 12s embedding slice
  (:313-330; _embed_pending:102-123) can exceed the Lambda wall. Proposed
  resolution: document the actual bound, and later approve a bounded work
  design if desired. No infrastructure proposal is made here.

6. RESOLVED DOCUMENT CONFLICTS AND SCOPE
- INC-002: docs/bugs/tutor-ask-hits-the-30s-wall.md:25-40,98-100 is historical.
  Current dedicated role/defaults at ai/router.py:15-39,53-68 and config.py:
  128-165 differ. Per Fred: preserve incident, keep live recovery unverified.
- Root CLAUDE.md:96 ('pill-shaped') versus styles/DESIGN.md:39 ('boxy/not
  pills') was resolved by Fred: DESIGN.md governs. No visual work performed.
- Superseded docs/SUPABASE.md setup versus all 36 migrations: Fred's resolution
  retained; no schema replay, hosted inspection or Part C work was performed.
- Proposed handover pack is not installed. Root CLAUDE.md was read; AGENTS.md,
  docs/README.md, docs/features/ and WI-01 work-item paths are absent here.
  Missing services/api/CLAUDE.md was recorded. The supplied brief is this
  audit's work item; no pack files were copied or created in the repository.
- Revised stop rule permits recording repository doc/code conflicts and
  continuing. No remaining pack/brief contradiction blocks the audit as written.
  Its 29s/status claims were treated as hypotheses per explicit instruction.
- Supabase skill was read for the DB-wrapper trace. No implementation or
  schema work occurred; official changelog markdown retrieval through web
  failed with unsupported content-type. No Supabase capability claim or fix
  depends on that unavailable changelog; no retry against a hosted project.
- No db:* script was executed or added. Existing schema:types is hosted-ref
  oriented but was not run; changes to package scripts are outside this task.

7. CHECKS, EVIDENCE AND LIMITATIONS
Exact command forms and static check results are in checks.txt; raw tool
commands/results are also recorded in this chat. Inventory validation asserted
12 included routers, 60 unique route method/path pairs, 42 extracted frontend
calls, 42 method/path matches, 18 routes without a wrapper. All passed.
Source scanning read Python/TS/TF/docs and migration text only. App was not
imported, so Settings did not load .env or invoke Secrets Manager. No dependency
installation, generated OpenAPI export, lint, typecheck, build or test suite was
run. Those would not establish live endpoint recovery and were unnecessary for
this no-change static audit. SQL was not executed. No true wall-clock maximum
or deployed model/SDK setting is claimed. All needed Part A inventories/tables,
current tutor trace/hypotheses/query guidance and deck-state trace are supplied.
The intentionally incomplete checks are live/runtime verification, not missing
Part A source analysis. Part B implementation remains explicitly gated.

Evidence files in this scratch directory:
- audit-report.txt: this complete human-readable report, including all tables.
- routes.tsv / routes.json: full 60 application-route inventory with auth.
- frontend-calls.tsv / frontend-calls.json: all 42 calls, source lines, hooks,
  full screen paths, normalized method/path and match results.
- unmatched-frontend.tsv: zero-row mismatch result (header only).
- no-frontend.tsv: 18 classified routes without SPA wrappers.
- timing-paths.tsv: complete model/LMS timing-risk table.
- cloudwatch-queries.txt: maintainer queries; not executed.
- source-evidence.txt: selected numbered, non-secret source excerpts.
- manifest.json: revision, counts, method and limitations.
- checks.txt: performed checks and resource/worktree state.
- build_report.py: local scratch report builder (no app import/network).

AUDIT REPORT
Task / brief ID: BRIEF-01 / WI-01, Part A complete as a static audit
Branch and worktree: codex/endpoint-reachability; .
Base revision: e9de105d7f3074ec39f54e32b1f2b5e2bda669ed
Files changed: none in repository; scratch evidence only outside repository
REQ / WI IDs touched: WI-01 audited; no REQ/spec/file changes
Commands run and results (tests, lint, typecheck, build):
  Read-only git/source searches and AST/reference checks; static assertions passed.
  Tests/lint/typecheck/build/runtime/DB checks not run; see checks.txt.
Spec changes made: none
Evidence added: /tmp/kala-endpoint-audit-20261024-a705/ (outside repository) (local only, not retained)
Anything not done, and why:
  Part B not authorized. Hosted API/CloudWatch/LTI recovery evidence belongs to Fred.
  No live deployment configuration, HTTP responses, local DB replay or performance
  measurements obtained; this report distinguishes source findings from runtime proof.
Risks or questions for the planner:
  Prioritize cumulative request budgets, counts-only peek mutation, claimed/unreviewed
  card eligibility, current tutor data/model boundaries, and staff-route authorization.
  No remaining audit blocker; planner approval is required for any Part B fix list.
Worktree cleanliness: clean at final verification; same branch/HEAD; no repository edits
Scratch/Docker resources: only this scratch directory; no DB/container/server/process started
Secrets printed: none (confirmed)
