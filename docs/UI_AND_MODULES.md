# UI principles and module scoping

Scoped working doc, same pattern as `BACKEND.md` / `SUPABASE.md`. Not part of
`masterplan.md` itself, this is implementation instruction for this batch of
changes. Delete or fold into `architecture.md` once done.

---

## 1. Do now: layout width

The main content area renders too narrow, with excess side whitespace, across
every shell (student and instructor). This is a container class, not a
per-page issue.

**Fix:** find the wrapper around `{children}` in the shell components
(`InstructorShell.tsx` and its student equivalent). It's currently capped
too tight (something like `max-w-7xl mx-auto`). Widen it, or drop the max
width entirely and rely on consistent side padding instead. Do not touch
the sidebar or top bar, only the content wrapper.

## 2. Do now: task-driven UI, not metadata-driven UI

Principle to hold going forward, for any new screen: Kala's core surfaces
(diagnostic, practice, tutor, flashcards, heatmap, twin, at-risk list) are
each a fixed, purpose-built workflow. Build each one bespoke, hand-laid-out
for what that workflow actually needs. Do **not** build a generic
schema-driven form/table renderer that walks `skills` or `mastery_state`
column-by-column and infers a UI from field types. That pattern is right for
CRM-style record management, not for these workflows, and it would make the
Heatmap and Twin visualizations worse, they only work because they're
hand-built around Bloom's specific six-level ladder shape.

**The one exception:** skill and module curation is genuinely record-shaped,
variable data (name, Bloom level, module, weight, description) with a CRUD
lifecycle. That's the one place a lightweight metadata-driven admin form is
appropriate, see section 3.

Apply this as a review lens on any new screen, not a one-time refactor: if a
new page is a workflow, build it bespoke; if it's record curation, it can be
form-driven.

## 3. Done: module scoping (backend)

Built and tested (32/32 tests passing, including 6 new ones), not deferred
anymore. This section now documents what shipped, for anyone reading the
repo later, rather than instructing someone to build it.

### What was true before this
- `skills` and `content_items` were flat per `course_id` only, no module or
  week concept anywhere in the schema.
- `lms/blackboard.py`'s `get_content()` already fetched `parent_id` for every
  content item, but `ingest_course()` discarded it, only `course_id`,
  `lms_ref`, and chunk text were persisted.
- Blackboard course content is organized as top-level module folders (e.g.
  `Module 1 | AWS Solution Prototype Building`), a structure already present
  in every course and simply being thrown away on ingest.
- The CEA skills spreadsheet's "Course / Module" column had nowhere in the
  schema to land.

### Design decision (unchanged from the original plan)
Derive module scope from a course's own top-level content folders, generic
over however many levels deep or however an institution names them, not
from unit count and not primarily from the spreadsheet.

### What actually shipped
1. `packages/db/migrations/0006_module_scope.sql`: adds `parent_lms_ref`,
   `folder_path` (jsonb, full ancestor chain root→immediate parent), and
   `module_ref` (top-level ancestor, denormalized for fast filtering) to
   `content_items`; `module_ref` to `skills`.
2. New module: `app/lms/hierarchy.py`. `build_folder_paths()` walks the flat
   list `get_content()` returns via `parent_id` and reconstructs each item's
   ancestor chain, no assumption about nesting depth or naming, so it works
   the same for MMCM's one-level `Module N` convention and for a
   hypothetically deeper `Module → Week → Lesson` convention at another
   Cintana school. `module_ref_for()` derives the convenience top-level
   label from that chain. Covered by `tests/test_lms_hierarchy.py` (single
   level, three-level nesting, no-folder content, a dangling parent
   reference, and a cyclical parent chain, five cases, all defensive against
   malformed data from a real LMS).
3. `ingest_course()` in `routers/diagnostic.py` now computes the hierarchy
   once per ingest run and persists it on every `content_items` row. When a
   chunk is tagged to a skill, that skill's `module_ref` is backfilled
   automatically from the first tagged item, gap-filling only, a manual
   override (spreadsheet or otherwise) already present is never touched.
4. New endpoint: `GET /courses/{course_id}/modules`, lists detected modules
   for a course with content/skill counts. Lets you or an admin screen sanity
   check an ingest run without querying the database directly.
5. `GET /dashboard/{course_id}/heatmap` and `GET /courses/{course_id}/diagnostic`
   both take an optional `module_ref` query param now. Omitted, behavior is
   byte-identical to before this change. Passed, both return a module-scoped
   slice. This is the hook a future "filter by module" control calls
   directly, no further backend work needed for that.

### Still not done (this part remains deferred)
A small instructor/admin screen for skill and module curation, editing
`skills` rows (name, Bloom level, module, weight) directly in-app instead of
round-tripping the CEA spreadsheet over email. This is the metadata-driven
exception from section 2, a form over the `skills` table shape, permissioned
to instructor/admin. Not built. Backend has everything this screen would
need (`module_ref` on `skills`, the `/modules` endpoint for populating a
picker), but the screen itself is separate frontend work, sequence after
Sept 1 unless it turns out to be needed for the demo itself.

### Masterplan updates needed alongside this
See the small edits called out separately in `masterplan.md` sections 3.1,
5.3, 8, and 18, Canvas status and the module-scoping open decision, these
are still pending, they weren't part of the code change.
