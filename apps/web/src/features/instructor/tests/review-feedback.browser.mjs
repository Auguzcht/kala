/** INSTR-REQ-001/002: real components/hooks, intercepted synthetic API only. */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
const requireBrowser = createRequire(resolve(process.env.KALA_BROWSER_TEST_DEPS ?? 'apps/web', 'package.json'));
const { chromium } = requireBrowser('playwright');
const browser = await chromium.launch({headless:true,...(process.env.KALA_BROWSER_EXECUTABLE ? {executablePath:process.env.KALA_BROWSER_EXECUTABLE} : {})});
const out=resolve(process.env.KALA_UI_SCREENSHOTS ?? '/tmp/kala-instructor-feedback');
await mkdir(out,{recursive:true});
let assertions=0;
const check=(condition,label)=>{assert.ok(condition,label);assertions++;};
const proposal={id:'proposal-1',name:'Explain durable cloud storage',bloom_level:'understand',blueprint_weight:1,proposed_source:'Course material'};
const recommendation={id:'rec-1',userId:'learner',courseId:'course',skillId:null,skillName:null,title:'Review cloud storage',kind:'practice',priority:'medium',rationale:'Use the recorded practice evidence.',evidence:[{label:'Practice recorded',detail:'Synthetic fixture'}],status:'suggested',confidence:0.8,expectedGain:0.1,source:'heuristic',decidedBy:null,decidedAt:null,decisionNote:null,instructorNote:null,createdAt:null};
async function fixture({type='skill',fail=false,slow=false,reduced=false}={}) {
  const context=await browser.newContext({viewport:{width:1100,height:900},reducedMotion:reduced?'reduce':'no-preference'});
  const page=await context.newPage();
  page.setDefaultTimeout(10000);
  const hookSource=await (await page.request.get('http://localhost:5173/src/features/instructor/hooks/use-instructor.ts')).text();
  const queryModule=hookSource.match(/from "([^"]*\/@tanstack_react-query\.js[^\"]*)"/)[1];
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.clock.install({time:new Date('2026-10-25T00:00:00Z')});
  const state={requests:[],responseSent:false,done:false,fail,release:null,page};
  let release;
  const held=new Promise(r=>{release=r;});state.release=release;
  await context.route('**/*',async route=>{
    const url=new URL(route.request().url());
    if(url.hostname!=='localhost'||url.port!=='5173')return route.abort();
    if(url.pathname==='/__instructor_feedback')return route.fulfill({contentType:'text/html',body:`<div id="root"></div><script type="module">
      import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;
      </script><script type="module">
      import React from '/node_modules/.vite/deps/react.js';
      import ReactDOM from '/node_modules/.vite/deps/react-dom_client.js';
      import {QueryClient,QueryClientProvider} from '${queryModule}';
      import {SkillReviewPanel} from '/src/features/instructor/components/SkillReviewPanel.tsx';
      import {DecisionCenter} from '/src/features/instructor/components/DecisionCenter.tsx';
      import {Toaster} from '/src/components/ui/sonner.tsx';
      import '/src/styles/globals.css';
      const client=new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}});
      ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(QueryClientProvider,{client},React.createElement('main',{style:{padding:24}},React.createElement(${type==='skill'?'SkillReviewPanel':'DecisionCenter'},{courseId:'course',userId:'learner',learnerName:'Demo learner'}),React.createElement(Toaster))));
    </script>`});
    if(url.pathname.endsWith('/src/lib/api/client.ts'))return route.fulfill({contentType:'application/javascript',body:`export async function api(path,init){const r=await fetch('/__feedback_api'+path,init);if(!r.ok)throw new Error('API '+r.status);return r.json();}`});
    if(!url.pathname.startsWith('/__feedback_api'))return route.continue();
    const path=url.pathname.slice('/__feedback_api'.length);
    if(route.request().method()==='PATCH') {
      const body=route.request().postDataJSON();state.requests.push(body);
      if(slow)await held;
      if(state.fail){state.responseSent=true;return route.fulfill({status:500,json:{detail:'Synthetic failure'}});}
      state.done=true;state.responseSent=true;
      return route.fulfill({json:type==='skill'?{skillId:proposal.id,status:body.status}:{...recommendation,status:body.status,title:body.title??recommendation.title,kind:body.kind??recommendation.kind,decisionNote:body.decision_note??null,instructorNote:body.instructor_note??null,decidedBy:'teacher',decidedAt:'2026-10-25T00:00:00Z'}});
    }
    if(path.endsWith('/skills/proposed'))return route.fulfill({json:{courseId:'course',proposed:state.done?[]:[proposal]}});
    if(path.endsWith('/recommendations'))return route.fulfill({json:{courseId:'course',userId:'learner',recommendations:[{...recommendation,status:state.done?state.requests.at(-1).status:'suggested'}]}});
    throw new Error('Unexpected fixture request '+path);
  });
  await page.goto('http://localhost:5173/__instructor_feedback');
  await page.getByText(type==='skill'?proposal.name:'Kala recommends. You decide.',{exact:true}).waitFor().catch(async e=>{throw new Error(`${errors.join('; ')}; ${await page.locator('body').innerText()}; ${e.message}`);});
  await page.clock.pauseAt(new Date('2026-10-25T00:00:10Z'));
  return {context,page,state,errors};
}
const waitPatch=async state=>{for(let i=0;i<100&&!state.responseSent;i++)await new Promise(r=>setTimeout(r,10));check(state.responseSent,'synthetic network response delivered');await state.page.clock.runFor(10);};
try {
  for(const action of ['approved','rejected']) {
    const f=await fixture({reduced:action==='rejected'}),{page,state}=f;
    const button=page.getByRole('button',{name:action==='approved'?'Approve':'Reject',exact:true});
    if(action==='rejected') {await button.focus();await button.press('Enter');} else await button.click();
    await waitPatch(state);
    check(state.requests.length===1&&state.requests[0].status===action,'INSTR-REQ-001 sends the chosen review immediately once');
    check(await button.isDisabled(),'INSTR-REQ-001 fast response retains pending lock');
    check(await button.getAttribute('aria-busy')==='true','INSTR-REQ-001 selected review exposes busy state');
    check(await button.locator('svg.animate-spin').count()===1,'INSTR-REQ-001 selected action shows shared Spinner');
    if(action==='rejected')check(await button.locator('svg').evaluate(el=>getComputedStyle(el).animationName)==='none','INSTR-REQ-001 reduced motion keeps Spinner static');
    await page.clock.runFor(300);
    check(await page.getByText(proposal.name,{exact:true}).isVisible(),'INSTR-REQ-001 row stays visible during minimum interval');
    await page.screenshot({path:resolve(out,`skill-${action}-pending.png`)});
    await page.clock.runFor(80);await page.clock.resume();await page.getByText(proposal.name,{exact:true}).waitFor({state:'hidden'});
    check(f.errors.length===0,'skill fixture has no runtime errors');await f.context.close();
  }
  for(const mode of ['fail','slow']) {
    const f=await fixture({fail:mode==='fail',slow:mode==='slow'}),{page,state}=f;
    const approve=page.getByRole('button',{name:'Approve',exact:true});
    await approve.click();
    if(mode==='slow') {
      await page.clock.runFor(1000);
      check(await approve.isDisabled()&&state.requests.length===1,'INSTR-REQ-001 slow network stays locked beyond minimum');
      state.release();await waitPatch(state);await page.clock.runFor(80);await page.clock.resume();
      await page.getByText(proposal.name,{exact:true}).waitFor({state:'hidden'});
    } else {
      await waitPatch(state);await page.clock.runFor(380);await page.clock.resume();
      await page.getByRole('alert').waitFor();
      check(await approve.isEnabled(),'INSTR-REQ-001 failed review is retryable');
      check(await page.getByText(proposal.name,{exact:true}).isVisible(),'INSTR-REQ-001 failure retains proposal');
      state.fail=false;state.responseSent=false;await approve.click();await waitPatch(state);await page.clock.runFor(380);await page.clock.resume();
      await page.getByText(proposal.name,{exact:true}).waitFor({state:'hidden'});
      check(state.requests.length===2,'INSTR-REQ-001 retry sends exactly one new request');
    }
    check(f.errors.length===0,'review outcome fixture has no runtime errors');await f.context.close();
  }
  for(const choice of ['approved','modified','rejected']) {
    const f=await fixture({type:'recommendation'}),{page,state}=f;
    await page.getByRole('button',{name:choice==='approved'?'Approve':choice==='modified'?'Modify':'Decline',exact:true}).click();
    if(choice==='modified')await page.getByLabel('Rewrite the action').fill('Review the edited storage task');
    await page.getByRole('button',{name:choice==='rejected'?'Confirm decline':'Confirm and assign to learner',exact:true}).click();
    await waitPatch(state);
    const recording=page.getByRole('button',{name:'Recording',exact:true});
    check(await recording.isVisible()&&await recording.isDisabled(),'INSTR-REQ-002 keeps card mounted with Recording after fast success');
    check(await recording.getAttribute('aria-busy')==='true'&&await recording.locator('svg.animate-spin').count()===1,'INSTR-REQ-002 recording exposes busy Spinner');
    check(await page.getByRole('button',{name:'Approve',exact:true}).isDisabled(),'INSTR-REQ-002 locks decision choices');
    await page.clock.runFor(300);check(await recording.isVisible(),'INSTR-REQ-002 minimum interval is visible');
    if(choice==='approved')await page.screenshot({path:resolve(out,'recommendation-recording.png')});
    await page.clock.runFor(80);await page.clock.resume();await recording.waitFor({state:'hidden'});
    check(await page.getByRole('button',{name:/Decision history/}).isVisible(),'INSTR-REQ-002 confirmed decision moves to history');
    check(state.requests.length===1&&state.requests[0].status===choice,'INSTR-REQ-002 sends exactly the selected decision');
    if(choice==='modified')check(state.requests[0].title==='Review the edited storage task','INSTR-REQ-002 preserves edited decision payload');
    check(f.errors.length===0,'decision fixture has no runtime errors');await f.context.close();
  }
  for(const mode of ['fail','slow']) {
    const f=await fixture({type:'recommendation',fail:mode==='fail',slow:mode==='slow',reduced:true}),{page,state}=f;
    await page.getByRole('button',{name:'Approve',exact:true}).click();
    const note=page.getByLabel(/Why you approved/);await note.fill('Keep this decision note');
    await page.getByRole('button',{name:'Confirm and assign to learner',exact:true}).click();
    await page.clock.runFor(10);
    const recording=page.getByRole('button',{name:'Recording',exact:true});
    check(await recording.locator('svg').evaluate(el=>getComputedStyle(el).animationName)==='none','INSTR-REQ-002 reduced motion keeps Spinner static');
    check(await note.isDisabled(),'INSTR-REQ-002 recording locks notes');
    if(mode==='slow') {
      await page.clock.runFor(1000);check(await recording.isVisible(),'INSTR-REQ-002 slow response stays Recording');
      state.release();await waitPatch(state);await page.clock.runFor(80);await page.clock.resume();await recording.waitFor({state:'hidden'});
    } else {
      await waitPatch(state);await page.clock.runFor(380);await page.clock.resume();await recording.waitFor({state:'hidden'});
      check(await note.inputValue()==='Keep this decision note'&&await note.isEnabled(),'INSTR-REQ-002 failure preserves editable note');
      check(await page.getByRole('button',{name:'Confirm and assign to learner',exact:true}).isEnabled(),'INSTR-REQ-002 failed confirmation is retryable');
      check(await page.getByRole('button',{name:/Decision history/}).count()===0,'INSTR-REQ-002 failed decision never reaches history');
      state.fail=false;state.responseSent=false;await page.getByRole('button',{name:'Confirm and assign to learner',exact:true}).click();await waitPatch(state);await page.clock.runFor(380);await page.clock.resume();
      await page.getByRole('button',{name:/Decision history/}).waitFor();check(state.requests.length===2,'INSTR-REQ-002 retry sends one new request');
    }
    check(f.errors.length===0,'decision outcome fixture has no runtime errors');await f.context.close();
  }
  console.log(`Instructor feedback checks passed: ${assertions} assertions; screenshots: ${out}`);
} finally {await browser.close();}
