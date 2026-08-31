import { useEffect, useState } from "react";
import { driver, type Popover } from "driver.js";
import { useLocation, useNavigate } from "@tanstack/react-router";
import { useReducedMotion } from "motion/react";
import { useUI } from "@/stores/ui-store";
import { TOUR_STEPS, studentTourDismissKey } from "@/components/shell/student-tour";
import { waitForElement } from "@/lib/wait-for-element";
import { useSession } from "@/lib/auth/AuthProvider";

// The cross-page tour runner. CourseShell (the /course layout) stays mounted
// across route changes, so ONE watcher can own the whole walkthrough instead
// of trying to keep a single Driver.js instance alive across a route change
// (its overlay/positioning breaks on unmount).
//
// Per page: one driver instance holds that page's contiguous steps (each
// page carries several real sub-steps — question card + choices, lesson card
// + explain + continue, etc.), with driver.js's OWN showProgress inside the
// popover as the only progress indicator. "Next" on a page's last step
// destroys the instance, advances the store, and navigates to the next page;
// in-page steps advance inside the instance so progress keeps counting.
// A step with `click` (the Lessons card) closes its own instance — clicking
// swaps the page content, which unmounts the next steps' elements.
//
// Before highlighting, each step's target is scrolled into view and a frame
// is awaited so the popover positions against the settled scroll position,
// not mid-scroll (smooth unless prefers-reduced-motion).
//
// The Lessons "explain" step waits for real content: if the lesson is still
// being generated, a wait-state popover ("Kala is writing this lesson…")
// drives on the generating panel and polls for the ready content before
// restarting the instance — never highlighting against a skeleton.
//
// Exiting (popover close, Escape, overlay click) just clears the store —
// the user stays wherever they are, no forced navigation back.
const OVERLAY_COLOR = "rgba(14,27,51,0.35)";

export function TourStepRunner() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const session = useSession();
  const reduceMotion = useReducedMotion();
  const tourStep = useUI((s) => s.tourStep);
  const setTourStep = useUI((s) => s.setTourStep);
  // Bumped when a wait-state resolves so the effect re-runs against the now-
  // ready content without changing the store.
  const [recheck, setRecheck] = useState(0);

  useEffect(() => {
    if (tourStep === null) return;
    const step = TOUR_STEPS[tourStep];
    if (!step) {
      setTourStep(null);
      return;
    }
    // Navigation in flight: the store advanced but this page isn't mounted
    // yet. The pathname dep re-runs this effect when it lands.
    if (pathname !== step.route) return;

    let cancelled = false;
    let flowDestroy = false; // we destroyed on purpose (wait-state resolving)
    let instance: ReturnType<typeof driver> | null = null;

    const exit = () => setTourStep(null);
    const advanceTo = (index: number) => {
      if (index >= TOUR_STEPS.length) {
        // Completed the walkthrough — same permanent dismissal as "Got it".
        if (session?.userId) {
          localStorage.setItem(studentTourDismissKey(session.userId), "dismissed");
        }
        exit();
        return;
      }
      setTourStep(index);
      if (TOUR_STEPS[index].route !== TOUR_STEPS[tourStep].route) {
        void navigate({ to: TOUR_STEPS[index].route });
      }
    };

    const frame = () =>
      new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));

    // Fill the tutor input and submit through the same path the Ask button
    // uses (native value setter + input event so React's controlled state
    // picks it up, then requestSubmit on the form). Two frames for React to
    // flush the state before submit.
    const askTutor = async (question: string) => {
      const input = document.querySelector<HTMLInputElement>("#tour-tutor-input input");
      if (!input) return;
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        "value"
      )?.set;
      setter?.call(input, question);
      input.dispatchEvent(new Event("input", { bubbles: true }));
      await frame();
      await frame();
      document.querySelector<HTMLFormElement>("#tour-tutor-input")?.requestSubmit();
    };

    const scrollThenDrive = async (el: Element | null) => {
      if (el) {
        el.scrollIntoView({ block: "start", behavior: reduceMotion ? "auto" : "smooth" });
        await frame();
      }
      if (!cancelled && instance) instance.drive();
    };

    // Instance boundary: contiguous steps on the same route; a click step
    // or a tutorAsk step always closes its own instance (their Next swaps
    // the page content / fires a request the following steps must wait on).
    let end = tourStep + 1;
    while (
      end < TOUR_STEPS.length &&
      TOUR_STEPS[end].route === step.route &&
      !TOUR_STEPS[end - 1].click &&
      !TOUR_STEPS[end - 1].tutorAsk
    ) {
      end++;
    }

    const onDestroyed = () => {
      // Fires on ANY destroy: ours (advance/exit/cleanup) or the user's
      // (Escape/overlay click). Only treat it as an exit if the tour is
      // still on THIS step — after `advanceTo` the store already moved.
      if (!flowDestroy && useUI.getState().tourStep === tourStep) exit();
    };

    const first = TOUR_STEPS[tourStep];

    if (first.waitFor && !document.querySelector(first.waitFor) && first.waitState) {
      // Content not ready (guided lesson still generating): drive the
      // wait-state popover on the generating panel, poll for the real
      // content, then restart this instance on it.
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
              showButtons: ["close"],
              onCloseClick: exit,
            },
          },
        ],
        onDestroyed,
      });
      void scrollThenDrive(document.querySelector(first.waitState.selector));
      void waitForElement(first.waitFor, { timeout: 120_000 }).then(() => {
        if (cancelled) return;
        flowDestroy = true;
        instance?.destroy();
        setRecheck((r) => r + 1);
      });
    } else {
      // Normal instance: this page's real steps, driver's own progress bar.
      const steps = TOUR_STEPS.slice(tourStep, end).map((s, i) => {
        const globalIndex = tourStep + i;
        const isLastGlobal = globalIndex === TOUR_STEPS.length - 1;
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
        if (s.click) {
          // Click a target (the highlighted element, or clickSelector when
          // the click target differs), then move on — the store advance
          // swaps the page content.
          popover.onNextClick = (el) => {
            const target = s.clickSelector
              ? document.querySelector(s.clickSelector)
              : el;
            (target as HTMLElement | undefined)?.click();
            advanceTo(globalIndex + 1);
          };
        } else if (s.tutorAsk) {
          popover.onNextClick = () => {
            void askTutor(s.tutorAsk!.question);
            advanceTo(globalIndex + 1);
          };
        } else if (isInstanceLast) {
          popover.onNextClick = () => advanceTo(end);
        }
        return { element: s.selector, popover };
      });
      instance = driver({
        showProgress: true,
        overlayColor: OVERLAY_COLOR,
        overlayClickBehavior: "close",
        smoothScroll: !reduceMotion,
        steps,
        onDestroyed,
      });
      void waitForElement(first.selector, { timeout: 8000 }).then((el) => {
        if (cancelled) return;
        void scrollThenDrive(el);
      });
    }

    return () => {
      cancelled = true;
      instance?.destroy();
    };
  }, [tourStep, pathname, navigate, setTourStep, session?.userId, reduceMotion, recheck]);

  return null;
}
