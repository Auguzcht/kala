import { toast } from "sonner";
import { useEffect, useRef } from "react";
import { driver } from "driver.js";
import { useLocation, useNavigate } from "@tanstack/react-router";
import { useReducedMotion } from "motion/react";
import { useUI } from "@/stores/ui-store";
import { useSession } from "@/lib/auth/AuthProvider";
import { isTourUiClick, matchesTourRoute } from "@/components/shell/tour-route";
import type { TourStepConfig } from "@/components/shell/student-tour";

export type TourPresentationStep = TourStepConfig & {
  explainOnly?: boolean;
  fallbackDescription?: string;
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
  const { pathname, search } = useLocation();
  const session = useSession();
  const instructor = session?.role === "instructor" || session?.role === "admin";
  const reduceMotion = useReducedMotion();
  const tourStep = useUI((state) => state.tourStep);
  const setTourStep = useUI((state) => state.setTourStep);
  const visits = useRef<Visit[]>([]);
  const routes = useRef<Record<string, string>>({});
  const backwards = useRef(false);
  const notified = useRef(false);

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
      backwards.current = false;
      notified.current = false;
      return;
    }
    const step = steps[tourStep];
    if (!step) { setTourStep(null); return; }
    let cancelled = false;
    let moving = false;
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
    // Never send a literal $uid or wildcard to the router. A UI-only record
    // link supplies the first concrete learner route; Back can reuse it.
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
    const ready = instructor && step.explainOnly
      ? Promise.resolve(visibleTarget(step.selector))
      : wait(step.waitFor ?? step.selector, instructor ? 1200 : step.waitState ? 120_000 : step.optional || backwards.current ? 1200 : 8000);
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
  }, [tourStep, pathname, search, navigate, steps, dismissKey, session?.userId, instructor, reduceMotion, setTourStep]);
  return null;
}
