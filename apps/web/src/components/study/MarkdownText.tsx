import { useEffect, useRef, useState } from "react";
import { MessageResponse } from "@/components/ai-elements/message";
import { useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

// One markdown recipe for every place Kala's model output is rendered as
// prose. The model answers in markdown (bold, lists, code, headings,
// blockquotes); Streamdown turns that into real elements, but without this
// recipe those elements land on raw browser defaults — cramped lists, code
// invisible against the surrounding text, unstyled links. Kept as one shared
// constant (not copied per component) so a graded explanation and a chat
// reply can never drift into two different typographies.
//
// Spacing here is deliberately tight: these render inside stream blocks that
// already space themselves, so the recipe only needs to fix the *internal*
// rhythm of a markdown document, not its outer margins.
export const MD_RECIPE =
  "[&_p]:my-1.5 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 " +
  "[&_ul]:my-1.5 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-1.5 [&_ol]:list-decimal [&_ol]:pl-5 " +
  "[&_li]:my-0.5 [&_code]:rounded-sm [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 " +
  "[&_pre]:my-1.5 [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-muted [&_pre]:p-3 " +
  "[&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_a]:text-brand-orange [&_a]:underline " +
  "[&_h1]:text-base [&_h2]:text-base [&_h3]:text-[13.5px] [&_blockquote]:border-l-2 " +
  "[&_blockquote]:border-border [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground " +
  // --- Code-block chrome (Streamdown's own component, tightened with CSS) ---
  // Its header is a full-width `h-8` row holding only a small language label,
  // with the copy/download controls floated over it via a negative margin.
  // That leaves a tall empty band above the code and pushes the controls up
  // out of alignment with the label. Tighter header, less outer padding, and
  // the label/controls share one baseline.
  "[&_[data-streamdown='code-block']]:gap-0 " +
  "[&_[data-streamdown='code-block']]:p-1.5 " +
  "[&_[data-streamdown='code-block-header']]:h-7 " +
  "[&_[data-streamdown='code-block-header']]:justify-between " +
  "[&_[data-streamdown='code-block-header']]:px-1 " +
  "[&_[data-streamdown='code-block-actions']]:border-0 " +
  "[&_[data-streamdown='code-block-actions']]:bg-transparent " +
  "[&_[data-streamdown='code-block-actions']]:px-0 " +
  "[&_[data-streamdown='code-block-actions']]:py-0 " +
  // The actions wrapper is offset with -mt-10 to sit over the header; with the
  // header now shorter, pull it back to the same line instead of above it.
  "[&_[data-streamdown='code-block']>div:has([data-streamdown='code-block-actions'])]:-mt-7 " +
  "[&_[data-streamdown='code-block']>div:has([data-streamdown='code-block-actions'])]:h-7 " +
  "[&_[data-streamdown='code-block']>div:has([data-streamdown='code-block-actions'])]:pr-1";

/**
 * Free-text model output rendered as markdown, with a writing-out reveal.
 *
 * Use this anywhere a string came from a model (tutor answers, lesson
 * explanations, graded feedback) — never a bare <p>, which shows the model's
 * markdown syntax literally.
 *
 * ## Why the reveal is here and not in the backend
 *
 * Kala's model endpoints are single-shot JSON, not token streams: the whole
 * answer lands in one render. Streamdown's own reveal animates content that
 * *grows between renders*, so a full string dropped in once appears instantly
 * — which is the "the text just appears, there's no animation" symptom. This
 * component supplies the missing growth by revealing the string in slices, and
 * Streamdown cascades the result word by word.
 *
 * When the backend gains real streaming, pass the already-growing `text` and
 * set `animate={false}`: the reveal becomes a no-op and Streamdown animates
 * the live stream directly. Nothing else changes for any caller.
 */
export function MarkdownText({
  children,
  className,
  animate = true,
  streaming = false,
}: {
  children: string;
  className?: string;
  /** Reveal the text as it appears. On by default so every surface gets the
   * same writing-out motion without opting in. */
  animate?: boolean;
  /** True when `children` is genuinely arriving in pieces (real token
   * streaming). Disables the local reveal so the two don't compound. */
  streaming?: boolean;
}) {
  const reduceMotion = useReducedMotion();
  const shouldReveal = animate && !streaming && !reduceMotion;
  const { visible, isRevealing } = useRevealText(children, shouldReveal);

  return (
    <MessageResponse
      className={cn(MD_RECIPE, className)}
      animated={
        shouldReveal ? { animation: "blurIn", sep: "word", stagger: 0.006, duration: 0.28 } : false
      }
      mode={shouldReveal ? "streaming" : "static"}
      // True only WHILE the reveal is running, then flipped false on the last
      // slice. Leaving it true on a finished message would keep Streamdown
      // parsing the text as an incomplete stream (caret, partial-markdown
      // handling), which is wrong once the answer has fully arrived.
      isAnimating={isRevealing}
    >
      {visible}
    </MessageResponse>
  );
}

/**
 * Hands back `text` in growing slices so a streaming-aware renderer has
 * something to animate, plus whether the reveal is still in flight. No-op
 * (returns the full text immediately) when `reveal` is false, which is the
 * reduced-motion path.
 *
 * Two things make this read as smooth typing rather than chunky jumps:
 *
 *  1. It is driven by elapsed wall-clock time on requestAnimationFrame, not
 *     by a step counter on a timer. Every frame the reveal advances to
 *     wherever the eased progress curve says it should be, so a dropped or
 *     late frame self-corrects instead of falling permanently behind.
 *  2. Slices land on word boundaries. Cutting mid-word makes the markdown
 *     renderer re-parse a partial token on every frame, which is what made
 *     the text visibly stutter as words assembled character by character.
 */
function useRevealText(
  text: string,
  reveal: boolean
): { visible: string; isRevealing: boolean } {
  const [visibleLength, setVisibleLength] = useState(reveal ? 0 : text.length);
  const [isRevealing, setIsRevealing] = useState(reveal);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;

    if (!reveal || text.length === 0) {
      setVisibleLength(text.length);
      setIsRevealing(false);
      return;
    }

    // End-of-word offsets: the only positions the reveal is allowed to pause
    // at. Falls back to the whole length when the text has no spaces.
    const wordEnds: number[] = [];
    for (let i = 0; i < text.length; i += 1) {
      if (i === text.length - 1 || /\s/.test(text[i + 1])) wordEnds.push(i + 1);
    }
    if (wordEnds.length === 0) wordEnds.push(text.length);

    setIsRevealing(true);
    const startedAt = performance.now();
    // Scale duration with length, but only gently: a wall of text shouldn't
    // take proportionally longer or it feels like waiting for a page to load.
    const durationMs = Math.min(2200, 450 + text.length * 1.1);

    const tick = (now: number) => {
      const t = Math.min(1, (now - startedAt) / durationMs);
      // easeOutCubic: quick off the mark, easing to a stop — reads like
      // natural typing rather than a linear crawler.
      const eased = 1 - Math.pow(1 - t, 3);
      const target = Math.round(eased * wordEnds.length);
      const nextLength = wordEnds[Math.min(wordEnds.length - 1, Math.max(0, target - 1))] ?? 0;

      setVisibleLength((prev) => (nextLength > prev ? nextLength : prev));

      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        setVisibleLength(text.length);
        setIsRevealing(false);
      }
    };
    // Defer the first frame so the empty render commits first — the
    // animation needs somewhere to come from.
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [text, reveal]);

  return { visible: reveal ? text.slice(0, visibleLength) : text, isRevealing };
}
