-- =====================================================================
-- Kala — question-bank reset for one course (AWS101 | Cloud Practitioner)
--
-- DRAFT. NOT RUN. The user runs this in the Supabase SQL editor; this
-- environment has no linked CLI and no DB password, same as every migration
-- so far.
--
-- WHY THIS EXISTS
--   The generated question bank was built before three fixes landed, and its
--   contents reflect all three old failure modes:
--     1. Skills with no retrievable content used to fall back to generating
--        from the skill's bare name, producing fabricated items. (Fixed
--        earlier: NoCourseContentError is now raised instead.)
--     2. Retrieval was k=3 with an identical excerpt handed to every roll in
--        a batch, so a batch reworded one fact five times. (Fixed in f0ad10e.)
--     3. The model's "according to the excerpt" habit. (Fixed in f0ad10e.)
--   None of those conditions apply to a fresh generation call, so the existing
--   rows are stale by construction and worth clearing before a demo.
--
-- SCOPE WARNING — READ BEFORE RUNNING
--   There is NO per-user generated content. `generated_items` and `quiz_sets`
--   have no user_id column, by design: diagnostic items are one row per skill
--   shared across every student in the course, and quiz sets are shared decks.
--   So this is a COURSE-WIDE reset, not one test account's cleanup.
--
--   That is acceptable right now because every current user is a test account.
--   It stops being acceptable the moment a real student exists — resetting
--   mid-term would delete questions students are actively working through.
--   Re-read this paragraph before running it on a live cohort.
--
--   SCOPE, as decided 2026-09-21: diagnostic + practice + FLASHCARD items, and
--   the course's practice quiz_sets. Tutor items are OUT of scope and must
--   stay out — see the collision note below for why that is not negotiable.
--
-- WHAT THIS DOES *NOT* TOUCH
--   evidence_events and mastery_state are NOT deleted. No FK links them to the
--   item bank: they hold the actual learning history (what each student
--   answered, and the mastery estimate derived from it), and they remain valid
--   after the questions themselves are gone. `evidence_events` is append-only
--   by trigger and cannot be updated anyway. Deleting them would destroy the
--   study split's evidence base.
--
-- TWO FKs THE ORIGINAL BRIEF MISSED — both checked, both safe, but read this:
--   Two tables DO reference generated_items(id), contrary to "nothing links
--   them by FK":
--     * srs_state.item_id            -> generated_items(id) ON DELETE CASCADE
--       (a student's spaced-repetition schedule)
--     * guided_lesson_steps.check_item_id -> generated_items(id) ON DELETE SET NULL
--       (a lesson's comprehension-check question)
--
-- COLLISIONS — the two scopes are NOT treated the same, deliberately:
--
--   FLASHCARD-SCOPED: EXPECTED TO BE NON-ZERO. This reset INCLUDES flashcards
--   (decided 2026-09-21), so the srs_state rows pointing at flashcard items
--   cascade away with them. Measured before running: 14 such rows, of which 4
--   have real review history (max 2 reps each). That is the ACCEPTED COST of
--   including flashcards, not a red flag and not a reason to abort — the goal
--   is a clean regenerated bank, and a handful of lightly-reviewed flashcard
--   schedules is worth that. Do not stop on a non-zero flashcard count.
--
--   TUTOR-SCOPED: MUST BE 0, and is unchanged by this decision. Tutor items
--   are NOT deleted (17 srs_state rows point at them, one with 28 reps) and
--   all 30 lesson comprehension checks do too. A non-zero tutor collision
--   means the filter was widened past what was decided — stop and investigate.
--
-- The `kind in ('diagnostic','practice','flashcard')` filter is what keeps the
-- tutor side safe. Never add 'tutor'.
-- =====================================================================

-- ---------------------------------------------------------------------
-- STEP 0 — inspect first. Do not skip this.
-- Run these FRESH immediately before the deletes. Do not reuse numbers from
-- an earlier session or an earlier run of this file.
-- ---------------------------------------------------------------------
-- \set course_id 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'

-- What is in the bank, by kind.
select kind, count(*)
  from public.generated_items
 where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
 group by kind
 order by kind;

-- Blast radius. Two of these are HARD GATES, two are INFORMATIONAL:
--
--   tutor_srs_collisions        MUST BE 0  — tutor is excluded; non-zero means
--                                             the filter was widened too far.
--   lesson_check_collisions     MUST BE 0  — all checks are tutor-scoped.
--   flashcard_srs_collisions    EXPECTED    — non-zero is the accepted cost of
--                                             including flashcards. Note the
--                                             number, do not abort on it.
--   flashcard_srs_reviewed      INFO        — how many of those rows have real
--                                             review history (reps > 0).
select
  (select count(*) from public.quiz_sets
    where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de')            as sets,
  (select count(*) from public.quiz_set_attempts a
     join public.quiz_sets s on s.id = a.set_id
    where s.course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de')          as set_attempts,
  (select count(*) from public.evidence_events
    where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de')            as evidence_to_keep,
  (select count(*) from public.mastery_state
    where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de')            as mastery_to_keep,
  -- MUST be 0.
  (select count(*) from public.srs_state ss
     join public.generated_items gi on gi.id = ss.item_id
    where gi.course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
      and gi.kind = 'tutor')                                             as tutor_srs_collisions,
  -- MUST be 0.
  (select count(*) from public.guided_lesson_steps gs
     join public.generated_items gi on gi.id = gs.check_item_id
    where gi.course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
      and gi.kind in ('diagnostic','practice','flashcard'))              as lesson_check_collisions,
  -- EXPECTED non-zero: this is the flashcard trade-off, already accepted.
  (select count(*) from public.srs_state ss
     join public.generated_items gi on gi.id = ss.item_id
    where gi.course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
      and gi.kind = 'flashcard')                                         as flashcard_srs_cascading,
  -- How many of those carried real review history.
  (select count(*) from public.srs_state ss
     join public.generated_items gi on gi.id = ss.item_id
    where gi.course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
      and gi.kind = 'flashcard' and ss.reps > 0)                         as flashcard_srs_reviewed;


-- ---------------------------------------------------------------------
-- STEP 1 — delete the quiz sets.
--
-- This cascades TWO things automatically, so do NOT delete them separately:
--   * generated_items WHERE set_id = that set  (via the set_id FK)
--   * quiz_set_attempts rows for that set       (per-student attempt counters)
--
-- Only kind='practice' sets are removed. Diagnostic items are NOT grouped
-- into sets (they are one row per skill), so they have set_id null and would
-- not be caught here — step 2 handles them.
-- ---------------------------------------------------------------------
delete from public.quiz_sets
 where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
   and kind = 'practice';


-- ---------------------------------------------------------------------
-- STEP 2 — delete the remaining item rows for this course.
--
-- Catches: ungrouped practice items (/next), diagnostic items, and (as of the
-- 2026-09-21 decision) flashcard items. Explicitly scoped to these three
-- kinds; TUTOR IS NEVER INCLUDED — 17 srs_state rows (one with 28 reps) and
-- all 30 lesson comprehension checks point at tutor items.
--
-- Including 'flashcard' cascades its srs_state rows. That is the accepted
-- cost recorded in the header. Expect a non-zero flashcard count in step 0.
-- ---------------------------------------------------------------------
delete from public.generated_items
 where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
   and kind in ('diagnostic', 'practice', 'flashcard');


-- ---------------------------------------------------------------------
-- STEP 3 — verify.
--
--   generated_items_remaining   MUST BE 0 for the widened scope
--   quiz_sets_remaining         MUST BE 0
--   evidence_events             MUST equal step 0's evidence_to_keep
--   mastery_state               MUST equal step 0's mastery_to_keep
--   srs_flashcard_remaining     MUST BE 0  — those cascaded, as accepted
--   srs_tutor_remaining         MUST equal step 0's tutor count (17)
--   lesson_checks_remaining     MUST equal step 0's count (30)
-- ---------------------------------------------------------------------
select 'generated_items remaining (scope)' as check, count(*)::text as value
  from public.generated_items
 where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
   and kind in ('diagnostic', 'practice', 'flashcard')
union all
select 'quiz_sets remaining', count(*)::text
  from public.quiz_sets
 where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
union all
select 'tutor items remaining (must be UNCHANGED)', count(*)::text
  from public.generated_items
 where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
   and kind = 'tutor'
union all
select 'srs_state flashcard remaining (expect 0, cascaded)', count(*)::text
  from public.srs_state ss
  join public.generated_items gi on gi.id = ss.item_id
 where gi.course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
   and gi.kind = 'flashcard'
union all
select 'srs_state tutor remaining (must be UNCHANGED)', count(*)::text
  from public.srs_state ss
  join public.generated_items gi on gi.id = ss.item_id
 where gi.course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
   and gi.kind = 'tutor'
union all
select 'lesson checks remaining (must be UNCHANGED)', count(*)::text
  from public.guided_lesson_steps gs
  join public.generated_items gi on gi.id = gs.check_item_id
 where gi.course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
union all
select 'evidence_events (must be UNCHANGED)', count(*)::text
  from public.evidence_events
 where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
union all
select 'mastery_state (must be UNCHANGED)', count(*)::text
  from public.mastery_state
 where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de';


-- =====================================================================
-- NOTE ON WHAT HAPPENS NEXT
--   The next diagnostic or practice request per skill will regenerate items
--   with the new prompt and the wider retrieval window. That means the
--   reset doubles as a fresh live test of both fixes — but be aware the
--   corpus is still the pre-PDF one (88 chunks, see task #22), so
--   repetition on shallow skills will persist until the AWS PDFs are
--   ingested. Clearing the bank does not add content.
-- =====================================================================
