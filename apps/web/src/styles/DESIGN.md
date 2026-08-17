# DESIGN.md — Kala visual system

Read this before writing or restyling any UI. Kala's look is derived from Cintana Education's brand (navy, gold, teal, a chevron motif, confident large headings) sitting on a shadcn new-york foundation. The goal is a design that reads as Cintana's academic-serious cousin, not as generic rounded SaaS.

## Direction

- **Foundation:** shadcn/ui (new-york style), Tailwind v4, oklch tokens. Accessible primitives we do not reinvent.
- **Identity on top:** Cintana palette, a chevron signature, generous whitespace, large confident headings, calm neutral surfaces.
- **The mix, resolved:** keep shadcn's structure and accessibility; replace its default neutrality with Cintana color and one signature move. Do not ship default-shadcn-gray with a blue accent; that is the generic look we are avoiding. Do not over-round everything into pills either. The discipline is: pills for primary actions, `xl` radius for cards and inputs, and the chevron as the one memorable element.

## Palette (tokens, do not hardcode hex)

Semantic tokens (shadcn) and brand tokens both live in `globals.css`. Use them by name.

| Role | Token | Cintana source |
|---|---|---|
| Primary / ink | `--primary`, `bg-primary` | navy `#17294B` |
| Gold accent | `--brand-gold`, `bg-brand-gold` | gold `#E8A33C` |
| Teal secondary | `--brand-teal`, `bg-brand-teal` | teal `#2F8FB4` |
| Coral (sparing) | `--brand-coral` | coral `#E86F35` |
| Page background | `--background` | cool near-white `#F6F7F8` |
| Body text | `--foreground`, `--muted-foreground` | navy ink / slate |
| Focus ring | `--ring` | teal |

Rules:
- Primary buttons and primary emphasis use navy (`--primary`). This matches Cintana's own navy buttons.
- Gold is the accent for the single most important call to action on a view, and for small highlights. It is not a background for large areas.
- Teal is the secondary and the focus-ring color. Coral is rare, for a single point of emphasis.
- Charts use the brand ramp via `--chart-1..5` (navy, teal, gold, coral, slate) so dashboards stay on-brand.

Accessibility note on gold: bright Cintana gold does not pass AA with white text. `--brand-gold-foreground` is set to dark navy so gold buttons are readable. If you must match Cintana's white-on-gold exactly, flip that one token and keep gold to large text or non-text use only.

## Radius and shape

- Base `--radius` is `0.75rem`. Cards and inputs use `rounded-xl`.
- Primary and secondary action buttons are **pill** (`rounded-full`), echoing Cintana's "Discover More" and "Contact us".
- Single-sided borders never get rounded corners.

## The signature: the chevron

Cintana's hero drives the eye rightward with a large chevron/arrow. Kala adopts a chevron as its one signature element:
- The logo mark (`components/brand/KalaMark.tsx`) is a chevron built from navy and gold.
- Use a small chevron as the forward-progress motif: "continue", "next step", mastery progress, the diagnostic-to-practice flow. Do not scatter it; it means forward motion.
- Spend boldness here and keep everything else quiet.

## Typography

- **Display / headings:** a confident grotesque. Default to a strong sans (for example the variable font already loaded, or Space Grotesk / Sora if adding one). Headings are large, tight, navy, weight 600 to 700. Cintana's hero is big and unafraid; match that on section headers.
- **Body:** a clean, legible sans (Inter or the system stack). Weight 400 to 500, comfortable line height.
- **Data / captions:** the same body face at smaller sizes, or a mono for numeric tables if helpful.
- Two weights per surface is usually enough. Sentence case everywhere. No ALL CAPS except tiny eyebrow labels with tracking.

## Layout

- Generous whitespace, a clear single job per screen. The masterplan's screens (course workspace, diagnostic, practice, tutor, twin, instructor dashboard) each have one primary action.
- Left-aligned large headings with a short supporting line, in the Cintana manner.
- Dashboards (instructor heatmap, student twin) are the data-dense exception: there, precision in spacing and alignment carries the quality.

## Motion

- Restrained. A page-load settle, hover micro-interactions on interactive cards, and a chevron nudge on progress. Nothing ambient or decorative.
- Always wrap non-essential motion so `prefers-reduced-motion` disables it.

## Quality floor (every screen)

Responsive to mobile, visible keyboard focus (the teal ring), reduced motion respected, empty and error states written as direction not mood ("Take a diagnostic to build your baseline", not "No data"). Errors say what happened and how to fix it, in the product's voice.

## Do not

- Do not hardcode colors or radii; use tokens.
- Do not use the warm-cream-plus-terracotta or the near-black-plus-acid-accent AI-default looks. Kala is navy, gold, teal on cool near-white.
- Do not round every element into a pill. Pills are for actions only.
- Do not let the chevron become decoration; it means forward motion.
