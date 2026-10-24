import { useState, type RefObject } from "react";
import { Paperclip } from "lucide-react";
import {
  PromptInput,
  PromptInputButton,
  PromptInputBody,
  PromptInputTools,
  PromptInputTextarea,
  PromptInputSubmit,
  usePromptInputAttachments,
} from "@/components/ai-elements/prompt-input";
import { dockLayout } from "@/components/ai-elements/dock-layout";
import { AttachFileIcon } from "@/features/tutor/components/icons/attach-file";
import { CornerDownLeftIcon } from "@/features/tutor/components/icons/corner-down-left";
import { XIcon } from "@/components/ui/x";
import { useTutorIcon } from "@/features/tutor/hooks/use-tutor-icon";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import type { TutorAttachment } from "@/features/tutor/schema/tutor.schema";
import { dockShape } from "@/features/tutor/lib/presentation";

function AttachButton({ disabled }: { disabled: boolean }) {
  const hover = useTutorIcon();
  const attachments = usePromptInputAttachments();
  return (
    <PromptInputButton
      aria-label="Attach a file"
      type="button"
      disabled={disabled}
      onClick={attachments.openFileDialog}
      {...hover.events}
      className={dockLayout.control}
    >
      <AttachFileIcon
        ref={hover.ref}
        size={17}
        className="inline-flex"
        aria-hidden
      />
    </PromptInputButton>
  );
}

function RemoveAttachmentButton({
  name,
  disabled,
  onRemove,
}: {
  name: string;
  disabled: boolean;
  onRemove: () => void;
}) {
  const hover = useTutorIcon();
  return (
    <button
      type="button"
      aria-label={`Remove ${name}`}
      disabled={disabled}
      onClick={onRemove}
      {...hover.events}
      className="rounded-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
    >
      <XIcon ref={hover.ref} size={13} className="inline-flex" aria-hidden />
    </button>
  );
}

export function TutorComposer({
  dropTarget,
  dragging,
  onDragChange,
  attachments,
  onFiles,
  onRemove,
  removingId,
  onAsk,
  onTyping,
  pending,
  uploading,
}: {
  dropTarget: RefObject<HTMLDivElement | null>;
  dragging: boolean;
  onDragChange: (active: boolean) => void;
  attachments: TutorAttachment[];
  onFiles: (files: File[]) => void;
  onRemove: (id: string) => void;
  removingId: string | null;
  onAsk: (text: string) => void;
  onTyping: () => void;
  pending: boolean;
  uploading: boolean;
}) {
  const [draft, setDraft] = useState("");
  const submitIcon = useTutorIcon();
  return (
    <PromptInput
      id="tour-tutor-input"
      aria-label="Message Kala"
      accept=".txt,.md,.pdf,text/plain,text/markdown,application/pdf"
      multiple
      dropTarget={dropTarget}
      onDragActiveChange={onDragChange}
      onFilesSelected={onFiles}
      onSubmit={({ text }) => {
        if (!text.trim() || pending || uploading) return;
        onTyping();
        onAsk(text.trim());
        setDraft("");
      }}
      className={cn(
        dockLayout.form,
        "[&_[data-slot=input-group]]:transition-[border-radius] [&_[data-slot=input-group]]:duration-200 motion-reduce:[&_[data-slot=input-group]]:transition-none",
        dockShape(dragging, attachments.length > 0 || uploading) ===
          "rounded-full"
          ? dockLayout.pill
          : dockLayout.expanded,
      )}
    >
      {attachments.length || uploading ? (
        <div className="flex w-full flex-wrap gap-2 px-3 pb-2 pt-1">
          {attachments.map((attachment) => (
            <span
              key={attachment.id}
              className="inline-flex max-w-full items-center gap-2 rounded-md border bg-background px-2 py-1 text-xs"
            >
              <Paperclip size={12} className="shrink-0 text-muted-foreground" />
              <span className="max-w-40 truncate">{attachment.filename}</span>
              {attachment.status === "failed" ? (
                <span className="text-destructive">Couldn't read</span>
              ) : null}
              {attachment.status === "processing" ? (
                <Spinner className="size-3" />
              ) : null}
              <RemoveAttachmentButton
                name={attachment.filename}
                disabled={removingId === attachment.id}
                onRemove={() => onRemove(attachment.id)}
              />
            </span>
          ))}
          {uploading ? (
            <span
              role="status"
              className="flex items-center gap-2 text-xs text-muted-foreground"
            >
              <Spinner className="size-3" /> Attaching…
            </span>
          ) : null}
        </div>
      ) : null}
      <div className={dockLayout.row}>
        <PromptInputTools className="shrink-0">
          <AttachButton disabled={uploading} />
        </PromptInputTools>
        <PromptInputBody>
          <PromptInputTextarea
            rows={1}
            placeholder="Ask Kala…"
            value={draft}
            onChange={(event) => {
              setDraft(event.target.value);
              onTyping();
            }}
            className={dockLayout.textarea}
          />
        </PromptInputBody>
        <PromptInputSubmit
          aria-label={pending ? "Waiting for reply" : "Send message"}
          disabled={pending || uploading || !draft.trim()}
          status={pending ? "submitted" : undefined}
          className={dockLayout.control}
          {...submitIcon.events}
        >
          {pending ? undefined : (
            <CornerDownLeftIcon
              ref={submitIcon.ref}
              size={16}
              className="inline-flex"
              aria-hidden
            />
          )}
        </PromptInputSubmit>
      </div>
    </PromptInput>
  );
}
