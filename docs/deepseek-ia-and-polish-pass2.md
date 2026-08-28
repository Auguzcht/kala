# Frontend pass 2: stop showing students the backend, fix the visual bugs, give Twin the depth it deserves

Context: pass 1 (component-audit doc) got motion/skeleton/hint-reveal/accordion-grouping
wired in — visible progress in these screenshots (hornbill loading state, box/due
badges, Hint/Reveal buttons on flashcards). This pass is about two different things
found in the new screenshots: (1) an information-architecture mistake — Bloom's
taxonomy and system internals are being shown to students who never asked for them
— and (2) a set of real visual bugs and "flat/lifeless" polish gaps. Two different
fix types, don't blend them.

## The rule (apply everywhere below)

**Bloom's taxonomy level and system internals (RAG, "server-side," "your twin")
are backend/Twin-page concepts. Diagnostic, Practice, and Lessons speak in terms
of the course topic and never mention either.** The Twin page is the one place a
student opted into seeing the analytical layer, so it's the only place taxonomy
labels and architecture framing are allowed.

---

## A. Copy — remove system internals from student-facing text

**Diagnostic page subtitle**, currently: *"One RAG-grounded question per skill,
self-paced. Graded server-side — your answers set the starting estimate for your
twin."* Three implementation nouns in one sentence a student never asked about.
Rewrite to something like: *"One question per topic, at your own pace. This
builds your starting point — you'll see it improve as you practice."* Same
information (what happens, why it matters), zero system nouns.

**Diagnostic question eyebrows**, currently show the raw Bloom's word (`ANALYZE`,
`APPLY`) above each question (screenshot: image 2). Remove entirely, or if a
category header is genuinely useful for scanning, use the skill's own module/topic
instead (see B below) — never the taxonomy word.

**Tutor page subtitle**, currently: *"Grounded in your course content. Kala
teaches and gives hints — it never hands back answers to graded work."* This one
is actually fine, it describes behavior a student cares about (won't just give
answers) without naming the mechanism. Keep this one as the model for how to
phrase the diagnostic/practice rewrites above — behavior, not architecture.

---

## B. Information architecture — group by topic, not by Bloom's level

**Lessons page** groups its accordion by Bloom's level (`Understand`, `Apply`,
`Analyze`, `Evaluate`, `Create` — screenshot: image 5). A student opening Lessons
wants "what topic is this," not "what cognitive tier is this." Regroup by
`module_ref` (already on every skill and content item, currently unused for this)
— e.g. "Module 1 · Signals & Sensors," "Module 2 · Logic Design." If Bloom's level
is still useful for scanning within a module, make it a small secondary tag on
the individual lesson card, not the section header a student has to parse first.

**Twin's Skills accordion** (image 11/12) is correctly Bloom-grouped — this is
the one screen where that's the right axis, because a student here has already
opted into the analytical view. Leave this one alone.

**Practice question eyebrows** — same fix as diagnostic (A above): drop the raw
Bloom's word, or replace with the skill's topic/module if a category label is
wanted at all.

---

## C. Real bugs (not a design opinion, these are broken)

1. **Diagnostic answer rows are vertically off-center.** Screenshot (image 2):
   the radio circle doesn't sit centered against its label text — check the row's
   flex alignment (`items-center` missing, or the radio and label are in separate
   flex contexts with different line-heights).
2. **No spacing between diagnostic question blocks.** Consecutive questions run
   together with too little breathing room — increase vertical gap between
   question groups (each question + its choices + category label needs to read
   as one visually separated unit, not blend into the next).
3. **Loading skeleton card doesn't match the real content's width.** Compare
   image 3 (loading, narrow centered card) against image 4 (loaded, full-width
   content) — the skeleton container is noticeably smaller than what replaces
   it, causing a jarring resize the moment content lands. Give the skeleton
   container the same max-width/padding as the loaded state.
4. **Accordion header numbers aren't aligned.** Image 5/11: the count (`2`, `7`,
   `2`, `1`, `4`) sits at an inconsistent baseline relative to its label and
   chevron across rows — check the header row's flex/grid alignment, likely a
   missing `items-center` or inconsistent line-height between the label span and
   the number span.

---

## D. "It lacks life" — Practice page

Direct quote worth keeping as the bar to clear: compared to Gizmo, Practice has
*"no change in color or icons in the buttons, no slider, no nothing."* Concretely:

- **Choice buttons need a real selected/hover state** — color shift, not just a
  border. Right now every choice looks identical whether idle, hovered, or picked.
- **A session progress indicator.** Practice is a loop, not a fixed set, so this
  isn't "question 3 of 10" — but *something* should show movement: a subtle
  streak counter ("3 in a row"), or a slim progress rail that fills as the
  session continues. Blank space above the question card right now.
- **XP and mastery movement must render, and it's already in the API response.**
  This is the important one: `practice/{course_id}/submit` already returns
  `mastery` (the post-answer estimate) in its response body, and the
  gamification `reward` payload (`xp`, `streakDays`, `badges`) exists and is
  already wired into `FlashcardDeck.tsx`. Practice isn't rendering either. After
  an answer, show the delta inline — a small "+10 XP" tick and the mastery band
  transition (e.g. "Developing → Proficient") the same way flashcards already
  do it. The data is not missing, the render is.
- **Icons**, sparingly, per-topic or per-outcome (a check/x on the graded result,
  maybe a subject-area glyph), not decoration for its own sake — same "motion
  encodes state change" rule from pass 1 applies to icons too: an icon should
  mean something (correct/incorrect, topic), not fill space.

---

## E. Tutor chat is still plain

"Kala tutor is just plain" (image 10) — this is the free-form Ask Kala mode,
separate from Guided Lessons, and it looks like the original scaffold: a bare
input, no message history visible, no visual identity. At minimum:
- Give it the same card/corner-bracket treatment the rest of the app uses.
- Render the hornbill mark next to Kala's responses (DESIGN.md signature element
  #7 names the hornbill as the guide for exactly this kind of surface).
- Message bubbles with real visual weight once a conversation exists — right now
  the screenshot shows only the empty state, but if the populated state is
  similarly bare, it needs the same pass TutorChat.tsx got scoped for in the
  original tutor redesign discussion (structured answer card, follow-up chips).
  If chat mode was deliberately left simpler than guided mode, that's a fair
  call, but "simple" still needs a floor — this currently reads unfinished, not
  minimal.

---

## F. Twin page: this is where the depth belongs, so give it depth

Direct quote: *"only 1 graph? no other bento grids considered? stats only end
on evidence ledger nothing else to show?"* — and this tracks with the IA rule
above: since Twin is now confirmed as the one place students opt into deep
stats, it should actually deliver on that instead of fizzling out after one
radar chart and a list.

Concrete tile ideas for a proper bento layout (mix of sizes, not a single column):
- **Readiness ring** (already exists) — keep as a hero tile.
- **Bloom radar** (already exists, and per pass 1 should already be aggregated
  to 6 nodes) — keep.
- **Module-by-module progress** — bars or mini-rings per `module_ref`, this data
  already exists via `GET /courses/{id}/modules` and skill `module_ref`, just
  isn't surfaced anywhere on Twin today.
- **Streak + XP summary tile** — the same `gamification/summary` data already
  used in the top bar deserves a real tile here too (badges earned, current
  streak, total XP), not just a number in the header.
- **Weakest-skill callout** — a single prominent "focus area" tile (already
  computed server-side as `weakest_skill` for practice) — surfacing it here as
  a real callout, not just buried alphabetically in the Skills accordion, gives
  the page a point of view instead of just a data dump.
- **Evidence ledger** (already exists) — keep as the page's closing detail
  section, but it shouldn't be the *only* thing after the fold; the tiles above
  should fill that space first.

This page is allowed to be dense and analytical — that's the whole point of it
being opt-in rather than the daily surface. Spend the "life" budget here that
Practice and Diagnostic should NOT be spending on taxonomy jargon.

---

## Priority order

1. **A + B** (copy + IA) first — these are the "why does this feel like a
   showcase, not a product" issues, and they're mostly text/grouping-key changes,
   not new components.
2. **C** (real bugs) — quick, contained fixes, do them in the same pass as A/B
   since you'll already be in these files.
3. **D** (Practice life + dynamic XP/mastery) — the reward/mastery rendering is
   the highest-value single item here since the data already exists server-side.
4. **E** (tutor polish) and **F** (Twin bento) — bigger lifts, appropriately last.
