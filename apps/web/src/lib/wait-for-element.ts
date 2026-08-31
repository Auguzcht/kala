// Wait for a real DOM element to exist, polling via requestAnimationFrame.
// These pages render loading skeletons first, and a tour must never highlight
// against a skeleton — resolve once the real content is in the tree, or give
// up after `timeout` and let the caller degrade gracefully.

export function waitForElement(
  selector: string,
  { timeout = 8000 }: { timeout?: number } = {}
): Promise<Element | null> {
  return new Promise((resolve) => {
    const found = document.querySelector(selector);
    if (found) {
      resolve(found);
      return;
    }
    const start = performance.now();
    const check = () => {
      const el = document.querySelector(selector);
      if (el) {
        resolve(el);
        return;
      }
      if (performance.now() - start >= timeout) {
        resolve(null);
        return;
      }
      requestAnimationFrame(check);
    };
    requestAnimationFrame(check);
  });
}
