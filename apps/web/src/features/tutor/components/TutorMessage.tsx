import { useEffect, useRef, useState } from "react";
import { CheckIcon, CopyIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { UserBlock } from "@/components/study/UserBlock";
import { AssistantBlock } from "@/components/study/AssistantBlock";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

/** Tutor-only clipboard actions leave shared Study message defaults alone. */
export function TutorMessage({ role, text, initials, id, animate, animationKey }: {
  role: "user" | "assistant";
  text: string;
  initials?: string;
  id?: string;
  animate?: boolean;
  animationKey?: string;
}) {
  const [status, setStatus] = useState<"idle" | "copying" | "copied" | "failed">("idle");
  const busy = useRef(false);
  useEffect(() => {
    if (status !== "copied") return;
    const timer = window.setTimeout(() => setStatus("idle"), 2000);
    return () => window.clearTimeout(timer);
  }, [status]);

  async function copy() {
    if (busy.current) return;
    busy.current = true;
    setStatus("copying");
    try {
      if (typeof navigator === "undefined" || !navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(text);
      setStatus("copied");
    } catch {
      setStatus("failed");
    } finally {
      busy.current = false;
    }
  }

  return (
    <div data-tutor-message={role} className="w-full">
      <div className={cn("group/tutor-message space-y-1", role === "user"
        ? "ml-auto w-fit max-w-[85%] [&>div:first-child]:max-w-full" : "w-full")}>
      {role === "user" ? <UserBlock text={text} initials={initials} />
        : <AssistantBlock text={text} id={id} animate={animate} animationKey={animationKey} />}
      {text ? <div data-message-actions className={cn("flex flex-wrap items-center gap-2",
        role === "user" ? "justify-end" : "justify-start",
        status === "idle" ? "pointer-events-none opacity-0" : "opacity-100",
        "group-hover/tutor-message:pointer-events-auto group-hover/tutor-message:opacity-100 group-focus-within/tutor-message:pointer-events-auto group-focus-within/tutor-message:opacity-100 [@media(hover:none)]:pointer-events-auto [@media(hover:none)]:opacity-100")}>
        <Tooltip>
        <TooltipTrigger asChild>
        <Button type="button" variant="ghost" size="icon-sm" className="rounded-md text-muted-foreground [@media(hover:none)]:size-11"
          aria-label={role === "user" ? "Copy your message" : "Copy Kala's reply"}
          aria-busy={status === "copying"} disabled={status === "copying"} onClick={() => void copy()}>
          {status === "copied" ? <CheckIcon className="size-3.5" aria-hidden /> : <CopyIcon className="size-3.5" aria-hidden />}
        </Button>
        </TooltipTrigger>
        <TooltipContent side="top" sideOffset={6} className="motion-reduce:animate-none motion-reduce:transition-none">
          {status === "copied" ? "Copied" : "Copy message"}
        </TooltipContent>
        </Tooltip>
        <span role="status" aria-live="polite" className={status === "failed" ? "text-xs text-muted-foreground" : "sr-only"}>
          {status === "failed" ? "Couldn't copy. Select the text and copy it." : status === "copied" ? "Copied" : ""}
        </span>
      </div> : null}
      </div>
    </div>
  );
}
