import { FileText, File } from "lucide-react";
import { XIcon } from "@/components/ui/x";
import { useTutorIcon } from "@/features/tutor/hooks/use-tutor-icon";
import { tutorFileSize } from "@/features/tutor/lib/attachments";
import { cn } from "@/lib/utils";

export function TutorFileCard({
  name,
  size,
  status,
  disabled,
  onRemove,
  onPreview,
}: {
  name: string;
  size: number;
  status: string;
  disabled: boolean;
  onRemove: () => void;
  onPreview: (trigger: HTMLButtonElement) => void;
}) {
  const removeIcon = useTutorIcon();
  const extension = name.split(".").at(-1)?.toUpperCase() ?? "File";
  const formatAccent =
    extension === "PDF"
      ? "bg-brand-orange/10 text-foreground"
      : extension === "TXT"
        ? "bg-brand-green/10 text-foreground"
        : "bg-primary/10 text-foreground";
  const body = (
    <>
      <span
        className={cn("flex size-9 items-center justify-center rounded-lg", formatAccent)}
        data-file-format={extension}
      >
        {extension === "PDF" ? (
          <File size={23} aria-hidden />
        ) : (
          <FileText size={23} aria-hidden />
        )}
      </span>
      <span
        className="mt-2 block w-full truncate text-sm font-medium"
        title={name}
      >
        {name}
      </span>
      <span className="block text-xs text-muted-foreground">
        {extension} · {tutorFileSize(size)}
      </span>
      <span
        className="mt-1 flex items-center gap-1 text-xs text-muted-foreground"
        role="status"
      >
        {status}
      </span>
    </>
  );
  return (
    <div
      className="relative w-44 shrink-0 rounded-xl border bg-muted/40"
      data-tutor-file-card
    >
      <button
        type="button"
        aria-label={`Preview ${name}`}
        onClick={(event) => onPreview(event.currentTarget)}
        className="flex w-full flex-col items-start rounded-xl p-3 pr-8 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring hover:bg-muted"
      >
        {body}
      </button>
      <button
        type="button"
        aria-label={`Remove ${name}`}
        disabled={disabled}
        onClick={onRemove}
        {...removeIcon.events}
        className="absolute right-1 top-1 flex size-6 items-center justify-center rounded-full text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring disabled:opacity-50"
      >
        <XIcon ref={removeIcon.ref} size={12} aria-hidden />
      </button>
    </div>
  );
}
