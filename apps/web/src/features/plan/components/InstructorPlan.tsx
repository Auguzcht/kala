import { useNavigate } from "@tanstack/react-router";
import { usePlan } from "@/features/plan/hooks/use-plan";
import type { PlanItemKind } from "@/features/plan/schema/plan.schema";
import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { CheckIcon } from "@/components/ui/check";
import { GraduationCapIcon } from "@/components/ui/graduation-cap";
import { LayersIcon } from "@/components/ui/layers";
import { MessageSquareIcon } from "@/components/ui/message-square";
import { FileTextIcon } from "@/components/ui/file-text";
import { ZapIcon } from "@/components/ui/zap";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

// "From your instructor" — the visible proof that a human is in this loop.
//
// This card is the payoff for everything the instructor surface does. A
// learner opening their workspace sees actions their teacher personally
// approved, in their teacher's words, with a path straight into the work.
// Without it the human-in-the-loop story is a claim the instructor screen
// makes about itself; with it, the loop closes somewhere the learner can
// see.
//
// Deliberately absent: any AI framing. No "Kala is 84% confident", no
// priority badges shouting HIGH, no risk language. The learner is told
// what to do and who asked, and the ordering carries the priority.

type Icon = typeof ZapIcon;

const KIND_META: Record<PlanItemKind, { label: string; icon: Icon; to: string; bg: string }> = {
  practice: { label: "Practice", icon: ZapIcon, to: "/course/practice", bg: "bg-brand-orange" },
  lesson: {
    label: "Guided lesson",
    icon: GraduationCapIcon,
    to: "/course/lessons",
    bg: "bg-brand-gold",
  },
  flashcards: { label: "Review", icon: LayersIcon, to: "/course/flashcards", bg: "bg-brand-green" },
  tutor: { label: "Tutor", icon: MessageSquareIcon, to: "/course/tutor", bg: "bg-brand-gold" },
  diagnostic: {
    label: "Diagnostic",
    icon: FileTextIcon,
    to: "/course/diagnostic",
    bg: "bg-brand-slate",
  },
  // Outreach is a conversation the instructor initiates. There is nowhere
  // to send the learner, so the row renders without a CTA rather than
  // pretending there is a button for "your teacher wants to talk".
  outreach: { label: "From your instructor", icon: MessageSquareIcon, to: "", bg: "bg-brand-slate" },
};

export function InstructorPlan({ courseId }: { courseId: string }) {
  const { data, isLoading } = usePlan(courseId);
  const navigate = useNavigate();

  if (isLoading) return <Skeleton className="h-40 w-full" />;

  const items = data?.plan ?? [];
  // An empty plan is not a broken screen: most of the time a teacher has
  // simply not assigned anything, and the learner's own "Next up" already
  // tells them what to do. Render nothing rather than an empty shell.
  if (items.length === 0) return null;

  const open = items.filter((i) => i.status !== "completed");
  const done = items.filter((i) => i.status === "completed");

  return (
    <div className="border bg-card">
      <div className="flex items-center gap-2 border-b bg-brand-slate/5 px-5 py-3">
        <span className="size-1.5 rounded-full bg-brand-orange" aria-hidden />
        <h2 className="font-display text-[15px] font-semibold text-foreground">
          From your instructor
        </h2>
        <span className="rounded-full bg-brand-orange/15 px-2 py-0.5 font-mono text-[10.5px] font-bold text-brand-orange-foreground">
          {open.length}
        </span>
        <div className="flex-1" />
        <p className="hidden text-[11px] text-muted-foreground sm:block">
          Reviewed and approved by your instructor
        </p>
      </div>

      <div className="divide-y">
        {open.map((item) => {
          const meta = KIND_META[item.kind];
          const Icon = meta.icon;
          return (
            <div key={item.id} className="flex flex-wrap items-center gap-3 px-5 py-3.5">
              <span className={cn("grid size-8 shrink-0 place-items-center rounded-[4px]", meta.bg)}>
                <Icon size={15} className="text-background" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-[13.5px] font-semibold text-foreground">{item.title}</p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">
                  {meta.label}
                  {item.skillName ? ` · ${item.skillName}` : ""}
                </p>
                {item.instructorNote ? (
                  <p className="mt-1.5 border-l-2 border-brand-gold pl-2.5 text-[12px] italic leading-relaxed text-foreground/75">
                    {item.instructorNote}
                  </p>
                ) : null}
              </div>
              {meta.to ? (
                <Button
                  variant="outline"
                  size="sm"
                  className="shrink-0"
                  onClick={() => navigate({ to: meta.to })}
                >
                  Start <ArrowRightIcon size={14} />
                </Button>
              ) : null}
            </div>
          );
        })}

        {done.map((item) => (
          <div key={item.id} className="flex items-center gap-3 px-5 py-2.5 opacity-60">
            <span className="grid size-8 shrink-0 place-items-center rounded-[4px] bg-muted">
              <CheckIcon size={15} className="text-brand-green" />
            </span>
            <p className="min-w-0 flex-1 truncate text-[13px] text-muted-foreground line-through">
              {item.title}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
