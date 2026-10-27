import { useEffect, useLayoutEffect, useRef, useState, type RefObject, type KeyboardEvent } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { toast } from "sonner";
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
import { useTutorIcon } from "@/features/tutor/hooks/use-tutor-icon";
import { cn } from "@/lib/utils";
import type { TutorAttachment } from "@/features/tutor/schema/tutor.schema";
import { validateTutorFile } from "@/features/tutor/lib/presentation";
import { createPromptHistory, historyDirection } from "@/features/tutor/lib/prompt-history";
import type { AssignedTutorDraft } from "@/features/tutor/lib/assigned-draft";
import {
  type StagedTutorFile,
  type TutorFileUploadResult,
} from "@/features/tutor/lib/attachments";
import { TutorFileCard } from "@/features/tutor/components/TutorFileCard";
import {
  TutorFilePreview,
  type TutorPreviewSelection,
} from "@/features/tutor/components/TutorFilePreview";

function AttachButton({ disabled }: { disabled: boolean }) {
  const hover = useTutorIcon();
  const attachments = usePromptInputAttachments();
  return (
    <PromptInputButton
      data-tour="tutor-attach"
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

export function TutorComposer({
  dropTarget,
  onDragChange,
  attachments,
  onFiles,
  onRemove,
  removingId,
  onAsk,
  onTyping,
  pending,
  uploading,
  initialDraft,
  promptHistory = [],
}: {
  dropTarget: RefObject<HTMLDivElement | null>;
  onDragChange: (active: boolean) => void;
  attachments: TutorAttachment[];
  onFiles: (files: File[]) => Promise<TutorFileUploadResult>;
  onRemove: (id: string) => void;
  removingId: string | null;
  onAsk: (text: string) => void;
  onTyping: () => void;
  pending: boolean;
  uploading: boolean;
  initialDraft?: AssignedTutorDraft;
  promptHistory?: readonly string[];
}) {
  const [draft, setDraft] = useState(() => initialDraft?.text ?? "");
  const history = useRef(createPromptHistory());
  const recalledCaret = useRef<{ input: HTMLTextAreaElement; start: number; end: number } | null>(null);
  // Restore before paint so a later native key cannot race a deferred caret move.
  useLayoutEffect(() => {
    const caret = recalledCaret.current;
    recalledCaret.current = null;
    if (caret?.input.isConnected) caret.input.setSelectionRange(caret.start, caret.end);
  });
  const [staged, setStaged] = useState<StagedTutorFile[]>([]);
  const [localFiles, setLocalFiles] = useState<Map<string, File>>(
    () => new Map(),
  );
  const [preview, setPreview] = useState<TutorPreviewSelection | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const submitLock = useRef(false);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  const submitIcon = useTutorIcon();
  const reducedMotion = useReducedMotion();
  const busy = submitting || uploading;
  const hasFiles = staged.length > 0 || attachments.length > 0;
  const blockedAttachment = attachments.some((file) => file.status !== "ready");

  function recallPrompt(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.defaultPrevented || busy || pending || submitLock.current) return;
    const input = event.currentTarget;
    const direction = historyDirection({
      key: event.key, value: input.value, start: input.selectionStart, end: input.selectionEnd,
      modified: event.shiftKey || event.altKey || event.ctrlKey || event.metaKey,
      composing: event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229,
    });
    if (!direction) return;
    const recalled = history.current.move(direction, promptHistory, input.value,
      { start: input.selectionStart, end: input.selectionEnd });
    if (!recalled) return;
    event.preventDefault();
    if (input.value === recalled.text) {
      input.setSelectionRange(recalled.caret.start, recalled.caret.end);
    } else {
      recalledCaret.current = { input, ...recalled.caret };
      setDraft(recalled.text);
    }
    onTyping();
  }

  function stageFiles(files: File[]) {
    if (submitLock.current || uploading) return;
    const valid: File[] = [];
    for (const file of files) {
      const reason = validateTutorFile(file);
      if (reason)
        toast.error("Couldn't attach that file", { description: reason });
      else valid.push(file);
    }
    setStaged((current) => {
      const next = [...current];
      for (const file of valid) {
        if (
          !next.some(
            (item) =>
              item.file.name === file.name &&
              item.file.size === file.size &&
              item.file.lastModified === file.lastModified,
          )
        )
          next.push({ id: crypto.randomUUID(), file });
      }
      return next;
    });
    if (valid.length) onTyping();
  }

  return (
    <>
      <PromptInput
        id="tour-tutor-input"
        aria-label="Message Kala"
        accept=".txt,.md,.pdf,text/plain,text/markdown,application/pdf"
        multiple
        dropTarget={dropTarget}
        onDragActiveChange={onDragChange}
        onFilesSelected={stageFiles}
        onSubmit={async ({ text }) => {
          if (
            !text.trim() ||
            pending ||
            busy ||
            blockedAttachment ||
            submitLock.current
          )
            return;
          submitLock.current = true;
          setSubmitting(true);
          onTyping();
          try {
            if (staged.length) {
              const result = await onFiles(staged.map((item) => item.file));
              if (!mounted.current) return;
              setLocalFiles((current) => {
                const next = new Map(current);
                for (const item of result.uploaded)
                  next.set(item.attachment.id, item.file);
                return next;
              });
              setStaged((current) =>
                current
                  .filter(
                    (item) =>
                      !result.uploaded.some((done) => done.file === item.file),
                  )
                  .map((item) => ({
                    ...item,
                    failed: result.failed.includes(item.file),
                  })),
              );
              if (
                result.failed.length ||
                result.uploaded.some(
                  (item) => item.attachment.status !== "ready",
                )
              )
                return;
            }
            if (!mounted.current) return;
            onAsk(text.trim());
            history.current.reset();
            setDraft((current) =>
              current.trim() === text.trim() ? "" : current,
            );
          } catch {
            if (mounted.current)
              toast.error("Couldn't attach those files", {
                description:
                  "Your files and question are still here. Please try again.",
              });
          } finally {
            submitLock.current = false;
            if (mounted.current) setSubmitting(false);
          }
        }}
        className={cn(dockLayout.form, dockLayout.pill)}
      >
        <AnimatePresence initial={false}>
          {hasFiles ? (
            <motion.div
              key="file-cards"
              className="w-full overflow-hidden"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{
                duration: reducedMotion ? 0 : 0.2,
                ease: "easeInOut",
              }}
            >
              <div
                className="flex gap-3 overflow-x-auto pb-2 pl-1.5 pr-1.5 pt-3"
                aria-label="Chat attachments"
              >
                {attachments.map((attachment) => {
                  const file = localFiles.get(attachment.id);
                  return (
                    <TutorFileCard
                      key={attachment.id}
                      name={attachment.filename}
                      size={attachment.sizeBytes}
                      status={
                        attachment.status === "ready"
                          ? "Attached"
                          : attachment.status === "failed"
                            ? "Couldn't read"
                            : "Processing"
                      }
                      disabled={busy || pending || removingId === attachment.id}
                      onRemove={() => onRemove(attachment.id)}
                      onPreview={(trigger) => setPreview({
                        name: attachment.filename, size: attachment.sizeBytes,
                        status: attachment.status === "ready" ? "Attached" : attachment.status === "failed" ? "Couldn't read" : "Processing",
                        file, trigger,
                      })}
                    />
                  );
                })}
                {staged.map((item) => (
                  <TutorFileCard
                    key={item.id}
                    name={item.file.name}
                    size={item.file.size}
                    status={
                      busy
                        ? "Uploading"
                        : item.failed
                          ? "Upload failed — send to retry"
                          : "Ready to attach"
                    }
                    disabled={busy}
                    onRemove={() =>
                      setStaged((current) =>
                        current.filter((file) => file.id !== item.id),
                      )
                    }
                    onPreview={(trigger) => setPreview({
                      name: item.file.name, size: item.file.size,
                      status: item.failed ? "Upload failed" : "Ready to attach",
                      file: item.file, trigger,
                    })}
                  />
                ))}
              </div>
            </motion.div>
          ) : null}
        </AnimatePresence>
        <div className={dockLayout.row}>
          <PromptInputTools className="shrink-0">
            <AttachButton disabled={busy} />
          </PromptInputTools>
          <PromptInputBody>
            <PromptInputTextarea
              rows={1}
              placeholder="Ask Kala…"
              autoFocus={Boolean(initialDraft)}
              value={draft}
              onKeyDown={recallPrompt}
              onChange={(event) => {
                history.current.reset();
                setDraft(event.target.value);
                onTyping();
              }}
              className={dockLayout.textarea}
            />
          </PromptInputBody>
          <PromptInputSubmit
            aria-label={busy ? "Attaching files" : "Send message"}
            disabled={pending || busy || blockedAttachment || !draft.trim()}
            aria-busy={pending || busy || undefined}
            status={busy && !pending ? "submitted" : undefined}
            className={dockLayout.control}
            {...submitIcon.events}
          >
            {busy && !pending ? undefined : (
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
      <TutorFilePreview selection={preview} onClose={() => setPreview(null)} />
    </>
  );
}
