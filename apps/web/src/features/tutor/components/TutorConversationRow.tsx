import { useRef, useState } from "react";
import { MoreHorizontal, Pin, PinOff, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { TutorRenameDialog } from "@/features/tutor/components/TutorRenameDialog";
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
  const trigger = useRef<HTMLButtonElement>(null);
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
  return (
    <div
      className={cn(
        "group flex min-h-10 items-center gap-1 border-l-2 px-2 py-1",
        active
          ? "border-brand-orange bg-accent"
          : "border-transparent hover:bg-accent/60",
      )}
    >
      <TutorTitle name={name} active={active} onSelect={onSelect} />
      {renaming && capable ? <TutorRenameDialog conversation={conversation} courseId={courseId}
        onClose={() => setRenaming(false)} trigger={trigger} /> : null}
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
              ref={trigger}
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
            aria-busy={update.isPending || undefined}
            onClick={() => pin()}
          >
            {conversation.pinnedAt ? <PinOff size={14} /> : <Pin size={14} />}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
