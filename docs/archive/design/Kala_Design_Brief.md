> Archived: 2026-10-24 (Asia/Manila), under APPROVAL-01. Historical source: `Kala Frontend Mockup/assets/Kala_Design_Brief.md` at base `e9de105` / ignored main-only input.
> Replacement: [apps/web/src/styles/DESIGN.md](<../../../apps/web/src/styles/DESIGN.md>). This original is evidence, not current policy; old commands and next-step queues are not authorization to execute them. Source line references below and in audits refer to the original, before this header.

# Kala Design Brief and Claude Design Prompt

Reference document for the Kala product design pass. Part one is the design system and principles. Part two is the copy-paste prompt to carry into Claude Design, written so a code-gen agent can execute it. Built for the CEA pilot and the ASU-Cintana AI conference showcase.

---

## 0. Thesis

**Blackboard and Canvas record learning. Kala measures it.**

Every surface should make that one idea legible. Kala is an instrument that reads the LMS and renders a living, Bloom's-aligned model of each learner. The design language is "measurement instrument and learning ledger," warmed by the hornbill so it stays human. The anti-slop rule for the whole project: no decorative element earns its place unless it encodes something true about learners, mastery, or evidence.

The single signature we spend boldness on is the **digital twin visualization**. Everything around it stays quiet and disciplined.

---

## 1. What keeps this from looking AI-generated

Three things ground the work in Kala's own world instead of generic dashboard tropes:

1. **Bloom's Revised Taxonomy is a real six-rung ladder** (Remember, Understand, Apply, Analyze, Evaluate, Create). It becomes the recurring structural axis: the heatmap's vertical scale, the twin's mastery breakdown, the shape of badges. Structure that carries real meaning, not numbered markers for decoration.
2. **The digital twin is a real longitudinal object.** It deserves one signature visualization (a mastery constellation or radar across skills) that pulses when new evidence updates it. This is the hero contribution from the masterplan, so it gets hero treatment.
3. **The evidence log is a literal append-only ledger.** Render it as one: a monospaced, immutable stream where each event slides in and nothing ever edits or deletes. Reinforces the responsible-AI and research-dataset story at the same time.

Two caution notes so "boxed" does not become slop:
- A pure hairline-rule, zero-radius, newspaper-column look is one of the current AI-default aesthetics. Kala's boxing must read as *instrument panel*, justified by the data it frames, not broadsheet-for-its-own-sake.
- Reserve the showy landing-page effects (aurora, spotlight, background beams) for the conference and marketing surface only. Inside the daily-use app, motion stays subtle and state-driven.

---

## 2. Color system

Locked from the Kala brand board, resolved against the ASU-Cintana orange-blue partnership. Colors are semantic first. A color means one thing across the whole product.

| Token | Hex | Meaning and use |
|---|---|---|
| `--ink` | `#0E1B33` | Darkest navy. Primary text on light, dark surfaces and nav, the structural base. |
| `--slate` | `#1F2F4D` | Secondary navy. Chrome, panel headers, border base at low opacity. |
| `--orange` | `#FF8A00` | Action and intervention. Primary CTA, "do the next thing," the intervene signal. |
| `--gold` | `#FFC63D` | Mastery and achievement. Badges, readiness highlights, earned progress. |
| `--red` | `#D62828` | At-risk and alert. Pain points, threshold crossings, the early-warning signal. |
| `--green` | `#2E9E6B` | On-track and positive delta. Mastery gained, on-track learners. (Pairs with red for the instructor's early-warning read.) |
| `--maroon` | `#8C1D40` | ASU deep accent. Sparing, for the conference co-brand strip and researcher/export surface only. |

Surfaces:
- **App canvas** (dashboard, learn loop): cool near-white, `#F7F8FB`, for data legibility. Not warm cream (that reads as an AI default and hurts contrast on dense data).
- **Marketing and conference canvas**: warm paper `#F7F5EF` from the brand board, where the hornbill and illustrations live.

Rule of restraint: navy and neutrals carry ~85 percent of every screen. Orange, gold, red, and green are reserved for meaning, never for filling space.

---

## 3. Typography

A deliberate three-role pairing, chosen to avoid the Poppins/Montserrat default the wordmark might otherwise pull toward.

- **Display** (headings, the twin's hero numbers): **Space Grotesk**. Measured, slightly technical, distinctive without shouting. Used with restraint at large sizes and tight tracking. It echoes the geometric confidence of the KALA wordmark.
- **Body and UI**: **Inter** (or Geist Sans). Neutral, highly legible, invisible in the good way for dense reading.
- **Data and ledger**: **Geist Mono** (or JetBrains Mono). Tabular figures for every metric, mastery estimate, and the evidence log. This is functional, not stylistic: monospaced numerals align in the heatmap and the readiness gauges, and the mono ledger reinforces the append-only, instrument feel.

Set a clear scale. Let the twin's mastery numbers be the one place type gets large and confident.

---

## 4. Shape and structure language

The "boxed" direction, grounded as an instrument.

- **Low radius**, 2 to 4px on interactive elements, 0 on data surfaces (the heatmap, the ledger, tables). Not the default pill or blob.
- **Hairline borders over heavy shadows.** 1px `--slate` at low opacity defines panels. Cards are *panels* with a header strip, not soft floating blobs. This is the instrument read.
- **Grid lines as first-class.** The evidence ledger, the skills-by-Bloom's heatmap, and the roster all use visible, crisp grid structure. The structure is the information.
- **Bracket and corner-accent motif.** Small `[ ]` style corner ticks on key panels, echoing the hornbill's angular crest and giving a subtle "targeting and measurement" character. Use sparingly, as a signature detail, not everywhere.
- **Density is a dial, not a constant.** Student surfaces breathe; instructor surfaces pack in. Same tokens, different density (see section 6).

---

## 5. Signature product motifs

These are the elements that relate to Kala specifically. Prioritize building these over generic components.

1. **The digital twin** (the signature). A live mastery constellation or radar across the student's skills, broken out by Bloom's level. Subtle pulse animation when an evidence event updates a node. This is the one bold thing on the page.
2. **The connector beam.** On the landing and conference surface, visualize the LMS-to-Kala data flow: Blackboard and Canvas on one side, the twin on the other, pulses traveling across (Magic UI Animated Beam). This literally shows the positioning line and is the conference hero moment.
3. **Bloom's ladder.** The six-rung vertical scale as a recurring axis and legend. The taxonomy made visible.
4. **Mastery rings.** The continuous 0-to-1 estimate shown as a ring that fills, animating on update, not a flat bar.
5. **Evidence ledger.** Append-only monospaced stream. New events slide in, color-coded by correct, incorrect, tutor, flashcard. Nothing edits or deletes.
6. **Readiness gauge.** The blueprint-weighted rollup as one prominent instrument-panel meter.
7. **Grounding chips.** RAG answers carry "grounded in [content item]" chips, reinforcing the not-a-black-box, responsible-AI story.
8. **The hornbill as guide.** The mascot is the warm, recurring presence: the tutor avatar, the onboarding guide, empty states, loading moments. It gives the instrument a soul. Its crest informs the corner-accent motif.

---

## 6. Entry paths, site map, and page inventory

### 6.1 Two front doors

Kala has two distinct ways in, and the design must make each feel native to how that person arrives.

**Door 1: LTI 1.3 launch (no login screen).** Students and instructors enter from inside an LMS course. Flow: LMS course, click the Kala placement, `/lti/login` (OIDC handshake), `/lti/launch` validates the launch and mints a first-party session, then `/launch` lands and routes by the role claim. Student role routes to the student learn loop; instructor role routes to the class dashboard. Everything past this door is scoped to the launching course. The user never picks a course and never sees a password field.

**Door 2: standalone login (has a login screen).** Institution admins and researchers enter at `/login` on the Kala domain with credentials, because they are not tied to a single course. Role routing after login sends admins to the institution console and researchers to the researcher portal. This is the "universities and researchers" path.

### 6.2 Site map

```
PUBLIC (conference + marketing)
  /                         Landing / showcase (hero thesis, connector beam, stats)
  /how-it-works             Optional. Positioning + the connector story
  /for-researchers          Optional. Research + export framing
  /login                    Standalone login (admins + researchers)

LTI-ENTERED APP (course-scoped, no login screen)
  /lti/login                OIDC handshake (backend)
  /lti/launch               Validate + mint first-party session (backend)
  /launch                   Transient landing. "Signing you in", routes by role
    |
    +-- role = student  -->  STUDENT LEARN LOOP (scoped to course)
    |     /course/:id                Course workspace / home
    |     /course/:id/diagnostic     Build your baseline
    |     /course/:id/practice       Quick practice
    |     /course/:id/flashcards     Flashcards
    |     /course/:id/tutor          AI tutor chat
    |     /course/:id/twin           My twin + readiness view
    |     /course/:id/progress       Optional. XP, streaks, badges
    |
    +-- role = instructor -->  INSTRUCTOR DASHBOARD (scoped to course)
          /class/:id                 Class dashboard (heatmap + at-risk list)
          /class/:id/student/:uid    Per-student twin drill-down + interventions
          /class/:id/skills          Optional. Skill + Bloom's map for the cohort

STANDALONE-LOGIN APP (not course-scoped)
  role = admin -->  INSTITUTION CONSOLE
    /admin                    Institution overview
    /admin/connector          Install + configure LTI and REST app
    /admin/mapping            Content-to-skill taxonomy mapping
    /admin/roster             Roster sync config
  role = researcher -->  RESEARCHER PORTAL
    /research                 Explore anonymized, aggregated evidence
    /research/export          Dataset export

SYSTEM / SHARED
  /launch (error state)       Launch failed. "Open Kala from inside your course"
  /unauthorized               Wrong role for this route
  /session-expired            Re-launch or re-login prompt
  *                           Not found
```

URL paths above are a proposed structure for the design flow, not a locked contract. Today the scaffold has only `/` and `/launch`; `/launch` captures the session and has a standing TODO to route by role once the instructor and twin features exist.

### 6.3 Role routing

- After `/launch`: read the `app_role` claim from the minted session. `student` goes to the course workspace, `instructor` goes to the class dashboard. Both stay scoped to the launch course.
- After `/login`: `admin` goes to the institution console, `researcher` goes to the researcher portal. Neither is course-scoped.
- A wrong-role visit to any route lands on `/unauthorized`, not a blank page.

### 6.4 September priority

Grounded in the masterplan must-have core. Build these first:

- Must-have for the demo: `/launch` role routing, the student learn loop (diagnostic, practice, flashcards, tutor, twin), and the instructor class dashboard (heatmap + at-risk + student drill-down). Plus the public landing as the conference showcase.
- Lighter or stubbed for September: the institution console (the install is largely one-time and backend) and the researcher portal (the masterplan lists shipping-vs-stubbing the researcher portal as an open decision). Design them, but they are not the demo hero.

### 6.5 Surface character

Four surfaces, one language, tuned by audience and density.

- **Student learn loop** (daily use). Encouraging, more whitespace, gold and green forward. Gamification tied to the twin: XP for evidence that moves mastery, streaks for spaced practice, mastery badges per skill and Bloom's level. The tutor is the warm hornbill.
- **Instructor dashboard** (pitch-critical). Dense, analytical, red and amber forward. The skills-by-Bloom's heatmap and the at-risk list are the core. Tabular data, per-student drill-down into the twin, suggested interventions. It should feel like an instrument reading a cohort.
- **Institution console and researcher portal** (standalone login). Minimal, restrained, maroon accent. The console is configuration and mapping; the researcher portal is anonymized aggregate evidence and dataset export.
- **Conference and landing surface** (the showcase). Warm paper canvas, the connector beam, number tickers on the alliance-style stats, the hero thesis line, the hornbill. The only surface that gets the aceternity and tailark flourishes.

---

## 7. Motion principles

- **Motion encodes state change, not vanity.** Mastery moved, the ring animates. New evidence, it slides into the ledger. At-risk threshold crossed, the alert pulses once. If an animation does not report a real change, cut it.
- **Onboarding tours** via Driver.js on first LTI launch. Student path: diagnostic to practice to tutor to twin. Instructor path: heatmap to at-risk to drill-down. The same tours script the live conference demo walkthrough, which de-risks the September 1 presentation.
- **Microanimations** via animated Lucide icons for state feedback: a recording spinner resolving to a check when evidence is written, a bell for at-risk alerts.
- **Quality floor**, non-negotiable: responsive to mobile, visible keyboard focus, and `prefers-reduced-motion` respected everywhere. This is an education product for a diverse cohort.

---

## 8. Responsible-AI and accessibility guardrails

This is a research product shown to a responsible-AI audience, so these are requirements, not polish.

**At-risk framing (decided).** The early-warning list is instructor-only. Students never see a risk label about themselves; their own view shows "focus areas" in constructive language. Instructor-facing flags use supportive wording ("Needs support," "Check in"), never "Failing" or "At risk" as a verdict. Every flag appears with its reason, the specific evidence that triggered it (for example, "low mastery and high hint use on 3 Analyze-level skills, no activity in 8 days"), never a bare score. The signal is a prompt to reach out, not a label on a person.

**De-identification, made visible.** The masterplan de-identifies before every external model call. Surface that as a designed cue, not a backend footnote: a small, quiet "de-identified" indicator wherever content is sent to a model, and pseudonyms rather than names in any model-facing or researcher-facing view. This visible privacy posture is a differentiator in the conference room.

**Honest mastery display (decided).** Mastery is a heuristic estimate, and the masterplan names "overpromising the ML" as a risk. So the primary display is a qualitative band, not a raw number:
- No evidence yet (neutral, an empty state, not zero)
- Developing (low)
- Proficient (mid)
- Mastered (high)

The numeric estimate is secondary, available on hover or in a detail view, never the headline. Bands use a neutral-to-gold progression (mastery is gold). Keep red out of the mastery scale; red belongs to the at-risk axis, which is a different object (per-student, not per-skill). Conflating "low mastery on one skill" with "at-risk student" is a category error the design must avoid.

**Color is never the only signal (decided).** The instructor early-warning is built on red versus green, the most common colorblind pairing, so state is never encoded by hue alone. Always pair color with an icon, shape, or text label. The heatmap encodes value with both color and a secondary cue (a value label or fill pattern). Orange and gold fail text contrast on white, so they are fills and accents only; text stays ink or slate. Meet WCAG AA for text.

---

## 9. State system

For a pilot and a conference, the first-run state is the demo. Every data surface needs its states designed, not just the happy path.

- **Twin:** no-evidence-yet (an invitation to take the diagnostic), building (sparse, a few nodes), populated (the full constellation).
- **Heatmap:** before content is tagged (an admin prompt), sparse (a few skills), full grid.
- **At-risk list:** the good-news empty state ("No one needs support right now") reads as success, not a broken screen; populated shows flags with reasons.
- **Evidence ledger:** before the first event (explains what will appear here), streaming.
- **Every surface:** loading (skeletons, not spinners where possible) and error (direction, not apology).

The masterplan seeds a six-row smoke-test taxonomy, not real curriculum, so day one is genuinely sparse. Design for sparse-but-real, not a tidy full mock that collapses when real data lands.

---

## 10. Brand assets: logo usage and co-brand

**Kala logo variants** (from the brand board). Use the right one per surface:
- Primary lockup (hornbill + wordmark + tagline): landing and login.
- Compact or monochrome mark: the app sidebar and instructor nav.
- Circle or app-avatar mark: the tutor avatar and favicons.
- The hornbill alone: empty states, loading, onboarding guide moments.

**Co-brand (decided).** Kala is the primary brand and always leads. ASU, Cintana, and Mapua appear only on the landing and conference surface, as a restrained partnership strip ("Built at Mapua Malayan Colleges Mindanao for the ASU-Cintana AI Challenge"), not merged into a single combined logo and never competing with the Kala hero. Partner marks stay off the in-app student and instructor surfaces, which are product, not marketing. Each partner has its own brand-usage rules (clear space, no recoloring, no implying endorsement beyond what is real); follow them and use official logo files, do not recreate the marks.

---

## 11. Microcopy starter

Voice: plain, warm, active, sentence case. The tutor is encouraging and never reveals graded answers. Errors give direction, not apology. A sample kit to keep the agent from writing generic filler:
- Diagnostic empty: "Take a short diagnostic to build your baseline for this course."
- Twin empty: "No evidence yet. Your twin fills in as you practice."
- At-risk empty (instructor): "No one needs support right now. Check back after the next activity."
- Tutor intro: "Hi, I'm Kala. Ask me about this course and I'll help you work it out."
- Launch failed: "Open Kala from inside your course to sign in."
- Badge names tie to the twin, not vanity: mastery and Bloom's-level badges ("Reached Proficient in Thermodynamics," "First Analyze-level mastery").

---

## 12. Component library palette

Which library for which job, so the pi agent pulls from the right source.

- **shadcn/ui** (`ui.shadcn.com`): the foundation. Button, Card rendered as Panel, Tabs, Table rendered as DataGrid, Dialog, Sheet, Badge, Tooltip, Progress, Command, Popover, Separator, ScrollArea. The `--preset b5LC5lyQi` is the locked base theme; the boxed direction and Kala tokens are applied as overrides on top (radius down, borders up, semantic colors mapped).
- **shadcnblocks.com, shadcn.io, shadcnstudio.com**: pre-built blocks for the dashboard shell, sidebar nav, stat blocks, and landing scaffolds. Speed, not novelty.
- **tailark.com**: marketing and landing blocks plus animated illustrations for the conference-facing page.
- **tailgrids.com**: broad blocks, tables, stat cards, section blocks for landing and admin.
- **magicui.design**: Animated Beam (the connector, signature), Number Ticker (stats), Bento Grid (landing feature layout), Shimmer and gradient text (sparingly), Marquee (partner logos).
- **motion-primitives.com**: in-view reveals, animated text, morphing dialog transitions. App-wide polish.
- **aceternity.com/ui**: hero flourishes for the landing only (spotlight, background beams, card hover). Keep out of the daily app.
- **reactbits.dev**: text animations, counters, subtle backgrounds for the landing.
- **animata.design**: interaction snippets, skeletons, small delight moments.
- **lucide-animated.com**: animated icons for nav and state feedback across the app.
- **coss.com/ui**: Cal.com's Base-UI design system, copy-paste and explicitly built to be AI-legible, which suits the pi agent. Good source for accessible composed patterns (date pickers, tables, OTP, command). Caution: it is early and Base-UI-based, while shadcn is Radix-based, so mix composed patterns carefully rather than mid-component.
- **driverjs.com**: onboarding product tours and the scripted conference demo walkthrough.

---

## 13. Open flags to resolve

- Confirm the exact palette that `--preset b5LC5lyQi` ships, so the orange and navy tokens either come from it or override it cleanly.
- coss.com/ui is beta and Base-UI-based. Decide whether it is a pattern reference only, or a real dependency, before the pi agent leans on it.
- Decide the first surface to build. Recommended order: instructor dashboard first (pitch-critical per the masterplan), then the student learn loop (daily core), then the conference landing (showcase), then the researcher surface.

---

# Part Two: Claude Design Prompt

Copy everything below into Claude Design. Swap the TARGET SURFACE line for the screen you want to iterate on. It restates the essentials so it stands alone.

---

**Product:** Kala, an AI learning-intelligence layer that sits on top of an LMS (Blackboard, Canvas) and produces a living, Bloom's-aligned digital twin of each learner plus early-warning analytics for instructors. Positioning: "Blackboard and Canvas record learning. Kala measures it." Built for a college engineering pilot and shown as a research product at the ASU-Cintana AI conference.

**Audience:** university students (daily learners) and their instructors (analysts watching a cohort), plus institution admins, researchers, and a conference audience.

**Site flow (two front doors):** Door 1 is an LTI 1.3 launch with no login screen: students and instructors enter from inside an LMS course, a transient `/launch` screen mints a first-party session and routes by role (student to the learn loop, instructor to the class dashboard), and everything stays scoped to that course. Door 2 is a standalone `/login` for institution admins and researchers who are not tied to a course, routing to an institution console or a researcher portal. Design the target surface as native to whichever door leads to it: LTI surfaces never show a course picker or a password field; standalone surfaces do.

**TARGET SURFACE:** [ Instructor dashboard (`/class/:id`): skills-by-Bloom's heatmap + at-risk list, with a per-student twin drill-down (`/class/:id/student/:uid`). Entered via LTI as an instructor, scoped to one course, no login screen. ]  *(swap this line for: student course workspace and learn loop / student twin + readiness view / AI tutor chat / conference landing / standalone login / institution console / researcher portal)*

**Design language:** measurement instrument and learning ledger, warmed by a hornbill mascot (symbol of insight and guardianship). Boxed as in *instrument panel*, not broadsheet. Every visual element must encode something real about learners, mastery, or evidence. No decoration for its own sake. This must not look like a blue-and-rounded shadcn starter or a generic AI dashboard.

**Color tokens** (semantic, one meaning each):
- ink `#0E1B33` (text, dark chrome, structural base)
- slate `#1F2F4D` (secondary navy, panel headers, hairline borders at low opacity)
- orange `#FF8A00` (action, intervene, primary CTA)
- gold `#FFC63D` (mastery, achievement, badges)
- red `#D62828` (at-risk, alert)
- green `#2E9E6B` (on-track, positive delta)
- app canvas `#F7F8FB` (cool near-white for data legibility)
Navy and neutrals carry ~85 percent of the screen; the accent colors are reserved for meaning.

**Typography:** Space Grotesk for display and hero numbers (tight tracking, used with restraint), Inter for body and UI, Geist Mono for all metrics, mastery estimates, and the evidence ledger (tabular figures).

**Shape:** low radius (2 to 4px interactive, 0 on data surfaces), hairline slate borders over heavy shadows, cards are panels with a header strip, visible crisp grids on the heatmap, ledger, and roster. Optional small bracket-style corner ticks on key panels as a signature detail, echoing the hornbill crest, used sparingly.

**Signature element** (spend boldness here, keep everything else quiet): the digital twin, a live mastery constellation or radar across skills broken out by the six Bloom's levels, with a subtle pulse when an evidence event updates a node.

**Product motifs to use where relevant:** Bloom's six-rung ladder as a recurring axis and legend; mastery rings that fill and animate on update; an append-only monospaced evidence ledger where new events slide in color-coded by type; a single prominent readiness gauge; "grounded in [content item]" chips on any AI answer; the hornbill as tutor avatar, onboarding guide, and empty-state presence.

**Motion:** subtle and state-driven inside the app. Animation must report a real change (mastery moved, evidence written, threshold crossed) or be cut. Reserve showy effects (spotlight, beams, aurora) for the landing surface only. Respect `prefers-reduced-motion`. Include a Driver.js first-launch tour concept for this surface.

**Component sourcing:** shadcn/ui primitives as the base (theme preset `b5LC5lyQi` with the tokens above layered as overrides: radius down, borders up, semantic colors mapped). Pull dashboard shells and blocks from shadcnblocks / shadcn.io / tailgrids. Use Magic UI Animated Beam for any LMS-to-Kala data-flow visual and Number Ticker for stats. Animated Lucide icons for state feedback. Keep aceternity and tailark flourishes to the landing surface.

**Quality floor:** responsive to mobile, visible keyboard focus, reduced motion respected, empty and error states written as direction ("No evidence yet. Assign a diagnostic to start the twin.") in the interface's own voice, active-voice button labels that keep the same name through the flow.

**Non-negotiables (responsible-AI research product):**
- At-risk is instructor-only, worded as support not verdict ("Needs support," never "Failing"), and every flag shows the specific evidence that triggered it, never a bare score. Students see their own "focus areas" constructively, never a risk label.
- Mastery shows as a qualitative band (No evidence yet / Developing / Proficient / Mastered) with the numeric estimate secondary on hover. Bands run neutral-to-gold; red is reserved for the separate at-risk axis, not the mastery scale.
- Never encode state by color alone: pair every color signal with an icon, shape, or label. The heatmap encodes value plus a secondary cue. Orange and gold are fills only; text stays ink or slate; meet WCAG AA.
- Show a quiet "de-identified" cue wherever content goes to a model; use pseudonyms, not names, in model-facing and researcher views.
- Design the states, not just the happy path: empty and first-run (the demo state, sparse-but-real), loading (skeletons), populated, error (direction not apology). The good-news at-risk empty state reads as success.
- Light mode first, dark mode later. Responsive: the heatmap needs a real small-screen strategy, not a tidy grid that collapses. Students are on phones, instructors on desktop.
- Logo: primary lockup on landing and login, compact mark in nav, avatar mark for the tutor, the hornbill alone for empty and loading states.

**Deliver:** the target surface as a clean, distinctive layout with the signature twin visualization treated as the hero, the Bloom's structure legible, and the instrument character carried by structure rather than shadow. Take one justified aesthetic risk specific to a learning-measurement instrument.
