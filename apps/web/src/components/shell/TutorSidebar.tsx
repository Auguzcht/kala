import { useState } from "react";
import { useNavigate, useSearch } from "@tanstack/react-router";
import { ChevronDown, Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  useDeleteTutorConversation,
  useTutorConversations,
  groupConversations,
  TutorConversationRow,
} from "@/features/tutor";
import type { TutorConversation } from "@/features/tutor";
import { apiErrorReason } from "@/lib/api-error";

/** Layout is owned by CourseShell; the same history works in its mobile Sheet. */
export function TutorSidebar({
  courseId,
  onSelect,
}: {
  courseId: string;
  onSelect?: () => void;
}) {
  const navigate = useNavigate();
  const search = useSearch({ strict: false });
  const activeId = "conversation" in search ? search.conversation : undefined;
  const conversations = useTutorConversations(courseId);
  const remove = useDeleteTutorConversation(courseId);
  const [deleting, setDeleting] = useState<TutorConversation | null>(null);
  const [expanded, setExpanded] = useState({ Pinned: true, Recents: true });
  const grouped = groupConversations(conversations.data ?? []);

  function select(id?: string) {
    void navigate({
      to: "/course/tutor",
      search: id ? { conversation: id } : {},
    });
    onSelect?.();
  }
  function confirmDelete() {
    if (!deleting || remove.isPending) return;
    const id = deleting.id;
    remove.mutate(id, {
      onSuccess: () => {
        setDeleting(null);
        if (id === activeId) select();
      },
      onError: (error) =>
        toast.error("Couldn't delete this chat", {
          description: apiErrorReason(error) ?? "Please try again.",
        }),
    });
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-card">
      <div className="flex h-12 shrink-0 items-center border-b px-4">
        <span className="font-display text-sm font-semibold">Chats</span>
      </div>
      <div className="px-3 py-3">
        <Button
          variant="outline"
          className="w-full justify-start"
          onClick={() => select()}
        >
          <Plus size={15} /> New chat
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-4">
        {conversations.isLoading ? (
          <p
            role="status"
            className="flex items-center gap-2 p-3 text-xs text-muted-foreground"
          >
            <Spinner className="size-3.5" /> Loading chats…
          </p>
        ) : conversations.isError ? (
          <div className="space-y-2 p-3 text-xs text-muted-foreground">
            <p>Chats could not be loaded.</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void conversations.refetch()}
            >
              Retry
            </Button>
          </div>
        ) : !conversations.data?.length ? (
          <p className="p-3 text-xs leading-relaxed text-muted-foreground">
            Ask something about your course to start a chat.
          </p>
        ) : (
          (["Pinned", "Recents"] as const).map((label) =>
            label === "Pinned" && !grouped.Pinned.length ? null : (
              <Collapsible
                key={label}
                open={expanded[label]}
                onOpenChange={(open) =>
                  setExpanded((value) => ({ ...value, [label]: open }))
                }
                className="mb-3"
              >
                <CollapsibleTrigger className="group flex w-full items-center gap-2 rounded-md px-2 py-2 text-xs font-medium text-muted-foreground hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                  <ChevronDown
                    size={13}
                    className="transition-transform group-data-[state=closed]:-rotate-90 motion-reduce:transition-none"
                  />
                  {label}
                  <span className="ml-auto font-mono text-[11px]">
                    {grouped[label].length}
                  </span>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  {grouped[label].map((conversation) => (
                    <TutorConversationRow
                      key={conversation.id}
                      conversation={conversation}
                      courseId={courseId}
                      active={conversation.id === activeId}
                      onSelect={() => select(conversation.id)}
                      onDelete={() => setDeleting(conversation)}
                    />
                  ))}
                </CollapsibleContent>
              </Collapsible>
            ),
          )
        )}
      </div>
      <Dialog
        open={Boolean(deleting)}
        onOpenChange={(open) => {
          if (!open && !remove.isPending) setDeleting(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this chat?</DialogTitle>
            <DialogDescription>
              “{deleting?.title || "Untitled chat"}” and its attachments will be
              deleted. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              disabled={remove.isPending}
              onClick={() => setDeleting(null)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={remove.isPending}
              onClick={confirmDelete}
            >
              {remove.isPending ? "Deleting…" : "Delete chat"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
