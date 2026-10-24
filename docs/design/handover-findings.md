# Design reconciliation notes — 2026-10-24

Status: findings recorded under APPROVAL-01 / WI-03. No CSS, tokens or component behavior changed. [DESIGN.md](../../apps/web/src/styles/DESIGN.md) remains the visual authority. Full visual/study-surface requirements are planned in WI-08; these notes do not define new intent.

| Finding | Evidence | Treatment |
| --- | --- | --- |
| F01: root pill-button summary conflicts with DESIGN.md | Old root CLAUDE.md required pills; DESIGN.md Radius and shape requires boxy action buttons. | Root is now an AGENTS pointer. Preserve design authority, not the obsolete summary. |
| F08: numeric radius annotation differs from the token | [Design plan, original line 140](../ai-overhaul-v2/00_DESIGN_PLAN.md) calls `rounded-md` 6px; [globals.css lines 15 and 235](../../apps/web/src/styles/globals.css#L235) resolves it to the 0.25rem base (4px), consistent with DESIGN.md. | Record the annotation mismatch; use the existing token rather than prescribing a new radius. Rounded conversational dock rationale is local to that surface, not a blanket button policy. |
| F09: orange rule conflicts with its exceptions | [Token reference, original lines 12, 19](../ai-overhaul-v2/07_TOKEN_USAGE_REFERENCE.md) allows focus/progress exceptions but says two orange objects are a bug; [design plan, original lines 72–79](../ai-overhaul-v2/00_DESIGN_PLAN.md) limits actionable primaries. | Preserve one orange **actionable primary** per view and semantic focus/progress exceptions as historical intent for reconciliation. No palette or CSS change. |

[Guide knowledge](../work/handover-2026/evidence/local-guide-knowledge.md) preserves motif, marketing and motion rationale. Motion Primitives provenance and React 19/ESLint adaptations are in [local development](../engineering/local-development.md#component-provenance). The original brand brief is [archived provenance](../archive/design/Kala_Design_Brief.md), not a competing visual authority.
