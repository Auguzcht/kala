import { useMemo, useState } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { ChevronLeftIcon } from "@/components/ui/chevron-left";
import { ChevronRightIcon } from "@/components/ui/chevron-right";
import { XIcon } from "@/components/ui/x";
import { Button } from "@/components/ui/button";
import { useDeleteTutorConversation, useTutorConversations } from "@/features/tutor";
import type { TutorConversation } from "@/features/tutor";
import { cn } from "@/lib/utils";

// Extends the icon rail, immediately to its right, in normal layout flow —
// NOT an overlay (see components/ui/sheet.tsx's LearnerSheet usage for what
// an overlay drawer looks like here; this is deliberately not that). A
// student's chat history is the whole point of a persisted tutor, so it
// gets the same always-visible left rail treatment ChatGPT/Claude/
// Perplexity give theirs, rather than being buried in a dropdown in the
// session bar the way the pre-migration Select switcher had it.
//
// Collapse state is OWNED BY CourseShell, not this component: the content
// column's left padding has to match whichever width this renders at, so
// the source of truth has to live where that padding decision is made.
// This component is a controlled view over it.
export function TutorSidebar({
  courseId,
  collapsed,
  onToggleCollapsed,
}: {
  courseId: string;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}) {
  const navigate = useNavigate();
  // NOT `useSearch({ from: "/course/tutor" })`. This component is rendered
  // by CourseShell, which is the PARENT `/course` layout route — TutorChat
  // is the one actually living under `/course/tutor` via <Outlet/>. The
  // strict form requires the router's current match array to already
  // contain that exact route at render time, and during a navigation into
  // or out of /course/tutor there's a real window where useLocation()'s
  // pathname (what CourseShell's isTutorRoute check uses) has updated but
  // the match array hasn't caught up yet — that race threw "Invariant
  // failed: Could not find an active match from '/course/tutor'" here,
  // reliably, on real navigations. `strict: false` reads the merged search
  // state without requiring that guarantee, which is exactly the documented
  // escape hatch for a shell-level component like this one.
  const search = useSearch({ strict: false });
  const activeId =
    typeof search === "object" && search !== null && "conversation" in search
      ? (search as { conversation?: string }).conversation
      : undefined;
  const conversations = useTutorConversations(courseId);
  const deleteConversation = useDeleteTutorConversation(courseId);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const grouped = useMemo(() => groupByRecency(conversations.data ?? []), [conversations.data]);
  const hasAny = GROUP_ORDER.some((label) => grouped[label].length > 0);

  function selectConversation(id: string | undefined) {
    void navigate({ to: "/course/tutor", search: id ? { conversation: id } : {} });
  }

  function handleDelete(id: string) {
    setDeletingId(id);
    deleteConversation.mutate(id, {
      onSettled: () => setDeletingId(null),
      onSuccess: () => {
        // Deleting the active thread must not leave the URL pointing at a
        // conversation that no longer exists — TutorChat would fetch a 404.
        if (id === activeId) selectConversation(undefined);
      },
    });
  }

  if (collapsed) {
    return (
      <div className="fixed inset-y-0 left-14 z-10 flex w-9 flex-col items-center border-r bg-card py-4">
        <button
          type="button"
          onClick={onToggleCollapsed}
          aria-label="Show chat history"
          className="inline-flex size-8 items-center justify-center rounded-full border border-border text-muted-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronRightIcon size={14} />
        </button>
      </div>
    );
  }

  return (
    <div className="fixed inset-y-0 left-14 z-10 flex w-64 flex-col border-r bg-card">
      <div className="flex h-12 shrink-0 items-center justify-between gap-2 border-b bg-card px-3">
        <span className="font-display text-sm font-semibold text-foreground">Chats</span>
        <button
          type="button"
          onClick={onToggleCollapsed}
          aria-label="Hide chat history"
          className="inline-flex size-7 items-center justify-center rounded-full border border-border text-muted-foreground transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronLeftIcon size={14} />
        </button>
      </div>

      <div className="shrink-0 px-3 pt-3">
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-center"
          onClick={() => selectConversation(undefined)}
        >
          New chat
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        {conversations.isLoading ? (
          <p className="px-1 py-2 text-xs text-muted-foreground">Loading…</p>
        ) : !hasAny ? (
          <p className="px-1 py-2 text-xs text-muted-foreground">
            No chats yet — ask something to start one.
          </p>
        ) : (
          GROUP_ORDER.map((label) =>
            grouped[label].length > 0 ? (
              <div key={label} className="mb-4 last:mb-0">
                <p className="mb-1.5 px-1 text-[11px] font-semibold uppercase tracking-[0.06em] text-muted-foreground">
                  {label}
                </p>
                <div className="flex flex-col gap-0.5">
                  {grouped[label].map((c) => (
                    <div
                      key={c.id}
                      className={cn(
                        "group flex items-center gap-1 border-l-2 py-2 pl-2.5 pr-1.5 transition-colors",
                        c.id === activeId
                          ? "border-brand-orange bg-brand-orange/10"
                          : "border-transparent hover:bg-accent/60"
                      )}
                    >
                      <button
                        type="button"
                        onClick={() => selectConversation(c.id)}
                        className="min-w-0 flex-1 truncate text-left text-sm text-foreground focus-visible:outline-none"
                      >
                        {c.title ?? "Untitled chat"}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(c.id)}
                        disabled={deletingId === c.id}
                        aria-label={`Delete ${c.title ?? "this chat"}`}
                        className="shrink-0 text-muted-foreground opacity-0 transition-opacity hover:text-destructive focus-visible:opacity-100 disabled:opacity-50 group-hover:opacity-100"
                      >
                        <XIcon size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ) : null
          )
        )}
      </div>
    </div>
  );
}

const GROUP_ORDER = ["Today", "Yesterday", "Older"] as const;
type GroupLabel = (typeof GROUP_ORDER)[number];

function groupByRecency(list: TutorConversation[]): Record<GroupLabel, TutorConversation[]> {
  const groups: Record<GroupLabel, TutorConversation[]> = {
    Today: [],
    Yesterday: [],
    Older: [],
  };
  for (const c of list) groups[bucketLabel(c.updatedAt)].push(c);
  return groups;
}

function bucketLabel(iso: string): GroupLabel {
  const d = new Date(iso);
  const now = new Date();
  const startOfDay = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diffDays = Math.round((startOfDay(now) - startOfDay(d)) / 86_400_000);
  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  return "Older";
}

// Exported so CourseShell can compute the content column's left padding
// without duplicating these numbers — the rail is 56px (w-14); this panel
// is 256px expanded (w-64), 36px collapsed (w-9).
export const TUTOR_SIDEBAR_EXPANDED_PX = 256;
export const TUTOR_SIDEBAR_COLLAPSED_PX = 36;
