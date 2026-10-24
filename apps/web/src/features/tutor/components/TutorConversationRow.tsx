import { useState } from "react";
import { MoreHorizontal, Pin, PinOff, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { TutorTitle } from "@/features/tutor/components/TutorTitle";
import { SquarePenIcon } from "@/features/tutor/components/icons/square-pen";
import { useTutorIcon } from "@/features/tutor/hooks/use-tutor-icon";
import { TutorHistoryMenuContent } from "@/features/tutor/components/TutorHistoryMenu";
import { useUpdateTutorConversation } from "@/features/tutor/hooks/use-tutor";
import { supportsConversationManagement } from "@/features/tutor/lib/presentation";
import type { TutorConversation } from "@/features/tutor/schema/tutor.schema";
import { apiErrorReason } from "@/lib/api-error";
import { cn } from "@/lib/utils";

export function TutorConversationRow({
  conversation,
  courseId,
  active,
  onSelect,
  onDelete,
}: {
  conversation: TutorConversation;
  courseId: string;
  active: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  const renameIcon = useTutorIcon();
  const [menuOpen, setMenuOpen] = useState(false);
  const update = useUpdateTutorConversation(courseId);
  const [renaming, setRenaming] = useState(false);
  const [title, setTitle] = useState("");
  const capable = supportsConversationManagement(conversation);
  const name = conversation.title || "Untitled chat";
  function onError(error: unknown) {
    toast.error("Couldn't update this chat", {
      description: apiErrorReason(error) ?? "Please try again.",
    });
  }
  function pin() {
    update.mutate(
      { id: conversation.id, pinned: !conversation.pinnedAt },
      { onError },
    );
  }
  function saveTitle() {
    if (!title.trim() || update.isPending) return;
    update.mutate(
      { id: conversation.id, title: title.trim() },
      { onSuccess: () => setRenaming(false), onError },
    );
  }
  return (
    <div
      className={cn(
        "group flex min-h-10 items-center gap-1 border-l-2 px-2 py-1",
        active
          ? "border-brand-orange bg-accent"
          : "border-transparent hover:bg-accent/60",
      )}
    >
      {renaming && capable ? (
        <form
          className="min-w-0 flex-1 space-y-1 py-1"
          onSubmit={(event) => {
            event.preventDefault();
            saveTitle();
          }}
        >
          <Input
            autoFocus
            aria-label="Chat title"
            value={title}
            maxLength={80}
            disabled={update.isPending}
            onChange={(event) => setTitle(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Escape") setRenaming(false);
            }}
          />
          <div className="flex gap-1">
            <Button
              size="sm"
              type="submit"
              disabled={!title.trim() || update.isPending}
            >
              Save
            </Button>
            <Button
              size="sm"
              variant="ghost"
              type="button"
              onClick={() => setRenaming(false)}
            >
              Cancel
            </Button>
          </div>
        </form>
      ) : (
        <TutorTitle name={name} active={active} onSelect={onSelect} />
      )}
      <div
        className={cn(
          "flex shrink-0 items-center",
          menuOpen || conversation.pinnedAt
            ? "opacity-100"
            : "opacity-100 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100",
        )}
      >
        <DropdownMenu open={menuOpen} onOpenChange={setMenuOpen}>
          <DropdownMenuTrigger asChild>
            <Button
              size="icon"
              variant="ghost"
              className="size-7 rounded-lg focus-visible:ring-inset focus-visible:ring-offset-0"
              aria-label={`Actions for ${name}`}
            >
              <MoreHorizontal size={16} />
            </Button>
          </DropdownMenuTrigger>
          <TutorHistoryMenuContent
            onCloseAutoFocus={(event) => {
              if (renaming) event.preventDefault();
            }}
          >
            {capable ? (
              <>
                <DropdownMenuItem
                  className="rounded-lg px-3 py-2"
                  {...renameIcon.events}
                  onSelect={() => {
                    setRenaming(true);
                    setTitle(conversation.title ?? "");
                  }}
                >
                  <SquarePenIcon
                    ref={renameIcon.ref}
                    size={16}
                    className="inline-flex"
                    aria-hidden
                  />
                  Rename
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="rounded-lg px-3 py-2"
                  disabled={update.isPending}
                  onSelect={() => pin()}
                >
                  {conversation.pinnedAt ? <PinOff /> : <Pin />}
                  {conversation.pinnedAt ? "Unpin" : "Pin"}
                </DropdownMenuItem>
                <DropdownMenuSeparator className="mx-1 my-2" />
              </>
            ) : null}
            <DropdownMenuItem
              className="rounded-lg px-3 py-2"
              variant="destructive"
              onSelect={() => onDelete()}
            >
              <Trash2 />
              Delete
            </DropdownMenuItem>
          </TutorHistoryMenuContent>
        </DropdownMenu>
        {capable ? (
          <Button
            size="icon"
            variant="ghost"
            className="size-7 rounded-lg focus-visible:ring-inset focus-visible:ring-offset-0"
            aria-label={`${conversation.pinnedAt ? "Unpin" : "Pin"} ${name}`}
            disabled={update.isPending}
            onClick={() => pin()}
          >
            {conversation.pinnedAt ? <PinOff size={14} /> : <Pin size={14} />}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
