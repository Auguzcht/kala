import { useMemo, useState } from "react";
import { useRoster } from "@/features/instructor";
import type { LearnerStatus, RosterRow } from "@/features/instructor";
import { CornerBrackets, MasteryBand } from "@/components/kala";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/shared/EmptyState";
import { cn } from "@/lib/utils";

// The class roster. This is the screen a teacher opens first, so it shows
// the roster as a roster: real names, sortable, searchable, paginated,
// with the numbers that decide who they talk to today.
//
// Two decisions worth naming.
//
// Real names by default. The instructor is the teacher of record; this
// roster is already in their gradebook. De-identification (CLAUDE.md 4)
// governs what leaves for a model or a researcher, and it still holds —
// the prescriber is handed pseudonyms and never a name. The "De-identify"
// switch flips the whole table to pseudonyms for screen-sharing and
// recording, which is also the honest way to demo this on camera.
//
// Students only. The backend requires role='student' on both the
// enrollment and the user, so co-teachers and admins never appear here as
// learners sitting at 0% mastery.

const PAGE_SIZE = 10;

const STATUS_META: Record<LearnerStatus, { label: string; dot: string; text: string }> = {
  "needs-support": {
    label: "Needs support",
    dot: "bg-destructive",
    text: "text-destructive",
  },
  "not-started": {
    label: "Not started",
    dot: "bg-brand-slate",
    text: "text-muted-foreground",
  },
  developing: { label: "Developing", dot: "bg-brand-orange", text: "text-foreground" },
  "on-track": { label: "On track", dot: "bg-brand-green", text: "text-foreground" },
};

type SortKey = "status" | "name" | "readiness" | "accuracy" | "active";

function lastActiveLabel(row: RosterRow): string {
  if (row.daysInactive === null) return "never";
  if (row.daysInactive === 0) return "today";
  if (row.daysInactive === 1) return "yesterday";
  return `${row.daysInactive}d ago`;
}

function pct(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

export function RosterTable({
  courseId,
  onSelect,
  selectedUserId,
  filter,
  onFilterChange,
  deidentified,
}: {
  courseId: string;
  onSelect: (userId: string) => void;
  selectedUserId?: string | null;
  /** Controlled from the page so the "View all in roster" handoff from
   * AtRiskList and this table's own filter chips stay in sync. */
  filter: "all" | LearnerStatus;
  onFilterChange: (filter: "all" | LearnerStatus) => void;
  /** Controlled from the page so one switch covers this table and the
   * Needs support panel — flipping it in either place should not leave
   * the other showing a different identity mode. */
  deidentified: boolean;
}) {
  const { data, isLoading } = useRoster(courseId);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortKey>("status");
  const [page, setPage] = useState(0);


  const rows = useMemo(() => {
    const all = data?.students ?? [];
    const q = query.trim().toLowerCase();
    const filtered = all.filter((r) => {
      if (filter !== "all" && r.status !== filter) return false;
      if (!q) return true;
      return (
        r.displayName.toLowerCase().includes(q) ||
        r.pseudonym.toLowerCase().includes(q) ||
        (r.weakestSkillName ?? "").toLowerCase().includes(q)
      );
    });

    const rank: Record<LearnerStatus, number> = {
      "needs-support": 0,
      "not-started": 1,
      developing: 2,
      "on-track": 3,
    };
    const sorted = [...filtered];
    sorted.sort((a, b) => {
      switch (sort) {
        case "name":
          return a.displayName.localeCompare(b.displayName);
        case "readiness":
          return (b.readiness ?? -1) - (a.readiness ?? -1);
        case "accuracy":
          return (b.accuracy ?? -1) - (a.accuracy ?? -1);
        case "active":
          return (a.daysInactive ?? 9999) - (b.daysInactive ?? 9999);
        default:
          return rank[a.status] - rank[b.status] || (a.readiness ?? -1) - (b.readiness ?? -1);
      }
    });
    return sorted;
  }, [data, query, filter, sort]);

  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const safePage = Math.min(page, pages - 1);
  const slice = rows.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const total = data?.students.length ?? 0;

  return (
    <div className="relative border bg-card">
      <CornerBrackets />

      <div className="flex flex-wrap items-center gap-3 border-b px-5 py-4">
        <div className="min-w-0">
          <h2 className="font-display text-[19px] font-semibold text-foreground">Class roster</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {total} enrolled {total === 1 ? "student" : "students"} · sorted by who needs you first
          </p>
        </div>

        <div className="flex-1" />

        <Input
          id="tour-roster-search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(0);
          }}
          placeholder="Search name or skill"
          className="h-8 w-52 text-[13px]"
          aria-label="Search the roster"
        />

        <ToggleGroup
          id="tour-roster-filter"
          type="single"
          value={filter}
          onValueChange={(v) => {
            if (v) onFilterChange(v as "all" | LearnerStatus);
            setPage(0);
          }}
          variant="outline"
          size="sm"
        >
          <ToggleGroupItem value="all" className="px-2.5 text-[11.5px]">
            All
          </ToggleGroupItem>
          <ToggleGroupItem value="needs-support" className="px-2.5 text-[11.5px]">
            Needs support
          </ToggleGroupItem>
          <ToggleGroupItem value="not-started" className="px-2.5 text-[11.5px]">
            Not started
          </ToggleGroupItem>
          <ToggleGroupItem value="on-track" className="px-2.5 text-[11.5px]">
            On track
          </ToggleGroupItem>
        </ToggleGroup>
      </div>

      {rows.length === 0 ? (
        <div className="px-5 py-8">
          <EmptyState
            title={total === 0 ? "No students enrolled yet" : "No one matches that filter"}
            description={
              total === 0
                ? "The roster syncs from your LMS. Once students launch Kala and start the diagnostic, they appear here."
                : "Clear the search or pick a different filter to see the rest of the class."
            }
          />
        </div>
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <SortableHead label="Learner" k="name" sort={sort} setSort={setSort} />
                <SortableHead label="Status" k="status" sort={sort} setSort={setSort} />
                <SortableHead label="Readiness" k="readiness" sort={sort} setSort={setSort} />
                <SortableHead label="Accuracy" k="accuracy" sort={sort} setSort={setSort} />
                <TableHead className="text-[11px] uppercase tracking-[0.05em]">
                  Weakest skill
                </TableHead>
                <SortableHead label="Last active" k="active" sort={sort} setSort={setSort} />
              </TableRow>
            </TableHeader>
            <TableBody>
              {slice.map((r, i) => {
                const meta = STATUS_META[r.status];
                return (
                  <TableRow
                    key={r.userId}
                    id={i === 0 ? "tour-roster-first-row" : undefined}
                    onClick={() => onSelect(r.userId)}
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelect(r.userId);
                      }
                    }}
                    className={cn(
                      "cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      selectedUserId === r.userId && "bg-accent/60"
                    )}
                  >
                    <TableCell>
                      <div className="flex items-center gap-2.5">
                        <span className="grid size-7 shrink-0 place-items-center rounded-full bg-brand-slate text-[10.5px] font-bold text-background">
                          {deidentified ? "••" : r.initials}
                        </span>
                        <div className="min-w-0">
                          <p className="truncate text-[13px] font-semibold text-foreground">
                            {deidentified ? r.pseudonym : r.displayName}
                          </p>
                          <p className="font-mono text-[10.5px] text-muted-foreground">
                            {r.skillsWithEvidence}/{r.skillsTotal} skills measured
                          </p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className={cn("flex items-center gap-1.5 text-[12px]", meta.text)}>
                        <span className={cn("size-1.5 rounded-full", meta.dot)} aria-hidden />
                        {meta.label}
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-16 overflow-hidden rounded-full bg-muted">
                          <div
                            className="h-full rounded-full bg-brand-gold"
                            style={{ width: `${Math.round((r.readiness ?? 0) * 100)}%` }}
                          />
                        </div>
                        <span className="font-mono text-xs tabular-nums text-muted-foreground">
                          {pct(r.readiness)}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-xs tabular-nums text-muted-foreground">
                      {pct(r.accuracy)}
                      <span className="ml-1 text-[10px]">({r.attempts})</span>
                    </TableCell>
                    <TableCell className="max-w-[240px]">
                      {r.weakestSkillName ? (
                        // `truncate` only works on a flex child once the
                        // child can actually shrink — a bare flex item
                        // defaults to min-width:auto, which refuses to
                        // shrink below its content's natural width no
                        // matter what the parent's max-width says. That's
                        // what let one long skill name (this course has a
                        // genuinely long one) blow the whole table wider
                        // than the viewport instead of scrolling or
                        // wrapping cleanly. `min-w-0` on both the flex
                        // container and the truncating span is what makes
                        // the cap in the TableCell above actually bite.
                        <div className="flex min-w-0 items-center gap-2">
                          <span
                            className="min-w-0 flex-1 truncate text-[12.5px] text-foreground"
                            title={r.weakestSkillName}
                          >
                            {r.weakestSkillName}
                          </span>
                          <MasteryBand band={r.band} />
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {lastActiveLabel(r)}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          {/* Footer always shows the result range; pager appears once
              there is more than one page. The page links are windowed —
              first, last, current ±1, ellipsis between — so a hundred-
              student class doesn't render a hundred links. */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-t px-5 py-3">
            <p className="font-mono text-[11px] text-muted-foreground">
              {rows.length === 0
                ? "0 results"
                : `${safePage * PAGE_SIZE + 1}–${Math.min(
                    rows.length,
                    (safePage + 1) * PAGE_SIZE
                  )} of ${rows.length}`}
            </p>
            {pages > 1 ? (
              <Pagination>
                <PaginationContent>
                  <PaginationItem>
                    <PaginationPrevious
                      onClick={() => setPage((p) => Math.max(0, p - 1))}
                      className={safePage === 0 ? "pointer-events-none opacity-40" : undefined}
                    />
                  </PaginationItem>
                  {pageWindow(safePage, pages).map((item, i) =>
                    item === null ? (
                      <PaginationItem key={`gap-${i}`}>
                        <span className="px-0.5 font-mono text-xs text-muted-foreground">…</span>
                      </PaginationItem>
                    ) : (
                      <PaginationItem key={item}>
                        <PaginationLink isActive={item === safePage} onClick={() => setPage(item)}>
                          {item + 1}
                        </PaginationLink>
                      </PaginationItem>
                    )
                  )}
                  <PaginationItem>
                    <PaginationNext
                      onClick={() => setPage((p) => Math.min(pages - 1, p + 1))}
                      className={
                        safePage >= pages - 1 ? "pointer-events-none opacity-40" : undefined
                      }
                    />
                  </PaginationItem>
                </PaginationContent>
              </Pagination>
            ) : null}
          </div>
        </>
      )}
    </div>
  );
}

// Page-number window for the pager: first, last, current ±1, and ellipsis
// for the gaps — never more than ~7 links regardless of class size. Returns
// page indices (0-based) with null standing in for the ellipsis.
function pageWindow(current: number, pages: number): (number | null)[] {
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i);
  const items: (number | null)[] = [0];
  const start = Math.max(1, current - 1);
  const end = Math.min(pages - 2, current + 1);
  if (start > 1) items.push(null);
  for (let i = start; i <= end; i++) items.push(i);
  if (end < pages - 2) items.push(null);
  items.push(pages - 1);
  return items;
}

function SortableHead({
  label,
  k,
  sort,
  setSort,
}: {
  label: string;
  k: SortKey;
  sort: SortKey;
  setSort: (k: SortKey) => void;
}) {
  return (
    <TableHead className="text-[11px] uppercase tracking-[0.05em]">
      <button
        type="button"
        onClick={() => setSort(k)}
        className={cn(
          "inline-flex items-center gap-1 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          sort === k && "text-foreground"
        )}
      >
        {label}
        {sort === k ? <span aria-hidden>↓</span> : null}
      </button>
    </TableHead>
  );
}
