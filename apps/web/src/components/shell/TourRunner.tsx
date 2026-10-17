import { toast } from "sonner";
import { matchesTourRoute } from "@/components/shell/tour-route";
import { useEffect, useState } from "react";
import { driver, type Popover } from "driver.js";
import { useLocation, useNavigate } from "@tanstack/react-router";
import { useReducedMotion } from "motion/react";
import { useUI } from "@/stores/ui-store";
import type { TourStepConfig } from "@/components/shell/student-tour";
import { waitForElement } from "@/lib/wait-for-element";
import { useSession } from "@/lib/auth/AuthProvider";

// The cross-page tour runner, shared by the student and instructor tours.
// The shell layout (/course for students, /class for instructors) stays
// mounted across route changes, so ONE watcher can own the whole
// walkthrough instead of trying to keep a single Driver.js instance alive
// across a route change (its overlay/positioning breaks on unmount).
//
// Per page: one driver instance holds that page's contiguous steps (each
// page carries several real sub-steps), with driver.js's OWN showProgress
// inside the popover as the only progress indicator. "Next" on a page's
// last step destroys the instance, advances the store, and navigates to
// the next page; in-page steps advance inside the instance so progress
// keeps counting. A step with `click` (open a sheet, switch a tab, open a
// lesson) closes its own instance — clicking swaps the page content,
// which unmounts the next steps' elements.
//
// Before highlighting, each step's target is scrolled into view and a frame
// is awaited so the popover positions against the settled scroll position,
// not mid-scroll (smooth unless prefers-reduced-motion).
//
// A step with `waitFor` never highlights against a skeleton: if the target
// is missing and a `waitState` is provided, a wait-state popover drives on
// that selector while polling for the real content, then restarts the
// instance on it.
//
// Exiting (popover close, Escape, overlay click) just clears the store —
// the user stays wherever they are, no forced navigation back.

const OVERLAY_COLOR = "rgba(14,27,51,0.35)";

export function TourRunner({
  steps,
  dismissKey,
}: {
  steps: readonly TourStepConfig[];
  /** Per-user dismissal key writer: same shape as the per-tour
   * `...TourDismissKey(userId)` helpers. */
  dismissKey: (userId: string) => string;
}) {
  const navigate = useNavigate();
  const { pathname, search } = useLocation();
  const session = useSession();
  const reduceMotion = useReducedMotion();
  const tourStep = useUI((s) => s.tourStep);
  const setTourStep = useUI((s) => s.setTourStep);
  // Bumped when a wait-state resolves so the effect re-runs against the now-
  // ready content without changing the store.
  const [recheck, setRecheck] = useState(0);

  useEffect(() => {
    if (tourStep === null) return;
    const step = steps[tourStep];
    if (!step) {
      setTourStep(null);
      return;
    }
    // Navigation in flight: the store advanced but this page isn't mounted
    // yet. The pathname dep re-runs this effect when it lands.
    if (!matchesTourRoute(pathname, step.route)) return;
    if (step.search && Object.entries(step.search).some(([key, value]) =>
      (search as Record<string, unknown>)[key] !== value)) return;

    let cancelled = false;
    let finishedAction = false;
    let flowDestroy = false; // we destroyed on purpose (wait-state resolving)
    let instance: ReturnType<typeof driver> | null = null;

    const exit = () => setTourStep(null);
    const unavailable = () => {
      if (cancelled) return;
      flowDestroy = true;
      instance?.destroy();
      toast.info("This tour step is not available yet. You can restart the tour later.");
      exit();
    };
    const advanceTo = (index: number) => {
      if (index >= steps.length) {
        // Completed the walkthrough — same permanent dismissal as "Got it".
        if (session?.userId) {
          localStorage.setItem(dismissKey(session.userId), "dismissed");
        }
        exit();
        return;
      }
      setTourStep(index);
      if (steps[index].search || (steps[index].route !== steps[tourStep].route && !steps[index].route.endsWith("/*"))) {
        void navigate({ to: steps[index].route, search: steps[index].search ?? {} });
      }
    };

    const frame = () =>
      new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));

    // Editable draft only: never submit or replace text the student wrote.
    const prefillInput = (sample: NonNullable<TourStepConfig["prefill"]>) => {
      const input = document.querySelector<HTMLTextAreaElement>(`#${sample.inputId} textarea`);
      if (!input || input.value.trim()) return;
      const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value")?.set;
      setter?.call(input, sample.question);
      input.dispatchEvent(new Event("input", { bubbles: true }));
    };
    const skipAction = (action: NonNullable<TourStepConfig["studentAction"]>) => {
      if (cancelled || finishedAction) return;
      finishedAction = true;
      const target = steps.findIndex((candidate) => candidate.key === action.skipTo);
      if (target < 0) exit();
      else advanceTo(target);
    };

    const scrollThenDrive = async (el: Element | null) => {
      if (el) {
        el.scrollIntoView({ block: "start", behavior: reduceMotion ? "auto" : "smooth" });
        await frame();
      }
      if (!cancelled && !finishedAction && instance) {
        if (step.prefill) prefillInput(step.prefill);
        instance.drive();
      }
    };

    // Keep navigation, editable drafts and student-action waits in separate
    // instances. Skipping an action also skips all steps that depend on it.
    let end = tourStep + 1;
    while (
      end < steps.length &&
      steps[end].route === step.route &&
      !steps[end].search &&
      !steps[end].waitFor &&
      !steps[end].prefill &&
      !steps[end].studentAction &&
      !steps[end - 1].click &&
      !steps[end - 1].prefill &&
      !steps[end - 1].studentAction
    ) {
      end++;
    }

    const onDestroyed = () => {
      // Fires on ANY destroy: ours (advance/exit/cleanup) or the user's
      // (Escape/overlay click). Only treat it as an exit if the tour is
      // still on THIS step — after `advanceTo` the store already moved.
      if (!cancelled && !flowDestroy && useUI.getState().tourStep === tourStep) exit();
    };

    const first = steps[tourStep];
    const finishActionIfReady = () => {
      if (!first.studentAction || !document.querySelector(first.studentAction.completeWhen)) return false;
      finishedAction = true;
      advanceTo(tourStep + 1);
      return true;
    };
    if (finishActionIfReady()) return;
    const readySelector = [first.waitFor, first.studentAction?.completeWhen].filter(Boolean).join(", ");

    if (first.waitFor && !document.querySelector(readySelector) && first.waitState) {
      // Content not ready (guided lesson still generating, sheet still
      // loading): drive the wait-state popover on the generating panel,
      // poll for the real content, then restart this instance on it.
      instance = driver({
        overlayColor: OVERLAY_COLOR,
        overlayClickBehavior: "close",
        smoothScroll: !reduceMotion,
        steps: [
          {
            element: first.waitState.selector,
            popover: {
              title: first.title,
              description: first.waitState.description,
              side: "bottom",
              align: "start",
              showButtons: first.studentAction ? ["next", "close"] : ["close"],
              nextBtnText: "Skip this step",
              onNextClick: first.studentAction ? () => skipAction(first.studentAction!) : undefined,
              onCloseClick: exit,
            },
          },
        ],
        onDestroyed,
      });
      void scrollThenDrive(document.querySelector(first.waitState.selector));
      void waitForElement(readySelector, { timeout: 120_000 }).then((element) => {
        if (cancelled || finishedAction) return;
        if (!element) {
          if (first.studentAction) skipAction(first.studentAction);
          else unavailable();
          return;
        }
        if (finishActionIfReady()) return;
        flowDestroy = true;
        instance?.destroy();
        setRecheck((r) => r + 1);
      });
    } else {
      // Normal instance: this page's real steps, driver's own progress bar.
      const instanceSteps = steps.slice(tourStep, end).map((s, i) => {
        const globalIndex = tourStep + i;
        const isLastGlobal = globalIndex === steps.length - 1;
        const isInstanceLast = i === end - tourStep - 1;
        const popover: Popover = {
          title: s.title,
          description: s.description,
          side: "bottom",
          align: "start",
          showProgress: true,
          showButtons: ["next", "close"],
          nextBtnText: isLastGlobal ? "Done" : "Next",
          onCloseClick: exit,
        };
        if (s.studentAction) {
          popover.nextBtnText = "Skip this step";
          popover.onNextClick = () => skipAction(s.studentAction!);
        } else if (s.click) {
          // Click a target (clickSelector when the click target differs
          // from the highlighted element, else the highlighted element
          // itself), then move on — the store advance swaps the page
          // content. IMPORTANT: driver.js calls onNextClick with NO
          // arguments (its DriverHook type says it may pass the element,
          // the implementation never does), so the target must be
          // resolved from the step config, never from the callback arg.
          //
          // Radix primitives (Tabs, Select, etc.) activate on onMouseDown,
          // not onClick — a programmatic .click() dispatches no mousedown,
          // so the tab never switches and the tour stalls until the user
          // clicks by hand. Dispatch a real mousedown (button 0, ctrl-less
          // — the exact condition Radix checks) before the click; plain
          // onClick handlers ignore the mousedown, so both handler kinds
          // work from the same step.
          popover.onNextClick = () => {
            // clickOnlyWhenClosed: skip the click when that selector is
            // already present. The skill-review trigger is a toggle and
            // the panel auto-opens when a queue exists — clicking an
            // already-open trigger would collapse it mid-tour. This keeps
            // the step working for both states (open → highlight only;
            // closed → click to open).
            const alreadyOpen =
              s.clickOnlyWhenClosed &&
              document.querySelector(s.clickOnlyWhenClosed);
            if (!alreadyOpen) {
              const target = document.querySelector(
                s.clickSelector ?? s.selector
              ) as HTMLElement | null;
              target?.dispatchEvent(
                new MouseEvent("mousedown", {
                  bubbles: true,
                  cancelable: true,
                  button: 0,
                  ctrlKey: false,
                })
              );
              target?.click();
            }
            advanceTo(globalIndex + 1);
          };
        } else if (isInstanceLast) {
          popover.onNextClick = () => advanceTo(end);
        }
        return { element: s.selector, popover };
      });
      instance = driver({
        showProgress: true,
        disableActiveInteraction: false,
        overlayColor: OVERLAY_COLOR,
        overlayClickBehavior: "close",
        smoothScroll: !reduceMotion,
        steps: instanceSteps,
        onDestroyed,
      });
      const targetSelector = [first.selector, first.studentAction?.completeWhen].filter(Boolean).join(", ");
      void waitForElement(targetSelector, { timeout: 8000 }).then((el) => {
        if (cancelled || finishedAction) return;
        if (finishActionIfReady()) return;
        if (!el) { unavailable(); return; }
        void scrollThenDrive(el);
        if (first.studentAction) {
          const action = first.studentAction;
          void waitForElement(action.completeWhen, { timeout: 120_000 }).then((result) => {
            if (cancelled || finishedAction) return;
            if (!result) {
              toast.info("No action taken yet. Continuing to the next part of the tour.");
              skipAction(action);
              return;
            }
            finishedAction = true;
            advanceTo(tourStep + 1);
          });
        }
      });
    }

    return () => {
      cancelled = true;
      instance?.destroy();
    };
  }, [tourStep, pathname, search, navigate, setTourStep, session?.userId, reduceMotion, recheck, steps, dismissKey]);

  return null;
}
