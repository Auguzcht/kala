import { useNavigate } from "@tanstack/react-router";
import { useAtRisk } from "@/features/instructor";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { ArrowRightIcon } from "@/components/ui/arrow-right";

// Needs-support list. Flags are evidence-triggered with supportive wording
// ("Needs support", never "Failing"); every flag carries its reason. The
// good-news empty state reads as success, not a broken screen.
//
// Two things this version fixes over the first pass.
//
// Real names. This panel was still reading `pseudonym` after the roster
// rework gave every other instructor surface a display name — a leftover
// from /at-risk being an older, untouched endpoint. `deidentified` is now a
// prop controlled by the page, so this list and the roster's own toggle
// flip together as one switch, not two that can disagree.
//
// Bounded height. This card sat directly above the trends and heatmap
// panels with no cap on its length, so a class of sixty flagged students
// would push everything below it off the first screen. A max-height
// ScrollArea keeps the card's footprint constant regardless of cohort
// size: the first few flags are always visible, the rest scroll inside
// the same box, and past a threshold a "View all in roster" handoff opens
// the roster's own Needs support filter — which already exists and is
// sortable and searchable — rather than growing a second, worse list here.

const VISIBLE_BEFORE_SCROLL = 4;
const LINK_TO_ROSTER_AFTER = 6;
// One flag card with a clamped two-line reason: 32px vertical padding +
// 28px identity row + 10px gap + two ~20px reason lines + 1px border.
// Kept in one place so the box height and the visible-entry math can't
// drift apart — the previous version multiplied a rough card height and
// landed mid-way through the 4th entry, which read as a broken cut rather
// than a scrollable list.
const CARD_HEIGHT = 112;
const CARD_GAP = 10;

export function AtRiskList({
  courseId,
  deidentified = false,
  onViewAllInRoster,
}: {
  courseId: string;
  deidentified?: boolean;
  onViewAllInRoster?: () => void;
}) {
  const { data, isLoading } = useAtRisk(courseId);
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }

  const flags = data?.flags ?? [];
  const scrollable = flags.length > VISIBLE_BEFORE_SCROLL;
  // The box holds exactly VISIBLE_BEFORE_SCROLL complete cards, never a
  // clipped one, and it does not depend on the roster's height at all:
  // height = N cards + (N-1) gaps. Deterministic by design — a mid-card
  // cut at any class size reads as a rendering bug on a screen recording,
  // and pixel-perfect alignment with the table is the kind of thing
  // nobody registers. Cards are a fixed height (h, clamped reason), so
  // the math holds exactly.
  const boxHeight = scrollable
    ? VISIBLE_BEFORE_SCROLL * CARD_HEIGHT + (VISIBLE_BEFORE_SCROLL - 1) * CARD_GAP
    : undefined;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <h2 className="font-display text-base font-semibold text-foreground">Needs support</h2>
        {flags.length > 0 ? (
          <span className="rounded-full bg-destructive px-2 py-0.5 font-mono text-[11.5px] font-bold text-white">
            {flags.length}
          </span>
        ) : null}
      </div>

      {flags.length === 0 ? (
        <div className="flex items-start gap-3 border border-dashed bg-card p-5">
          <span className="mt-1 size-2 shrink-0 rounded-full bg-brand-green" aria-hidden />
          <p className="text-[13px] leading-relaxed text-muted-foreground">
            No one needs support right now. Check back after the next activity.
          </p>
        </div>
      ) : (
        <>
          {/* `max-height` alone caps this box's layout size but does nothing
              to its overflow behavior — the default `overflow: visible`
              means content taller than the cap paints straight past the
              edge instead of scrolling, which is exactly the bleed into
              whatever sits next to or below this panel. `overflow-hidden`
              plus a real `height` (not `max-height`, so the value always
              applies rather than only when content is shorter) is what
              actually clips it and lets the ScrollArea's own scrollbar
              take over. */}
          <div className="relative">
            <ScrollArea
              style={boxHeight ? { height: boxHeight } : undefined}
              className={boxHeight ? "overflow-hidden pr-3" : undefined}
            >
              <div className="space-y-2.5">
                {flags.map((f, i) => (
                  <button
                    key={f.userId}
                    type="button"
                    id={i === 0 ? "tour-at-risk-first-flag" : undefined}
                    onClick={() => navigate({ to: "/class/student/$uid", params: { uid: f.userId } })}
                    // Fixed height, not min-height: the clamp on the reason
                    // below caps content at two lines, so h-[112px] is a
                    // real invariant the box math above can rely on. The
                    // reason paragraph flexes to absorb the slack on
                    // one-line reasons, so every card is exactly
                    // CARD_HEIGHT.
                    className="group flex h-[112px] w-full flex-col border bg-card p-4 text-left transition-colors hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <div className="flex items-center gap-2.5">
                      <span className="grid size-7 shrink-0 place-items-center rounded-full bg-brand-slate text-[10.5px] font-bold text-background">
                        {deidentified ? "••" : f.initials}
                      </span>
                      <span className="flex-1 truncate text-[13px] font-semibold text-foreground group-hover:underline">
                        {deidentified ? f.pseudonym : f.displayName}
                      </span>
                      {f.daysInactive != null && f.daysInactive >= 1 ? (
                        <span className="shrink-0 font-mono text-[11px] text-muted-foreground">
                          {f.daysInactive}d inactive
                        </span>
                      ) : null}
                    </div>
                    <p
                      className="mt-2.5 line-clamp-2 flex-1 text-[12.5px] leading-relaxed text-muted-foreground"
                      title={f.reason}
                    >
                      {f.reason}
                    </p>
                  </button>
                ))}
              </div>
            </ScrollArea>
            {/* More entries below the fold: a soft fade signals scroll
                without hiding the scrollbar (which only appears on
                hover/scroll in the shadcn ScrollArea). Sits above the
                box, pointer-events off so it never eats a click. */}
            {scrollable ? (
              <div
                aria-hidden
                className="pointer-events-none absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-background to-transparent"
              />
            ) : null}
          </div>

          {flags.length > LINK_TO_ROSTER_AFTER && onViewAllInRoster ? (
            <Button
              variant="outline"
              size="sm"
              className="w-full"
              onClick={onViewAllInRoster}
            >
              View all {flags.length} in roster <ArrowRightIcon size={14} />
            </Button>
          ) : null}
        </>
      )}
    </div>
  );
}
