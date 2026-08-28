import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { ArrowRightIcon } from "@/components/ui/arrow-right";
import { FileTextIcon } from "@/components/ui/file-text";
import { GraduationCapIcon } from "@/components/ui/graduation-cap";
import { LayersIcon } from "@/components/ui/layers";
import { MessageSquareIcon } from "@/components/ui/message-square";
import { ZapIcon } from "@/components/ui/zap";
import { useSession } from "@/lib/auth/AuthProvider";
import { useCourse } from "@/features/courses";
import { useNextUp, useTwin } from "@/features/twin";
import { MasteryBand } from "@/components/kala";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export const Route = createFileRoute("/course/")({
  component: WorkspaceHome,
});

type QuickIcon = typeof FileTextIcon;
const QUICK_LINKS: { label: string; copy: string; icon: QuickIcon; iconBg: string; to: string }[] = [
  { label: "Diagnostic", copy: "Build your baseline for this course.", icon: FileTextIcon, iconBg: "bg-brand-slate", to: "/course/diagnostic" },
  { label: "Lessons", copy: "Step-by-step walkthroughs with checks.", icon: GraduationCapIcon, iconBg: "bg-brand-gold", to: "/course/lessons" },
  { label: "Practice", copy: "Quick sets tuned to your twin.", icon: ZapIcon, iconBg: "bg-brand-orange", to: "/course/practice" },
  { label: "Flashcards", copy: "Spaced review of key terms.", icon: LayersIcon, iconBg: "bg-brand-green", to: "/course/flashcards" },
  { label: "Tutor", copy: "Ask Kala to work through it with you.", icon: MessageSquareIcon, iconBg: "bg-brand-gold", to: "/course/tutor" },
];

function first(name?: string): string {
  return name ? name.split(/\s+/)[0] : "there";
}

function WorkspaceHome() {
  const session = useSession();
  const navigate = useNavigate();
  const courseId = session?.courseId ?? "";
  const { data: course } = useCourse(courseId);
  const { data: nextUp, isLoading: nextLoading } = useNextUp(courseId);
  const { data: twin, isLoading: twinLoading } = useTwin(courseId);

  const next = nextUp?.next ?? null;
  const evidenceCount = twin?.evidence.length ?? 0;
  const skills = twin?.skills ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Welcome back, {first(session?.displayName)}
        </h1>
        {course ? (
          <p className="mt-1 text-sm text-muted-foreground">{course.title}</p>
        ) : (
          <Skeleton className="mt-2 h-4 w-56" />
        )}
      </div>

      {/* Next up — the one recommendation, the primary action */}
      {nextLoading ? (
        <Skeleton className="h-28 w-full" />
      ) : next ? (
        <div className="flex items-center justify-between gap-6 bg-primary px-7 py-6">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.06em] text-brand-gold">
              Next up
            </p>
            <p className="mt-1.5 font-display text-lg font-semibold text-primary-foreground">
              Practice: {next.skillName}
            </p>
            <p className="mt-1 text-[13px] text-primary-foreground/70">{next.reason}</p>
          </div>
          <Button
            variant="orange"
            onClick={() => navigate({ to: "/course/practice" })}
            className="shrink-0"
          >
            Start practice <ArrowRightIcon size={16} />
          </Button>
        </div>
      ) : (
        <div className="flex items-center justify-between gap-6 border border-dashed bg-card px-7 py-6">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.06em] text-brand-slate">
              Next up
            </p>
            <p className="mt-1.5 font-display text-lg font-semibold text-foreground">
              No skills mapped yet
            </p>
            <p className="mt-1 text-[13px] text-muted-foreground">
              Course content hasn't been tagged to the skill taxonomy yet. Check back after the
              ingest pass.
            </p>
          </div>
        </div>
      )}

      {/* Quick links */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {QUICK_LINKS.map(({ label, copy, icon: Icon, iconBg, to }) => (
          <button
            key={label}
            type="button"
            onClick={() => navigate({ to })}
            className="group border bg-card p-4 text-left transition-colors hover:bg-accent/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <div className={`mb-3 grid size-8 place-items-center rounded-[4px] ${iconBg}`}>
              <Icon size={16} className="text-background" />
            </div>
            <div className="text-sm font-semibold text-foreground group-hover:underline">{label}</div>
            <div className="mt-1 text-xs leading-relaxed text-muted-foreground">{copy}</div>
          </button>
        ))}
      </div>

      {/* Twin snapshot + baseline card */}
      <div className="flex flex-wrap gap-5">
        <div className="min-w-72 flex-1 border bg-card p-5">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-[0.05em] text-brand-slate">
              Your twin, at a glance
            </span>
            <button
              type="button"
              onClick={() => navigate({ to: "/course/twin" })}
              className="text-xs font-semibold text-brand-orange hover:underline"
            >
              View full twin →
            </button>
          </div>
          {twinLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : skills.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground">
              No skills mapped for this course yet.
            </p>
          ) : (
            <div className="divide-y divide-border">
              {skills.slice(0, 5).map((s) => (
                <div key={s.skillId} className="flex items-center gap-3 py-2.5">
                  <span className="min-w-0 flex-1 truncate text-[13px] text-foreground">{s.name}</span>
                  <MasteryBand band={s.band} />
                </div>
              ))}
            </div>
          )}
        </div>

        {evidenceCount === 0 ? (
          <div className="flex w-full max-w-[300px] shrink-0 flex-col items-center justify-center gap-3 border bg-card p-6 text-center">
            <img src="/assets/kala-mark.png" alt="" className="size-12 object-contain opacity-80" />
            <div>
              <p className="text-[13.5px] font-semibold text-foreground">Building your baseline</p>
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                Your twin fills in as you practice. A few sessions and every skill will have a real
                estimate.
              </p>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
