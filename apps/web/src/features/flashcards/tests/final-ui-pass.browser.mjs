/** APPROVAL-08 U2: real components/hooks, synthetic requests, external traffic blocked. */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
const requireBrowser = createRequire(resolve(process.env.KALA_BROWSER_TEST_DEPS ?? 'apps/web', 'package.json'));
const { chromium } = requireBrowser('playwright');
const browser = await chromium.launch({ headless: true, ...(process.env.KALA_BROWSER_EXECUTABLE ? { executablePath: process.env.KALA_BROWSER_EXECUTABLE } : {}) });
const out = resolve(process.env.KALA_UI_SCREENSHOTS ?? '/tmp/kala-u2-ui');
await mkdir(out, { recursive: true });
let assertions = 0;
const check = (condition, label) => { assert.ok(condition, label); assertions++; };
const card = id => ({ itemId: id, skillId: 'skill', skillName: 'Cloud skill', prompt: `Recall ${id}`, back: { label: `Answer ${id}`, explanation: 'Synthetic explanation' }, state: 'new', box: 0 });
const question = { id: 'question', skillId: 'skill', bloomLevel: 'understand', prompt: 'Choose the durable storage option.', choices: [{ id: 'a', label: 'Object storage' }, { id: 'b', label: 'Temporary disk' }] };
const reward = { xp: 0, attempts: 1, correct: 1, streakDays: 1, badges: [] };
async function fixture(width, { view = 'study', role = 'student', mode = 'review', reduced = true, hold = false, noMaterial = false } = {}) {
 const context = await browser.newContext({ viewport: { width, height: 950 }, reducedMotion: reduced ? 'reduce' : 'no-preference', timezoneId: 'Asia/Manila', locale: 'en-US' });
 const page = await context.newPage(); page.setDefaultTimeout(15000);
 const errors = [], state = { deckCalls: [], reviews: [], posts: [], initialCards: [card('first')], nextCards: [], failDiagnostic: false, diagnostic: null, hold, noMaterial, holdNew: false, holdAsk: false, sizes: [] };
 page.on('pageerror', e => errors.push(e.message));
 let release; const pending = new Promise(r => { release = r; }); state.release = () => { state.hold = false; release(); };
 await context.route('**/*', async route => {
  const req = route.request(), url = new URL(req.url());
  if (url.hostname !== 'localhost' || url.port !== '5173') return route.abort();
  if (url.pathname.endsWith('/src/lib/auth/AuthProvider.tsx')) return route.fulfill({ contentType: 'application/javascript', body: `export const AuthProvider=({children})=>children;export const useSession=()=>(${JSON.stringify({ role, courseId: 'course', userId: 'learner', institutionId: 'institution', displayName: 'Demo learner' })});export const useSetSession=()=>()=>{};` });
  if (url.pathname.endsWith('/src/lib/api/client.ts')) return route.fulfill({ contentType: 'application/javascript', body: `export async function api(path,init){const r=await fetch('/__u2_api'+path,init);if(!r.ok)throw new Error('API '+r.status);return r.json();}` });
  if (url.pathname === '/__u2') {
   const hook = await (await page.request.get('http://localhost:5173/src/features/flashcards/hooks/use-flashcards.ts')).text();
   const queryModule = hook.match(/from "([^"]*\/@tanstack_react-query\.js[^\"]*)"/)[1];
   const views = { study: 'FlashcardDeck', diagnostic: 'DiagnosticPanel', test: 'PracticePanel', browse: 'TestBrowser', proposals: 'SkillReviewPanel', studyBrowse: 'StudyBrowser', analysis: 'DecisionCenter' };
   return route.fulfill({ contentType: 'text/html', body: `<link rel="stylesheet" href="/src/styles/globals.css"><div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;</script><script type="module">
   import React from '/node_modules/.vite/deps/react.js';import ReactDOM from '/node_modules/.vite/deps/react-dom_client.js';import {QueryClient,QueryClientProvider} from '${queryModule}';
   import {FlashcardDeck} from '/src/features/flashcards/components/FlashcardDeck.tsx';import {DiagnosticPanel} from '/src/features/diagnostic/components/DiagnosticPanel.tsx';import {PracticePanel} from '/src/features/practice/components/PracticePanel.tsx';import {TestBrowser} from '/src/features/skill-hub/components/TestBrowser.tsx';import {StudyBrowser} from '/src/features/skill-hub/components/StudyBrowser.tsx';import {SkillReviewPanel} from '/src/features/instructor/components/SkillReviewPanel.tsx';import {DecisionCenter} from '/src/features/instructor/components/DecisionCenter.tsx';
   const client=new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}});window.u2Client=client;
   ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(QueryClientProvider,{client},React.createElement('main',{style:{height:'100vh',maxWidth:'100%',overflow:'hidden'}},React.createElement(${views[view]},{courseId:'course',skillId:'skill',${view === 'test' ? "setId:'saved'," : ''}mode:'${mode}',onExit:()=>{},onStart:()=>{},onSelectSet:()=>{},userId:'learner',learnerName:'Demo learner'}))));</script>` });
  }
  if (!url.pathname.startsWith('/__u2_api')) return route.continue();
  const path = url.pathname.slice('/__u2_api'.length), reply = (json, status = 200) => route.fulfill({ json, status });
  if (req.method() !== 'GET') state.posts.push({ path, method: req.method(), body: req.postDataJSON() });
  if (path.endsWith('/review')) { state.reviews.push(req.postDataJSON()); return reply({ remembered: true, graduated: false, dueInHours: 1, dueAt: '2099-11-02T08:30:00Z', box: 1, reward }); }
  if (path.endsWith('/ask')) { if (state.holdAsk) await new Promise(r => { state.releaseAsk = r; }); return reply({ answer: 'Synthetic hint answer.' }); }
  if (path.endsWith('/deck')) {
   state.deckCalls.push(Object.fromEntries(url.searchParams));
   if (state.hold) await pending;
   if (state.holdNew && state.deckCalls.length > 1) await new Promise(r => { state.releaseNew = r; });
   return reply({ courseId: 'course', cards: state.deckCalls.length === 1 ? state.initialCards : state.nextCards, stats: { tracked: 1, due: 0, learning: 1, mastered: 0 }, mode: url.searchParams.get('mode') ?? 'review', sessionId: `session-${state.deckCalls.length}`, hasMore: false, newRemainingToday: 0 });
  }
  if (path.endsWith('/cards')) return reply({ skillId: 'skill', counts: { new: 1, learning: 0, slipping: 0, known: 0, dueToday: 0 }, cards: state.initialCards.map(c => ({ ...c, due: false, dueAt: null })) });
  if (path.endsWith('/diagnostic/status')) return reply({ courseId: 'course', due: false, dueSkillCount: 0, waitingForMaterialCount: 2 });
  if (path.endsWith('/diagnostic')) { if (state.hold) await pending; return reply({ courseId: 'course', status: 'ready', questions: [question], readyCount: 1, pendingSkillIds: [], failedSkillIds: [], skippedSkillCount: 0, ...state.diagnostic }, state.failDiagnostic ? 500 : 200); }
  if (path.endsWith('/bank/status')) return reply({ courseId: 'course', bankServing: true, building: false, skills: [{ skillId: 'skill', status: state.noMaterial ? 'no_material' : 'ready', usable: !state.noMaterial, mcqReady: state.noMaterial ? 0 : 20, mcqTarget: 20, depth: 3 }] });
  if (path.endsWith('/set') && req.method() === 'POST') { state.sizes.push(req.postDataJSON().size); return reply({ courseId: 'course', skillId: 'skill', setId: null, status: 'preparing', items: [], requestedSize: req.postDataJSON().size, readyCount: 0, pendingCount: 0, failedCount: 0, failedOffsets: [] }); }
  if (path.endsWith('/sets/saved')) { if (state.hold) await pending; return reply({ courseId: 'course', setId: 'saved', skillId: 'skill', kind: 'practice', status: 'ready', items: [question], requestedSize: 1, readyCount: 1, pendingCount: 0, failedCount: 0, failedOffsets: [], attemptedCount: 0, correctCount: 0, lastAttemptedAt: null }); }
  if (path.endsWith('/results')) return reply({ courseId: 'course', setId: 'saved', score: { correct: 0, answered: 0, total: 1, percent: null }, totalXp: 0, masteryBefore: { level: 'developing', value: .2 }, masteryAfter: { level: 'developing', value: .2 }, questions: [] });
  if (path.endsWith('/sets')) return reply({ courseId: 'course', sets: [] });
  if (path.endsWith('/summary')) return reply({ xp: 0, attempts: 0, correct: 0, streakDays: 0, badges: [] });
  if (path.endsWith('/twin')) return reply({ courseId: 'course', readiness: .2, skills: [{ skillId: 'skill', name: 'Cloud skill', moduleRef: null, bloomLevel: 'understand', estimate: .2, attempts: 0, band: 'developing' }], evidence: [] });
  if (path === '/courses/course') return reply({ id: 'course', title: 'AWS101' });
  if (path.endsWith('/next-up')) return reply({ courseId: 'course', next: null });
  if (path.endsWith('/plan')) return reply({ plan: [] });
  if (path.endsWith('/skills/proposed')) return reply({ courseId: 'course', proposed: [{ id: 'proposal', name: 'Cloud skill', bloom_level: 'understand', blueprint_weight: 1, proposed_source: 'Thin material: synthetic context' }] });
  if (path.endsWith('/recommendations')) return reply({ courseId: 'course', userId: 'learner', recommendations: [] });
  throw new Error(`Unexpected synthetic request ${req.method()} ${path}`);
 });
 return { page, context, state, errors };
}
const capture = async (page, name, width) => page.screenshot({ path: resolve(out, `${name}-${width}.png`), animations: 'disabled' });
const widthOf = locator => locator.evaluate(el => el.getBoundingClientRect().width);
const recall = async page => { await page.getByRole('button', { name: 'Show answer', exact: true }).click(); await page.getByRole('button', { name: 'Got it', exact: true }).click(); };
try {
 for (const width of [375, 1440]) {
  const measurements = {};
  for (const view of ['study', 'test', 'diagnostic']) {
   const f = await fixture(width, { view, hold: true, reduced: width === 375 });
   await f.page.goto('http://localhost:5173/__u2');
   const loading = f.page.getByRole('status').filter({ has: f.page.locator('img[src="/Kala-Logo.png"]') });
   await loading.waitFor(); const loadingWidth = await widthOf(loading);
   check(await loading.locator('svg.animate-spin').count() === 0, `${view} loading has no spinner`);
   check(await loading.locator('img').evaluate(el => getComputedStyle(el).animationName === 'none'), `${view} static mascot`);
   check(await loading.locator('.bg-muted').count() >= 3, `${view} has skeleton lines`);
   f.state.release();
   const content = view === 'study' ? f.page.locator('.relative.border.bg-card').filter({ has: f.page.getByText('Recall first', { exact: true }) }) : view === 'test' ? f.page.locator('#tour-practice-card') : f.page.locator('#tour-diagnostic-card > div').last();
   await content.waitFor(); const contentWidth = await widthOf(content); measurements[view] = contentWidth;
   check(Math.abs(loadingWidth - contentWidth) < 1, `${view} loading/content width match ${width}: ${loadingWidth}/${contentWidth}`);
   check(await f.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${view} no horizontal overflow`);
   await capture(f.page, `${view}-content`, width); check(f.errors.length === 0, `${view} runtime clean: ${f.errors}`); await f.context.close();
  }
  check(Math.abs(measurements.test - measurements.diagnostic) < 1, `Diagnostic/Test same column ${width}`);
  for (const role of ['student', 'instructor']) {
   const f = await fixture(width, { role }); await f.page.goto('http://localhost:5173/course');
   await f.page.getByRole('heading', { name: 'Welcome back, Demo', exact: true }).waitFor();
   check(await f.page.getByText('2 topics are waiting for course material', { exact: true }).count() === (role === 'student' ? 0 : 1), `E4 ${role} material boundary`);
   check(await f.page.locator('#nav-diagnostic').getAttribute('aria-label') === 'Diagnostic', `E4 actionable-zero badge preserved for ${role}`);
   check(f.state.posts.length === 0, `E4 ${role} makes no writes`); await f.context.close();
  }
  const d = await fixture(width, { view: 'diagnostic' }); d.state.diagnostic = { questions: [], readyCount: 0, waitingForMaterialCount: 2 };
  await d.page.goto('http://localhost:5173/__u2'); await d.page.getByText("Your baseline check isn't ready yet.", { exact: true }).waitFor();
  await d.page.getByText('Check back later.', { exact: true }).waitFor(); check(!/material|course team/i.test(await d.page.locator('main').innerText()), 'student unavailable copy is exact and neutral');
  d.state.diagnostic = { questions: [], readyCount: 0 }; await d.page.reload(); await d.page.getByText("You're all caught up", { exact: true }).waitFor();
  check(await d.page.getByText(/isn't ready/).count() === 0, 'caught up stays distinct');
  d.state.failDiagnostic = true; await d.page.reload(); await d.page.getByText('We could not load the diagnostic', { exact: true }).waitFor();
  check(await d.page.getByRole('button', { name: 'Retry', exact: true }).isVisible(), 'fetch failure retains Retry');
  d.state.failDiagnostic = false; await d.page.getByRole('button', { name: 'Retry', exact: true }).click(); await d.page.getByText("You're all caught up", { exact: true }).waitFor(); check(d.state.posts.length === 0, 'Diagnostic read recovery never submits'); await d.context.close();
  const i = await fixture(width, { view: 'diagnostic', role: 'instructor' }); i.state.diagnostic = { questions: [], readyCount: 0, waitingForMaterialCount: 2 }; await i.page.goto('http://localhost:5173/__u2'); await i.page.getByText('Waiting for course material', { exact: true }).waitFor(); check(true, 'instructor Diagnostic retains material copy'); await i.context.close();
  const p = await fixture(width, { view: 'proposals', role: 'instructor' }); await p.page.goto('http://localhost:5173/__u2'); await p.page.getByText('Thin material', { exact: true }).waitFor(); check(true, 'instructor skill review retains truthful material concern'); await p.context.close();
  const b = await fixture(width, { view: 'browse', noMaterial: true }); await b.page.goto('http://localhost:5173/__u2');
  const newSet = b.page.locator('#tour-test-new-set'); await newSet.waitFor(); await newSet.getByText('New practice set', { exact: true }).waitFor(); await newSet.getByText('Fresh questions. Choose 5, 10, or 20 at a time.', { exact: true }).waitFor();
  check(await newSet.isDisabled() && !/material/i.test(await b.page.locator('main').innerText()), 'student exact Test copy preserves unavailable gate'); check(b.state.posts.length === 0, 'unavailable Test creates no set'); await b.context.close();
  for (const mode of ['review', 'all']) {
   const f = await fixture(width, { mode, reduced: width === 375 }); await f.page.goto('http://localhost:5173/__u2');
   await f.page.getByText('Recall first', { exact: true }).waitFor();
   f.state.holdAsk = true; await f.page.getByRole('button', { name: 'Give me a hint', exact: true }).click();
   await f.page.getByText('Kala is preparing a hint…', { exact: true }).waitFor();
   check(await f.page.getByRole('button', { name: 'Give me a hint', exact: true }).isDisabled(), 'model initiating label stable and disabled');
   check(await f.page.locator('svg.animate-spin').count() === 0 && await f.page.getByText('Thinking…', { exact: true }).count() === 0, 'one model shimmer and no second spinner/Thinking');
   f.state.releaseAsk(); await f.page.getByText('Synthetic hint answer.', { exact: true }).waitFor();
   await recall(f.page); await f.page.getByText('Study complete', { exact: true }).waitFor();
   f.state.holdNew = true; const getNew = f.page.getByRole('button', { name: 'Get new cards', exact: true }); await getNew.click();
   check(await getNew.isDisabled() && await f.page.getByText('Study complete', { exact: true }).isVisible(), 'delayed Get new cards retains completion');
   f.state.releaseNew(); await f.page.getByText(/No new cards right now. Your next review is November 2, 2099 at 4:30 PM/).waitFor();
   check(f.state.deckCalls.at(-1).mode === 'review' && f.state.deckCalls.at(-1).limit === '20' && !f.state.deckCalls.at(-1).offset, `${mode} completion uses existing due/new selector`);
   check(f.state.reviews.length === 1, 'empty refresh writes no review'); await capture(f.page, `completion-${mode}`, width);
   f.state.holdNew = false; f.state.nextCards = [card('first')]; await getNew.click(); await f.page.getByText(/No new cards right now/).waitFor(); check(await f.page.getByText('Recall first', { exact: true }).count() === 0, 'rated-only refresh never resurfaces card');
   f.state.nextCards = [card('first'), card('new')]; await getNew.click(); await f.page.getByText('Recall new', { exact: true }).waitFor(); await recall(f.page);
   check(f.state.reviews.map(r => r.item_id).join(',') === 'first,new', 'mixed refresh rates only unseen item');
   await f.page.getByRole('button', { name: 'Go through these again', exact: true }).click(); await recall(f.page); check(f.state.reviews.length === 2, 'local replay preserves posted guard');
   check(f.state.reviews.every(r => r.mode === 'flashcard' && r.idempotency_key && r.session_id), 'review request semantics retained'); check(f.errors.length === 0, `Study runtime clean: ${f.errors}`); await f.context.close();
  }
 }
 console.log(`U2 final UI passed: ${assertions} assertions; screenshots: ${out}`);
} finally { await browser.close(); }
