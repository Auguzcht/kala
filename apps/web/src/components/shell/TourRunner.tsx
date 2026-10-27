import { toast } from "sonner";
import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { driver } from "driver.js";
import { useLocation, useNavigate } from "@tanstack/react-router";
import { useReducedMotion } from "motion/react";
import { useUI } from "@/stores/ui-store";
import { useSession } from "@/lib/auth/AuthProvider";
import { isTourUiClick, matchesTourRoute } from "@/components/shell/tour-route";
import type { TourStepConfig } from "@/components/shell/student-tour";
import type { Roster } from "@/features/instructor";
import { progressLearnerSearch, progressTourLearner } from "@/components/shell/tour-learner";

export type TourPresentationStep = TourStepConfig & {
  explainOnly?: boolean;
  fallbackDescription?: string;
  progressLearner?: "select" | "record";
  activateSelector?: string;
};

type Visit = { index: number; pathname: string; search: Record<string, unknown> };

function visibleTarget(selector: string): Element | undefined {
  return [...document.querySelectorAll(selector)].find((element) => {
    const style = getComputedStyle(element);
    const box = element.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && box.width > 0 && box.height > 0;
  });
}

/** One validated target per driver instance; no unchecked in-page steps. */
export function TourRunner({ steps, dismissKey }: {
  steps: readonly TourPresentationStep[];
  dismissKey: (userId: string) => string;
}) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { pathname, search } = useLocation();
  const session = useSession();
  const instructor = session?.role === "instructor" || session?.role === "admin";
  const reduceMotion = useReducedMotion();
  const tourStep = useUI((state) => state.tourStep);
  const setTourStep = useUI((state) => state.setTourStep);
  const visits = useRef<Visit[]>([]);
  const routes = useRef<Record<string, string>>({});
  const rosterLearnerRoute = useRef<string | undefined>(undefined);
  const rosterLearnerCourse = useRef<string | undefined>(undefined);
  const restoreRoster = useRef<(() => void) | undefined>(undefined);
  const backwards = useRef(false);
  const notified = useRef(false);
  useEffect(() => () => restoreRoster.current?.(), []);
  useEffect(() => {
    if (!matchesTourRoute(pathname, "/class")) {
      restoreRoster.current?.();
      restoreRoster.current = undefined;
    }
  }, [pathname]);

  // Escape also works while waiting for a target or animating the overlay.
  useEffect(() => {
    if (tourStep === null) return;
    const close = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopPropagation();
      setTourStep(null);
    };
    window.addEventListener("keydown", close, true);
    return () => window.removeEventListener("keydown", close, true);
  }, [tourStep, setTourStep]);

  useEffect(() => {
    if (tourStep === null) {
      visits.current = [];
      routes.current = {};
      rosterLearnerRoute.current = undefined;
      rosterLearnerCourse.current = undefined;
      restoreRoster.current?.();
      restoreRoster.current = undefined;
      backwards.current = false;
      notified.current = false;
      return;
    }
    const step = steps[tourStep];
    if (!step) { setTourStep(null); return; }
    let cancelled = false;
    let moving = false;
    let progressRowReady = false;
    let instance: ReturnType<typeof driver> | undefined;
    const exit = () => setTourStep(null);
    const complete = () => {
      if (session?.userId) localStorage.setItem(dismissKey(session.userId), "dismissed");
      exit();
    };
    const back = () => {
      if (cancelled || moving) return;
      moving = true;
      backwards.current = true;
      visits.current.pop();
      const previous = visits.current.at(-1);
      if (!previous) { exit(); return; }
      setTourStep(previous.index);
      void navigate({ to: previous.pathname, search: previous.search });
    };
    const advance = (index: number) => {
      if (cancelled || moving) return;
      moving = true;
      backwards.current = false;
      if (index >= steps.length) { complete(); return; }
      setTourStep(index);
    };
    const skip = () => {
      if (cancelled) return;
      if (instructor) { showStep(); return; }
      if (backwards.current) { back(); return; }
      if (!notified.current) {
        notified.current = true;
        toast.info("Some parts are not available yet. Continuing the tour.");
      }
      advance(tourStep + 1);
    };
    // Never send a literal $uid or wildcard to the router. A progress row
    // from the current course's roster supplies a concrete route for Back.
    const routeMatches = matchesTourRoute(pathname, step.route);
    if (routeMatches) routes.current[step.route] = pathname;
    if (!routeMatches) {
      const concrete = /[$*]/.test(step.route) ? routes.current[step.route] : step.route;
      if (concrete) void navigate({ to: concrete, search: step.search ?? {} });
      else {
        const timer = window.setTimeout(skip, 300);
        return () => { cancelled = true; window.clearTimeout(timer); instance?.destroy(); };
      }
      return () => { cancelled = true; };
    }
    if (step.search && Object.entries(step.search).some(([key, value]) =>
      (search as Record<string, unknown>)[key] !== value)) {
      void navigate({ to: pathname, search: step.search });
      return () => { cancelled = true; };
    }

    async function wait(selector: string, timeout: number) {
      const start = performance.now();
      while (!cancelled) {
        const element = visibleTarget(selector);
        if (element) return element;
        if (performance.now() - start >= timeout) return undefined;
        await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
      }
    }
    async function prepareProgressRow() {
      rosterLearnerRoute.current = undefined;
      rosterLearnerCourse.current = undefined;
      delete routes.current["/class/student/$uid"];
      const courseId = session?.courseId ?? "";
      const key = ["roster", courseId];
      const cacheStart = performance.now();
      while (!cancelled && queryClient.getQueryState<Roster>(key)?.status === "pending"
          && performance.now() - cacheStart < 1200) {
        await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
      }
      if (cancelled) return;
      const roster = queryClient.getQueryState<Roster>(key);
      const learner = roster?.status === "success" ? progressTourLearner(roster.data, courseId) : undefined;
      if (!learner || !roster?.data) return;
      rosterLearnerRoute.current = `/class/student/${encodeURIComponent(learner.userId)}`;
      rosterLearnerCourse.current = courseId;
      const query = progressLearnerSearch(roster.data, learner);
      const input = visibleTarget("#tour-roster-search");
      const buttons = [...document.querySelectorAll<HTMLButtonElement>("#tour-roster-filter button")];
      const all = buttons.find((button) => button.textContent?.trim() === "All");
      if (!query || !(input instanceof HTMLInputElement) || !all) return;
      const previousSearch = input.value;
      const previousFilter = buttons.find((button) => button.dataset.state === "on");
      const setSearch = (value: string) => {
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(input, value);
        input.dispatchEvent(new Event("input", { bubbles: true }));
      };
      if (!restoreRoster.current) restoreRoster.current = () => {
        if (input.isConnected) setSearch(previousSearch);
        if (isTourUiClick("#tour-roster-filter") && previousFilter?.isConnected && previousFilter.dataset.state !== "on") previousFilter.click();
      };
      if (isTourUiClick("#tour-roster-filter") && all.dataset.state !== "on") all.click();
      setSearch(query);
      const start = performance.now();
      while (!cancelled && performance.now() - start < 1200) {
        const rows = document.querySelectorAll("#roster-panel tbody tr");
        const row = visibleTarget(step.selector);
        const label = row?.querySelector("td")?.textContent ?? "";
        if (rows.length === 1 && row && input.value === query
            && [learner.displayName, learner.pseudonym].some((name) => label.includes(name))) {
          progressRowReady = true;
          return row;
        }
        await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
      }
    }
    function prefill() {
      if (!step.prefill) return;
      const input = document.querySelector<HTMLTextAreaElement>(`#${step.prefill.inputId} textarea`);
      if (!input || input.value.trim()) return;
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set?.call(input, step.prefill.question);
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }
    function skipAction() {
      const next = steps.findIndex((candidate) => candidate.key === step.studentAction?.skipTo);
      if (next < 0) exit(); else advance(next);
    }
    function next() {
      if (cancelled || moving || tourStep === null) return;
      if (!instructor && step.studentAction) { skipAction(); return; }
      const selector = step.clickSelector ?? step.selector;
      if (instructor && step.progressLearner === "record" && rosterLearnerRoute.current
          && rosterLearnerCourse.current === session?.courseId) {
        routes.current["/class/student/$uid"] = rosterLearnerRoute.current;
      }
      if (instructor && step.progressLearner === "select" && !progressRowReady) {
        advance(tourStep + 1);
        return;
      }
      if (step.click && !step.explainOnly && isTourUiClick(selector) &&
          !(step.clickOnlyWhenClosed && visibleTarget(step.clickOnlyWhenClosed))) {
        const target = visibleTarget(selector);
        if (target instanceof HTMLElement && !target.matches(":disabled, [aria-disabled=true]")) {
          advance(tourStep + 1);
          target.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, button: 0 }));
          target.click();
          return;
        }
      }
      advance(tourStep + 1);
    }
    function showStep(target?: Element) {
      if (cancelled || tourStep === null) return;
      if (visits.current.at(-1)?.index !== tourStep) visits.current.push({ index: tourStep, pathname, search: search as Record<string, unknown> });
      if (target) prefill();
      instance = driver({
        animate: !reduceMotion,
        smoothScroll: !reduceMotion,
        overlayColor: "var(--brand-ink)",
        overlayOpacity: 0.35,
        overlayClickBehavior: "close",
        disableActiveInteraction: instructor,
        showProgress: true,
        progressText: `${tourStep + 1} of ${steps.length}`,
        steps: [{ ...(target ? { element: target } : {}), popover: {
          title: step.title,
          description: target ? step.description : step.fallbackDescription
            ?? "This part of the workspace is not visible right now. Select Next to continue.",
          side: "bottom", align: "start",
          showButtons: ["previous", "next", "close"],
          prevBtnText: "Back",
          nextBtnText: !instructor && step.studentAction ? "Skip this step" : tourStep === steps.length - 1 ? "Done" : "Next",
          onNextClick: () => { void next(); }, onPrevClick: back, onCloseClick: exit,
          onPopoverRender: (popover) => {
            popover.wrapper.dataset.tourStep = String(tourStep);
            popover.wrapper.dataset.tourFallback = String(!target);
            popover.previousButton.disabled = visits.current.length < 2;
            popover.previousButton.classList.toggle("driver-popover-btn-disabled", visits.current.length < 2);
            popover.closeButton.setAttribute("aria-label", "Skip tour");
            popover.closeButton.title = "Skip tour";
          },
        } }],
        onDestroyed: () => { if (!cancelled && !moving && useUI.getState().tourStep === tourStep) exit(); },
      });
      instance.drive();
      if (!instructor && step.studentAction) {
        void wait(step.studentAction.completeWhen, 120_000).then((found) => {
          if (cancelled || moving) return;
          if (found) advance(tourStep + 1); else skipAction();
        });
      }
    }
    async function readyTarget() {
      if (instructor && step.activateSelector && !visibleTarget(step.selector) && isTourUiClick(step.activateSelector)) {
        const tab = visibleTarget(step.activateSelector);
        if (tab instanceof HTMLElement && !tab.matches(":disabled, [aria-disabled=true]")) {
          tab.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true, button: 0 }));
          tab.click();
          await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
        }
      }
      if (cancelled) return;
      return instructor && step.progressLearner === "select" ? prepareProgressRow()
        : instructor && step.explainOnly ? visibleTarget(step.selector)
        : wait(step.waitFor ?? step.selector, instructor ? 1200 : step.waitState ? 120_000 : step.optional || backwards.current ? 1200 : 8000);
    }
    const ready = readyTarget();
    void ready.then(async (element) => {
      if (cancelled) return;
      const target = visibleTarget(step.selector);
      if (!element || !target) { skip(); return; }
      target.scrollIntoView({ block: "center", behavior: reduceMotion ? "auto" : "smooth" });
      await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
      if (cancelled || !target.isConnected || !visibleTarget(step.selector)) { if (!cancelled) skip(); return; }
      showStep(target);
    });
    return () => { cancelled = true; instance?.destroy(); };
  }, [tourStep, pathname, search, navigate, steps, dismissKey, session?.userId, session?.courseId, queryClient, instructor, reduceMotion, setTourStep]);
  return null;
}
