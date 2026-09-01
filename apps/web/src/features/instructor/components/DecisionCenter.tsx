import { useState, useRef, type ReactNode } from "react";
import { toast } from "sonner";
import {
  useDecideRecommendation,
  useGenerateRecommendations,
  useRecommendations,
} from "@/features/instructor";
import type { Recommendation, RecommendationKind } from "@/features/instructor";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { SparklesIcon, type SparklesIconHandle } from "@/components/ui/sparkles";
import { CheckIcon, type CheckIconHandle } from "@/components/ui/check";
import { XIcon, type XIconHandle } from "@/components/ui/x";
import { ZapIcon, type ZapHandle } from "@/components/ui/zap";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

// The gate. Kala proposes next actions for one learner; a named instructor
// approves, modifies, or rejects each one; only a decided action reaches
// the learner's plan.
//
// Three things this component insists on, because they are the difference
// between human-in-the-loop and a rubber stamp:
//
//   1. Every card shows the evidence it was derived from. A teacher is
//      being asked to make a judgement, and you cannot judge a bare score.
//   2. "Modify" is a real, separate outcome, not a cosmetic edit of an
//      approval. How often a teacher rewrites the AI rather than accepting
//      it is a finding, and it needs its own value in the column.
//   3. The reason box is offered on every decision including rejection.
//      A rejected recommendation with a reason is training signal; one
//      without is a shrug.

const KIND_LABEL: Record<RecommendationKind, string> = {
  practice: "Practice set",
  lesson: "Guided lesson",
  flashcards: "Spaced review",
  tutor: "Tutor session",
  diagnostic: "Diagnostic",
  outreach: "Personal outreach",
};

const PRIORITY_STYLE: Record<string, string> = {
  high: "border-destructive/30 bg-destructive/8 text-destructive",
  medium: "border-brand-orange/30 bg-brand-orange/10 text-brand-orange-foreground",
  low: "border-border bg-muted text-muted-foreground",
};

function pct(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

export function DecisionCenter({
  courseId,
  userId,
  learnerName,
}: {
  courseId: string;
  userId: string;
  learnerName: string;
}) {
  const { data, isLoading } = useRecommendations(courseId, userId);
  const generate = useGenerateRecommendations(courseId, userId);

  // Motion reports a real state change (DESIGN.md): the sparkle draws when
  // the teacher actually clicks Run analysis, not when the cursor happens
  // to pass over it. Attaching the ref switches the icon out of hover
  // mode into controlled mode, same as the learn-loop surfaces.
  const sparklesRef = useRef<SparklesIconHandle | null>(null);

  const all = data?.recommendations ?? [];
  const pending = all.filter((r) => r.status === "suggested");
  const decided = all.filter((r) => r.status !== "suggested");

  const runAnalysis = () => {
    sparklesRef.current?.startAnimation();
    generate.mutate(undefined, {
      onSuccess: (result) => {
        toast.success(
          result.generated === 0
            ? "Nothing to recommend right now"
            : `${result.generated} recommendation${result.generated === 1 ? "" : "s"} ready for your decision`,
          {
            description:
              result.source === "heuristic"
                ? "Generated from mastery state directly — the model was unavailable, so these are the deterministic fallback."
                : "Kala analysed this learner's twin. Nothing reaches them until you decide.",
          }
        );
      },
      onError: () =>
        toast.error("Could not run the analysis", {
          description: "Check your connection and try again.",
        }),
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-0 flex-1">
          {/* No icon here on purpose: the heading already says who is
              proposing, and the button directly below carries the sparkle.
              Two of the same mark on one line is noise, not meaning. */}
          <h3 className="font-display text-base font-semibold text-foreground">
            Kala recommends. You decide.
          </h3>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            Proposed next actions for {learnerName}, each with the evidence behind it. Nothing here
            reaches the learner until you approve or modify it.
          </p>
        </div>
        <Button
          variant="orange"
          size="sm"
          onClick={runAnalysis}
          disabled={generate.isPending}
          onMouseEnter={() => sparklesRef.current?.startAnimation()}
          onMouseLeave={() => sparklesRef.current?.stopAnimation()}
          className="shrink-0"
        >
          {generate.isPending ? (
            <>
              <Spinner className="size-3.5" /> Analysing
            </>
          ) : (
            <>
              <SparklesIcon ref={sparklesRef} size={14} />{" "}
              {all.length === 0 ? "Run analysis" : "Re-run analysis"}
            </>
          )}
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : pending.length === 0 && decided.length === 0 ? (
        <div className="border border-dashed bg-card px-5 py-8 text-center">
          <p className="text-[13px] font-semibold text-foreground">No recommendations yet</p>
          <p className="mx-auto mt-1.5 max-w-md text-xs leading-relaxed text-muted-foreground">
            Run the analysis to have Kala read this learner's twin and propose next actions. It
            sends a pseudonym and mastery numbers to the model, never a name.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {pending.map((rec, index) => (
            <RecommendationCard
              key={rec.id}
              rec={rec}
              courseId={courseId}
              userId={userId}
              index={index + 1}
              defaultOpen={index === 0}
            />
          ))}

          {decided.length > 0 ? (
            <Collapsible>
              <CollapsibleTrigger className="flex w-full items-center gap-2 border-t pt-3 text-left text-[11.5px] font-semibold uppercase tracking-[0.05em] text-brand-slate hover:text-foreground">
                Decision history
                <span className="rounded-full bg-muted px-1.5 font-mono text-[10.5px] font-bold text-muted-foreground">
                  {decided.length}
                </span>
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 space-y-1.5">
                {decided.map((rec) => (
                  <DecidedRow key={rec.id} rec={rec} />
                ))}
              </CollapsibleContent>
            </Collapsible>
          ) : null}
        </div>
      )}
    </div>
  );
}

function RecommendationCard({
  rec,
  courseId,
  userId,
  index,
  defaultOpen,
}: {
  rec: Recommendation;
  courseId: string;
  userId: string;
  index: number;
  defaultOpen: boolean;
}) {
  const decide = useDecideRecommendation(courseId, userId);
  const [open, setOpen] = useState(defaultOpen);
  const [choice, setChoice] = useState<"approved" | "modified" | "rejected" | null>(null);
  const [title, setTitle] = useState(rec.title);
  const [kind, setKind] = useState<RecommendationKind>(rec.kind);
  const [note, setNote] = useState("");
  const [learnerNote, setLearnerNote] = useState("");

  // The decision icons draw on hover over the BUTTON and on click — the
  // animation reports the choice being made, same as the learn-loop
  // surfaces. Attaching the refs switches them to controlled mode, so
  // hover is forwarded explicitly rather than native: startAnimation on
  // enter, stopAnimation on leave, and again on click. The evidence rows
  // below are the exception — status indicators must not wiggle on hover
  // (the audit called this out; "needs support" should not read as
  // playful), so they keep a static ref that never animates.
  const checkRef = useRef<CheckIconHandle | null>(null);
  const zapRef = useRef<ZapHandle | null>(null);
  const xRef = useRef<XIconHandle | null>(null);
  const staticCheckRef = useRef<CheckIconHandle | null>(null);

  const submit = () => {
    if (!choice) return;
    decide.mutate(
      {
        recId: rec.id,
        status: choice,
        title: choice === "modified" ? title : undefined,
        kind: choice === "modified" ? kind : undefined,
        decisionNote: note.trim() || undefined,
        instructorNote: choice === "rejected" ? undefined : learnerNote.trim() || undefined,
      },
      {
        onSuccess: () => {
          if (choice === "rejected") {
            toast("Recommendation declined", {
              description: "It stays in the decision history and never reaches the learner.",
            });
          } else {
            toast.success(
              choice === "modified" ? "Approved with your edits" : "Approved and assigned",
              {
                description: `"${choice === "modified" ? title : rec.title}" is now in the learner's plan.`,
              }
            );
          }
        },
        onError: () =>
          toast.error("Could not record your decision", {
            description: "Nothing was assigned. Try again.",
          }),
      }
    );
  };

  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      className={cn("border bg-card", open && "ring-1 ring-brand-orange/20")}
    >
      <CollapsibleTrigger className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-accent/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
        <span className="grid size-6 shrink-0 place-items-center rounded-[3px] bg-brand-slate font-mono text-[11px] font-bold text-background">
          {index}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13.5px] font-semibold text-foreground">{rec.title}</p>
          <p className="mt-0.5 font-mono text-[10.5px] uppercase tracking-wide text-muted-foreground">
            {KIND_LABEL[rec.kind]}
            {rec.skillName ? ` · ${rec.skillName}` : ""}
            {rec.expectedGain ? ` · +${Math.round(rec.expectedGain * 100)}% readiness` : ""}
          </p>
        </div>
        <span
          className={cn(
            "shrink-0 rounded-full border px-2 py-0.5 text-[10.5px] font-semibold capitalize",
            PRIORITY_STYLE[rec.priority]
          )}
        >
          {rec.priority} priority
        </span>
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div className="space-y-4 border-t px-4 py-4">
          {rec.rationale ? (
            <div>
              <p className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-brand-slate">
                Why
              </p>
              <p className="mt-1 text-[12.5px] leading-relaxed text-foreground/80">
                {rec.rationale}
              </p>
            </div>
          ) : null}

          <div className="flex flex-wrap gap-4">
            {rec.evidence.length > 0 ? (
              <div className="min-w-0 flex-1">
                <p className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-brand-slate">
                  Evidence
                </p>
                <ul className="mt-1.5 space-y-1">
                  {rec.evidence.map((e, i) => (
                    <li key={i} className="flex items-start gap-2 text-[12px]">
                      <CheckIcon
                        ref={staticCheckRef}
                        size={13}
                        className="mt-0.5 shrink-0 text-brand-green"
                        aria-hidden
                      />
                      <span className="text-foreground/80">
                        {e.label}
                        {e.detail ? (
                          <span className="ml-1 font-mono text-muted-foreground">{e.detail}</span>
                        ) : null}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div className="flex shrink-0 gap-2">
              <div className="border bg-muted/40 px-3 py-2 text-center">
                <p className="font-display text-lg font-semibold tabular-nums text-foreground">
                  {pct(rec.confidence)}
                </p>
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  Confidence
                </p>
              </div>
              <div className="border bg-muted/40 px-3 py-2 text-center">
                <p className="font-display text-lg font-semibold tabular-nums text-foreground">
                  {rec.expectedGain === null ? "—" : `+${Math.round(rec.expectedGain * 100)}%`}
                </p>
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  Est. gain
                </p>
              </div>
            </div>
          </div>

          {/* The decision itself. Three outcomes, each a real branch. */}
          <div className="border-t pt-4">
            <p className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-brand-slate">
              Your decision
            </p>
            <div className="mt-2 grid grid-cols-3 gap-2">
              <DecisionButton
                active={choice === "approved"}
                tone="green"
                icon={<CheckIcon ref={checkRef} size={14} />}
                label="Approve"
                onIconPlay={() => checkRef.current?.startAnimation()}
                onIconEnter={() => checkRef.current?.startAnimation()}
                onIconLeave={() => checkRef.current?.stopAnimation()}
                onClick={() => setChoice("approved")}
              />
              <DecisionButton
                active={choice === "modified"}
                tone="orange"
                icon={<ZapIcon ref={zapRef} size={14} />}
                label="Modify"
                onIconPlay={() => zapRef.current?.startAnimation()}
                onIconEnter={() => zapRef.current?.startAnimation()}
                onIconLeave={() => zapRef.current?.stopAnimation()}
                onClick={() => setChoice("modified")}
              />
              <DecisionButton
                active={choice === "rejected"}
                tone="red"
                icon={<XIcon ref={xRef} size={14} />}
                label="Decline"
                onIconPlay={() => xRef.current?.startAnimation()}
                onIconEnter={() => xRef.current?.startAnimation()}
                onIconLeave={() => xRef.current?.stopAnimation()}
                onClick={() => setChoice("rejected")}
              />
            </div>

            {choice === "modified" ? (
              <div className="mt-3 space-y-2.5 border-l-[3px] border-brand-orange bg-brand-orange/5 p-3">
                <div>
                  <Label htmlFor={`title-${rec.id}`} className="text-[11px]">
                    Rewrite the action
                  </Label>
                  <Input
                    id={`title-${rec.id}`}
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="mt-1 h-8 text-[13px]"
                  />
                </div>
                <div>
                  <Label htmlFor={`kind-${rec.id}`} className="text-[11px]">
                    Change the activity
                  </Label>
                  <Select value={kind} onValueChange={(v) => setKind(v as RecommendationKind)}>
                    <SelectTrigger id={`kind-${rec.id}`} className="mt-1 h-8 text-[13px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(Object.keys(KIND_LABEL) as RecommendationKind[]).map((k) => (
                        <SelectItem key={k} value={k}>
                          {KIND_LABEL[k]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            ) : null}

            {choice ? (
              <div className="mt-3 space-y-2.5">
                <div>
                  <Label htmlFor={`note-${rec.id}`} className="text-[11px]">
                    Why {choice === "rejected" ? "you declined" : "you approved"} (optional, kept in
                    the audit trail)
                  </Label>
                  <Textarea
                    id={`note-${rec.id}`}
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    rows={2}
                    placeholder={
                      choice === "rejected"
                        ? "She already covered this in the lab on Tuesday."
                        : "Reinforce the fundamentals before we move on to the next module."
                    }
                    className="mt-1 text-[13px]"
                  />
                </div>
                {choice !== "rejected" ? (
                  <div>
                    <Label htmlFor={`learner-note-${rec.id}`} className="text-[11px]">
                      A note the learner will see (optional)
                    </Label>
                    <Input
                      id={`learner-note-${rec.id}`}
                      value={learnerNote}
                      onChange={(e) => setLearnerNote(e.target.value)}
                      placeholder="Take this before Thursday's session and bring your questions."
                      className="mt-1 h-8 text-[13px]"
                    />
                  </div>
                ) : null}
                <Button
                  variant={choice === "rejected" ? "outline" : "orange"}
                  size="sm"
                  className="w-full"
                  onClick={submit}
                  disabled={decide.isPending}
                >
                  {decide.isPending ? (
                    <>
                      <Spinner className="size-3.5" /> Recording
                    </>
                  ) : choice === "rejected" ? (
                    "Confirm decline"
                  ) : (
                    "Confirm and assign to learner"
                  )}
                </Button>
              </div>
            ) : null}
          </div>

          <p className="border-t pt-3 font-mono text-[10.5px] text-muted-foreground">
            Proposed by {rec.source === "heuristic" ? "Kala's deterministic fallback" : rec.source ?? "Kala"} ·
            de-identified before the model call
          </p>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

function DecisionButton({
  active,
  tone,
  icon,
  label,
  onClick,
  onIconPlay,
  onIconEnter,
  onIconLeave,
}: {
  active: boolean;
  tone: "green" | "orange" | "red";
  icon: ReactNode;
  label: string;
  onClick: () => void;
  onIconPlay?: () => void;
  onIconEnter?: () => void;
  onIconLeave?: () => void;
}) {
  const activeClass = {
    green: "border-brand-green bg-brand-green/10 text-brand-green",
    orange: "border-brand-orange bg-brand-orange/10 text-brand-orange-foreground",
    red: "border-destructive bg-destructive/8 text-destructive",
  }[tone];

  return (
    <button
      type="button"
      onClick={() => {
        onIconPlay?.();
        onClick();
      }}
      onMouseEnter={onIconEnter}
      onMouseLeave={onIconLeave}
      aria-pressed={active}
      className={cn(
        "flex items-center justify-center gap-1.5 rounded-md border px-3 py-2 text-[12.5px] font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        active ? activeClass : "border-border text-muted-foreground hover:bg-accent"
      )}
    >
      {icon}
      {label}
    </button>
  );
}

function DecidedRow({ rec }: { rec: Recommendation }) {
  const tone =
    rec.status === "rejected"
      ? "text-muted-foreground"
      : rec.status === "completed"
        ? "text-brand-green"
        : "text-foreground";
  return (
    <div className="flex items-start gap-2.5 border-l-2 border-border py-1.5 pl-3">
      <span
        className={cn(
          "mt-1 size-1.5 shrink-0 rounded-full",
          rec.status === "rejected" ? "bg-border" : "bg-brand-green"
        )}
        aria-hidden
      />
      <div className="min-w-0 flex-1">
        <p className={cn("truncate text-[12.5px]", tone)}>
          {rec.title}
          <span className="ml-1.5 font-mono text-[10.5px] uppercase text-muted-foreground">
            {rec.status}
          </span>
        </p>
        {rec.decisionNote ? (
          <p className="mt-0.5 text-[11.5px] italic leading-relaxed text-muted-foreground">
            “{rec.decisionNote}”
          </p>
        ) : null}
      </div>
    </div>
  );
}
