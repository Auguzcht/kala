import { useEffect, useRef, useState } from "react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { useReducedMotion } from "motion/react";
import {
  Dialog,
  DialogPortal,
  DialogOverlay,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { XIcon } from "@/components/ui/x";
import { useTutorIcon } from "@/features/tutor/hooks/use-tutor-icon";
import {
  TEXT_PREVIEW_BYTES,
  canPreviewTutorFile,
  tutorFileSize,
} from "@/features/tutor/lib/attachments";

export type TutorPreviewSelection = {
  name: string;
  size: number;
  status: string;
  file?: File;
  trigger: HTMLButtonElement;
};
export function TutorFilePreview({
  selection,
  onClose,
}: {
  selection: TutorPreviewSelection | null;
  onClose: () => void;
}) {
  const [loaded, setLoaded] = useState<{
    file: File;
    text: string | null;
    failed?: boolean;
  } | null>(null);
  const reduced = useReducedMotion();
  const closeIcon = useTutorIcon();
  const lastSelection = useRef(selection);
  if (selection) lastSelection.current = selection;
  const details = selection ?? lastSelection.current;
  const file = details?.file;
  const rawPreview = file && canPreviewTutorFile(file);
  useEffect(() => {
    if (!file || !canPreviewTutorFile(file)) return;
    let cancelled = false;
    void file
      .slice(0, TEXT_PREVIEW_BYTES)
      .text()
      .then((text) => {
        if (!cancelled) setLoaded({ file, text });
      })
      .catch(() => {
        if (!cancelled) setLoaded({ file, text: null, failed: true });
      });
    return () => {
      cancelled = true;
    };
  }, [file]);
  const content = loaded?.file === file ? loaded : null;
  const noMotion = reduced
    ? { animation: "none", transition: "none" }
    : undefined;
  return (
    <Dialog
      open={Boolean(selection)}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogPortal>
        <DialogOverlay
          className="bg-background/40 backdrop-blur-xs"
          style={noMotion}
        />
        <DialogPrimitive.Content
          aria-describedby="tutor-file-preview-description"
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            lastSelection.current?.trigger.focus();
          }}
          className="fixed left-1/2 top-1/2 z-50 flex max-h-[80vh] w-[calc(100%-2rem)] max-w-3xl -translate-x-1/2 -translate-y-1/2 flex-col gap-3 rounded-xl border bg-background p-4 shadow-lg outline-none duration-150 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95"
          style={noMotion}
        >
          <div className="flex min-w-0 items-center justify-between gap-3">
            <DialogTitle className="min-w-0 truncate text-base">
              {details?.name}
            </DialogTitle>
            <DialogClose asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="Close file preview"
                onMouseEnter={closeIcon.events.onMouseEnter}
                onMouseLeave={closeIcon.events.onMouseLeave}
              >
                <XIcon ref={closeIcon.ref} size={16} aria-hidden />
              </Button>
            </DialogClose>
          </div>
          <DialogDescription
            id="tutor-file-preview-description"
            className="text-xs"
          >
            {details?.name.split(".").at(-1)?.toUpperCase()} · {details ? tutorFileSize(details.size) : ""} · {details?.status}
            {rawPreview ? " · Plain text preview" : " · File details"}
            {rawPreview && file.size > TEXT_PREVIEW_BYTES
              ? " · Showing the first 128 KB"
              : ""}
          </DialogDescription>
          <div className="min-h-0 overflow-auto rounded-lg bg-muted/40 p-4">
            {!rawPreview ? (
              <p className="text-sm leading-6 text-muted-foreground">
                {details?.name.toLowerCase().endsWith(".pdf")
                  ? "PDF content preview isn't available yet. This card shows the file's details; an attached PDF can still be used by Kala when its status is ready."
                  : "File contents aren't available in this session. Raw-text preview is available for TXT and MD files selected in this chat. Select the original file again to preview its contents locally."}
              </p>
            ) : !content ? (
              <div role="status" className="space-y-2 text-sm text-muted-foreground">
                <p>Loading preview…</p>
                <Skeleton className="h-4 w-full motion-reduce:animate-none" /><Skeleton className="h-4 w-3/4 motion-reduce:animate-none" />
              </div>
            ) : content.failed ? (
              <p role="alert" className="text-sm">
                Couldn't read this file. You can still remove it and choose it
                again.
              </p>
            ) : (
              <pre className="whitespace-pre-wrap break-words font-mono text-xs leading-6">
                {content.text || "This file is empty."}
              </pre>
            )}
          </div>
        </DialogPrimitive.Content>
      </DialogPortal>
    </Dialog>
  );
}
