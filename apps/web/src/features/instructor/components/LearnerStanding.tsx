import type {
  AtRiskFlag,
  LearnerRecordData,
  LearnerStatus,
} from "@/features/instructor";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

// The standing block shared by the triage sheet and the full record page:
// identity, why-flagged (if any), and the four comparison numbers. This is
// the judgement-relevant material — a teacher who reads nothing else still
// knows where this learner sits relative to the cohort and how long since
// they showed up.
//
// Deliberately presentational: it receives the record and flag from its
// consumer (which owns the queries and the de-identify state), so the two
// surfaces can never drift — the sheet and the full page render the exact
// same header even though they deliberately differ below it.

const STATUS_META: Record<LearnerStatus, { label: string; className: string }> = {
  "needs-support": {
    label: "Needs support",
    className: "border-destructive/30 bg-destructive/8 text-destructive",
  },
  "not-started": {
    label: "Not started",
    className: "border-border bg-muted text-muted-foreground",
  },
  developing: {
    label: "Developing",
    className: "border-brand-orange/30 bg-brand-orange/10 text-brand-orange-foreground",
  },
  "on-track": {
    label: "On track",
    className: "border-brand-green/30 bg-brand-green/10 text-brand-green",
  },
};

function pct(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `${Math.round(value * 100)}%`;
}

export function LearnerStanding({
  userId,
  record,
  flag,
  deidentified,
  onDeidentifiedChange,
}: {
  userId: string;
  record: LearnerRecordData;
  flag?: AtRiskFlag;
  deidentified: boolean;
  onDeidentifiedChange: (v: boolean) => void;
}) {
  const r = record;
  const name = deidentified ? r.pseudonym : r.displayName;
  const status = STATUS_META[r.status];

  return (
    <div className="space-y-5" id="tour-standing">
      {/* Identity + standing. The header carries the judgement-relevant
          facts, so a teacher who reads nothing else still knows where this
          learner sits and how long since they showed up. */}
      <div className="flex flex-wrap items-start gap-4 border bg-card p-5">
        <span className="grid size-12 shrink-0 place-items-center rounded-full bg-brand-slate font-display text-base font-bold text-background">
          {deidentified ? "••" : r.initials}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-display text-xl font-semibold text-foreground">{name}</h2>
            <span
              className={cn(
                "rounded-full border px-2 py-0.5 text-[11px] font-semibold",
                status.className
              )}
            >
              {status.label}
            </span>
          </div>
          <p className="mt-1 font-mono text-[11.5px] text-muted-foreground">
            {r.evidenceCount} evidence events · {r.attempts} attempts ·{" "}
            {r.daysInactive === null
              ? "never active"
              : r.daysInactive === 0
                ? "active today"
                : `last active ${r.daysInactive}d ago`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id={`deid-${userId}`}
            checked={deidentified}
            onCheckedChange={onDeidentifiedChange}
          />
          <Label htmlFor={`deid-${userId}`} className="text-[11.5px] text-muted-foreground">
            De-identify
          </Label>
        </div>
      </div>

      {flag ? (
        <div className="border-l-[3px] border-destructive bg-destructive/5 p-3.5">
          <p className="text-[11px] font-bold uppercase tracking-[0.05em] text-destructive">
            Why this learner is flagged
          </p>
          <p className="mt-1 text-[12.5px] leading-relaxed text-foreground/80">{flag.reason}</p>
        </div>
      ) : null}

      {/* Standing strip: the four numbers that only exist by comparison. */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat
          label="Readiness"
          value={pct(r.readiness)}
          sub={
            r.cohortReadiness !== null && r.readiness !== null
              ? `${r.readiness >= r.cohortReadiness ? "+" : ""}${Math.round(
                  (r.readiness - r.cohortReadiness) * 100
                )} pts vs class`
              : "no class average yet"
          }
        />
        <Stat
          label="Class standing"
          value={r.percentile === null ? "—" : `${r.percentile}th`}
          sub={r.cohortReadiness === null ? "—" : `class at ${pct(r.cohortReadiness)}`}
        />
        <Stat
          label="Accuracy"
          value={pct(r.accuracy)}
          sub={`${r.hintsUsed} hints used`}
        />
        <Stat
          label="Momentum"
          value={
            r.momentum === null
              ? "—"
              : `${r.momentum > 0 ? "+" : ""}${Math.round(r.momentum * 100)} pts`
          }
          sub="last 10 vs previous 10"
          tone={r.momentum === null ? "neutral" : r.momentum >= 0 ? "green" : "red"}
        />
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
  tone = "neutral",
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "neutral" | "green" | "red";
}) {
  return (
    <div className="border bg-card px-4 py-3">
      <p className="text-[10.5px] font-semibold uppercase tracking-[0.05em] text-brand-slate">
        {label}
      </p>
      <p
        className={cn(
          "mt-1 font-display text-xl font-semibold tabular-nums",
          tone === "green" && "text-brand-green",
          tone === "red" && "text-destructive",
          tone === "neutral" && "text-foreground"
        )}
      >
        {value}
      </p>
      {sub ? <p className="mt-0.5 font-mono text-[10.5px] text-muted-foreground">{sub}</p> : null}
    </div>
  );
}
