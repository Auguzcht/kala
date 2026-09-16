-- =====================================================================
-- Kala — 0014_content_tag_attempted.sql
-- Records that a chunk has been THROUGH the tagger, independently of whether
-- the tagger matched it to a skill.
--
-- Why this is needed. Ingest is now bounded and resumable: it tags chunks
-- whose skill_id is still null, a slice at a time, and reports `remaining` so
-- the caller knows whether to call again. That worked while tagging was
-- failing outright, but it has a hole with tagging WORKING: a chunk whose text
-- legitimately matches none of the course's skills would stay skill_id null
-- forever, so `remaining` could never reach zero and a caller would loop
-- re-POSTing against content that will never tag.
--
-- Nullable timestamp rather than a boolean: it costs the same, and "when was
-- this last attempted" is the question you actually want when diagnosing why
-- something did not tag (e.g. re-attempting after new skills are approved).
-- Rows tagged before this migration have skill_id set and are already excluded
-- from the pending query, so backfilling them is unnecessary.
-- =====================================================================

alter table public.content_items
  add column if not exists tag_attempted_at timestamptz;

-- Partial index: the resume query filters on skill_id is null, and only those
-- rows matter. Keeps the pending scan cheap as a corpus grows.
create index if not exists content_items_untagged_idx
  on public.content_items (course_id, institution_id)
  where skill_id is null;
