import { useState, type RefObject } from "react";
import { Paperclip, X } from "lucide-react";
import {
  PromptInput,
  PromptInputButton,
  PromptInputBody,
  PromptInputTools,
  PromptInputTextarea,
  PromptInputSubmit,
  usePromptInputAttachments,
} from "@/components/ai-elements/prompt-input";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import type { TutorAttachment } from "@/features/tutor/schema/tutor.schema";
import { dockShape } from "@/features/tutor/lib/presentation";

function AttachButton({ disabled }: { disabled: boolean }) {
  const attachments = usePromptInputAttachments();
  return (
    <PromptInputButton
      aria-label="Attach a file"
      type="button"
      disabled={disabled}
      onClick={attachments.openFileDialog}
      className="rounded-md"
    >
      <Paperclip size={17} />
    </PromptInputButton>
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
        "[&_[data-slot=input-group]]:h-auto [&_[data-slot=input-group]]:min-h-12 [&_[data-slot=input-group]]:flex-col [&_[data-slot=input-group]]:border-input [&_[data-slot=input-group]]:shadow-sm [&_[data-slot=input-group]]:px-1.5",
        "[&_[data-slot=input-group]]:transition-[border-radius] [&_[data-slot=input-group]]:duration-200 motion-reduce:[&_[data-slot=input-group]]:transition-none",
        dockShape(dragging, attachments.length > 0 || uploading) ===
          "rounded-full"
          ? "[&_[data-slot=input-group]]:rounded-full"
          : "[&_[data-slot=input-group]]:rounded-xl",
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
              <button
                type="button"
                aria-label={`Remove ${attachment.filename}`}
                disabled={removingId === attachment.id}
                onClick={() => onRemove(attachment.id)}
                className="rounded-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
              >
                <X size={13} />
              </button>
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
      <div className="flex w-full items-center">
        <PromptInputBody>
          <PromptInputTextarea
            rows={1}
            placeholder="Ask Kala…"
            value={draft}
            onChange={(event) => {
              setDraft(event.target.value);
              onTyping();
            }}
            className="min-h-12 max-h-32 py-3"
          />
        </PromptInputBody>
        <PromptInputTools className="shrink-0 pl-1">
          <AttachButton disabled={uploading} />
        </PromptInputTools>
        <PromptInputSubmit
          aria-label={pending ? "Waiting for reply" : "Send message"}
          disabled={pending || uploading || !draft.trim()}
          status={pending ? "submitted" : undefined}
          className="shrink-0 rounded-full"
        />
      </div>
    </PromptInput>
  );
}
