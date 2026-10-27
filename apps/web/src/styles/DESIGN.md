# DESIGN.md — Kala visual system

Read this before writing or restyling any UI. Kala's look is a **measurement instrument and learning ledger**, warmed by a hornbill mascot. Locked from the Kala brand board and the design brief (`Kala Frontend Mockup/assets/Kala_Design_Brief.md` — mockups in the same folder use these exact values). Sitting on a shadcn new-york foundation with Tailwind v4 tokens in `globals.css`. Accessible primitives we do not reinvent.

Thesis: **"Blackboard and Canvas record learning. Kala measures it."** Every surface makes that legible. No decorative element earns its place unless it encodes something true about learners, mastery, or evidence.

## Direction

- **Foundation:** shadcn/ui (new-york style), Tailwind v4, tokens in `globals.css`. Accessible primitives we do not reinvent.
- **Identity on top:** instrument-panel shape language (boxy, hairline borders, low radius), the Bloom's taxonomy ladder as a recurring structural axis, and the digital twin as the one signature visualization.
- **The anti-default rule:** this must not read as a blue-and-rounded shadcn starter or a generic AI dashboard. Navy and neutrals carry ~85% of every screen; orange, gold, red, green are reserved for meaning, never for filling space.

## Palette (tokens, do not hardcode hex)

Semantic tokens (shadcn) and brand tokens both live in `globals.css`. Use them by name. A color means one thing across the whole product.

| Token | Hex | Meaning and use |
|---|---|---|
| `--brand-ink` / `--primary` | `#0E1B33` | Darkest navy. Primary text, dark chrome, nav, primary buttons, the structural base. |
| `--brand-slate` / `--secondary` | `#1F2F4D` | Secondary navy. Chrome, panel headers, hairline borders at low opacity, secondary fills. |
| `--brand-orange` | `#FF8A00` | Action and intervention. Primary CTA, "do the next thing", focus ring, active nav accent. |
| `--brand-gold` | `#FFC63D` | Mastery and achievement. Badges, readiness highlights, the mastery band progression. |
| `--brand-red` / `--destructive` | `#D62828` | At-risk and alert. Pain points, threshold crossings, the early-warning signal. |
| `--brand-green` | `#2E9E6B` | On-track and positive delta. Mastery gained, on-track learners. |
| `--brand-maroon` | `#8C1D40` | ASU deep accent. Sparing, for the conference co-brand strip and researcher/export surface only. |
| `--background` | `#F7F8FB` | App canvas: cool near-white for data legibility. Not warm cream. |
| `--brand-paper` | `#F7F5EF` | Marketing and conference canvas, where the hornbill and illustrations live. |

Rules:
- **Orange and gold are fills and accents only.** Both fail text contrast on white; text stays ink or slate. `--brand-orange-foreground` / `--brand-gold-foreground` are set to dark ink so filled buttons pass AA.
- **Red never enters the mastery scale.** Mastery bands run neutral-to-gold. Red belongs to the at-risk axis only — a different object (per-student, not per-skill).
- **Never encode state by color alone.** Pair color with an icon, shape, or label. The heatmap encodes value plus a secondary cue (value label or fill pattern).
- Charts use the brand ramp via `--chart-1..6` (ink, slate, orange, gold, green — red last, at-risk axis only).

### DESIGN-REQ-001: Text-selection colors

Approved APPROVAL-09,2026-10-27. Define semantic selection tokens in globals.css: `--selection-background` is `#BCD3F4`; `--selection-foreground` uses the existing ink token. Apply them to text selection, including input/textarea selection, without changing the primary brand token to recolor other controls. Preserve text contrast and native selection behavior. The new blue is scoped to text-selection feedback, not a new decorative brand palette.

At the approved base there is no authored global ::selection rule in globals.css. Input.tsx's selection:bg-primary / selection:text-primary-foreground utilities are the explicit dark-selection source found in code. Fred implements the token/global rule and reconciles local overrides; do not claim an unobserved global rule caused every selection. Verify selected body and editable text in both themes and at375px/1440px.

### DESIGN-REQ-002: Shared content and dock column edges

Approved APPROVAL-09,2026-10-27. Study and Tutor message/content columns and their corresponding dock containers share the same left/right column edges at every viewport. Use one consistent max-width/gutter contract; do not independently combine outer footer padding, inner column padding and dock padding so one becomes narrower or shifts sideways. Textarea internal padding is distinct from the outer dock edge. Preserve scroll ownership, bottom clearance, action state, empty/attachment layouts, reduced motion and the scoped dock shape exceptions.

The shared column defines the 800px maximum shell width and horizontal gutters once: 16px below the small breakpoint and 24px above it. Content and dock inherit the same inset from this ancestor. The scroll region must span the full available surface width so its native scrollbar stays at the page's right edge, outside the centered message column. A full-bleed stream may cancel and restore the inherited inset inside its scroller without defining another gutter or maximum width. Keep session bars outside the column and keep textarea/card internal padding distinct from column gutters. In a full-viewport fixture, content and loading cards remain 343px wide at 375px and 752px wide at 1440px.

Measure actual card, Kala reply container and complete dock row edges in Study action and compose modes, plus Tutor message containers and composer in empty, conversation and attachment states at 375px/1440px. Corresponding left and right edges must agree within 1px. Preserve scroll ownership and bottom clearance when moving the shared ancestor. APPROVAL-09 item 1 authorizes the frontend implementation and its browser measurements.

## Radius and shape

- Base `--radius` is `0.25rem`. Interactive elements 2–4px, data surfaces 0. Not the default pill or blob.
- Cards are **panels with a header strip**: 1px hairline `--border` (slate at ~14% opacity), 4–8px radius, no heavy shadow. Panels define structure, shadows do not.
- Primary and secondary action buttons are boxy (`rounded-md`, 4px), not pills. The side rail uses small 8px icon chips.
- **Bracket / corner-accent motif:** small `[ ]` style corner ticks on key panels, echoing the hornbill's angular crest — sparingly, as a signature detail.

### Scoped exception: chat-entry containers

Approved APPROVAL-05, 2026-10-25. Applies only to the text-entry dock containers: Study hub `ComposeDock` and Tutor `PromptInput`. These containers may be pill-shaped when empty. The Tutor container becomes a rounded rectangle using an existing radius token while dragging files or holding attachments. ComposeDock stays text-only; this exception does not authorize behavior changes to it.

Rationale: distinguish the conversational entry surface and make room for Tutor attachments. APPROVAL-06 section 2 reconciles Fred's accepted Lane U refinements to this APPROVAL-05 exception (2026-10-25): shared dock corners use `calc(var(--radius-xl) * 2)` and remain finite while the collapsed 48px pill expands. Tutor attachment/send controls and shared dock send controls are circular; Tutor user-message bubbles and shared follow-up controls retain their rounded shapes. Tutor history menus are rounded and padded, with an inset rounded sort focus ring. These scoped refinements supersede the initial instruction that every chat control remain boxy. All other controls keep the existing boxy rules. Use existing tokens; no hardcoded radii. Shared ComposeDock changes are visual only. Lead designer review remains a handover follow-up.

## Typography

Three deliberate roles (loaded in `index.html` from Google Fonts):

- **Display:** Space Grotesk (`font-display`), for headings and hero numbers. Tight tracking, weight 600–700, used with restraint. The twin's mastery numbers are the one place type gets large and confident.
- **Body / UI:** Inter (`font-sans`), neutral and legible for dense reading. Weight 400–500.
- **Data / ledger:** JetBrains Mono (`font-mono`), tabular figures for every metric, mastery estimate, and the evidence ledger. Functional, not stylistic: monospaced numerals align in the heatmap and gauges.

Sentence case everywhere. No ALL CAPS except tiny eyebrow labels with tracking.

## Layout

- Generous whitespace, a clear single job per screen, one primary action per view.
- Left-aligned large headings with a short supporting line.
- **Density is a dial, not a constant:** student surfaces breathe; instructor surfaces pack in (visible crisp grids on the heatmap, ledger, and roster). Same tokens, different density.
- Grid lines are first-class: the evidence ledger, skills-by-Bloom's heatmap, and roster use visible, crisp grid structure. The structure is the information.

## Signature elements (custom, in `src/components/kala/`)

1. **The digital twin** (the signature). A live mastery constellation/radar across the student's skills, broken out by Bloom's level. Subtle pulse animation when an evidence event updates a node. The one bold thing on the page.
2. **Bloom's ladder.** The six-rung vertical scale (Remember → Create) as a recurring axis and legend. The taxonomy made visible.
3. **Mastery rings.** The continuous 0-to-1 estimate as a ring that fills and animates on update, never a flat bar.
4. **Evidence ledger.** Append-only monospaced stream; new events slide in, color-coded by type; nothing edits or deletes.
5. **Readiness gauge.** The blueprint-weighted rollup as one prominent instrument-panel meter.
6. **Grounding chips.** RAG answers carry "grounded in [content item]" chips — the not-a-black-box, responsible-AI story.
7. **The hornbill as guide.** Tutor avatar, onboarding guide, empty states, loading moments.

## Motion

- **Motion encodes state change, not vanity.** Mastery moved → ring animates. New evidence → row slides into the ledger. At-risk threshold crossed → alert pulses once. If an animation does not report a real change, cut it.
- First-launch onboarding tours via Driver.js on `/launch` (student path: diagnostic → practice → tutor → twin; instructor path: heatmap → at-risk → drill-down). Same script runs the conference demo walkthrough.
- Always wrap non-essential motion so `prefers-reduced-motion` disables it.
- Showy effects (spotlight, beams, aurora) are **landing/conference surface only** — never imported from `/course/*`, `/class/*`, `/admin/*`, `/research/*`.

### Scoped exception: Tutor empty-state mascot

Approved APPROVAL-05, 2026-10-25. Only Kala's own logo mark in the Tutor new-chat empty state may have a slow, subtle idle loop, built with existing tokens. Stop the loop when the student starts typing or sends a message. Never show this animated empty-state mark mid-conversation, in Study, in Test or in Diagnostic. Under `prefers-reduced-motion`, render a static mark with no animation.

Rationale: identify the empty conversational entry point without competing with reading or writing. This exception does not relax the rule against motion unrelated to state changes anywhere else. Lead designer review is recorded in the handover notes.

### Scoped interaction feedback amendment

APPROVAL-06 section 2, reconciling Fred's accepted 2026-10-25 Lane U refinements: Tutor action glyphs may use their published lucide-animated variants on whole-control hover/focus, with static fallback for unavailable variants. Do not substitute a generic tilt/nudge/pulse. The drop overlay's Upload glyph reacts to drag entry. Overflowing history titles may make one gentle hover journey to the end and back; short titles remain static. History popup entry/exit remains immediate. Local attachment preview dialogs may have short state-transition motion. Reduced motion disables these effects. These are scoped interaction responses, not additional idle loops; only the empty-state logo has the idle exception above. Lead designer review remains pending.

## Pending and loading states

Approved APPROVAL-08, 2026-10-27. This replaces the earlier app-wide Spinner convention.

- A spinner appears only inside the control the user just activated for a submit-type action (Send, Save, Submit, Start set, Retry), while its request is pending. Disable that control during the request. Preserve accessible names, focus and reduced motion.
- Never put a spinner in a skeleton, loading card, tab body, header stat or beside status text. A page/card load uses skeleton blocks and at most one line of text.
- Waiting for a model answer uses exactly one indicator: the existing shimmer text line, for example “Kala is preparing a hint”. No spinner accompanies it. The initiating control is disabled with a stable label/icon, rather than becoming a second “Thinking…” indicator. This single-indicator rule takes precedence over a submit-control spinner during the model-answer phase.
- Test, Study and Diagnostic share one loading card: static Kala mascot, one line and skeleton lines. Its width matches the content card it replaces; Diagnostic and Test runners share one content-column width. Use existing tokens and honor 375px/1440px layouts. This does not grant a new mascot idle loop.

## Quality floor (every screen)

Responsive to mobile, visible keyboard focus (the orange ring), reduced motion respected, empty and error states written as direction not mood ("Take a short diagnostic to build your baseline", not "No data"). Errors say what happened and how to fix it, in the product's voice.

## Responsible-AI guardrails (requirements, not polish)

- **At-risk is instructor-only**, worded as support not verdict ("Needs support", never "Failing"). Every flag shows the specific evidence that triggered it, never a bare score. Students see "focus areas" constructively, never a risk label.
- **Mastery shows as a qualitative band** (No evidence yet / Developing / Proficient / Mastered). The numeric estimate is secondary — on hover or in detail, never the headline.
- **De-identification is visible:** a small quiet "de-identified" cue wherever content is sent to a model; pseudonyms in model-facing and researcher-facing views.
- **Light mode first**, dark mode later. The heatmap needs a real small-screen strategy.

## Do not

- Do not hardcode colors or radii; use tokens.
- Do not use the warm-cream-plus-terracotta or near-black-plus-acid-accent AI-default looks. Kala is ink, slate, orange, gold on cool near-white.
- Do not round everything into pills. Boxy 2–4px radius; pills were the previous system's mistake.
- Do not let the chevron become decoration; the previous chevron mark and the old hornbill are superseded by the current Kala logo (`public/Kala-Logo.png`).
- Do not import Aceternity / Tailark / Magic UI flourishes into the daily-use app surfaces. Marketing components stay in `src/components/marketing/`.


## Change log

| Date | Change | Authority / IDs |
| --- | --- | --- |
| 2026-10-27 | Specify one ancestor for the 800px shell and responsive gutters, matching stream/dock edges within 1px, retaining loading widths and keeping the native scrollbar at the page edge | APPROVAL-09 item 1 and Fred's scrollbar correction, WI-34, DESIGN-REQ-002 |
| 2026-10-27 | Define selection background token and common content/dock edges before Fred's direct polish | APPROVAL-09; DESIGN-REQ-001/002 |
