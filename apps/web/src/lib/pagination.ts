// Shared pagination helper. Page-number window for a pager: first, last,
// current ±1, and null standing in for an ellipsis between the gaps — never
// more than ~7 links regardless of total page count. Used by the roster
// table and the skill-review queue, which both render 8–10 rows per page
// but can grow to dozens of pages on a big course.
//
// Returns page indices (0-based); null items render as an ellipsis.
export function pageWindow(current: number, pages: number): (number | null)[] {
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
