-- =====================================================================
-- Kala — 0016_lms_course_resolution_cache.sql
--
-- Three dev-instance problems, one cause: Kala re-asks Blackboard for things
-- it already knows, on every launch, with no backoff.
--
--   1. resolve_course_ref hit GET /courses/externalId:{id} on EVERY launch
--      because the courses table stored the RESOLVED internal id but never
--      the external id it was resolved from — so no local lookup was even
--      possible. lms_course_external_id closes that: once resolved, Kala can
--      find the course by the id the LTI launch actually carries.
--
--   2/3. Roster sync and skill seeding are documented as running on every
--      instructor launch (self-healing on a timescale of minutes). That is
--      right for production and ruinous for dev testing, where the same
--      instructor relaunches repeatedly and repays a full paginated roster
--      pull plus a content walk each time. last_roster_sync_at and
--      last_skill_seed_at let the launch check a cooldown first.
--
-- Additive and nullable throughout: existing rows keep working and simply
-- resolve once more (populating lms_course_external_id) on their next launch.
-- No backfill, no rewrite of historical rows.
-- =====================================================================

alter table public.courses
  add column lms_course_external_id text,
  add column last_roster_sync_at    timestamptz,
  add column last_skill_seed_at     timestamptz;

-- One course per (institution, external id). Partial: the column is null for
-- every course created before this migration and for any course whose launch
-- carried no context id, and those must not collide with each other.
--
-- This is the index the launch's lookup rides: WHERE institution_id = ?
-- AND lms_course_external_id = ?. It is also the guard that stops two
-- concurrent first-launches of the same course from creating two rows.
create unique index courses_institution_lms_external_id_key
  on public.courses (institution_id, lms_course_external_id)
  where lms_course_external_id is not null;

comment on column public.courses.lms_course_external_id is
  'The LMS-side course identifier exactly as the LTI launch presents it '
  '(LTI context id). Distinct from lms_course_id, which is the id the LMS '
  'REST API uses internally. Stored so a launch can resolve the course '
  'locally instead of paying a Blackboard REST call every time.';

comment on column public.courses.last_roster_sync_at is
  'When a roster reconciliation last COMPLETED successfully. The launch '
  'skips the pull if this is inside the cooldown window. Null means never '
  'synced, which always syncs. Written only on success so a failed or '
  'skipped attempt never blocks a later retry.';

comment on column public.courses.last_skill_seed_at is
  'When skill seeding last COMPLETED successfully. Same cooldown contract '
  'as last_roster_sync_at.';
