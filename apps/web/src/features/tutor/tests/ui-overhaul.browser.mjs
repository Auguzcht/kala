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
    askRequests: [],
    mutations: [],
    plan: [],
    rejectAsk: false,
    uploads: 0,
    attachmentDeletes: 0,
    rejectUploads: true,
    holdUpload: null,
    submit: null,
    holdAsk: null,
    holdPatch: null,
    rejectPatch: false,
    lastPatch: null,
    holdDetail: null,
    holdList: null,
    diagnosticCompleted: false,
    holdDiagnosticSubmit: null,
    masteryRows: [
      {skillId:'storage',skillName:'Choose durable cloud storage and apply appropriate access controls',priorEstimate:null,priorBand:'no-evidence',posteriorEstimate:0.7,posteriorBand:'proficient'},
      {skillId:'network',skillName:'Networking fundamentals',priorEstimate:0.3,priorBand:'developing',posteriorEstimate:0.9,posteriorBand:'mastered'},
      {skillId:'security',skillName:'Security responsibilities',priorEstimate:0.7,priorBand:'proficient',posteriorEstimate:0.7,posteriorBand:'proficient'},
    ],
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
    if (url.pathname.endsWith('/src/lib/celebrate.ts')) {
      const response = await route.fetch();
      const source = await response.text();
      return route.fulfill({response,body:source.replace('celebrated.add(key);', 'celebrated.add(key); (window.__celebrations ??= []).push(key);')});
    }
    if (!url.pathname.startsWith("/__lane_u_api__")) return route.continue();
    const path = url.pathname.slice("/__lane_u_api__".length),
      method = route.request().method();
    if (method !== "GET") state.mutations.push({ path, method });
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
        due: !state.diagnosticCompleted,
        dueSkillCount: state.diagnosticCompleted ? 0 : 6,
      });
    if (path.endsWith("/diagnostic/submit")) {
      state.submit = route.request().postDataJSON();
      if (state.holdDiagnosticSubmit) await state.holdDiagnosticSubmit();
      state.diagnosticCompleted = true;
      return reply({
        correctCount: 6,
        total: 6,
        results: [],
        masteryDelta: state.masteryRows,
      });
    }
    if (path.endsWith("/diagnostic"))
      return reply({
        courseId: "synthetic-course",
        status: "ready",
        readyCount: 6,
        questions: state.diagnosticCompleted ? [] : questions,
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
    if (path === "/tutor/conversations" && method === "GET") {
      if (state.holdList) await state.holdList;
      return reply({ conversations: state.rows });
    }
    if (path === "/tutor/conversations" && method === "POST") {
      state.creates++;
      const created = row("created");
      state.rows.push(created);
      return reply(created);
    }
    if (path === "/tutor/ask") {
      state.asks++;
      const body = route.request().postDataJSON();
      state.askRequests.push(body);
      if (state.holdAsk) await state.holdAsk;
      if (state.rejectAsk) return reply({ detail: 'Synthetic retryable answer failure.' }, 503);
      const { question } = body;
      if(state.skipPersistence)return reply({answer:"Unsaved synthetic answer.",conversationId:body.conversation_id??"created"});
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
          style: body.style,
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
        state.lastPatch = patch;
        if (state.holdPatch) await state.holdPatch;
        if (state.rejectPatch) return reply({detail:"Synthetic rename failed. Please try again."},503);
        const r = state.rows.find((x) => x.id === id);
        if ("title" in patch) r.title = patch.title;
        if ("pinned" in patch)
          r.pinnedAt = patch.pinned ? "2026-10-25T12:00:00Z" : null;
        return reply(r);
      }
      // Detail deliberately omits pinnedAt: capability belongs to list responses.
      if (state.holdDetail) await state.holdDetail;
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
    if (path.endsWith("/plan")) return reply({ courseId: 'synthetic-course', plan: state.plan });
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
const edgesOf = (locator) => locator.evaluate((el) => {
  const { left, right, width } = el.getBoundingClientRect();
  return { left, right, width };
});
const matchingEdges = (a, b) => Math.abs(a.left - b.left) <= 1 && Math.abs(a.right - b.right) <= 1;
try {
  for (const width of [375, 1440]) {
    const assigned = await fixture(width);
    const title = 'Reinforce cloud cost comparison';
    const topic = 'Compare cloud and traditional IT infrastructure';
    assigned.state.messages = [{ id: 'old-answer', role: 'assistant', content: 'Existing saved chat content', style: 'default', createdAt: '2026-10-27T10:00:00Z' }];
    assigned.state.plan = [
      { id: 'assigned-tutor', title, kind: 'tutor', priority: 'high', status: 'approved', skillId: 'storage', skillName: topic, instructorNote: 'Instructor note is displayed but not automatically sent', assignedAt: null },
      { id: 'assigned-practice', title: 'Assigned practice', kind: 'practice', priority: 'medium', status: 'approved', skillId: 'storage', skillName: topic, instructorNote: null, assignedAt: null },
      { id: 'assigned-outreach', title: 'Talk with your instructor', kind: 'outreach', priority: 'low', status: 'approved', skillId: null, skillName: null, instructorNote: null, assignedAt: null },
    ];
    const start = async () => {
      await assigned.page.goto('http://localhost:5173/course');
      const row = assigned.page.getByText(title, { exact: true }).locator('../..');
      await row.getByRole('button', { name: 'Start', exact: true }).click();
      await assigned.page.waitForURL('http://localhost:5173/course/tutor');
      await assigned.page.getByPlaceholder('Ask Kala…').waitFor();
    };
    await start();
    const input = assigned.page.getByPlaceholder('Ask Kala…');
    const initialText = await input.inputValue();
    check(initialText.includes(topic) && /key ideas.*example/.test(initialText), `TUTOR-REQ-018 assigned Start seeds relevant topic at ${width}`);
    check(await input.evaluate(el => el === document.activeElement) && await assigned.page.getByText('Existing saved chat content', { exact: true }).count() === 0, `TUTOR-REQ-018 fresh draft is focused without resuming saved chat at ${width}`);
    check(assigned.state.mutations.length === 0 && !assigned.page.url().includes(topic) && !assigned.page.url().includes('conversation='), `TUTOR-REQ-018 Start has no mutations or prompt in URL at ${width}`);
    check(!initialText.includes('Instructor note') && !initialText.includes('Demo learner'), `TUTOR-REQ-018 draft excludes note and profile at ${width}`);
    const edited = initialText + ' Focus on running costs.';
    await input.fill(edited);
    await assigned.page.locator('input[type=file]').setInputFiles({ name: 'draft.txt', mimeType: 'text/plain', buffer: Buffer.from('Local staged attachment') });
    await assigned.page.getByRole('button', { name: 'Remove draft.txt', exact: true }).waitFor();
    check(await input.inputValue() === edited && assigned.state.mutations.length === 0, `TUTOR-REQ-018 rerender and staging preserve edits without upload at ${width}`);
    await assigned.page.getByRole('button', { name: 'Remove draft.txt', exact: true }).click();
    if (width < 1024) await assigned.page.getByRole('button', { name: 'Open chat history' }).click();
    await assigned.page.getByRole('button', { name: 'New chat', exact: true }).filter({ has: assigned.page.locator('svg') }).click();
    await assigned.page.waitForFunction(() => document.querySelector('#tour-tutor-input textarea')?.value === '');
    check(await input.inputValue() === '' && assigned.state.mutations.length === 0, `TUTOR-REQ-018 New chat clears handoff without reapplying it at ${width}`);
    assigned.state.plan[0].skillName = null;
    await start();
    const fallbackText = await input.inputValue();
    check(fallbackText.includes(title), `TUTOR-REQ-018 missing skill uses assignment title at ${width}`);
    await input.fill(fallbackText + ' Give me a concrete example.');
    assigned.state.messages = [];
    if (width === 375) await input.press('Enter');
    else await assigned.page.getByRole('button', { name: 'Send message', exact: true }).click();
    await assigned.page.waitForURL('**/course/tutor?conversation=created');
    await assigned.page.locator('#tour-tutor-response').waitFor();
    check(assigned.state.creates === 1 && assigned.state.asks === 1 && assigned.state.askRequests[0].question === fallbackText + ' Give me a concrete example.', `TUTOR-REQ-018 explicit Enter/Send creates new chat and asks edited draft once at ${width}`);
    check(assigned.state.askRequests[0].conversation_id === 'created' && assigned.state.mutations.length === 2 && assigned.state.uploads === 0 && assigned.state.patches === 0, `TUTOR-REQ-018 submission uses fresh conversation without plan mutation at ${width}`);
    await screenshot(assigned.page, 'assigned-tutor-submitted', width);
    await assigned.page.goto('http://localhost:5173/course');
    const outreach = assigned.page.getByText('Talk with your instructor', { exact: true }).locator('../..');
    check(await outreach.getByRole('button').count() === 0, `INSTR-REQ-007 outreach keeps no invented CTA at ${width}`);
    await assigned.page.getByText('Assigned practice', { exact: true }).locator('../..').getByRole('button', { name: 'Start', exact: true }).click();
    await assigned.page.waitForURL('http://localhost:5173/course/skills');
    check(assigned.errors.length === 0, `INSTR-REQ-007 other Start destination remains unchanged at ${width}`);
    await assigned.context.close();
  }
  for (const width of [375, 1440]) {
    const follow = await fixture(width);
    const original = 'What is object storage?';
    follow.state.messages = [
      { id: 'original-user', role: 'user', content: original, style: null, createdAt: '2026-10-27T10:00:00Z' },
      { id: 'original-answer', role: 'assistant', content: 'Object storage keeps data as durable objects.', style: 'default', createdAt: '2026-10-27T10:00:01Z' },
    ];
    await follow.page.goto('http://localhost:5173/course/tutor?conversation=existing');
    await follow.page.getByRole('button', { name: "Explain like I'm 5", exact: true }).waitFor();
    check(await follow.page.getByRole('button',{name:"Explain like I'm 5",exact:true}).locator('[aria-hidden=true]').innerText()==='🧸',`TUTOR-REQ-021 simple explanation uses a static emoji at ${width}`);
    check(await follow.page.getByRole('button',{name:'More detail',exact:true}).locator('[aria-hidden=true]').innerText()==='🔎',`TUTOR-REQ-021 detail uses a static emoji at ${width}`);

    const historyInput=follow.page.getByPlaceholder('Ask Kala…');
    await historyInput.press('ArrowUp');
    check(await historyInput.inputValue()===original,`TUTOR-REQ-022 saved history recalls only the user prompt at ${width}`);
    await historyInput.press('ArrowDown');
    check(await historyInput.inputValue()===''&&follow.state.asks===0,`TUTOR-REQ-022 saved browsing restores empty without asking at ${width}`);
    await follow.page.evaluate(()=>{window.__messageCopies=[];Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.__messageCopies.push(text);}}});});
    const copyByKeyboard=async button=>{await button.focus();await button.press('Enter');};
    await copyByKeyboard(follow.page.getByRole('button',{name:'Copy your message',exact:true}).first());
    check(await follow.page.evaluate(()=>window.__messageCopies.at(-1))===original,`TUTOR-REQ-017 saved user content copies exactly at ${width}`);
    await copyByKeyboard(follow.page.getByRole('button',{name:"Copy Kala's reply",exact:true}).first());
    check(await follow.page.evaluate(()=>window.__messageCopies.at(-1))==='Object storage keeps data as durable objects.',`TUTOR-REQ-017 saved reply content copies exactly at ${width}`);
    check(follow.state.asks===0,`TUTOR-REQ-017 saved-message copy sends no ask at ${width}`);
    for (const [label, style, intent] of [["Explain like I'm 5", 'eli5', "Explain your last answer like I'm 5"], ['More detail', 'detail', 'Explain your last answer in more detail']]) {
      let release;
      follow.state.holdAsk = new Promise(done => { release = done; });
      await follow.page.getByRole('button', { name: label, exact: true }).click();
      const pendingUser = follow.page.locator('#tour-tutor-user-turn');
      await pendingUser.waitFor();
      check((await pendingUser.innerText()).startsWith(intent), `TUTOR-REQ-021 ${style} immediately renders explicit user instruction at ${width}`);
      await follow.page.locator('#tour-tutor-thinking').waitFor();
      await copyByKeyboard(pendingUser.getByRole('button',{name:'Copy your message',exact:true}));
      check((await follow.page.evaluate(()=>window.__messageCopies.at(-1))).startsWith(intent),`TUTOR-REQ-017 pending user turn copies its own explicit question at ${width}`);
      check(await follow.page.locator('#tour-tutor-thinking').getByRole('button').count()===0,`TUTOR-REQ-017 pending Kala reply has no copy control at ${width}`);

      const request = follow.state.askRequests.at(-1);
      check(request.question.startsWith(intent) && request.question !== original && request.style === style && request.conversation_id === 'existing', `TUTOR-REQ-021 ${style} request keeps intent/style/conversation at ${width}`);
      check(await follow.page.locator('svg.animate-spin').count() === 0 && await follow.page.locator('#tour-tutor-thinking [role=status]').count() === 1, `TUTOR-REQ-021 ${style} one pending indicator at ${width}`);
      release(); follow.state.holdAsk = null;
      await pendingUser.waitFor({ state: 'detached' });
      await follow.page.getByRole('button', { name: 'More detail', exact: true }).waitFor();
      check(await follow.page.getByText(original, { exact: true }).count() === 1, `TUTOR-REQ-021 ${style} never copies original input at ${width}`);
    }
    follow.state.rejectAsk = true;
    await follow.page.getByRole('button', { name: "Explain like I'm 5", exact: true }).click();
    await follow.page.getByRole('button', { name: 'Retry', exact: true }).waitFor();
    const failedRequest = follow.state.askRequests.at(-1);
    check(await follow.page.getByRole('button',{name:'More detail',exact:true}).count()===0,`TUTOR-REQ-021 failed newer turn hides old explanation actions at ${width}`);
    await historyInput.press('ArrowUp');
    check(await historyInput.inputValue()===failedRequest.question,`TUTOR-REQ-022 failed visible user turn remains available in history at ${width}`);
    await historyInput.press('ArrowDown');
    check(await historyInput.inputValue()==='',`TUTOR-REQ-022 failed-turn browsing restores empty draft at ${width}`);
    follow.state.rejectAsk = false;
    await follow.page.getByRole('button', { name: 'Retry', exact: true }).click();
    await follow.page.locator('#tour-tutor-user-turn').waitFor({ state: 'detached' });
    check(JSON.stringify(follow.state.askRequests.at(-1)) === JSON.stringify(failedRequest), `TUTOR-REQ-021 retry preserves exact follow-up request at ${width}`);
    follow.state.skipPersistence=true;
    await follow.page.getByRole('button',{name:'More detail',exact:true}).click();
    await follow.page.getByText('This answer may not have been saved.',{exact:true}).waitFor();
    const asksBeforeCopy=follow.state.asks;
    await copyByKeyboard(follow.page.getByRole('button',{name:'Copy your message',exact:true}).last());
    check(await follow.page.evaluate(()=>window.__messageCopies.at(-1))===follow.state.askRequests.at(-1).question,`TUTOR-REQ-017 local user turn copies its captured request at ${width}`);
    await copyByKeyboard(follow.page.getByRole('button',{name:"Copy Kala's reply",exact:true}).last());
    check(await follow.page.evaluate(()=>window.__messageCopies.at(-1))==='Unsaved synthetic answer.',`TUTOR-REQ-017 local answer excludes save-status text at ${width}`);
    check(follow.state.asks===asksBeforeCopy,`TUTOR-REQ-017 local copy makes no additional ask at ${width}`);
    await historyInput.fill('Keep my draft');
    await historyInput.press('ArrowUp');
    check(await historyInput.inputValue()===follow.state.askRequests.at(-1).question,`TUTOR-REQ-022 local unsaved user prompt joins the same history at ${width}`);
    await historyInput.press('ArrowDown');
    check(await historyInput.inputValue()==='Keep my draft'&&follow.state.asks===asksBeforeCopy,`TUTOR-REQ-022 local browsing restores draft without a new ask at ${width}`);
    await historyInput.fill('');
    check(follow.state.creates === 0 && follow.state.uploads === 0 && follow.state.patches === 0 && follow.state.deletes === 0, `TUTOR-REQ-021 explanation chips make only the existing ask at ${width}`);
    const completedBeforeGreeting=await follow.page.locator('[data-tutor-message=assistant]').count();
    await follow.page.getByPlaceholder('Ask Kala…').fill('Hello!');await follow.page.getByPlaceholder('Ask Kala…').press('Enter');
    await follow.page.waitForFunction(n=>document.querySelectorAll('[data-tutor-message=assistant]').length===n+1,completedBeforeGreeting);
    check(await follow.page.getByRole('button',{name:'More detail',exact:true}).count()===0,`TUTOR-REQ-021 local unsaved greeting hides chips after older learning turns at ${width}`);
    follow.state.skipPersistence=false;
    follow.state.messages.push({id:'casual-user',role:'user',content:'Hello!',style:null,createdAt:'2026-10-28T00:00:01Z'}, {id:'casual-answer',role:'assistant',content:'Hello! What would you like to learn today?',style:'default',createdAt:'2026-10-28T00:00:02Z'});
    await follow.page.reload();
    await follow.page.getByText('Hello! What would you like to learn today?',{exact:true}).waitFor();
    check(await follow.page.getByRole('button',{name:"Explain like I'm 5",exact:true}).count()===0&&await follow.page.getByRole('button',{name:'More detail',exact:true}).count()===0,`TUTOR-REQ-021 casual latest turn hides chips despite older learning messages at ${width}`);
    follow.state.messages.push({id:'learning-user',role:'user',content:'Hi, can you explain cloud storage?',style:null,createdAt:'2026-10-28T00:00:03Z'}, {id:'learning-answer',role:'assistant',content:'Object storage keeps data as durable objects.',style:'default',createdAt:'2026-10-28T00:00:04Z'});
    await follow.page.reload();
    await follow.page.getByRole('button',{name:'More detail',exact:true}).waitFor();
    check(await follow.page.getByRole('button',{name:"Explain like I'm 5",exact:true}).isVisible(),`TUTOR-REQ-021 reopened mixed greeting/learning exchange retains chips at ${width}`);
    check(follow.errors.length === 0, `TUTOR-REQ-021 no runtime errors at ${width}`);
    await screenshot(follow.page, 'tutor-explicit-followups', width);
    await follow.context.close();
  }
  for (const width of [375, 1440]) {
    const scrolling = await fixture(width);
    scrolling.state.messages = Array.from({ length: 60 }, (_, i) => ({ id: `long-answer-${i}`, role: 'assistant', content: `Synthetic paragraph ${i} with enough text to overflow the reading surface.`, style: 'default', createdAt: '2026-10-27T10:00:00Z' }));
    await scrolling.page.goto('http://localhost:5173/course/tutor?conversation=existing');
    await scrolling.page.locator('#tour-tutor-response').waitFor();
    await scrolling.page.clock.fastForward(10000);
    await scrolling.page.clock.resume();
    const scroller = scrolling.page.locator('[role=log] > div');
    const scrollEdges = await edgesOf(scroller);
    check(Math.abs(scrollEdges.right - width) <= 1, `DESIGN-REQ-002 overflowing Tutor native scrollbar stays at viewport right edge at ${width}`);
    check(await scroller.evaluate(el => el.scrollHeight > el.clientHeight), `DESIGN-REQ-002 Tutor scrollbar fixture really overflows at ${width}`);
    const answerEdges = await edgesOf(scrolling.page.locator('#tour-tutor-response'));
    check(matchingEdges(answerEdges, await edgesOf(scrolling.page.locator('#tour-tutor-input [data-slot=input-group]'))), `DESIGN-REQ-002 full-width scroller preserves Tutor column at ${width}`);
    await scrolling.page.addStyleTag({ content: '[role=log] > div::-webkit-scrollbar { width: 16px; } [role=log] > div { overflow-y: scroll; }' });
    check(matchingEdges(answerEdges, await edgesOf(scrolling.page.locator('#tour-tutor-response'))) && matchingEdges(answerEdges, await edgesOf(scrolling.page.locator('#tour-tutor-input [data-slot=input-group]'))), `DESIGN-REQ-002 persistent scrollbar preserves matching column edges at ${width}`);
    check(await scroller.evaluate(el => getComputedStyle(el).overflowX === 'hidden') && Math.abs((await edgesOf(scroller)).right - width) <= 1, `DESIGN-REQ-002 persistent scrollbar stays at right without a horizontal scrollbar at ${width}`);
    await scrolling.page.waitForFunction(() => {
      const el = document.querySelector('[role=log] > div');
      return el.scrollTop + el.clientHeight >= el.scrollHeight - 2;
    });
    const bottomPosition = await scroller.evaluate(el => el.scrollTop);
    await scroller.hover();
    await scrolling.page.mouse.wheel(0, -100000);
    await scrolling.page.waitForFunction(before => document.querySelector('[role=log] > div').scrollTop < before - 20, bottomPosition);
    check(await scroller.evaluate(el => el.scrollTop < el.scrollHeight - el.clientHeight - 20) && await scrolling.page.evaluate(() => window.scrollY === 0), `DESIGN-REQ-002 Tutor retains stream scroll ownership at ${width}`);
    console.log(`WI-34 overflowing Tutor scroller at ${width}: ${JSON.stringify(scrollEdges)}`);
    await screenshot(scrolling.page, 'tutor-page-edge-scrollbar', width);
    check(scrolling.errors.length === 0, 'Tutor full-width scrollbar has no runtime errors');
    await scrolling.context.close();
  }
  for (const width of [1440, 375]) {
    const { context, page, state, errors } = await fixture(width, {
      empty: true,
    });
    const headerType = () => page.getByRole('heading',{level:1}).evaluate(el => {
      const parts=[el,...el.parentElement.querySelectorAll('p')];
      return parts.map(part=>{
        const style=getComputedStyle(part);
        return [style.fontFamily,style.fontSize,style.fontWeight,style.lineHeight,style.letterSpacing];
      });
    });
    await page.goto('http://localhost:5173/course/skills');
    await page.getByRole('heading',{name:'Choose a skill',exact:true}).waitFor();
    const skillsHeaderType=await headerType();
    const skillsHeaderBox=await page.getByRole('heading',{level:1}).boundingBox();
    await screenshot(page,'skills-header',width);
    await page.goto('http://localhost:5173/course/twin');
    await page.getByRole('heading',{name:'Your twin',exact:true}).waitFor();
    check(JSON.stringify(await headerType())===JSON.stringify(skillsHeaderType),'WI-22 Skills and Twin header typography matches');
    await page.goto("http://localhost:5173/course/diagnostic");
    await page
      .getByRole("button", { name: "Submit diagnostic", exact: true })
      .waitFor().catch(async (error) => { throw new Error(`Diagnostic fixture: ${errors.join('; ')}; ${await page.locator('body').innerText()}; ${error.message}`); });
    check(JSON.stringify(await headerType())===JSON.stringify(skillsHeaderType),'DIAG-REQ-001 Diagnostic header typography matches Skills and Twin');
    const diagnosticHeaderBox=await page.getByRole('heading',{level:1}).boundingBox();
    check(Math.abs(diagnosticHeaderBox.x-skillsHeaderBox.x)<1&&Math.abs(diagnosticHeaderBox.y-skillsHeaderBox.y)<1,'DIAG-REQ-001 Diagnostic margins match Skills at the same viewport');
    check(skillsHeaderType[0][1]==='24px'&&skillsHeaderType[2][1]==='14px','DIAG-REQ-001 shared page title and description use the same 24px/14px tokens');
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
    check(await page.getByRole('heading',{name:'Find your starting point',level:1,exact:true}).isVisible(),
      'DIAG-REQ-001 compact purpose header is visible');
    check(await page.getByText('Answer a few questions so Kala can understand what you already know and where to begin.',{exact:true}).isVisible(),
      'DIAG-REQ-001 explanation describes the starting-point purpose');
    check(await page.locator('[data-study-surface]').evaluate(surface => {
      const card=[...surface.querySelector('#tour-diagnostic-card').children].find(el=>el.querySelector('button')).getBoundingClientRect();
      const title=surface.querySelector('header h1').getBoundingClientRect();
      const footer=surface.querySelector('footer');
      const count=footer.querySelector('[role=status]').getBoundingClientRect();
      const submit=footer.querySelector('button').getBoundingClientRect();
      return title.left>=surface.getBoundingClientRect().left+24 && Math.abs(card.left-count.left)<1 && Math.abs(card.right-submit.right)<1 &&
        getComputedStyle(surface.querySelector('header')).borderBottomWidth==='1px';
    }), 'DIAG-REQ-001/002 title uses page-content margins; footer aligns to cards');
    await screenshot(page,'diagnostic-introduction',width);
    const choices=page.locator('#tour-diagnostic-choices').getByRole('button');
    await choices.nth(0).hover();
    await page.waitForTimeout(200);
    const neutralHover=await choices.nth(0).evaluate(el=>getComputedStyle(el).backgroundColor);
    await choices.nth(0).click();
    await page.waitForTimeout(200);
    const selectedHover=await choices.nth(0).evaluate(el=>getComputedStyle(el).backgroundColor);
    check(selectedHover!==neutralHover && await choices.nth(0).getAttribute('aria-pressed')==='true',
      'DIAG-REQ-006 click retains visible selection under the stationary pointer');
    await page.getByRole('heading',{name:'Find your starting point'}).hover();
    await choices.nth(0).hover();
    await page.waitForTimeout(200);
    check(await choices.nth(0).evaluate((el,color)=>getComputedStyle(el).backgroundColor===color,selectedHover),
      'DIAG-REQ-006 returning hover preserves selected fill');
    await choices.nth(1).click();
    check(await choices.nth(0).getAttribute('aria-pressed')==='false' && await choices.nth(1).getAttribute('aria-pressed')==='true' &&
      await page.getByText('1 of 6 answered',{exact:true}).isVisible(),
      'DIAG-REQ-006 changing choice moves selection without double counting');
    await choices.nth(0).press('Enter');
    check(await choices.nth(0).getAttribute('aria-pressed')==='true',
      'DIAG-REQ-006 keyboard choice exposes the selected state');
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
    check(await page.getByRole('heading',{name:'Find your starting point'}).isVisible(),
      'DIAG-REQ-001 compact introduction stays visible while questions scroll');
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
    check((await page.getByRole('heading',{name:'Find your starting point'}).count())===0,
      'DIAG-REQ-001 answering introduction leaves on result reveal');
    check(
      state.submit.answers.length === 6 &&
        state.submit.answers.every((x) => x.choice_id === "a"),
      "DIAG-REQ-002 existing payload",
    );
    check((await page.getByRole('dialog').count())===0 && (await page.locator('footer').count())===0,
      'DIAG-REQ-007 completion has no modal or duplicate footer');
    check((await page.getByRole('button',{name:'Back to workspace',exact:true}).count())===1 &&
      (await page.getByRole('button',{name:'View your twin',exact:true}).count())===1,
      'DIAG-REQ-007 exactly one action per destination');
    check(await page.getByText('Networking fundamentals',{exact:true}).isVisible(),
      'DIAG-REQ-007 returned skill progression remains available');
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      'DIAG-REQ-007 long mastery names fit mobile');
    check(await page.locator('[data-mastery-marker]').evaluateAll(markers=>markers.every(marker=>{
      const track=marker.parentElement.getBoundingClientRect();
      const label=marker.parentElement.nextElementSibling.getBoundingClientRect();
      return track.right<=label.left || track.bottom<=label.top || label.right<=track.left || label.bottom<=track.top;
    })), 'DIAG-REQ-007 mastery tracks never overlap prior/posterior labels');
    check(await page.evaluate(() => !(window.__celebrations?.length)),
      'DIAG-REQ-007 reduced motion suppresses confetti');
    await screenshot(page,'diagnostic-results',width);
    await page.getByRole('button',{name:width===1440?'Back to workspace':'View your twin',exact:true}).click();
    await page.waitForURL(width===1440?'http://localhost:5173/course':'http://localhost:5173/course/twin');
    check(true,'DIAG-REQ-007 completion destination navigation');
    await page.goto('http://localhost:5173/course/diagnostic');
    await page.getByText("You're all caught up",{exact:true}).waitFor();
    check((await page.locator('[data-diagnostic-results]').count())===0,
      'DIAG-REQ-007 later visit uses actual caught-up state');

    await page.goto("http://localhost:5173/course/tutor");
    const input = page.getByPlaceholder("Ask Kala…");
    await input.waitFor();
    await page.getByRole("heading", { level: 1 }).waitFor();
    const composer = page.locator('#tour-tutor-input [data-slot=input-group]');
    const emptyComposerEdges = await edgesOf(composer);
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
    check(await page.locator('#tour-tutor-thinking [role=status]').count() === 1
      && await page.locator('svg.animate-spin').count() === 0,
      'TUTOR-REQ-010 one model shimmer with no spinner');
    check(await page.getByRole('button',{name:'Send message',exact:true}).isDisabled()
      && await page.getByRole('button',{name:'Send message',exact:true}).locator('svg').count() === 1,
      'TUTOR-REQ-010 initiating Send keeps its stable icon and name');
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
    const messageEdges = await edgesOf(page.locator('#tour-tutor-response'));
    const composerEdges = await edgesOf(composer);
    check(matchingEdges(messageEdges, composerEdges), `DESIGN-REQ-002 Tutor message/composer edges match at ${width}`);
    check(matchingEdges(emptyComposerEdges, composerEdges), `DESIGN-REQ-002 Tutor empty/conversation composer edges match at ${width}`);
    const userBubbleEdges = await edgesOf(page.getByText('How does object storage work?', { exact: true }).last());
    check(Math.abs(userBubbleEdges.right - composerEdges.right) <= 1, `DESIGN-REQ-002 Tutor user bubble stays at column right edge at ${width}`);
    await page.locator('input[type=file]').setInputFiles({ name: 'column.txt', mimeType: 'text/plain', buffer: Buffer.from('Synthetic column check') });
    await page.getByRole('button', { name: 'Remove column.txt', exact: true }).waitFor();
    const attachmentComposerEdges = await edgesOf(composer);
    check(matchingEdges(messageEdges, attachmentComposerEdges), `DESIGN-REQ-002 Tutor attachment composer retains edges at ${width}`);
    console.log(`WI-34 Tutor edges at ${width}: ${JSON.stringify({ message: messageEdges, composer: composerEdges, emptyComposer: emptyComposerEdges, attachmentComposer: attachmentComposerEdges, userBubble: userBubbleEdges })}`);
    await screenshot(page, 'shared-column-tutor', width);
    await page.getByRole('button', { name: 'Remove column.txt', exact: true }).click();
    check(await page.locator('#tour-tutor-thinking').count()===0,
      'TUTOR-REQ-010 completed answer removes the waiting indicator');
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
    check(
      await page.locator('[data-tutor-drop-overlay] svg g').evaluate(el =>
        getComputedStyle(el).transform === "none" || getComputedStyle(el).transform === "matrix(1, 0, 0, 1, 0, 0)"),
      "TUTOR-REQ-009 Upload glyph is static under reduced motion",
    );
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
    const rename = managed.page.getByRole('dialog',{name:'Rename chat',exact:true});
    const titleInput = rename.getByRole('textbox',{name:'Chat title'});
    await titleInput.waitFor();
    check(await rename.getByText('Keep it short and recognizable',{exact:true}).isVisible(),
      'TUTOR-REQ-012 dialog helper');
    check(await titleInput.evaluate(el => document.activeElement === el && el.value === 'Understanding cloud storage'
      && el.selectionStart === 0 && el.selectionEnd === el.value.length),
      'TUTOR-REQ-012 initial title selected and focused');
    check(await managed.page.locator('[data-tour=tutor-history] input[aria-label="Chat title"]').count() === 0,
      'TUTOR-REQ-012 no inline rename row');
    check(await rename.getByRole('button',{name:'Save',exact:true}).isDisabled(),
      'TUTOR-REQ-012 unchanged title disabled');
    await titleInput.fill('   ');
    check(await rename.getByRole('button',{name:'Save',exact:true}).isDisabled(),
      'TUTOR-REQ-012 blank title disabled');
    await titleInput.fill(' Understanding cloud storage ');
    check(await rename.getByRole('button',{name:'Save',exact:true}).isDisabled(),
      'TUTOR-REQ-012 trimmed unchanged title disabled');
    await titleInput.press('Escape');
    await rename.waitFor({state:'detached'});
    await managed.page.waitForFunction(()=>document.activeElement?.getAttribute('aria-label')==='Actions for Understanding cloud storage');
    check(managed.state.patches === 0 && await history.getByRole('button',{
      name:'Actions for Understanding cloud storage'}).evaluate(el=>document.activeElement===el),
      'TUTOR-REQ-012 Escape sends no PATCH and restores trigger focus');
    async function openRename(name) {
      const actions=history.getByRole('button',{name:`Actions for ${name}`,exact:true});
      await actions.focus();
      await actions.press('Enter');
      await managed.page.getByRole('menuitem',{name:'Rename',exact:true}).press('Enter');
      await titleInput.waitFor();
    }
    await openRename('Understanding cloud storage');
    await titleInput.fill('Discarded name');
    await rename.getByRole('button',{name:'Cancel',exact:true}).click();
    await rename.waitFor({state:'detached'});
    await managed.page.waitForFunction(()=>document.activeElement?.getAttribute('aria-label')==='Actions for Understanding cloud storage');
    check(managed.state.patches===0 && await history.getByRole('button',{
      name:'Actions for Understanding cloud storage'}).evaluate(el=>document.activeElement===el),
      'TUTOR-REQ-012 keyboard opening and Cancel restore focus without PATCH');
    await openRename('Understanding cloud storage');
    await titleInput.fill('  Storage review  ');
    await screenshot(managed.page,'tutor-rename-dialog',width);
    let releasePatch;
    managed.state.holdPatch=new Promise(done=>{releasePatch=done});
    await titleInput.press('Enter');
    await managed.page.waitForFunction(()=>document.querySelector('[role=dialog] button[aria-busy=true]'));
    await titleInput.press('Enter');
    const save=rename.getByRole('button',{name:'Save',exact:true});
    check(await save.isDisabled() && await titleInput.isDisabled()
      && await save.locator('svg.animate-spin').count()===1
      && await managed.page.locator('svg.animate-spin').count()===1,
      'TUTOR-REQ-012 pending lock and one spinner only in activated Save');
    check(managed.state.patches===1 && managed.state.lastPatch.title==='Storage review',
      'TUTOR-REQ-012 Enter sends exactly one trimmed PATCH');
    releasePatch();
    managed.state.holdPatch=null;
    await history
      .getByRole("button", { name: "Storage review", exact: true })
      .waitFor();
    check(
      managed.state.patches === 1,
      "TUTOR-REQ-005 rename from list capability despite detail omission",
    );
    await rename.waitFor({state:'detached'});
    await managed.page.waitForFunction(()=>document.activeElement?.getAttribute('aria-label')==='Actions for Storage review');
    check(await history.getByRole('button',{name:'Actions for Storage review'}).evaluate(el=>document.activeElement===el),
      'TUTOR-REQ-012 successful Save restores trigger focus');
    await openRename('Storage review');
    await titleInput.fill('Failed rename');
    managed.state.rejectPatch=true;
    await rename.getByRole('button',{name:'Save',exact:true}).click();
    await rename.getByRole('alert').waitFor();
    check(await rename.getByRole('alert').textContent()==='Synthetic rename failed. Please try again.'
      && await titleInput.inputValue()==='Failed rename',
      'TUTOR-REQ-012 failure retains draft and safe retry feedback');
    managed.state.rejectPatch=false;
    await titleInput.press('Escape');
    await rename.waitFor({state:'detached'});
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
      managed.state.patches === 4,
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
  const completed = await fixture(1440,{empty:true,reducedMotion:'no-preference'});
  let finishDiagnostic;
  const diagnosticGate = new Promise(resolve=>{finishDiagnostic=resolve});
  completed.state.holdDiagnosticSubmit=()=>diagnosticGate;
  await completed.page.goto('http://localhost:5173/course/diagnostic');
  await completed.page.locator('#tour-diagnostic-choices').waitFor();
  for(let i=0;i<6;i++) await completed.page.locator('#tour-diagnostic-card').getByRole('button').nth(i*3).click();
  await completed.page.getByRole('button',{name:'Submit diagnostic',exact:true}).click();
  const submitting = completed.page.getByRole('button',{name:'Building your baseline…',exact:true});
  check(await submitting.isDisabled() && await submitting.locator('svg.animate-spin').count()===1,
    'DIAG-REQ-008 submission displays the shared spinner while locked');
  finishDiagnostic();
  await completed.page.locator('[data-diagnostic-results]').waitFor();
  const marker=completed.page.locator('[data-mastery-marker]').first();
  const initialPosition=await marker.evaluate(el=>parseFloat(getComputedStyle(el).left));
  await completed.page.clock.runFor(1800);
  const finalPosition=await marker.evaluate(el=>parseFloat(getComputedStyle(el).left));
  check(finalPosition>initialPosition+10,'DIAG-REQ-007 mastery marker animates from prior to returned band on show');
  check(await completed.page.evaluate(()=>window.__celebrations?.length===1),
    'DIAG-REQ-007 completion celebrates exactly once');
  await completed.page.waitForTimeout(300);
  await screenshot(completed.page,'diagnostic-results-motion',1440);
  const refetched=completed.page.waitForResponse(r=>r.url().endsWith('/__lane_u_api__/courses/synthetic-course/diagnostic'));
  await completed.page.evaluate(()=>window.dispatchEvent(new Event('visibilitychange')));
  await refetched;
  check(await completed.page.getByRole('heading',{name:'Baseline set',exact:true}).isVisible() &&
    await completed.page.evaluate(()=>window.__celebrations.length===1),
    'DIAG-REQ-007 refetch retains completion without restarting celebration');
  check(completed.errors.length===0,'Diagnostic completion has no browser exceptions');
  await completed.context.close();

  const noRows = await fixture(375,{empty:true});
  noRows.state.masteryRows=[];
  await noRows.page.goto('http://localhost:5173/course/diagnostic');
  await noRows.page.locator('#tour-diagnostic-choices').waitFor();
  for(let i=0;i<6;i++) await noRows.page.locator('#tour-diagnostic-card').getByRole('button').nth(i*3).click();
  await noRows.page.getByRole('button',{name:'Submit diagnostic',exact:true}).click();
  await noRows.page.getByText('Your answers are saved. View your twin to explore your current skill profile.',{exact:true}).waitFor();
  check((await noRows.page.getByRole('button',{name:'Back to workspace',exact:true}).count())===1,
    'DIAG-REQ-007 empty mastery response retains one useful results exit');
  await noRows.context.close();

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
      body: `<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/src/styles/globals.css"></head><body><div id="root"></div><script type="module">
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
    import {LoadingRegion} from '/src/components/shared/LoadingRegion.tsx';
    import {LoadingPanel} from '/src/components/shared/LoadingPanel.tsx';
    import {AssistantBlock} from '/src/components/study/AssistantBlock.tsx';
    import {Skeleton} from '/src/components/ui/skeleton.tsx';
    window.fixtureResult={external:0,submitted:0};
    function Probe(){const a=usePromptInputAttachments();return React.createElement('span',{'data-file-count':a.files.length},a.files.length)}
    function FloatingStudy(){return React.createElement('section',{id:'floating-study',style:{height:400}},React.createElement(StudySurface,{dock:React.createElement(ComposeDock,{onAsk:()=>{},placeholder:'Floating dock'})},React.createElement(StudyStream,null,...Array.from({length:30},(_,i)=>React.createElement('p',{key:i},'Synthetic study explanation '+i)),React.createElement('button',{id:'last-study-action'},'Last study action'))))}
    function App(){const target=React.useRef(null);const [files,setFiles]=React.useState([]);const [busy,setBusy]=React.useState(true);window.setLoadingFixture=setBusy;window.setFixtureFiles=setFiles;return React.createElement('main',null,
      React.createElement('section',{id:'study-composer'},React.createElement(ComposeDock,{onAsk:()=>{},placeholder:'Shared dock'})),
      React.createElement('section',{id:'tutor-composer'},React.createElement(TutorComposer,{dropTarget:target,dragging:false,onDragChange:()=>{},attachments:files,onFiles:()=>{},onRemove:()=>setFiles([]),onAsk:()=>{},onTyping:()=>{},pending:false,uploading:false,removingId:null})),
      React.createElement('div',{id:'default-outer'},React.createElement(PromptInput,{id:'default-prompt',onSubmit:m=>{window.fixtureResult.submitted=m.files.length}},React.createElement(Probe),React.createElement(PromptInputTextarea),React.createElement(PromptInputSubmit))),
      React.createElement('div',{id:'opt-in-outer',ref:target},React.createElement(PromptInput,{id:'opt-in-prompt',dropTarget:target,onFilesSelected:files=>{window.fixtureResult.external+=files.length},onSubmit:()=>{}},React.createElement(PromptInputTextarea),React.createElement(PromptInputSubmit))),React.createElement(FloatingStudy),
      React.createElement('section',{id:'loading-fixtures'},busy?React.createElement(React.Fragment,null,
        React.createElement('div',{id:'loading-region-fixture'},React.createElement(LoadingRegion,{label:'Loading roster',className:'grid grid-cols-2 gap-3'},React.createElement(Skeleton,{className:'h-16'}),React.createElement(Skeleton,{className:'h-16'}))),
        React.createElement('div',{id:'loading-panel-fixture'},React.createElement(LoadingPanel,{label:'Preparing baseline…',lines:2})),React.createElement('div',{id:'loading-assistant-fixture'},React.createElement(AssistantBlock,{pending:true,pendingLabel:'Thinking…'}))):React.createElement('p',null,'Ready')))}
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
    check(await primitive.page.locator('#loading-fixtures svg.animate-spin').count()===0
      && await primitive.page.locator('#loading-fixtures [role=status]').count()===3,
      `DIAG-REQ-008 three accessible waiting regions with zero loading spinners at ${width}`);
    check(await primitive.page.locator('#loading-region-fixture [role=status]').getAttribute('aria-label')==='Loading roster'
      && await primitive.page.locator('#loading-region-fixture [role=status]').getAttribute('aria-busy')==='true'
      && await primitive.page.locator('#loading-region-fixture [data-slot=skeleton]').count()===2,
      `DIAG-REQ-008 skeleton region preserves its accessible label and two blocks at ${width}`);
    check(await primitive.page.locator('#loading-panel-fixture img').count()===1
      && await primitive.page.locator('#loading-panel-fixture img').getAttribute('src')==='/Kala-Logo.png'
      && await primitive.page.locator('#loading-panel-fixture p').count()===1
      && await primitive.page.locator('#loading-panel-fixture p').textContent()==='Preparing baseline…'
      && await primitive.page.locator('#loading-panel-fixture .bg-muted').count()===2,
      `DIAG-REQ-008 loading card has one Kala mascot, one line and two skeleton blocks at ${width}`);
    check(await primitive.page.locator('#loading-assistant-fixture [role=status]').count()===1
      && await primitive.page.locator('#loading-assistant-fixture [role=status] p').count()===1
      && await primitive.page.locator('#loading-assistant-fixture [role=status]').textContent()==='Thinking…',
      `TUTOR-REQ-010 shared assistant has exactly one model waiting line at ${width}`);
    check(await primitive.page.locator('#loading-panel-fixture img, #loading-panel-fixture .bg-muted, #loading-assistant-fixture [role=status] p').evaluateAll(elements=>
      elements.length===4 && elements.every(el=>getComputedStyle(el).animationName==='none'
        && getComputedStyle(el).transform==='none')),
      `DIAG-REQ-008 loading mascot and skeletons stay static and model line honors reduced motion at ${width}`);
  }
  await primitive.page.emulateMedia({reducedMotion:'no-preference'});
  check(await primitive.page.locator('#loading-panel-fixture img, #loading-panel-fixture .bg-muted').evaluateAll(elements=>
    elements.length===3 && elements.every(el=>getComputedStyle(el).animationName==='none'
      && getComputedStyle(el).transform==='none')),
    'DIAG-REQ-008 loading mascot and card skeletons stay static with motion enabled');
  await primitive.page.emulateMedia({reducedMotion:'reduce'});
  await primitive.page.evaluate(()=>window.setLoadingFixture(false));
  await primitive.page.locator('#loading-fixtures').getByText('Ready',{exact:true}).waitFor();
  check((await primitive.page.locator('#loading-fixtures svg').count())===0,
    'DIAG-REQ-008 resolved content removes waiting indicators');
  await primitive.page.evaluate(() =>
    window.setFixtureFiles([
      { id: "fixture-file", filename: "notes.txt", sizeBytes: 15, status: "ready" },
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
  // Restored attachments remain clickable even without a local File.
  const restored = primitive.page.getByRole('button', { name: 'Preview notes.txt', exact: true });
  const atRest = await restored.evaluate(el => getComputedStyle(el).backgroundColor);
  await restored.hover();
  check(await restored.evaluate((el, before) => getComputedStyle(el).backgroundColor !== before, atRest),
    'TUTOR-REQ-009 restored card has a visible hover shade');
  check(await primitive.page.locator('[data-tutor-file-card]').evaluate(el => {
    const card = el.getBoundingClientRect(), group = el.closest('[data-slot=input-group]').getBoundingClientRect();
    return Math.abs((card.left - group.left) - (card.top - group.top)) <= 1;
  }), 'TUTOR-REQ-009 attachment top and left insets match');
  await restored.click();
  const restoredDialog = primitive.page.getByRole('dialog', { name: 'notes.txt', exact: true });
  check(await restoredDialog.getByText("File contents aren't available in this session.", { exact: false }).isVisible(),
    'TUTOR-REQ-009 restored file opens honest metadata fallback');
  check((await restoredDialog.locator('pre').count()) === 0,
    'TUTOR-REQ-009 restored preview does not invent file text');
  await primitive.page.screenshot({path:resolve(out, 'tutor-file-restored-375.png')});
  await primitive.page.keyboard.press('Escape');
  await restoredDialog.waitFor({state:'detached'});
  await primitive.page.waitForFunction(() => document.activeElement?.getAttribute('aria-label') === 'Preview notes.txt');
  check(await restored.evaluate(el => document.activeElement === el),
    'TUTOR-REQ-009 metadata dialog restores keyboard focus');
  await primitive.page.evaluate(() => window.setFixtureFiles([
    {id:'md',filename:'notes.md',sizeBytes:15,status:'ready'},
    {id:'pdf',filename:'review.pdf',sizeBytes:512,status:'ready'},
    {id:'txt',filename:'notes.txt',sizeBytes:15,status:'ready'},
  ]));
  check(await primitive.page.locator('[data-file-format]').evaluateAll(elements =>
    new Set(elements.map(el=>getComputedStyle(el).backgroundColor)).size === 3),
    'TUTOR-REQ-009 formats have distinct subtle token fills and type labels');
  await primitive.page.getByRole('button',{name:'Preview review.pdf',exact:true}).click();
  check(await primitive.page.getByRole('dialog',{name:'review.pdf',exact:true}).getByText("PDF content preview isn't available yet.",{exact:false}).isVisible(),
    'TUTOR-REQ-009 PDF modal explains preview support');
  await primitive.page.keyboard.press('Escape');
  await primitive.page.getByRole('dialog').waitFor({state:'detached'});
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

  // The app forces light mode even when next-themes retains a dark preference.
  const notices = await fixture(1440);
  await notices.page.addInitScript(() => localStorage.setItem('theme','dark'));
  // Use Vite's canonical dependency URLs so the provider and toast singleton
  // are the same instances used by the actual Toaster component.
  const toastSource = await (await notices.page.request.get('http://localhost:5173/src/components/ui/sonner.tsx')).text();
  const sonnerModule = toastSource.match(/from "([^"]*\/sonner\.js[^\"]*)"/)[1];
  const themeModule = toastSource.match(/from "([^"]*\/next-themes\.js[^\"]*)"/)[1];
  await notices.context.route('**/__lane_u_toast_fixture', route => route.fulfill({
    contentType:'text/html',
    body:`<!doctype html><html><head><link rel="stylesheet" href="/src/styles/globals.css"></head><body><div id="root"></div><script type="module">
    import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;
    </script><script type="module">
    import React from '/node_modules/.vite/deps/react.js';import ReactDOM from '/node_modules/.vite/deps/react-dom_client.js';
    import {ThemeProvider} from '${themeModule}';import {toast} from '${sonnerModule}';import {Toaster} from '/src/components/ui/sonner.tsx';
    function App(){return React.createElement(ThemeProvider,{attribute:'class',forcedTheme:'light'},React.createElement(Toaster,{visibleToasts:4,expand:true}),...['success','error','info','warning'].map(type=>React.createElement('button',{key:type,onClick:()=>toast[type](type==='success'?'Badge earned':type+' notification',{description:'Readable synthetic description',duration:Infinity})},type)))}
    ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(App));</script></body></html>`,
  }));
  await notices.page.goto('http://localhost:5173/__lane_u_toast_fixture');
  for(const type of ['success','error','info','warning']) await notices.page.getByRole('button',{name:type,exact:true}).click();
  await notices.page.locator('[data-sonner-toast]').last().waitFor();
  await notices.page.waitForFunction(() => document.querySelectorAll('[data-description]').length === 4);
  check(await notices.page.locator('[data-sonner-toaster]').getAttribute('data-sonner-theme') === 'light',
    'WI-22 toast honors forced light theme over saved dark preference');
  check(await notices.page.locator('[data-description]').evaluateAll(elements => {
    const lum = color => {
      const rgb = color.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>{v/=255;return v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4});
      return rgb[0]*0.2126+rgb[1]*0.7152+rgb[2]*0.0722;
    };
    return elements.length === 4 && elements.every(el=>{
      const text=lum(getComputedStyle(el).color),bg=lum(getComputedStyle(el.closest('[data-sonner-toast]')).backgroundColor);
      return (Math.max(text,bg)+0.05)/(Math.min(text,bg)+0.05)>=4.5;
    });
  }), 'WI-22 badge/error/info/warning descriptions meet AA contrast');
  await notices.page.screenshot({path:resolve(out,'toast-contrast-1440.png')});
  check(notices.errors.length===0,'toast fixture has no browser exceptions');
  await notices.context.close();

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
  const dropData = await idle.page.evaluateHandle(() => {
    const transfer = new DataTransfer();
    transfer.items.add(new File(['synthetic'], 'notes.md', {type:'text/markdown'}));
    return transfer;
  });
  await idle.page.locator('[data-study-surface]').dispatchEvent('dragenter',{dataTransfer:dropData});
  await idle.page.locator('[data-tutor-drop-overlay]').waitFor();
  await idle.page.clock.runFor(300);
  check(await idle.page.locator('[data-tutor-drop-overlay] svg g').evaluate(el =>
    new DOMMatrixReadOnly(getComputedStyle(el).transform).m42 < -1),
    'TUTOR-REQ-009 published Upload arrow animates on drag entry');
  await idle.page.screenshot({path:resolve(out,'tutor-drop-animated-1440.png')});
  await idle.page.locator('[data-study-surface]').dispatchEvent('dragleave',{dataTransfer:dropData});
  await idle.page.locator('[data-tutor-drop-overlay]').waitFor({state:'detached'});
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
  check(await cancelled.page.getByRole('button',{name:'Attaching files'}).isDisabled()
    && await cancelled.page.getByRole('button',{name:'Attaching files'}).getAttribute('aria-busy')==='true'
    && await cancelled.page.getByRole('button',{name:'Attaching files'}).locator('svg').count()===1
    && await cancelled.page.locator('svg.animate-spin').count()===0
    && await cancelled.page.locator('[data-tutor-file-card] svg.animate-spin').count()===0,
    'TUTOR-REQ-009 upload keeps one stable icon in disabled busy Send and no spinners');
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

  for (const width of [375,1440]) {
    const reduced=await fixture(width,{reducedMotion:'reduce'});
    let releaseDetail;
    reduced.state.holdDetail=new Promise(done=>{releaseDetail=done});
    let releaseList;
    reduced.state.holdList=new Promise(done=>{releaseList=done});
    await reduced.page.goto('http://localhost:5173/course/tutor?conversation=existing');
    const chat=reduced.page.locator('[data-study-surface]');
    const conversationLoading=chat.getByRole('status',{name:'Loading conversation',exact:true});
    await conversationLoading.waitFor();
    check(await chat.locator('svg.animate-spin').count()===0
      && await chat.locator('[data-slot=skeleton]').count()===2
      && await chat.locator('[data-slot=skeleton]').evaluateAll(nodes=>nodes.every(n=>getComputedStyle(n).animationName==='none')),
      `TUTOR-REQ-010 reduced-motion conversation skeletons without spinner at ${width}`);
    check(await conversationLoading.innerText()==='' && await conversationLoading.getAttribute('aria-busy')==='true',
      `TUTOR-REQ-020 conversation loading is skeleton-only with accessible busy status at ${width}`);
    if(width<1024) await reduced.page.getByRole('button',{name:'Open chat history'}).click();
    const historyLoading=reduced.page.getByRole('status',{name:'Loading chats',exact:true});
    await historyLoading.waitFor();
    check(await historyLoading.innerText()==='' && await historyLoading.getAttribute('aria-busy')==='true'
      && await historyLoading.locator('[data-slot=skeleton]').count()===3
      && await historyLoading.locator('svg.animate-spin').count()===0
      && await historyLoading.locator('[data-slot=skeleton]').evaluateAll(nodes=>nodes.every(n=>getComputedStyle(n).animationName==='none')),
      `TUTOR-REQ-020 history loading is skeleton-only, accessible and static under reduced motion at ${width}`);
    check(reduced.state.creates===0 && reduced.state.asks===0 && reduced.state.uploads===0 && reduced.state.patches===0 && reduced.state.deletes===0,
      `TUTOR-REQ-020 pending read states make no mutations at ${width}`);
    await screenshot(reduced.page,'tutor-skeleton-only-loading',width);
    releaseList();
    reduced.state.holdList=null;
    await historyLoading.waitFor({state:'detached'});
    if(width<1024) await reduced.page.keyboard.press('Escape');
    releaseDetail();
    reduced.state.holdDetail=null;
    await conversationLoading.waitFor({state:'detached'});
    if(width<1024) await reduced.page.getByRole('button',{name:'Open chat history'}).click();
    await reduced.page.getByRole('button',{name:'Actions for Understanding cloud storage'}).click();
    await reduced.page.getByRole('menuitem',{name:'Rename',exact:true}).click();
    const dialog=reduced.page.getByRole('dialog',{name:'Rename chat',exact:true});
    await dialog.getByRole('textbox',{name:'Chat title'}).waitFor();
    check(await dialog.evaluate(el=>getComputedStyle(el).animationName==='none')
      && await reduced.page.locator('[data-slot=dialog-overlay]').evaluateAll(nodes=>nodes.length===1 && nodes.every(n=>getComputedStyle(n).animationName==='none')),
      `TUTOR-REQ-012 rename dialog and overlay honor reduced motion at ${width}`);
    await dialog.getByRole('textbox',{name:'Chat title'}).press('Escape');
    await dialog.waitFor({state:'detached'});
    if(width<1024) await reduced.page.keyboard.press('Escape');
    await reduced.page.evaluate(()=>{
      Blob.prototype.text=function(){return new Promise(done=>{window.releasePreview=()=>done('Synthetic local preview')})};
    });
    await reduced.page.locator('input[type=file]').setInputFiles({name:'pending.txt',mimeType:'text/plain',buffer:Buffer.from('Synthetic local preview')});
    await reduced.page.getByRole('button',{name:'Preview pending.txt',exact:true}).click();
    const preview=reduced.page.getByRole('dialog',{name:'pending.txt',exact:true});
    await preview.getByText('Loading preview…',{exact:true}).waitFor();
    check(await preview.locator('[data-slot=skeleton]').count()===2
      && await preview.locator('svg.animate-spin').count()===0
      && await preview.locator('[data-slot=skeleton]').evaluateAll(nodes=>nodes.every(n=>getComputedStyle(n).animationName==='none')),
      `TUTOR-REQ-009 preview loading is skeleton/text and static under reduced motion at ${width}`);
    await reduced.page.evaluate(()=>window.releasePreview());
    await preview.getByText('Synthetic local preview',{exact:true}).waitFor();
    check(reduced.state.creates===0 && reduced.state.uploads===0 && reduced.state.patches===0,
      `TUTOR-REQ-009/012 reduced-motion local loading/cancel makes no mutation at ${width}`);
    await reduced.context.close();
  }
  console.log(
    `WI-22 browser checks passed: ${assertions} assertions. Synthetic screenshots: ${out}`,
  );
} finally {
  await browser.close();
}
