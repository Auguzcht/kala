/** A wildcard observes a hub route selected by the preceding tour click. */
export function matchesTourRoute(pathname: string, route: string): boolean {
  return route.endsWith("/*") ? pathname.startsWith(route.slice(0, -1)) : pathname === route;
}
