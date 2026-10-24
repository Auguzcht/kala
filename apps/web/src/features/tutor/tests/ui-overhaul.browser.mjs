/** WI-22 synthetic browser checks. Run against the existing strict-port Vite.
 * KALA_BROWSER_TEST_DEPS=/path/to/package-root node .../ui-overhaul.browser.mjs
 * Uses Playwright from an external/bundled runtime; no repository dependencies added.
 * Auth and API modules are intercepted in this isolated browser. No tokens or live API.
 */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
import { resolve } from "node:path";
const requireBrowser = createRequire(
  resolve(process.env.KALA_BROWSER_TEST_DEPS ?? "apps/web", "package.json"),
);
const { chromium } = requireBrowser("playwright");
const out = resolve(
  process.env.KALA_UI_SCREENSHOTS ?? "/tmp/kala-lane-u-visuals",
);
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  ...(process.env.KALA_BROWSER_EXECUTABLE
    ? { executablePath: process.env.KALA_BROWSER_EXECUTABLE }
    : {}),
});
let assertions = 0;
const check = (value, label) => {
  assert.ok(value, label);
  assertions++;
};
const row = (id, pinnedAt = null) => ({
  id,
  courseId: "synthetic-course",
  skillId: null,
  title:
    id === "existing"
      ? "Understanding cloud storage"
      : id === "pinned"
        ? "Networking essentials"
        : "New chat",
  createdAt: "2026-10-24T10:00:00Z",
  updatedAt: "2026-10-25T10:00:00Z",
  pinnedAt,
});
const questions = Array.from({ length: 6 }, (_, i) => ({
  id: `question-${i}`,
  skillId: "storage",
  bloomLevel: "understand",
  prompt: `${i + 1}. Which approach fits this cloud storage scenario? ${i === 5 ? "Consider an application that must keep a durable copy of every document while allowing a team to retrieve the latest version from several locations." : "Choose the best starting point."}`,
  choices: [
    {
      id: "a",
      label: "Use durable object storage with appropriate access controls.",
    },
    { id: "b", label: "Keep the only copy on one temporary local disk." },
    { id: "c", label: "Make every document publicly writable." },
  ],
}));
async function fixture(
  width,
  { legacy = false, empty = false, reducedMotion = "reduce" } = {},
) {
  const context = await browser.newContext({
    viewport: { width, height: 900 },
    reducedMotion,
  });
  const page = await context.newPage();
  await page.clock.install();
  page.setDefaultTimeout(10000);
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const state = {
    rows: empty ? [] : [row("pinned", "2026-10-25T10:00:00Z"), row("existing")],
    messages: [],
    attachments: [],
    deletes: 0,
    patches: 0,
    creates: 0,
    asks: 0,
    uploads: 0,
    attachmentDeletes: 0,
    rejectUploads: true,
    holdUpload: null,
    submit: null,
    holdAsk: null,
  };
  if (legacy)
    state.rows = [
      Object.fromEntries(
        Object.entries(row("existing")).filter(([key]) => key !== "pinnedAt"),
      ),
    ];
  await context.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.hostname !== "localhost" || url.port !== "5173")
      return route.abort();
    if (url.pathname.endsWith("/src/lib/auth/AuthProvider.tsx"))
      return route.fulfill({
        contentType: "application/javascript",
        body: `export const AuthProvider=({children})=>children; export const useSession=()=>({userId:'synthetic-user',institutionId:'synthetic-institution',role:'student',courseId:'synthetic-course',displayName:'Demo learner'}); export const useSetSession=()=>()=>{};`,
      });
    if (url.pathname.endsWith("/src/lib/api/client.ts"))
      return route.fulfill({
        contentType: "application/javascript",
        body: `export async function api(path,init){const r=await fetch('/__lane_u_api__'+path,init);if(!r.ok)throw new Error('API '+r.status+': '+await r.text());return r.json();}`,
      });
    if (!url.pathname.startsWith("/__lane_u_api__")) return route.continue();
    const path = url.pathname.slice("/__lane_u_api__".length),
      method = route.request().method();
    const reply = (json, status = 200) => route.fulfill({ status, json });
    if (path === "/courses/synthetic-course")
      return reply({ id: "synthetic-course", title: "AWS101" });
    if (path.endsWith("/twin"))
      return reply({
        courseId: "synthetic-course",
        readiness: null,
        skills: [
          {
            skillId: "storage",
            name: "Cloud storage",
            estimate: null,
            attempts: 0,
            band: "no-evidence",
          },
          {
            skillId: "network",
            name: "Networking",
            estimate: null,
            attempts: 0,
            band: "no-evidence",
          },
        ],
        evidence: [],
      });
    if (path.endsWith("/next-up"))
      return reply({ courseId: "synthetic-course", next: null });
    if (path.endsWith("/summary"))
      return reply({
        xp: 0,
        attempts: 0,
        correct: 0,
        streakDays: 0,
        badges: [],
      });
    if (path.endsWith("/diagnostic/status"))
      return reply({
        courseId: "synthetic-course",
        due: true,
        dueSkillCount: 6,
      });
    if (path.endsWith("/diagnostic/submit")) {
      state.submit = route.request().postDataJSON();
      return reply({
        correctCount: 6,
        total: 6,
        results: [],
        masteryDelta: [],
      });
    }
    if (path.endsWith("/diagnostic"))
      return reply({
        courseId: "synthetic-course",
        status: "ready",
        readyCount: 6,
        questions,
        pendingSkillIds: [],
        failedSkillIds: [],
        skippedSkillCount: 0,
      });
    if (path.endsWith("/bank/status"))
      return reply({
        courseId: "synthetic-course",
        building: false,
        bankServing: true,
        skills: [
          {
            skillId: "storage",
            status: "ready",
            mcqReady: 10,
            mcqTarget: 10,
            depth: 1,
            usable: true,
          },
        ],
      });
    if (path === "/tutor/conversations" && method === "GET")
      return reply({ conversations: state.rows });
    if (path === "/tutor/conversations" && method === "POST") {
      state.creates++;
      const created = row("created");
      state.rows.push(created);
      return reply(created);
    }
    if (path === "/tutor/ask") {
      state.asks++;
      if (state.holdAsk) await state.holdAsk;
      const { question } = route.request().postDataJSON();
      state.messages.push(
        {
          id: `u-${state.asks}`,
          role: "user",
          content: question,
          style: null,
          createdAt: "2026-10-25T11:00:00Z",
        },
        {
          id: `a-${state.asks}`,
          role: "assistant",
          content:
            "Object storage keeps durable copies of your data. Access policies control who can read and update each object.",
          style: "default",
          createdAt: "2026-10-25T11:00:01Z",
        },
      );
      return reply({
        answer: state.messages.at(-1).content,
        conversationId: "created",
      });
    }
    if (path.endsWith("/attachments") && method === "POST") {
      state.uploads++;
      if (state.holdUpload) await state.holdUpload();
      if (
        state.rejectUploads &&
        route.request().postData().includes("rejected")
      )
        return reply(
          { detail: "Synthetic upload could not be stored. Please try again." },
          503,
        );
      const a = {
        id: `file-${state.uploads}`,
        filename:
          /filename="([^"]+)"/.exec(route.request().postData())?.[1] ??
          "notes.md",
        mimeType: "text/markdown",
        sizeBytes: 20,
        status: "ready",
        createdAt: "2026-10-25T11:00:00Z",
      };
      state.attachments.push(a);
      return reply(a);
    }
    if (/\/attachments\//.test(path) && method === "DELETE") {
      state.attachmentDeletes++;
      state.attachments = [];
      return reply({});
    }
    if (path.startsWith("/tutor/conversations/")) {
      const id = path.split("/")[3];
      if (method === "DELETE") {
        state.deletes++;
        state.rows = state.rows.filter((x) => x.id !== id);
        return reply({});
      }
      if (method === "PATCH") {
        state.patches++;
        const patch = route.request().postDataJSON();
        const r = state.rows.find((x) => x.id === id);
        if ("title" in patch) r.title = patch.title;
        if ("pinned" in patch)
          r.pinnedAt = patch.pinned ? "2026-10-25T12:00:00Z" : null;
        return reply(r);
      }
      // Detail deliberately omits pinnedAt: capability belongs to list responses.
      const r = {
        ...(state.rows.find((x) => x.id === id) ?? row(id)),
        messages: state.messages,
        attachments: state.attachments,
      };
      delete r.pinnedAt;
      return reply(r);
    }
    if (path.endsWith("/deck"))
      return reply({
        courseId: "synthetic-course",
        cards:
          url.searchParams.get("limit") === "0"
            ? []
            : [
                {
                  itemId: "card",
                  skillId: "storage",
                  skillName: "Cloud storage",
                  prompt: "What does object storage provide?",
                  back: {
                    label: "Durable storage for objects",
                    explanation: "An object contains data and metadata.",
                  },
                  state: "new",
                  box: 0,
                },
              ],
        stats: { tracked: 1, due: 1, learning: 0, mastered: 0 },
        mode: "review",
        sessionId: "synthetic-session",
        hasMore: false,
      });
    if (path.endsWith("/plan")) return reply({ plan: [] });
    return reply({});
  });
  return { context, page, state, errors };
}
async function screenshot(page, name, width) {
  await page.screenshot({
    path: `${out}/${name}-${width}.png`,
    animations: "disabled",
  });
}
try {
  for (const width of [1440, 375]) {
    const { context, page, state, errors } = await fixture(width, {
      empty: true,
    });
    await page.goto("http://localhost:5173/course/diagnostic");
    await page
      .getByRole("button", { name: "Submit diagnostic", exact: true })
      .waitFor();
    check(
      await page.getByText("0 of 6 answered", { exact: true }).isVisible(),
      "DIAG-REQ-002 initial count",
    );
    check(
      await page
        .getByRole("button", { name: "Submit diagnostic", exact: true })
        .isDisabled(),
      "DIAG-REQ-002 incomplete disabled",
    );
    check(
      (await page.getByText("Build your baseline", { exact: true }).count()) ===
        0,
      "DIAG-REQ-001 no redundant header",
    );
    check(
      (await page.getByRole("progressbar").count()) === 0,
      "DIAG-REQ-002 no progress bar",
    );
    check(
      (await page
        .getByRole("button", { name: "Open chat history" })
        .count()) === 0,
      "TUTOR-REQ-004 non-Tutor header unchanged",
    );
    check(
      await page
        .locator("main")
        .evaluate(
          (el) =>
            el.parentElement.getBoundingClientRect().x === 0 &&
            getComputedStyle(el.parentElement).paddingLeft === "56px",
        ),
      "TUTOR-REQ-004 non-Tutor retains rail offset",
    );
    const last = page.locator("#tour-diagnostic-card button").last();
    await last.scrollIntoViewIfNeeded();
    const lastBox = await last.boundingBox(),
      footerBox = await page.locator("footer").boundingBox();
    check(
      lastBox.y + lastBox.height <= footerBox.y + 1,
      "DIAG-REQ-003 complete last choice above footer",
    );
    check(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      "DIAG-REQ-003 no horizontal clipping",
    );
    await screenshot(page, "diagnostic", width);
    for (let i = 0; i < 6; i++)
      await page
        .locator("#tour-diagnostic-card")
        .getByRole("button")
        .nth(i * 3)
        .click();
    check(
      await page.getByText("6 of 6 answered", { exact: true }).isVisible(),
      "DIAG-REQ-002 selections count",
    );
    await page
      .getByRole("button", { name: "Submit diagnostic", exact: true })
      .click();
    await page.getByText("Baseline set", { exact: true }).first().waitFor();
    check(
      state.submit.answers.length === 6 &&
        state.submit.answers.every((x) => x.choice_id === "a"),
      "DIAG-REQ-002 existing payload",
    );

    await page.goto("http://localhost:5173/course/tutor");
    const input = page.getByPlaceholder("Ask Kala…");
    await input.waitFor();
    await page.getByRole("heading", { level: 1 }).waitFor();
    check(
      await page
        .locator("main")
        .evaluate(
          (el, expected) =>
            parseFloat(getComputedStyle(el.parentElement).paddingLeft) ===
            expected,
          width < 1024 ? 56 : 376,
        ),
      "TUTOR-REQ-004 responsive Tutor offset",
    );
    check(
      (await page
        .getByRole("button", {
          name: /^(Explain|Quiz me on|Help me practice) /,
        })
        .count()) === 0,
      "WI-22 long new-chat starters removed",
    );
    check(
      (await page.locator("[data-study-surface] img[alt=Kala]").count()) === 1,
      "TUTOR-REQ-007 own logo",
    );
    check(
      (await page
        .getByText("Course-grounded help · De-identified before model calls", {
          exact: true,
        })
        .count()) === 0,
      "WI-22 requested footer copy removed",
    );
    check(
      await input.evaluate((el) => {
        const box = el
            .closest("[data-slot=input-group]")
            .getBoundingClientRect(),
          surface = el.closest("[data-study-surface]").getBoundingClientRect();
        return (
          Math.abs(
            box.top + box.height / 2 - (surface.top + surface.height / 2),
          ) <= 1
        );
      }),
      `WI-22 new-chat composer centered in canvas at ${width}`,
    );
    const sendButton = page.getByRole("button", { name: "Send message" });
    check(
      await sendButton.evaluate(
        (el) =>
          parseFloat(getComputedStyle(el).borderTopLeftRadius) >=
          el.getBoundingClientRect().height / 2,
      ),
      "WI-22 send retains shared circular shape",
    );
    if (width >= 1024) {
      const resize = page.getByRole("separator", {
        name: "Resize chat history",
      });
      check(
        (await resize.getAttribute("aria-valuenow")) === "320",
        "WI-22 history starts wider",
      );
      const handle = await resize.boundingBox();
      await page.mouse.move(handle.x + handle.width / 2, handle.y + 150);
      await page.mouse.down();
      await page.mouse.move(handle.x + 1000, handle.y + 150);
      await page.mouse.up();
      check(
        (await resize.getAttribute("aria-valuenow")) === "440",
        "WI-22 drag clamps maximum",
      );
      check(
        await page
          .locator("main")
          .evaluate(
            (el) => getComputedStyle(el.parentElement).paddingLeft === "496px",
          ),
        "WI-22 shell follows dragged history",
      );
      await resize.press("Home");
      check(
        (await resize.getAttribute("aria-valuenow")) === "280",
        "WI-22 keyboard reaches minimum",
      );
      await resize.press("ArrowRight");
      check(
        (await resize.getAttribute("aria-valuenow")) === "296",
        "WI-22 keyboard adjusts width",
      );
      await resize.press("End");
      check(
        (await resize.getAttribute("aria-valuenow")) === "440",
        "WI-22 keyboard reaches maximum",
      );
      await resize.dblclick();
      check(
        (await resize.getAttribute("aria-valuenow")) === "320",
        "WI-22 double-click restores default",
      );
    } else {
      check(
        (await page
          .getByRole("separator", { name: "Resize chat history" })
          .count()) === 0,
        "WI-22 mobile retains Sheet without desktop resize handle",
      );
    }
    await page.getByRole("heading", { level: 1 }).click();
    await screenshot(page, "tutor-empty", width);
    await input.fill("How does object storage work?");
    let release;
    state.holdAsk = new Promise((done) => {
      release = done;
    });
    await page.getByRole("button", { name: "Send message" }).click();
    await page.getByText("Thinking", { exact: true }).waitFor();
    check(
      (await page.getByRole("heading", { level: 1 }).count()) === 0,
      "TUTOR-REQ-006 send leaves empty state",
    );
    await page.waitForURL("**/course/tutor?conversation=created");
    await page.clock.fastForward(8500);
    await page
      .getByText("Still working on it", { exact: true })
      .waitFor({ timeout: 10000 });
    check(
      await page.getByText("Still working on it", { exact: true }).isVisible(),
      "TUTOR-REQ-010 honest elapsed state",
    );
    release();
    state.holdAsk = null;
    await page
      .getByText("Object storage keeps durable copies", { exact: false })
      .first()
      .waitFor();
    await page.clock.resume();
    check(
      await page
        .getByText("How does object storage work?", { exact: true })
        .last()
        .evaluate(
          (el) => parseFloat(getComputedStyle(el).borderTopLeftRadius) >= 20,
        ),
      "WI-22 shared user-bubble rounding restored",
    );
    check(
      await input.evaluate((el) => {
        const group = el
            .closest("[data-slot=input-group]")
            .getBoundingClientRect(),
          surface = el.closest("[data-study-surface]"),
          stream = surface.querySelector("[role=log]").getBoundingClientRect();
        return (
          stream.bottom > group.top &&
          Math.abs(
            surface.getBoundingClientRect().bottom - group.bottom - 16,
          ) <= 1 &&
          getComputedStyle(surface.firstElementChild).borderBottomWidth ===
            "0px"
        );
      }),
      "WI-22 seamless floating Tutor dock overlaps stream with 16px bottom inset",
    );
    check(
      (await page
        .locator("main")
        .getByText("New chat", { exact: true })
        .count()) === 0,
      "WI-22 redundant conversation title header removed",
    );
    await screenshot(page, "tutor-conversation", width);
    check(
      state.creates === 1 && state.asks === 1,
      "TUTOR-REQ-009 lazy creation",
    );
    check(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      "TUTOR-REQ-004 no mobile overflow",
    );
    const data = await page.evaluateHandle(() => {
      const transfer = new DataTransfer();
      transfer.items.add(
        new File(["notes"], "notes.md", { type: "text/markdown" }),
      );
      return transfer;
    });
    await page
      .locator("[data-study-surface]")
      .dispatchEvent("dragenter", { dataTransfer: data });
    await page.getByText("Drop files to attach", { exact: true }).waitFor();
    await screenshot(page, "tutor-drag", width);
    await page
      .locator("[data-study-surface]")
      .dispatchEvent("drop", { dataTransfer: data });
    await page.getByText("notes.md", { exact: true }).waitFor();
    check(state.uploads === 0, "TUTOR-REQ-009 drop stages without upload");
    await page
      .getByRole("button", { name: "Preview notes.md", exact: true })
      .click();
    const fileDialog = page.getByRole("dialog", {
      name: "notes.md",
      exact: true,
    });
    await fileDialog.locator("pre").waitFor();
    check(
      await fileDialog.evaluate((el) => {
        const r = el.getBoundingClientRect();
        return (
          r.left >= 16 &&
          r.right <= innerWidth - 16 &&
          getComputedStyle(el).animationName === "none"
        );
      }),
      "TUTOR-REQ-009 raw preview fits mobile and honors reduced motion",
    );
    await page.screenshot({
      path: resolve(out, `tutor-file-preview-${width}.png`),
    });
    await page.keyboard.press("Escape");
    await page
      .getByRole("button", { name: "Preview notes.md", exact: true })
      .waitFor();
    await page.getByPlaceholder("Ask Kala…").fill("Use my notes");
    await page
      .getByRole("button", { name: "Send message", exact: true })
      .click();
    await page.waitForFunction(() =>
      document
        .querySelector("[data-tutor-file-card]")
        ?.textContent.includes("Attached"),
    );
    check(
      state.uploads === 1 && state.asks === 2,
      "TUTOR-REQ-009 Send uploads before asking through existing routes",
    );
    check(
      (await page
        .getByText("Drop files to attach", { exact: true })
        .count()) === 0,
      "TUTOR-REQ-009 drop clears overlay",
    );
    check(errors.length === 0, "no browser exceptions");
    await context.close();

    const managed = await fixture(width, { reducedMotion: "no-preference" });
    managed.state.rows.push({
      ...row("older"),
      title: "Alpha review",
      updatedAt: "2026-10-23T10:00:00Z",
    });
    await managed.page.goto(
      "http://localhost:5173/course/tutor?conversation=existing",
    );
    await managed.page.getByPlaceholder("Ask Kala…").waitFor();
    if (width < 1024)
      await managed.page
        .getByRole("button", { name: "Open chat history" })
        .click();
    const history =
      width < 1024
        ? managed.page.getByRole("dialog")
        : managed.page.getByRole("complementary", { name: "Tutor chats" });
    const newChat = history.getByRole("button", {
      name: "New chat",
      exact: true,
    });
    const newChatBackground = await newChat.evaluate(
      (el) => getComputedStyle(el).backgroundColor,
    );
    check(
      await newChat.evaluate(
        (el) => getComputedStyle(el).borderTopWidth === "0px",
      ),
      "WI-22 New chat has no outline",
    );
    check(
      await newChat.evaluate(
        (el) =>
          getComputedStyle(el).backgroundColor ===
          getComputedStyle(el.parentElement.closest("[class*=bg-card]"))
            .backgroundColor,
      ),
      "WI-22 New chat matches white history at rest",
    );
    await newChat.hover();
    await managed.page.waitForFunction((before) => {
      const button = [...document.querySelectorAll("button")].find(
        (el) =>
          el.textContent.trim() === "New chat" && el.getClientRects().length,
      );
      return button && getComputedStyle(button).backgroundColor !== before;
    }, newChatBackground);
    check(
      await newChat.evaluate(
        (el, before) => getComputedStyle(el).backgroundColor !== before,
        newChatBackground,
      ),
      "WI-22 New chat gains hover fill",
    );
    const recentTitle = await history
      .getByRole("button", { name: "Understanding cloud storage", exact: true })
      .boundingBox();
    check(
      await newChat.evaluate(
        (el, left) =>
          Math.abs(
            el.getBoundingClientRect().left +
              parseFloat(getComputedStyle(el).paddingLeft) -
              left -
              4,
          ) <= 1,
        recentTitle.x,
      ),
      "WI-22 new-chat icon aligns with recent title inset",
    );
    const sortTrigger = history.getByRole("button", {
      name: "Sort recent chats",
    });
    await sortTrigger.focus();
    await sortTrigger.press("Shift+Tab");
    await managed.page.keyboard.press("Tab");
    const sortBackground = await sortTrigger.evaluate(
      (el) => getComputedStyle(el).backgroundColor,
    );
    await sortTrigger.hover();
    check(
      await sortTrigger.evaluate(
        (el, bg) =>
          getComputedStyle(el).backgroundColor === bg &&
          el.querySelector("svg.lucide-list-filter") &&
          getComputedStyle(el).borderTopWidth === "0px" &&
          parseFloat(getComputedStyle(el).borderRadius) >= 8 &&
          getComputedStyle(el).getPropertyValue("--tw-ring-inset") === "inset",
        sortBackground,
      ),
      "WI-22 dedicated sort icon stays plain on hover",
    );
    await screenshot(managed.page, "tutor-sort-focus", width);
    const sortTriggerBox = await sortTrigger.boundingBox();
    await history.getByRole("button", { name: "Sort recent chats" }).click();
    check(
      await managed.page.getByRole("menu").evaluate(
        (el, bounds) => {
          const box = el.getBoundingClientRect();
          return (
            getComputedStyle(el).animationName === "none" &&
            (bounds.width >= 1024
              ? Math.abs(box.left - bounds.left) <= 1
              : box.left >= 8 && box.right <= bounds.width - 8)
          );
        },
        { width, left: sortTriggerBox.x },
      ),
      "WI-22 sort menu opens immediately toward right, bounded on mobile",
    );
    check(
      await managed.page
        .getByRole("menuitemradio")
        .evaluateAll((items) =>
          items.every((el) => el.querySelector("[data-tutor-sort-icon] svg")),
        ),
      "WI-22 sort choices include Lucide icons",
    );
    await screenshot(managed.page, "tutor-sort", width);
    await managed.page
      .getByRole("menuitemradio", { name: "Title A–Z" })
      .click();
    await history
      .getByRole("button", { name: "Alpha review", exact: true })
      .waitFor();
    const recentOrder = await history
      .getByRole("button")
      .evaluateAll((buttons) =>
        buttons.map(
          (el) => el.getAttribute("aria-label") ?? el.textContent.trim(),
        ),
      );
    check(
      recentOrder.indexOf("Alpha review") <
        recentOrder.indexOf("Understanding cloud storage"),
      "WI-22 title sorting reorders recent rows",
    );
    await history.getByRole("button", { name: "Sort recent chats" }).click();
    check(
      (await managed.page
        .getByRole("menuitemradio", { name: "Title A–Z" })
        .getAttribute("aria-checked")) === "true",
      "WI-22 local Recents sorting retains selection",
    );
    await managed.page.keyboard.press("Escape");
    check(
      await managed.page
        .locator("[data-slot=dropdown-menu-content]")
        .evaluateAll((elements) =>
          elements.every((el) => getComputedStyle(el).animationName === "none"),
        ),
      "WI-22 popup exit has no animation",
    );
    check(
      managed.state.patches === 0,
      "WI-22 sorting makes no hosted metadata writes",
    );
    const recentHeading = history.getByRole("button", { name: /^Recents/ });
    const headingBackground = await recentHeading.evaluate(
      (el) => getComputedStyle(el).backgroundColor,
    );
    await recentHeading.hover();
    await managed.page.clock.fastForward(250);
    check(
      await recentHeading.evaluate(
        (el, before) => getComputedStyle(el).backgroundColor === before,
        headingBackground,
      ),
      "WI-22 Recents heading keeps quiet hover",
    );
    const actionTriggerBox = await history
      .getByRole("button", { name: "Actions for Understanding cloud storage" })
      .boundingBox();
    await history
      .getByRole("button", { name: "Actions for Understanding cloud storage" })
      .click();
    await managed.page.getByRole("menuitem", { name: "Rename" }).waitFor();
    await managed.page.getByRole("menuitem", { name: "Rename" }).hover();
    check(
      await managed.page
        .locator(
          'button[aria-label="Actions for Understanding cloud storage"][data-state=open]',
        )
        .evaluate((el) => getComputedStyle(el.parentElement).opacity === "1"),
      "WI-22 row actions remain visible while popup is open",
    );
    check(
      await managed.page.getByRole("menu").evaluate(
        (el, bounds) => {
          const box = el.getBoundingClientRect();
          return (
            getComputedStyle(el).animationName === "none" &&
            (bounds.width >= 1024
              ? Math.abs(box.left - bounds.left) <= 1
              : box.left >= 8 && box.right <= bounds.width - 8)
          );
        },
        { width, left: actionTriggerBox.x },
      ),
      "WI-22 actions menu opens immediately toward right, bounded on mobile",
    );
    check(
      await managed.page.getByRole("menu").evaluate((el) => {
        const css = getComputedStyle(el);
        return (
          parseFloat(css.borderRadius) >= 12 &&
          parseFloat(css.paddingTop) >= 8 &&
          el.querySelector("[role=separator]")
        );
      }),
      "WI-22 action menu has rounded corners, padding and destructive separator",
    );
    await screenshot(managed.page, "tutor-menu", width);
    await managed.page.getByRole("menuitem", { name: "Rename" }).click();
    await history
      .getByRole("textbox", { name: "Chat title" })
      .fill("Storage review");
    await history.getByRole("button", { name: "Save", exact: true }).click();
    await history
      .getByRole("button", { name: "Storage review", exact: true })
      .waitFor();
    check(
      managed.state.patches === 1,
      "TUTOR-REQ-005 rename from list capability despite detail omission",
    );
    check(
      await history.getByRole("button", { name: "Pinned 1" }).evaluate((el) => {
        const recents = [
          ...el.closest("[class*=overflow-y-auto]").querySelectorAll("button"),
        ].find((x) => /^Recents/.test(x.textContent.trim()));
        return (
          el.getBoundingClientRect().top < recents.getBoundingClientRect().top
        );
      }),
      "WI-22 pinned category precedes Recents",
    );
    const directPin = history.getByRole("button", {
      name: "Pin Storage review",
      exact: true,
    });
    check(
      await directPin.evaluate((el) => {
        const previous = el.previousElementSibling;
        return (
          previous?.getAttribute("aria-label") ===
            "Actions for Storage review" &&
          el.getBoundingClientRect().left >
            previous.getBoundingClientRect().left
        );
      }),
      "WI-22 direct pin follows more-options control",
    );
    await history
      .getByRole("button", { name: "Pin Storage review", exact: true })
      .click();
    await history
      .getByRole("button", { name: "Unpin Storage review", exact: true })
      .waitFor();
    await history
      .getByRole("button", { name: "Unpin Storage review", exact: true })
      .click();
    await history
      .getByRole("button", { name: "Pin Storage review", exact: true })
      .waitFor();
    check(
      managed.state.patches === 3,
      "TUTOR-REQ-005 pin and unpin call PATCH",
    );
    const recents = history.getByRole("button", { name: /^Recents/ });
    await recents.click();
    check(
      !(await history
        .getByRole("button", { name: "Storage review", exact: true })
        .isVisible()),
      "TUTOR-REQ-005 Recents collapses",
    );
    await recents.click();
    await history
      .getByRole("button", { name: "Actions for Storage review" })
      .click();
    await managed.page
      .getByRole("menuitem", { name: "Delete", exact: true })
      .click();
    check(
      managed.state.deletes === 0,
      "TUTOR-REQ-005 menu never deletes directly",
    );
    const confirmation = managed.page.getByRole("dialog", {
      name: "Delete this chat?",
    });
    await confirmation
      .getByRole("button", { name: "Cancel", exact: true })
      .click();
    check(managed.state.deletes === 0, "TUTOR-REQ-005 cancel never deletes");
    await history
      .getByRole("button", { name: "Actions for Storage review" })
      .click();
    await managed.page
      .getByRole("menuitem", { name: "Delete", exact: true })
      .click();
    await confirmation
      .getByRole("button", { name: "Delete chat", exact: true })
      .click();
    await managed.page.waitForURL("http://localhost:5173/course/tutor");
    check(
      managed.state.deletes === 1,
      "TUTOR-REQ-005 confirm deletes once and clears URL",
    );
    check(managed.errors.length === 0, "no sidebar browser exceptions");
    await managed.context.close();
  }
  const focus = await fixture(1440);
  const ariaWarnings = [];
  focus.page.on("console", (message) => {
    if (message.text().includes("Blocked aria-hidden")) ariaWarnings.push(true);
  });
  await focus.page.goto("http://localhost:5173/course/flashcards");
  await focus.page.locator("#tour-flashcards-recommended").click();
  const front = focus.page
    .locator("button")
    .filter({ hasText: "Recall the answer, then flip to check yourself." });
  await front.click();
  const back = focus.page.locator('button[aria-label="Flip to question"]');
  await back.waitFor();
  check(
    await back.evaluate((el) => document.activeElement === el),
    "WI-22 flip focuses visible answer face",
  );
  check(
    await front.evaluate((el) => el.inert),
    "WI-22 hidden question face is inert",
  );
  await back.press("Enter");
  check(
    await front.evaluate((el) => document.activeElement === el && !el.inert),
    "WI-22 flip back restores question focus",
  );
  await front.press("Space");
  check(
    await back.evaluate((el) => document.activeElement === el && !el.inert),
    "WI-22 keyboard flip focuses visible face",
  );
  check(ariaWarnings.length === 0, "WI-22 no hidden-focus console warning");
  await focus.context.close();

  const marqueeName =
    "Understanding cloud storage, networking, security and infrastructure trade-offs";
  for (const reducedMotion of ["no-preference", "reduce"]) {
    const titleFixture = await fixture(1440, { reducedMotion });
    titleFixture.state.rows = [{ ...row("existing"), title: marqueeName }];
    await titleFixture.page.goto(
      "http://localhost:5173/course/tutor?conversation=existing",
    );
    const titleButton = titleFixture.page.getByRole("button", {
      name: marqueeName,
      exact: true,
    });
    await titleButton.waitFor();
    await titleButton.hover();
    await titleFixture.page.clock.runFor(2000);
    const titleSpan = titleButton.locator("[data-tutor-title]");
    check(
      await titleSpan.evaluate((el, reduced) => {
        const css = getComputedStyle(el),
          x =
            css.transform === "none"
              ? 0
              : new DOMMatrixReadOnly(css.transform).m41;
        return reduced
          ? css.visibility === "hidden" && x === 0
          : css.visibility === "visible" && x < -1;
      }, reducedMotion === "reduce"),
      "WI-22 overflow title reveals only with allowed motion",
    );
    await titleFixture.page.clock.runFor(16000);
    check(
      await titleSpan.evaluate(
        (el) => getComputedStyle(el).visibility === "hidden",
      ),
      "WI-22 title completes one trip and returns to ellipsis",
    );
    const newChatButton = titleFixture.page.getByRole("button", {
      name: "New chat",
      exact: true,
    });
    await newChatButton.hover({ position: { x: 100, y: 20 } });
    await titleFixture.page.clock.runFor(150);
    check(
      await newChatButton
        .locator("[data-tutor-action-icon]")
        .evaluate((el, reduced) => {
          const moving = [...el.querySelectorAll("svg, svg *")].some((node) => {
            const transform = getComputedStyle(node).transform;
            return (
              transform !== "none" &&
              !new DOMMatrixReadOnly(transform).isIdentity
            );
          });
          return reduced ? !moving : moving;
        }, reducedMotion === "reduce"),
      "WI-22 whole button drives Lucide feedback and honors reduced motion",
    );
    check(
      titleFixture.errors.length === 0,
      "WI-22 title/icon feedback has no browser exceptions",
    );
    await titleFixture.context.close();
  }
  const primitive = await fixture(1440, { empty: true });
  await primitive.context.route("**/__lane_u_prompt_fixture", (route) =>
    route.fulfill({
      contentType: "text/html",
      body: `<!doctype html><html><head><link rel="stylesheet" href="/src/styles/globals.css"></head><body><div id="root"></div><script type="module">
    import RefreshRuntime from '/@react-refresh';
    RefreshRuntime.injectIntoGlobalHook(window);
    window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;
    </script><script type="module">
    import React from '/node_modules/.vite/deps/react.js';
    import ReactDOM from '/node_modules/.vite/deps/react-dom_client.js';
    import {PromptInput,PromptInputTextarea,PromptInputSubmit,usePromptInputAttachments} from '/src/components/ai-elements/prompt-input.tsx';
    import {ComposeDock} from '/src/components/study/ComposeDock.tsx';
    import {TutorComposer} from '/src/features/tutor/components/TutorComposer.tsx';
    import {StudySurface} from '/src/components/study/StudySurface.tsx';
    import {StudyStream} from '/src/components/study/StudyStream.tsx';
    window.fixtureResult={external:0,submitted:0};
    function Probe(){const a=usePromptInputAttachments();return React.createElement('span',{'data-file-count':a.files.length},a.files.length)}
    function FloatingStudy(){return React.createElement('section',{id:'floating-study',style:{height:400}},React.createElement(StudySurface,{dock:React.createElement(ComposeDock,{onAsk:()=>{},placeholder:'Floating dock'})},React.createElement(StudyStream,null,...Array.from({length:30},(_,i)=>React.createElement('p',{key:i},'Synthetic study explanation '+i)),React.createElement('button',{id:'last-study-action'},'Last study action'))))}
    function App(){const target=React.useRef(null);const [files,setFiles]=React.useState([]);window.setFixtureFiles=setFiles;return React.createElement('main',null,
      React.createElement('section',{id:'study-composer'},React.createElement(ComposeDock,{onAsk:()=>{},placeholder:'Shared dock'})),
      React.createElement('section',{id:'tutor-composer'},React.createElement(TutorComposer,{dropTarget:target,dragging:false,onDragChange:()=>{},attachments:files,onFiles:()=>{},onRemove:()=>setFiles([]),onAsk:()=>{},onTyping:()=>{},pending:false,uploading:false,removingId:null})),
      React.createElement('div',{id:'default-outer'},React.createElement(PromptInput,{id:'default-prompt',onSubmit:m=>{window.fixtureResult.submitted=m.files.length}},React.createElement(Probe),React.createElement(PromptInputTextarea),React.createElement(PromptInputSubmit))),
      React.createElement('div',{id:'opt-in-outer',ref:target},React.createElement(PromptInput,{id:'opt-in-prompt',dropTarget:target,onFilesSelected:files=>{window.fixtureResult.external+=files.length},onSubmit:()=>{}},React.createElement(PromptInputTextarea),React.createElement(PromptInputSubmit))),React.createElement(FloatingStudy))}
    ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(App));
    </script></body></html>`,
    }),
  );
  await primitive.page.goto("http://localhost:5173/__lane_u_prompt_fixture");
  await primitive.page
    .locator("#default-prompt")
    .waitFor()
    .catch(() => {
      throw new Error(
        "Primitive fixture failed: " + primitive.errors.join("; "),
      );
    });
  for (const width of [1440, 375]) {
    await primitive.page.setViewportSize({ width, height: 900 });
    const metrics = await primitive.page.evaluate(() =>
      ["study-composer", "tutor-composer"].map((id) => {
        const root = document.getElementById(id),
          textarea = root.querySelector("textarea"),
          group = root.querySelector("[data-slot=input-group]");
        const input = textarea.getBoundingClientRect(),
          box = group.getBoundingClientRect(),
          css = getComputedStyle(textarea);
        const lineCenter =
          input.top +
          parseFloat(css.paddingTop) +
          parseFloat(css.lineHeight) / 2;
        return {
          height: box.height,
          radius: getComputedStyle(group).borderRadius,
          lineHeight: css.lineHeight,
          offset: Math.abs(lineCenter - (box.top + box.height / 2)),
        };
      }),
    );
    check(
      metrics.every((m) => m.height === 48 && m.offset <= 1),
      `WI-22 vertically centered 48px composers at ${width}`,
    );
    check(
      metrics[0].radius === metrics[1].radius &&
        metrics[0].lineHeight === metrics[1].lineHeight,
      `WI-22 shared dock radius and typography at ${width}`,
    );
    check(
      await primitive.page.locator("#tutor-composer").evaluate((el) => {
        const button = el.querySelector('button[aria-label="Attach a file"]'),
          rect = button.getBoundingClientRect();
        return (
          rect.right <
            el.querySelector("textarea").getBoundingClientRect().left + 1 &&
          rect.width === rect.height &&
          parseFloat(getComputedStyle(button).borderRadius) >= rect.height / 2
        );
      }),
      `WI-22 leading circular attachment at ${width}`,
    );
  }
  await primitive.page.evaluate(() =>
    window.setFixtureFiles([
      { id: "fixture-file", filename: "notes.txt", status: "ready" },
    ]),
  );
  await primitive.page
    .getByRole("button", { name: "Remove notes.txt" })
    .waitFor();
  await primitive.page.waitForFunction(
    () =>
      document
        .querySelector("#tutor-composer [data-slot=input-group]")
        .getBoundingClientRect().height > 100,
  );
  check(
    await primitive.page
      .locator("#tutor-composer [data-slot=input-group]")
      .evaluate(
        (el) =>
          el.getBoundingClientRect().height > 48 &&
          parseFloat(getComputedStyle(el).borderRadius) === 24,
      ),
    "WI-22 attached input expands with a preserved finite corner",
  );
  await primitive.page
    .getByRole("button", { name: "Remove notes.txt" })
    .click();
  await primitive.page.waitForFunction(
    () =>
      document
        .querySelector("#tutor-composer [data-slot=input-group]")
        .getBoundingClientRect().height === 48,
  );
  const transfer = await primitive.page.evaluateHandle(() => {
    const data = new DataTransfer();
    data.items.add(
      new File(["synthetic notes"], "notes.txt", { type: "text/plain" }),
    );
    return data;
  });
  await primitive.page
    .locator("#default-outer")
    .dispatchEvent("drop", { dataTransfer: transfer });
  check(
    (await primitive.page
      .locator("[data-file-count]")
      .getAttribute("data-file-count")) === "0",
    "TUTOR-REQ-009 default drop remains form-scoped",
  );
  await primitive.page
    .locator("#default-prompt")
    .dispatchEvent("drop", { dataTransfer: transfer });
  await primitive.page.locator('[data-file-count="1"]').waitFor();
  await primitive.page.locator("#default-prompt textarea").fill("Explain this");
  await primitive.page.locator("#default-prompt button[type=submit]").click();
  await primitive.page.waitForFunction(
    () => window.fixtureResult.submitted === 1,
  );
  check(
    (await primitive.page
      .locator("[data-file-count]")
      .getAttribute("data-file-count")) === "0",
    "TUTOR-REQ-009 default staging submits and clears",
  );
  await primitive.page
    .locator("#opt-in-outer")
    .dispatchEvent("drop", { dataTransfer: transfer });
  check(
    await primitive.page.evaluate(() => window.fixtureResult.external === 1),
    "TUTOR-REQ-009 opt-in enclosing drop delivers original file",
  );
  check(
    primitive.errors.length === 0,
    "shared primitive fixture has no exceptions",
  );
  await primitive.page.locator("#last-study-action").evaluate((el) => {
    let parent = el.parentElement;
    while (
      parent &&
      !["auto", "scroll"].includes(getComputedStyle(parent).overflowY)
    )
      parent = parent.parentElement;
    parent.scrollTop = parent.scrollHeight;
  });
  check(
    await primitive.page.locator("#last-study-action").evaluate((el) => {
      const surface = el.closest("[data-study-surface]"),
        input = surface
          .querySelector("[data-slot=input-group]")
          .getBoundingClientRect(),
        stream = surface.querySelector("[role=log]").getBoundingClientRect();
      return (
        el.getBoundingClientRect().bottom <= input.top &&
        stream.bottom > input.top
      );
    }),
    "WI-22 shared floating Study dock preserves final-action clearance",
  );
  await primitive.context.close();

  const idle = await fixture(1440, {
    empty: true,
    reducedMotion: "no-preference",
  });
  await idle.page.goto("http://localhost:5173/course/tutor");
  const logo = idle.page.locator("[data-study-surface] img[alt=Kala]");
  await logo.waitFor();
  await idle.page.waitForTimeout(180);
  check(
    await logo.evaluate((el) => getComputedStyle(el).transform !== "none"),
    "TUTOR-REQ-007 empty logo animates when permitted",
  );
  await idle.page.getByPlaceholder("Ask Kala…").fill("A draft");
  await idle.page.waitForTimeout(100);
  check(
    await logo.evaluate((el) =>
      ["none", "matrix(1, 0, 0, 1, 0, 0)"].includes(
        getComputedStyle(el).transform,
      ),
    ),
    "TUTOR-REQ-007 typing stops idle loop",
  );
  // Staging and preview never create a conversation or upload.
  const raw =
    "### Local heading\n<script>window.previewExecuted=true</script>\n**unformatted text**";
  await idle.page.locator("input[type=file]").setInputFiles({
    name: "notes.md",
    mimeType: "text/markdown",
    buffer: Buffer.from(raw),
  });
  const previewButton = idle.page.getByRole("button", {
    name: "Preview notes.md",
    exact: true,
  });
  await previewButton.waitFor();
  check(
    idle.state.creates === 0 && idle.state.uploads === 0,
    "TUTOR-REQ-009 choosing a file stages locally",
  );
  await previewButton.click();
  const previewDialog = idle.page.getByRole("dialog", {
    name: "notes.md",
    exact: true,
  });
  await previewDialog.locator("pre").waitFor();
  check(
    (await previewDialog.locator("pre").textContent()) === raw &&
      (await previewDialog.locator("h3,script,strong").count()) === 0,
    "TUTOR-REQ-009 preview shows raw markdown and HTML as text",
  );
  check(
    await idle.page.evaluate(() => !window.previewExecuted),
    "TUTOR-REQ-009 preview cannot execute file markup",
  );
  check(
    await idle.page
      .locator("[data-slot=dialog-overlay]")
      .evaluate((el) => getComputedStyle(el).backdropFilter !== "none"),
    "TUTOR-REQ-009 preview uses a subtle blurred overlay",
  );
  await idle.page.waitForFunction(
    () =>
      getComputedStyle(document.querySelector("[role=dialog]")).opacity === "1",
  );
  await idle.page.screenshot({
    path: resolve(out, "tutor-file-preview-1440.png"),
  });
  await previewDialog
    .getByRole("button", { name: "Close file preview" })
    .click();
  await previewButton.waitFor();
  await idle.page.waitForFunction(
    () =>
      document.activeElement?.getAttribute("aria-label") === "Preview notes.md",
  );
  check(
    idle.state.creates === 0 && idle.state.uploads === 0,
    "TUTOR-REQ-009 preview closes with focus restored and no upload",
  );
  await idle.page.getByRole("button", { name: "Remove notes.md" }).click();
  await idle.page
    .locator("[data-tutor-file-card]")
    .waitFor({ state: "detached" });
  check(
    (await idle.page.locator("[data-tutor-file-card]").count()) === 0 &&
      idle.state.attachmentDeletes === 0,
    "TUTOR-REQ-009 removing a staged file is local",
  );
  await idle.page.locator("input[type=file]").setInputFiles([
    { name: "notes.md", mimeType: "text/markdown", buffer: Buffer.from(raw) },
    {
      name: "rejected.md",
      mimeType: "text/markdown",
      buffer: Buffer.from("retry synthetic notes"),
    },
  ]);
  check(
    (await idle.page.getByPlaceholder("Ask Kala…").inputValue()) === "A draft",
    "TUTOR-REQ-009 staging preserves the draft",
  );
  await idle.page.waitForFunction(
    () =>
      document
        .querySelector("#tour-tutor-input [data-slot=input-group]")
        .getBoundingClientRect().height > 150,
  );
  await idle.page.getByRole("heading", { level: 1 }).hover();
  await idle.page.waitForFunction(() =>
    [...document.querySelectorAll("[data-tutor-file-card] svg path")].every(
      (el) => getComputedStyle(el).opacity === "1",
    ),
  );
  await idle.page.screenshot({
    path: resolve(out, "tutor-file-staged-1440.png"),
  });
  await idle.page
    .getByRole("button", { name: "Send message", exact: true })
    .click();
  await idle.page
    .getByText("Synthetic upload could not be stored. Please try again.", {
      exact: true,
    })
    .waitFor();
  await idle.page
    .getByText("Upload failed — send to retry", { exact: true })
    .waitFor();
  check(
    idle.state.creates === 1 &&
      idle.state.uploads === 2 &&
      idle.state.asks === 0,
    "TUTOR-REQ-009 partial upload does not ask or duplicate successful files",
  );
  check(
    (await idle.page.getByPlaceholder("Ask Kala…").inputValue()) === "A draft",
    "TUTOR-REQ-009 upload failure preserves the question",
  );
  // Retry only the failed local file; keep the prior successful upload.
  idle.state.rejectUploads = false;
  await idle.page
    .getByRole("button", { name: "Send message", exact: true })
    .click();
  await idle.page
    .getByText("Object storage keeps durable copies", { exact: false })
    .first()
    .waitFor();
  check(
    idle.state.creates === 1 &&
      idle.state.uploads === 3 &&
      idle.state.asks === 1,
    "TUTOR-REQ-009 successful uploads are reused on send retry",
  );
  await idle.context.close();

  const cancelled = await fixture(1440, { empty: true });
  let releaseUpload;
  const heldUpload = new Promise((resolve) => {
    releaseUpload = resolve;
  });
  cancelled.state.holdUpload = () => heldUpload;
  await cancelled.page.goto("http://localhost:5173/course/tutor");
  await cancelled.page.getByPlaceholder("Ask Kala…").fill("Old chat question");
  await cancelled.page.locator("input[type=file]").setInputFiles([
    {
      name: "first.md",
      mimeType: "text/markdown",
      buffer: Buffer.from("first"),
    },
    {
      name: "second.md",
      mimeType: "text/markdown",
      buffer: Buffer.from("second"),
    },
  ]);
  await cancelled.page
    .getByRole("button", { name: "Send message", exact: true })
    .click();
  await cancelled.page.waitForURL("**conversation=created");
  await cancelled.page.waitForFunction(() =>
    document.querySelector('button[aria-label="Attaching files"]'),
  );
  await cancelled.page
    .getByRole("button", { name: "New chat", exact: true })
    .filter({ has: cancelled.page.locator("svg") })
    .click();
  await cancelled.page.waitForURL("http://localhost:5173/course/tutor");
  await cancelled.page.getByPlaceholder("Ask Kala…").fill("New chat draft");
  check(
    await cancelled.page
      .getByRole("button", { name: "Send message", exact: true })
      .isEnabled(),
    "TUTOR-REQ-009 old upload does not lock the new chat",
  );
  releaseUpload();
  cancelled.state.holdUpload = null;
  await cancelled.page.waitForTimeout(250);
  check(
    cancelled.state.uploads === 1 && cancelled.state.asks === 0,
    "TUTOR-REQ-009 switching chat stops remaining batch and ask",
  );
  check(
    (await cancelled.page.getByPlaceholder("Ask Kala…").inputValue()) ===
      "New chat draft",
    "TUTOR-REQ-009 old upload completion preserves the new chat draft",
  );
  await cancelled.context.close();

  const legacy = await fixture(1440, { legacy: true });
  await legacy.page.goto(
    "http://localhost:5173/course/tutor?conversation=existing",
  );
  await legacy.page
    .getByRole("button", { name: "Actions for Understanding cloud storage" })
    .click();
  check(
    (await legacy.page.getByRole("menuitem", { name: "Rename" }).count()) === 0,
    "TUTOR-REQ-005 legacy hides rename",
  );
  check(
    (await legacy.page
      .getByRole("menuitem", { name: "Pin", exact: true })
      .count()) === 0,
    "TUTOR-REQ-005 legacy hides pin",
  );
  check(
    await legacy.page
      .getByRole("menuitem", { name: "Delete", exact: true })
      .isVisible(),
    "TUTOR-REQ-005 legacy retains confirmed delete",
  );
  await legacy.context.close();
  console.log(
    `WI-22 browser checks passed: ${assertions} assertions. Synthetic screenshots: ${out}`,
  );
} finally {
  await browser.close();
}
