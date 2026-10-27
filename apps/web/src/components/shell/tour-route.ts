/** Match concrete routes, parameter segments and a trailing hub wildcard. */
export function matchesTourRoute(pathname: string, route: string): boolean {
  const actual = pathname.split("/").filter(Boolean);
  const expected = route.split("/").filter(Boolean);
  const wildcard = expected.at(-1) === "*";
  if ((!wildcard && actual.length !== expected.length) || (wildcard && actual.length < expected.length)) return false;
  return expected.every((segment, index) =>
    segment === "*" && index === expected.length - 1 ||
    (segment.startsWith("$") ? Boolean(actual[index]) && !actual[index].startsWith("$") : segment === actual[index])
  );
}

/** Only these read/navigation controls may be clicked by the runner. */
export function isTourUiClick(selector: string): boolean {
  return [
    "#tour-roster-first-row", "#tour-roster-filter", "[data-slot='sheet-close']",
    "#tour-tab-heatmap", "#tour-skill-review-trigger", "#tour-at-risk-first-flag",
    "#tour-tab-decide", "#tour-tab-mastery", "#tour-tab-activity",
  ].includes(selector);
}
