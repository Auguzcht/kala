type Caret = { start: number; end: number };
type Recall = { text: string; caret: Caret };

export function historyDirection({ key, value, start, end, modified = false, composing = false }: {
  key: string; value: string; start: number; end: number; modified?: boolean; composing?: boolean;
}): "up" | "down" | undefined {
  if (modified || composing || start !== end) return;
  if (key === "ArrowUp" && !value.slice(0, start).includes("\n")) return "up";
  if (key === "ArrowDown" && !value.slice(end).includes("\n")) return "down";
}

/** Only the temporary browsing position/draft live here. The caller owns history. */
export function createPromptHistory() {
  let entries: readonly string[] = [];
  let index: number | undefined;
  let original: Recall | undefined;
  function reset() { entries = []; index = undefined; original = undefined; }
  return {
    reset,
    move(direction: "up" | "down", prompts: readonly string[], text: string, caret: Caret): Recall | undefined {
      if (index === undefined) {
        if (direction === "down") return;
        entries = prompts.filter((prompt) => prompt.trim().length > 0);
        if (!entries.length) return;
        original = { text, caret: { ...caret } };
        index = entries.length;
      }
      index = Math.max(0, Math.min(entries.length, index + (direction === "up" ? -1 : 1)));
      if (index === entries.length) {
        const restored = original;
        reset();
        return restored;
      }
      const recalled = entries[index];
      return { text: recalled, caret: { start: recalled.length, end: recalled.length } };
    },
  };
}
