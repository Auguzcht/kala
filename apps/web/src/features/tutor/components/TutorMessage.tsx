import { useEffect, useRef, useState } from "react";
import { CheckIcon, CopyIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { UserBlock } from "@/components/study/UserBlock";
import { AssistantBlock } from "@/components/study/AssistantBlock";

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
    <div data-tutor-message={role} className="w-full space-y-1">
      {role === "user" ? <UserBlock text={text} initials={initials} />
        : <AssistantBlock text={text} id={id} animate={animate} animationKey={animationKey} />}
      {text ? <div className={`flex flex-wrap items-center gap-2 ${role === "user" ? "justify-end" : "justify-start"}`}>
        <Button type="button" variant="ghost" size="sm" className="min-h-11 gap-1.5 px-2 text-xs text-muted-foreground"
          aria-label={role === "user" ? "Copy your message" : "Copy Kala's reply"}
          aria-busy={status === "copying"} disabled={status === "copying"} onClick={() => void copy()}>
          {status === "copied" ? <CheckIcon className="size-3.5" aria-hidden /> : <CopyIcon className="size-3.5" aria-hidden />}
          {status === "copied" ? "Copied" : "Copy"}
        </Button>
        <span role="status" aria-live="polite" className={status === "failed" ? "text-xs text-muted-foreground" : "sr-only"}>
          {status === "failed" ? "Couldn't copy. Select the text and copy it." : status === "copied" ? "Copied" : ""}
        </span>
      </div> : null}
    </div>
  );
}
