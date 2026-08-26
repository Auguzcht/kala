-- =====================================================================
-- Kala — 0006_module_scope.sql
-- Folder/module scoping for content and skills. Generic across
-- institutions: parent_lms_ref + folder_path capture whatever nesting an
-- institution's own Blackboard courses actually use (see
-- app/lms/hierarchy.py). module_ref is a convenience denormalization of
-- the top-level ancestor for the common case, not a hardcoded assumption.
-- =====================================================================

alter table public.content_items
  add column parent_lms_ref text,
  add column folder_path    jsonb not null default '[]'::jsonb,
  add column module_ref     text;

alter table public.skills
  add column module_ref text;  -- nullable: inferred from tagged content on
                                -- ingest, or a manual override (e.g. from
                                -- the CEA skills spreadsheet's "Course /
                                -- Module" column) for skills that don't map
                                -- cleanly to any single ingested folder.

create index content_items_module_idx on public.content_items (course_id, module_ref);
create index skills_module_idx on public.skills (course_id, module_ref);
