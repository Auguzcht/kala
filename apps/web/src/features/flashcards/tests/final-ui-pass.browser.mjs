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
 const errors = [], state = { deckCalls: [], reviews: [], posts: [], initialCards: [card('first')], nextCards: [], failDiagnostic: false, diagnostic: null, hold, noMaterial, holdNew: false, holdAsk: false, holdModel: false, holdSummary: false, sizes: [] };
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
   const views = { lesson: 'LessonChat', study: 'FlashcardDeck', diagnostic: 'DiagnosticPanel', test: 'PracticePanel', browse: 'TestBrowser', proposals: 'SkillReviewPanel', studyBrowse: 'StudyBrowser', analysis: 'DecisionCenter', stats: 'GamificationSummary' };
   return route.fulfill({ contentType: 'text/html', body: `<link rel="stylesheet" href="/src/styles/globals.css"><div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;</script><script type="module">
   import React from '/node_modules/.vite/deps/react.js';import ReactDOM from '/node_modules/.vite/deps/react-dom_client.js';import {QueryClient,QueryClientProvider} from '${queryModule}';
   import {GamificationSummary} from '/src/features/gamification/components/GamificationSummary.tsx';import {FlashcardDeck} from '/src/features/flashcards/components/FlashcardDeck.tsx';import {DiagnosticPanel} from '/src/features/diagnostic/components/DiagnosticPanel.tsx';import {PracticePanel} from '/src/features/practice/components/PracticePanel.tsx';import {TestBrowser} from '/src/features/skill-hub/components/TestBrowser.tsx';import {StudyBrowser} from '/src/features/skill-hub/components/StudyBrowser.tsx';import {SkillReviewPanel} from '/src/features/instructor/components/SkillReviewPanel.tsx';import {DecisionCenter} from '/src/features/instructor/components/DecisionCenter.tsx';
   import {LessonChat} from '/src/features/lessons/components/LessonChat.tsx';
   const client=new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}});window.u2Client=client;
   ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(QueryClientProvider,{client},React.createElement('main',{style:{height:'100vh',maxWidth:'100%',overflow:'hidden'}},React.createElement(${views[view]},{courseId:'course',skillId:'skill',${view === 'test' ? "setId:'saved'," : ''}mode:'${mode}',onExit:()=>{},onStart:()=>{},onSelectSet:()=>{},userId:'learner',learnerName:'Demo learner'}))));</script>` });
  }
  if (!url.pathname.startsWith('/__u2_api')) return route.continue();
  const path = url.pathname.slice('/__u2_api'.length), reply = (json, status = 200) => route.fulfill({ json, status });
  if (req.method() !== 'GET') state.posts.push({ path, method: req.method(), body: req.postDataJSON() });
  if (path === '/lessons/course/skill/skill') return reply({ lessonId: 'lesson', skillId: 'skill', moduleRef: null, title: 'Cloud lesson', status: 'ready', steps: [{ id: 'step', position: 0, summary: 'Synthetic lesson summary', detailPoints: ['Synthetic detail'], misconception: null, keyTakeaway: 'Synthetic takeaway', bloomLevel: 'understand', check: { itemId: question.id, prompt: question.prompt, choices: question.choices } }] });
  if (path.endsWith('/diagnostic/submit')) { await new Promise(r => { state.releaseSubmit = r; }); return reply({correctCount:2,total:2,results:[],masteryDelta:[]}); }
  if (path.endsWith('/review')) { state.reviews.push(req.postDataJSON()); return reply({ remembered: true, graduated: false, dueInHours: 1, dueAt: '2099-11-02T08:30:00Z', box: 1, reward }); }
  if (path.endsWith('/skills/propose')) { if (state.holdModel) await new Promise(r => { state.releaseModel = r; }); return reply({status:'queued'}); }
  if (path.endsWith('/ask')) { if (state.holdAsk) await new Promise(r => { state.releaseAsk = r; }); return state.failAsk ? reply({ detail: 'Synthetic retryable answer failure.' }, 503) : reply({ answer: 'Synthetic hint answer.' }); }
  if (path.endsWith('/deck')) {
   if (url.searchParams.get('limit') === '0') return reply({ courseId: 'course', cards: [], stats: { tracked: 1, due: 0, learning: 1, mastered: 0 }, mode: 'review', sessionId: null, hasMore: false });
   state.deckCalls.push(Object.fromEntries(url.searchParams));
   if (state.hold) await pending;
   if (state.holdNew && state.deckCalls.length > 1) await new Promise(r => { state.releaseNew = r; });
   return reply({ courseId: 'course', cards: state.deckCalls.length === 1 ? state.initialCards : state.nextCards, stats: { tracked: 1, due: 0, learning: 1, mastered: 0 }, mode: url.searchParams.get('mode') ?? 'review', sessionId: `session-${state.deckCalls.length}`, hasMore: false, newRemainingToday: 0 });
  }
  if (path.endsWith('/cards')) return reply({ skillId: 'skill', counts: { new: 1, learning: 0, slipping: 0, known: 0, dueToday: 0 }, cards: state.initialCards.map(c => ({ ...c, due: false, dueAt: null })) });
  if (path.endsWith('/diagnostic/status')) return reply({ courseId: 'course', due: false, dueSkillCount: 0, waitingForMaterialCount: 2 });
  if (path.endsWith('/diagnostic')) { if (state.hold) await pending; return reply({ courseId: 'course', status: 'ready', questions: [question], readyCount: 1, pendingSkillIds: [], failedSkillIds: [], skippedSkillCount: 0, ...state.diagnostic }, state.failDiagnostic ? 500 : 200); }
  if (path.endsWith('/bank/status')) return reply({ courseId: 'course', bankServing: true, building: false, skills: [{ skillId: 'skill', status: state.noMaterial ? 'no_material' : 'ready', usable: !state.noMaterial, mcqReady: state.noMaterial ? 0 : 20, mcqTarget: 20, depth: 3 }] });
  if (path.endsWith('/set') && req.method() === 'POST') { state.sizes.push(Number(url.searchParams.get('size'))); return reply({ courseId: 'course', skillId: 'skill', setId: null, status: 'preparing', items: [], requestedSize: Number(url.searchParams.get('size')), readyCount: 0, pendingCount: 0, failedCount: 0, failedOffsets: [] }); }
  if (path.endsWith('/sets/saved')) { if (state.hold) await pending; return reply({ courseId: 'course', setId: 'saved', skillId: 'skill', kind: 'practice', status: 'ready', items: [question], requestedSize: 1, readyCount: 1, pendingCount: 0, failedCount: 0, failedOffsets: [], attemptedCount: 0, correctCount: 0, lastAttemptedAt: null }); }
  if (path.endsWith('/results')) return reply({ courseId: 'course', setId: 'saved', score: { correct: 0, answered: 0, total: 1, percent: null }, totalXp: 0, masteryBefore: { level: 'developing', value: .2 }, masteryAfter: { level: 'developing', value: .2 }, questions: [] });
  if (path.endsWith('/sets')) return reply({ courseId: 'course', sets: [] });
  if (path.endsWith('/summary')) { if(state.holdSummary) await new Promise(r => { state.releaseSummary = r; }); return reply({ xp: 0, attempts: 0, correct: 0, streakDays: 0, badges: [] }); }
  if (path.endsWith('/twin')) return reply({ courseId: 'course', readiness: .2, skills: [{ skillId: 'skill', name: 'Cloud skill', moduleRef: null, bloomLevel: 'understand', estimate: .2, attempts: 0, band: 'developing' }], evidence: [] });
  if (path === '/courses/course') return reply({ id: 'course', title: 'AWS101' });
  if (path.endsWith('/next-up')) return reply({ courseId: 'course', next: null });
  if (path.endsWith('/plan')) return reply({ plan: [] });
  if (path.endsWith('/skills/proposed')) return reply({ courseId: 'course', proposed: [{ id: 'proposal', name: 'Cloud skill', bloom_level: 'understand', blueprint_weight: 1, proposed_source: 'Thin material: synthetic context' }] });
  if (path.endsWith('/recommendations')) { if (req.method() === 'POST' && state.holdModel) await new Promise(r => { state.releaseModel = r; }); return reply({ courseId: 'course', userId: 'learner', generated: 0, recommendations: [] }); }
  throw new Error(`Unexpected synthetic request ${req.method()} ${path}`);
 });
 return { page, context, state, errors };
}
const capture = async (page, name, width) => page.screenshot({ path: resolve(out, `${name}-${width}.png`), animations: 'disabled' });
const widthOf = locator => locator.evaluate(el => el.getBoundingClientRect().width);
const edgesOf = locator => locator.evaluate(el => {
 const { left, right, width } = el.getBoundingClientRect();
 return { left, right, width };
});
const matchingEdges = (a, b) => Math.abs(a.left - b.left) <= 1 && Math.abs(a.right - b.right) <= 1;
const recall = async page => { await page.getByRole('button', { name: 'Show answer', exact: true }).click(); await page.getByRole('button', { name: 'Got it', exact: true }).click(); };
try {
 for (const width of [375, 1440]) {
  const measurements = {};
  for (const view of ['study', 'test', 'diagnostic']) {
   const f = await fixture(width, { view, hold: true, reduced: width === 375 });
   await f.page.goto('http://localhost:5173/__u2');
   const loading = f.page.getByRole('status').filter({ has: f.page.locator('img[src="/Kala-Logo.png"]') });
   await loading.waitFor(); const loadingWidth = await widthOf(loading), loadingEdges = await edgesOf(loading);
   check(await loading.locator('svg.animate-spin').count() === 0, `${view} loading has no spinner`);
   check(await loading.locator('img').evaluate(el => getComputedStyle(el).animationName === 'none'), `${view} static mascot`);
   check(await loading.locator('.bg-muted').count() >= 3, `${view} has skeleton lines`);
   f.state.release();
   const content = view === 'study' ? f.page.locator('.relative.border.bg-card').filter({ has: f.page.getByText('Recall first', { exact: true }) }) : view === 'test' ? f.page.locator('#tour-practice-card') : f.page.locator('#tour-diagnostic-card > div').last();
   await content.waitFor(); const contentWidth = await widthOf(content); measurements[view] = contentWidth;
   check(Math.abs(loadingWidth - contentWidth) < 1, `${view} loading/content width match ${width}: ${loadingWidth}/${contentWidth}`);
   check(matchingEdges(loadingEdges, await edgesOf(content)), `DESIGN-REQ-002 ${view} loading/content edges match at ${width}`);
   check(Math.abs(contentWidth - (width === 375 ? 343 : 752)) <= 1, `DESIGN-REQ-002 ${view} retains U2 content width at ${width}`);
   check(await f.page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${view} no horizontal overflow`);
   await capture(f.page, `${view}-content`, width); check(f.errors.length === 0, `${view} runtime clean: ${f.errors}`); await f.context.close();
  }
  const lesson = await fixture(width, { view: 'lesson', reduced: true });
  await lesson.page.goto('http://localhost:5173/__u2');
  const teaching = lesson.page.locator('#tour-lesson-explain');
  await teaching.waitFor();
  const teachingEdges = await edgesOf(teaching);
  const lessonDockEdges = await edgesOf(lesson.page.locator('#tour-lesson-dock > div'));
  check(matchingEdges(teachingEdges, lessonDockEdges), `DESIGN-REQ-002 shared Lesson teaching/dock edges at ${width}`);
  await lesson.page.getByRole('button', { name: 'Continue', exact: true }).click();
  const lessonCheck = lesson.page.locator('#tour-lesson-check');
  await lessonCheck.waitFor();
  check(matchingEdges(teachingEdges, await edgesOf(lessonCheck)), `DESIGN-REQ-002 Lesson check inherits shared gutters once at ${width}`);
  check(lesson.state.posts.length === 0 && lesson.errors.length === 0, 'Lesson layout transition has no writes or runtime errors');
  await lesson.context.close();
  console.log(`U2 measured card widths at ${width}: ${JSON.stringify(measurements)}`);
  check(Math.abs(measurements.test - measurements.diagnostic) < 1, `Diagnostic/Test same column ${width}`);
  const shellStudy = await fixture(width, { hold: true, reduced: true });
  await shellStudy.page.goto('http://localhost:5173/course/flashcards');
  await shellStudy.page.locator('#tour-flashcards-recommended').click();
  const shellLoading = shellStudy.page.getByRole('status').filter({ has: shellStudy.page.locator('img[src="/Kala-Logo.png"]') });
  await shellLoading.waitFor();
  const shellLoadingEdges = await edgesOf(shellLoading);
  shellStudy.state.release();
  const shellCard = shellStudy.page.locator('.relative.border.bg-card').filter({ has: shellStudy.page.getByText('Recall first', { exact: true }) });
  await shellCard.waitFor();
  await shellStudy.page.getByRole('button', { name: 'Give me a hint', exact: true }).click();
  await shellStudy.page.getByText('Synthetic hint answer.', { exact: true }).waitFor();
  const shellReply = shellStudy.page.locator('.mr-auto.w-full.max-w-full').filter({ has: shellStudy.page.getByText('Synthetic hint answer.', { exact: true }) });
  await shellStudy.page.getByRole('button', { name: 'Show answer', exact: true }).click();
  const shellCardEdges = await edgesOf(shellCard), shellReplyEdges = await edgesOf(shellReply);
  const shellDockEdges = await edgesOf(shellStudy.page.locator('#tour-study-dock > div'));
  const shellScroll = await edgesOf(shellStudy.page.locator('[role=log] > div'));
  check(Math.abs(shellScroll.right - width) <= 1, `DESIGN-REQ-002 Study native scrollbar stays at viewport right edge at ${width}`);
  check(matchingEdges(shellCardEdges, shellReplyEdges) && matchingEdges(shellCardEdges, shellDockEdges), `DESIGN-REQ-002 full-page Study card/reply/action dock match at ${width}`);
  check(matchingEdges(shellLoadingEdges, shellCardEdges), `DESIGN-REQ-002 full-page Study loading/content match at ${width}`);
  await shellStudy.page.getByRole('button', { name: 'Ask a follow-up', exact: true }).click();
  const shellComposeEdges = await edgesOf(shellStudy.page.locator('#tour-study-dock > div'));
  check(matchingEdges(shellCardEdges, shellComposeEdges), `DESIGN-REQ-002 full-page Study compose dock matches at ${width}`);
  check(shellStudy.errors.length === 0 && shellStudy.state.reviews.length === 0, 'full-page Study measurements do not post reviews or raise runtime errors');
  console.log(`WI-34 full-page Study edges at ${width}: ${JSON.stringify({ loading: shellLoadingEdges, card: shellCardEdges, reply: shellReplyEdges, actionDock: shellDockEdges, composeDock: shellComposeEdges, scroller: shellScroll })}`);
  await capture(shellStudy.page, 'shared-column-study-page', width);
  await shellStudy.context.close();
  const progress = await fixture(width, { view: 'stats', reduced: true }); progress.state.holdSummary = true;
  await progress.page.goto('http://localhost:5173/__u2'); const statSkeleton = progress.page.getByRole('status', { name: 'Loading your progress', exact: true }); await statSkeleton.waitFor();
  check(await statSkeleton.evaluate(el => getComputedStyle(el).animationName === 'none'), 'progress stat skeleton honors reduced motion');
  check(await progress.page.locator('svg.animate-spin').count() === 0, 'progress stat has no loading spinner');
  progress.state.releaseSummary(); await statSkeleton.waitFor({ state: 'detached' }); check(progress.errors.length === 0, 'progress stat resolves without runtime error'); await progress.context.close();
  for (const role of ['student', 'instructor']) {
   const f = await fixture(width, { role });
   const statusLoaded = f.page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/diagnostic/status'));
   await f.page.goto('http://localhost:5173/course'); await statusLoaded;
   await f.page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
   if (role === 'instructor') await f.page.getByText('2 topics are waiting for course material', { exact: true }).waitFor();
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
  const submission = await fixture(width, { view: 'diagnostic' }); submission.state.diagnostic = {questions:[question,{...question,id:'second-question',prompt:'Choose a second storage option.'}],readyCount:2};
  await submission.page.goto('http://localhost:5173/course/diagnostic');
  const choices = submission.page.getByRole('button', {name:'Object storage',exact:true}); await choices.nth(0).click(); await choices.nth(1).click();
  await submission.page.locator('#tour-diagnostic-submit').click(); await submission.page.waitForTimeout(260);
  check(await submission.page.locator('#tour-diagnostic-submit').isDisabled(), 'Diagnostic activated submit remains disabled');
  check(await submission.page.locator('svg.animate-spin').count() === 1, 'Diagnostic bulk submission has exactly one spinner in its submit control');
  check(await submission.page.locator('#tour-diagnostic-card svg.animate-spin').count() === 0 && await submission.page.locator('#tour-diagnostic-card button').evaluateAll(buttons => buttons.every(button => button.disabled)), 'Diagnostic choices stay locked without grading spinners');
  check(submission.state.posts.length === 1 && submission.state.posts[0].body.answers.length === 2 && submission.state.posts[0].body.answers.every(answer => Object.keys(answer).sort().join(',') === 'choice_id,item_id,latency_ms'), 'Diagnostic submission request stays single and unchanged');
  await capture(submission.page, 'diagnostic-pending', width); submission.state.releaseSubmit();
  await submission.page.getByText('Diagnostic complete', {exact:true}).waitFor(); check(submission.errors.length === 0, 'Diagnostic pending feedback resolves into completion'); await submission.context.close();
  const i = await fixture(width, { view: 'diagnostic', role: 'instructor' }); i.state.diagnostic = { questions: [], readyCount: 0, waitingForMaterialCount: 2 }; await i.page.goto('http://localhost:5173/__u2'); await i.page.getByText('Waiting for course material', { exact: true }).waitFor(); check(true, 'instructor Diagnostic retains material copy'); await i.context.close();
  const p = await fixture(width, { view: 'proposals', role: 'instructor' }); await p.page.goto('http://localhost:5173/__u2'); await p.page.getByText('Thin material', { exact: true }).waitFor(); check(true, 'instructor skill review retains truthful material concern'); await p.context.close();
  const b = await fixture(width, { view: 'browse', noMaterial: true }); await b.page.goto('http://localhost:5173/__u2');
  const newSet = b.page.locator('#tour-test-new-set'); await newSet.waitFor(); await newSet.getByText('New practice set', { exact: true }).waitFor(); await newSet.getByText('Fresh questions. Choose 5, 10, or 20 at a time.', { exact: true }).waitFor();
  check(await newSet.isDisabled() && !/material/i.test(await b.page.locator('main').innerText()), 'student exact Test copy preserves unavailable gate'); check(b.state.posts.length === 0, 'unavailable Test creates no set'); await b.context.close();
  for (const view of ['study', 'studyBrowse']) {
   const empty = await fixture(width, { view, noMaterial: true }); empty.state.initialCards = [];
   await empty.page.goto('http://localhost:5173/__u2'); await empty.page.getByText('No cards yet', { exact: true }).waitFor();
   check(!/material|course team/i.test(await empty.page.locator('main').innerText()), `${view} unavailable student copy has no material explanation`);
   check(empty.state.posts.length === 0, `${view} empty presentation makes no writes`); await empty.context.close();
  }
  const sizes = await fixture(width, { view: 'browse' }); await sizes.page.goto('http://localhost:5173/__u2');
  for (const size of [5, 10, 20]) {
   await sizes.page.getByRole('button', { name: String(size), exact: true }).click();
   const response = sizes.page.waitForResponse(r => new URL(r.url()).pathname.endsWith('/set'));
   await sizes.page.locator('#tour-test-new-set').click(); await response;
  }
  check(sizes.state.sizes.join(',') === '5,10,20', 'Test keeps existing 5/10/20 request sizes');
  check(sizes.state.posts.length === 3 && sizes.state.posts.every(p => p.path.endsWith('/set')), 'Test generates only explicitly selected sets'); await sizes.context.close();
  for (const view of ['proposals', 'analysis']) {
   const model = await fixture(width, { view, role: 'instructor', reduced: width === 375 }); model.state.holdModel = true;
   await model.page.goto('http://localhost:5173/__u2'); const label = view === 'proposals' ? 'Refresh skills' : 'Run analysis';
   const control = model.page.getByRole('button', { name: label, exact: true }); await control.click();
   const pending = model.page.getByText(view === 'proposals' ? 'Kala is refreshing proposals. This can take a few minutes.' : 'Kala is preparing recommendations…', { exact: true });
   await pending.waitFor(); check(await control.isDisabled(), `${view} model initiating label remains stable and disabled`);
   check(await model.page.locator('svg.animate-spin').count() === 0 && await pending.count() === 1, `${view} one model shimmer without spinner`);
   model.state.releaseModel(); check(model.state.posts.length === 1, `${view} one explicit request`); await model.context.close();
  }
  for (const mode of ['review', 'all']) {
   const f = await fixture(width, { mode, reduced: width === 375 }); await f.page.goto('http://localhost:5173/__u2');
   await f.page.getByText('Recall first', { exact: true }).first().waitFor();
   f.state.holdAsk = true; await f.page.getByRole('button', { name: 'Give me a hint', exact: true }).click();
   await f.page.getByText('Kala is preparing a hint…', { exact: true }).waitFor();
   check(await f.page.getByRole('button', { name: 'Give me a hint', exact: true }).isDisabled(), 'model initiating label stable and disabled');
   check(await f.page.locator('svg.animate-spin').count() === 0 && await f.page.getByText('Thinking…', { exact: true }).count() === 0, 'one model shimmer and no second spinner/Thinking');
   f.state.releaseAsk(); await f.page.getByText('Synthetic hint answer.', { exact: true }).waitFor();
   const content = f.page.locator('.relative.border.bg-card').filter({ has: f.page.getByText('Recall first', { exact: true }) });
   const reply = f.page.locator('.mr-auto.w-full.max-w-full').filter({ has: f.page.getByText('Synthetic hint answer.', { exact: true }) });
   const dock = f.page.locator('#tour-study-dock > div');
   const cardEdges = await edgesOf(content), replyEdges = await edgesOf(reply);
   await f.page.getByRole('button', { name: 'Show answer', exact: true }).click();
   const actionEdges = await edgesOf(dock);
   check(matchingEdges(cardEdges, replyEdges) && matchingEdges(cardEdges, actionEdges), `DESIGN-REQ-002 ${mode} Study card/reply/action dock edges at ${width}`);
   await f.page.getByRole('button', { name: 'Ask a follow-up', exact: true }).click();
   const composeEdges = await edgesOf(dock);
   check(matchingEdges(cardEdges, composeEdges), `DESIGN-REQ-002 ${mode} Study compose dock edges at ${width}`);
   check(Math.abs((await edgesOf(dock.locator('[data-slot=input-group]'))).left - cardEdges.left) <= 1, `DESIGN-REQ-002 Study compose input starts at column edge at ${width}`);
   console.log(`WI-34 Study ${mode} edges at ${width}: ${JSON.stringify({ card: cardEdges, reply: replyEdges, actionDock: actionEdges, composeDock: composeEdges })}`);
   await capture(f.page, `shared-column-${mode}`, width);
   await f.page.getByRole('button', { name: 'Cancel', exact: true }).click();
   await f.page.getByRole('button', { name: 'Flip to question', exact: true }).click();
   await recall(f.page); await f.page.getByText('Study complete', { exact: true }).waitFor();
   f.state.holdNew = true; const getNew = f.page.getByRole('button', { name: 'Get new cards', exact: true }); await getNew.click();
   check(await getNew.isDisabled() && await f.page.getByText('Study complete', { exact: true }).isVisible(), 'delayed Get new cards retains completion');
   f.state.releaseNew(); await f.page.getByText(/No new cards right now. Your next review is November 2, 2099 at 4:30 PM/).waitFor();
   check(f.state.deckCalls.at(-1).mode === 'review' && f.state.deckCalls.at(-1).limit === '20' && !f.state.deckCalls.at(-1).offset, `${mode} completion uses existing due/new selector`);
   check(f.state.reviews.length === 1, 'empty refresh writes no review'); await capture(f.page, `completion-${mode}`, width);
   f.state.holdNew = false; f.state.nextCards = [card('first')]; await getNew.click(); await f.page.getByText(/No new cards right now/).waitFor(); check(await f.page.getByText('Recall first', { exact: true }).count() === 0, 'rated-only refresh never resurfaces card');
   f.state.nextCards = [card('first'), card('new')]; await getNew.click(); await f.page.getByText('Recall new', { exact: true }).first().waitFor(); await recall(f.page);
   check(f.state.reviews.map(r => r.item_id).join(',') === 'first,new', 'mixed refresh rates only unseen item');
   await f.page.getByRole('button', { name: 'Go through these again', exact: true }).click(); await recall(f.page); check(f.state.reviews.length === 2, 'local replay preserves posted guard');
   check(f.state.reviews.every(r => r.mode === 'flashcard' && r.idempotency_key && r.session_id), 'review request semantics retained'); check(f.errors.length === 0, `Study runtime clean: ${f.errors}`); await f.context.close();
  }
  const help = await fixture(width, { reduced: true });
  help.state.initialCards = [card('first'), card('second')];
  const asks = () => help.state.posts.filter(post => post.path.endsWith('/ask'));
  await help.page.goto('http://localhost:5173/__u2');
  help.state.holdAsk = true;
  await help.page.getByRole('button', { name: 'Give me a hint', exact: true }).click();
  const hintTurn = help.page.locator('[data-study-help-turn=hint]').first();
  await hintTurn.getByText('Kala is preparing a hint…', { exact: true }).waitFor();
  check(await hintTurn.locator('.ml-auto').innerText() === 'Give me a hint', `STUDY-REQ-008 pending hint has student bubble at ${width}`);
  check(asks().length === 1 && asks()[0].body.style === 'eli5' && asks()[0].body.question.includes('Recall first') && !asks()[0].body.question.includes('Answer first') && !asks()[0].body.conversation_id, `STUDY-REQ-008 front hint protects back and stays stateless at ${width}`);
  check(await help.page.locator('svg.animate-spin').count() === 0 && await help.page.getByRole('button', { name: 'Give me a hint', exact: true }).isDisabled(), `STUDY-REQ-008 hint has one shimmer with stable disabled action at ${width}`);
  help.state.holdAsk = false; help.state.releaseAsk();
  await hintTurn.getByText('Synthetic hint answer.', { exact: true }).waitFor();
  await help.page.getByRole('button', { name: 'Show answer', exact: true }).click();
  help.state.holdAsk = true;
  await help.page.getByRole('button', { name: 'Explain more', exact: true }).click();
  const explanation = help.page.locator('[data-study-help-turn=explain]').first();
  await explanation.getByText('Kala is preparing an explanation…', { exact: true }).waitFor();
  check(await explanation.locator('.ml-auto').innerText() === 'Explain more', `STUDY-REQ-008 pending explanation has student bubble at ${width}`);
  check(asks()[1].body.style === 'detail' && asks()[1].body.question.includes('Recall first') && asks()[1].body.question.includes('Answer first') && asks()[1].body.question.includes('Synthetic explanation'), `STUDY-REQ-008 explanation includes the flipped card context at ${width}`);
  help.state.holdAsk = false; help.state.releaseAsk();
  await explanation.getByText('Synthetic hint answer.', { exact: true }).waitFor();
  await help.page.getByRole('button', { name: 'Explain more', exact: true }).evaluate(el => { el.click(); el.click(); });
  await help.page.locator('[data-study-help-turn=explain]').nth(1).getByText('Synthetic hint answer.', { exact: true }).waitFor();
  check(asks().length === 3 && await help.page.locator('[data-study-help-turn]').count() === 3, `STUDY-REQ-008 repeated explanation appends one new pair and guards double activation at ${width}`);
  help.state.failAsk = true;
  await help.page.getByRole('button', { name: 'Explain more', exact: true }).click();
  const failedTurn = help.page.locator('[data-study-help-turn]').last();
  await failedTurn.getByRole('button', { name: 'Retry', exact: true }).waitFor();
  check(await failedTurn.locator('.ml-auto').innerText() === 'Explain more', `STUDY-REQ-008 failed explanation retains its student turn at ${width}`);
  const failedBody = asks().at(-1).body;
  help.state.failAsk = false;
  await failedTurn.getByRole('button', { name: 'Retry', exact: true }).click();
  await failedTurn.getByText('Synthetic hint answer.', { exact: true }).waitFor();
  check(JSON.stringify(asks().at(-1).body) === JSON.stringify(failedBody) && await help.page.locator('[data-study-help-turn]').count() === 4, `STUDY-REQ-008 retry reuses request without duplicating user turn at ${width}`);
  await help.page.getByRole('button', { name: 'Ask a follow-up', exact: true }).click();
  await help.page.getByPlaceholder('Ask Kala about this card…').fill('How can I use this?');
  await help.page.getByPlaceholder('Ask Kala about this card…').press('Enter');
  await help.page.locator('#tour-study-reply').getByText('Synthetic hint answer.', { exact: true }).waitFor();
  check(await help.page.locator('[data-study-help-turn=followup] .ml-auto').innerText() === 'How can I use this?' && asks().at(-1).body.style === 'default' && asks().at(-1).body.question.includes('Side shown: back.'), `STUDY-REQ-008 typed question joins same ordered card thread at ${width}`);
  check((await help.page.locator('[data-study-help-turn]').evaluateAll(nodes => nodes.map(el => el.dataset.studyHelpTurn))).join(',') === 'hint,explain,explain,explain,followup', `STUDY-REQ-008 keeps click order across all help types at ${width}`);
  check(await help.page.locator('[data-study-help-turn]').evaluateAll(nodes => nodes.every(el => Boolean(el.querySelector('.ml-auto').compareDocumentPosition(el.querySelector('.mr-auto')) & Node.DOCUMENT_POSITION_FOLLOWING))), `STUDY-REQ-008 every complete pair puts student before Kala at ${width}`);
  check(help.state.reviews.length === 0 && help.state.posts.every(post => post.path.endsWith('/ask')), `STUDY-REQ-008 help makes only existing stateless asks at ${width}`);
  await help.page.locator('#tour-study-reply').evaluate(el => {
   const scroller = el.closest('[role=log]').firstElementChild;
   scroller.scrollTop = scroller.scrollHeight;
  });
  await help.page.waitForFunction(() => document.querySelector('#tour-study-reply').getBoundingClientRect().bottom <= document.querySelector('#tour-study-dock [data-slot=input-group]').getBoundingClientRect().top + 1);
  check(await help.page.locator('#tour-study-reply').isVisible(), `STUDY-REQ-008 latest answer remains reachable above the dock at ${width}`);
  await capture(help.page, 'study-action-user-turns', width);
  await help.page.getByRole('button', { name: 'Cancel', exact: true }).click();
  help.state.holdAsk = true;
  await help.page.getByRole('button', { name: 'Explain more', exact: true }).click();
  await help.page.getByText('Kala is preparing an explanation…', { exact: true }).waitFor();
  await help.page.getByRole('button', { name: 'Got it', exact: true }).click();
  await help.page.getByText('Recall second', { exact: true }).first().waitFor();
  const lateResponse = help.page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/ask'));
  help.state.holdAsk = false; help.state.releaseAsk(); await lateResponse;
  await help.page.evaluate(() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))));
  check(await help.page.locator('[data-study-help-turn]').count() === 0 && help.state.reviews.length === 1, `STUDY-REQ-008 card switch ignores late assistance and keeps one explicit review at ${width}`);
  check(help.errors.length === 0, `STUDY-REQ-008 no runtime errors at ${width}`);
  await help.context.close();
 }
 console.log(`U2 final UI passed: ${assertions} assertions; screenshots: ${out}`);
} finally { await browser.close(); }
