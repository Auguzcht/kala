# DeepSeek instructions — functional "refresh skills" button (frontend)

Backend is done and tested (64/64). The incremental logic is fully in place,
see `INCREMENTAL_PROPOSAL.md` for the design. This is a frontend-only task:
wire a real, pressable button to the endpoint that already exists.

## The endpoint (no backend change needed)

`POST /courses/{courseId}/skills/propose` (instructor/admin only) is now
incremental by module. Call it as many times as you like, it only processes
modules that don't already have skills for this course. Response:

```
{
  "skipped": false,             // true when there was nothing new to do
  "modulesProcessed": 2,        // modules newly processed this run
  "modulesSkipped": 1,          // modules already covered
  "proposed": 5, "auto_approved": 1, "flagged_possible_duplicate": 0
}
```

## Build

On the instructor dashboard (`/class`), add a "Refresh skills" button. Put it
on the SkillReviewPanel header, and, importantly, make it visible even when
the panel is empty (no pending proposals), since the whole point is to let an
instructor trigger proposal when they got nothing on first launch.

On click:
1. `POST /courses/{courseId}/skills/propose`
2. On response, refetch `GET /courses/{courseId}/skills/proposed` to repopulate
   the panel, and invalidate the heatmap query (auto-approved matches may have
   added live skills).
3. Show a result summary from the response. Make it specific and honest:
   - `modulesProcessed > 0`: e.g. "Processed 2 new modules, 5 skills ready for
     review, 1 auto-matched from another course." (Use the actual counts.)
   - `skipped === true` / `modulesProcessed === 0`: "All modules already have
     skills, nothing new to propose." NOT a silent no-op, the instructor
     pressed a button and deserves to know why nothing changed.

## UX details that matter

- **Disable + spinner while in flight.** Proposal is a per-module sequence of
  model + embedding calls; on a multi-module course it can take real seconds.
  A button that looks idle while working invites double-clicks. Disable it and
  show a "Proposing…" state until the response lands.
- **A double-click is safe but wasteful.** The backend is idempotent, a second
  press won't duplicate anything, but it will re-run the model calls for any
  modules that finished between the two clicks. Disabling in-flight is enough;
  no extra guard needed.
- **Errors:** the call can fail (model/embedding provider hiccup). Show a
  retry-able error state, don't leave the button stuck in "Proposing…".

## What NOT to do

- Don't add a "re-propose everything from scratch" option. That's a
  destructive operation (it would require deleting existing skills first) and
  isn't what this button is for. If a from-scratch re-run is ever genuinely
  needed, that's a deliberate admin action for the future curation screen,
  not a button an instructor taps casually.
- Don't try to show per-module progress mid-run, the endpoint returns once at
  the end. A single in-flight spinner is the right fidelity for now.
