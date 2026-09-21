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
--   Deleting a row those point at would silently destroy SRS progress or
--   blank a lesson's check. Verified against the live DB on 2026-09-19 that
--   this is NOT a risk HERE: of 293 items matching the delete filter, ZERO
--   are referenced by srs_state (31 rows, all kind='tutor' or 'flashcard') or
--   by guided_lesson_steps (30 checks, all kind='tutor').
--
--   The `kind in ('diagnostic','practice')` filter is what keeps this safe.
--   If you ever widen it to include 'flashcard' or 'tutor', re-run the step 0
--   collision check below FIRST — that version WOULD cascade away SRS
--   schedules and null out lesson checks.
--
-- LIVE NUMBERS, measured 2026-09-21 (AWS101, immediately before the reset):
--   generated_items      313 rows  (practice 283, tutor 16, diagnostic 10,
--                                    flashcard 4)
--   srs_state             31 rows  (flashcard 14, tutor 17; 21 of them reviewed)
--   guided_lesson_steps   30 checks, ALL kind='tutor'
--
--   Collisions for the filter AS WRITTEN (diagnostic+practice): 0 and 0. Safe.
--
--   Collisions if you ALSO include 'flashcard': FOUR srs_state rows cascade
--   away — 4 of the 14 flashcard schedules (max 2 reps each). Not unreviewed
--   seeds: those four have real review history belonging to a student. Small,
--   but it is a decision rather than a formality. Widen only if you accept it.
--
--   Do NOT add 'tutor': it would take 17 srs_state rows (17 reviewed, one with
--   28 reps) AND all 30 lesson comprehension checks, which point at tutor
--   items. Nothing about this task calls for touching tutor.
--
--   Lesson checks are unaffected by the diagnostic+practice filter either way.
-- =====================================================================

-- ---------------------------------------------------------------------
-- STEP 0 — inspect first. Do not skip this.
-- Run these to see the blast radius before deciding. Substitute the real
-- course id; the one below is the AWS101 row from the 2026-09-19 probe.
-- ---------------------------------------------------------------------
-- \set course_id 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'

-- What is in the bank, by kind? This is where you decide whether flashcards
-- (kind='flashcard') belong in the reset. They were NOT called out as
-- low-quality, so they are deliberately EXCLUDED from the deletes below.
select kind, count(*)
  from public.generated_items
 where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
 group by kind
 order by kind;

-- How many sets, and how many student attempts would cascade away?
-- The srs_state / check_item_id columns are the collision check: these MUST
-- both read 0 before you run the deletes. See the FK note in the header.
select
  (select count(*) from public.quiz_sets
    where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de')            as sets,
  (select count(*) from public.quiz_set_attempts a
     join public.quiz_sets s on s.id = a.set_id
    where s.course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de')          as set_attempts,
  (select count(*) from public.evidence_events
    where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de')            as evidence_kept,
  (select count(*) from public.mastery_state
    where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de')            as mastery_kept,
  -- MUST be 0. Non-zero means an SRS schedule would be cascade-deleted.
  (select count(*) from public.srs_state ss
     join public.generated_items gi on gi.id = ss.item_id
    where gi.course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
      and gi.kind in ('diagnostic','practice'))                          as srs_collisions,
  -- MUST be 0. Non-zero means a lesson check would be set to null.
  (select count(*) from public.guided_lesson_steps gs
     join public.generated_items gi on gi.id = gs.check_item_id
    where gi.course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
      and gi.kind in ('diagnostic','practice'))                          as lesson_check_collisions;


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
-- Catches: ungrouped practice items (/next), diagnostic items, and
-- diagnostic items that were never given a set_id. Explicitly scoped to the
-- two kinds in question; flashcards are left alone.
--
-- If you decide flashcards SHOULD be reset, change this to
--   and kind in ('diagnostic', 'practice', 'flashcard')
-- The user has signalled they want flashcards included. See the LIVE NUMBERS
-- note in the header: that choice cascades 4 reviewed srs_state rows.
-- ---------------------------------------------------------------------
delete from public.generated_items
 where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
   and kind in ('diagnostic', 'practice');


-- ---------------------------------------------------------------------
-- STEP 3 — verify. Expect bank counts at zero and the kept counts unchanged
-- from the step 0 readings.
-- ---------------------------------------------------------------------
select 'generated_items remaining' as check, count(*)::text as value
  from public.generated_items
 where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
   and kind in ('diagnostic', 'practice')
union all
select 'quiz_sets remaining', count(*)::text
  from public.quiz_sets
 where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
union all
select 'evidence_events (must be unchanged)', count(*)::text
  from public.evidence_events
 where course_id = 'ae4e7680-f94b-4652-b3f6-b9c32f4420de'
union all
select 'mastery_state (must be unchanged)', count(*)::text
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
