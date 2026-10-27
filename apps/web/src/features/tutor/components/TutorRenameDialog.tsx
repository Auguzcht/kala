import { useRef, useState, type RefObject } from "react";
import { useReducedMotion } from "motion/react";
import { Dialog as DialogPrimitive } from "radix-ui";
import {
  Dialog, DialogPortal, DialogOverlay, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { useUpdateTutorConversation } from "@/features/tutor/hooks/use-tutor";
import { apiErrorReason } from "@/lib/api-error";
import type { TutorConversation } from "@/features/tutor/schema/tutor.schema";

export function TutorRenameDialog({ conversation, courseId, onClose, trigger }: {
  conversation: TutorConversation;
  courseId: string;
  onClose: () => void;
  trigger: RefObject<HTMLButtonElement | null>;
}) {
  const [title, setTitle] = useState(conversation.title ?? "");
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const submitting = useRef(false);
  const update = useUpdateTutorConversation(courseId);
  const reduced = useReducedMotion();
  const noMotion = reduced ? { animation: "none", transition: "none" } : undefined;
  const trimmed = title.trim();
  const valid = Boolean(trimmed) && trimmed !== (conversation.title ?? "").trim();

  function save() {
    if (!valid || update.isPending || submitting.current) return;
    submitting.current = true;
    setError(null);
    update.mutate({ id: conversation.id, title: trimmed }, {
      onSuccess: onClose,
      onError: (reason) => setError(apiErrorReason(reason) ?? "Couldn't rename this chat. Please try again."),
      onSettled: () => { submitting.current = false; },
    });
  }

  return (
    <Dialog open onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogPortal>
      <DialogOverlay style={noMotion} />
      <DialogPrimitive.Content
        className="fixed left-1/2 top-1/2 z-50 grid w-full max-w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 gap-4 rounded-lg border bg-background p-6 shadow-lg outline-none duration-200 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 sm:max-w-lg"
        style={noMotion}
        onOpenAutoFocus={(event) => {
          event.preventDefault();
          input.current?.focus();
          input.current?.select();
        }}
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          trigger.current?.focus();
        }}
      >
        <DialogHeader>
          <DialogTitle>Rename chat</DialogTitle>
          <DialogDescription>Keep it short and recognizable</DialogDescription>
        </DialogHeader>
        <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); save(); }}>
          <Input ref={input} aria-label="Chat title" maxLength={80} value={title}
            disabled={update.isPending} onChange={(event) => setTitle(event.target.value)} />
          {error ? <p role="alert" className="text-sm text-destructive">{error}</p> : null}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={!valid || update.isPending} aria-busy={update.isPending || undefined}>
              {update.isPending ? <Spinner aria-hidden /> : null}Save
            </Button>
          </DialogFooter>
        </form>
      </DialogPrimitive.Content>
      </DialogPortal>
    </Dialog>
  );
}
