/** WI-25 / TWIN-REQ-010 / INSTR-REQ-010: synthetic-only history integration. */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
const requireBrowser=createRequire(resolve(process.env.KALA_BROWSER_TEST_DEPS??'apps/web','package.json'));
const {chromium}=requireBrowser('playwright');
const browser=await chromium.launch({headless:true,...(process.env.KALA_BROWSER_EXECUTABLE?{executablePath:process.env.KALA_BROWSER_EXECUTABLE}:{})});
const out=resolve(process.env.KALA_UI_SCREENSHOTS??'/tmp/kala-evidence-history');await mkdir(out,{recursive:true});
let assertions=0;const check=(v,label)=>{assert.ok(v,label);assertions++;};
const makeEvents=n=>Array.from({length:n},(_,i)=>({id:`event-${i}`,type:['practice','diagnostic','flashcard','tutor'][i%4],correct:i%2===0,latencyMs:i%3?1250:null,skillName:`Event ${String(i+1).padStart(3,'0')}: Explain durable cloud storage and access controls`,createdAt:new Date(Date.UTC(2026,9,24,12,0)-i*60000).toISOString()}));
const skills=[{skillId:'storage',name:'Cloud storage',bloomLevel:'understand',moduleRef:'Cloud basics',estimate:0.55,attempts:5,band:'proficient'}];
async function fixture(width,{mode='components',reduced='reduce'}={}){
  const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:reduced});const page=await context.newPage();page.setDefaultTimeout(10000);
  const state={calls:[],nextStatus:200,mutations:0};const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await context.route('**/*',async route=>{
    const url=new URL(route.request().url());if(url.hostname!=='localhost'||url.port!=='5173')return route.abort();
    if(url.pathname==='/__twin_presentation')return route.fulfill({contentType:'text/html',body:`<!doctype html><html><head><link rel="stylesheet" href="/src/styles/globals.css"></head><body><div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;</script><script type="module">
      import React from '/node_modules/.vite/deps/react.js';import ReactDOM from '/node_modules/.vite/deps/react-dom_client.js';
      import {MasteryRing} from '/src/components/kala/mastery-ring.tsx';import {EvidenceLedger} from '/src/components/kala/evidence-ledger.tsx';
      const events=${JSON.stringify(makeEvents(200))};
      function App(){const [count,setCount]=React.useState(23);return React.createElement('main',{style:{padding:24,maxWidth:1100,margin:'auto'}},React.createElement('div',{className:'flex flex-wrap items-center gap-6'},...[['student-ring',176,0.55,'Board readiness'],['instructor-ring',144,0.55,'Readiness'],['compact-ring',56,0.55,'Skill'],['null-ring',144,null,'No estimate'],['zero-ring',144,0,'Zero'],['full-ring',144,1,'Full']].map(([id,size,estimate,label])=>React.createElement('div',{id,key:id},React.createElement(MasteryRing,{size,estimate,label})))),React.createElement('div',{className:'my-6 flex flex-wrap gap-2'},...[0,1,10,11,23,200,3].map(n=>React.createElement('button',{key:n,onClick:()=>setCount(n),className:'border p-2'},'Use '+n+' events'))),React.createElement('section',{'aria-label':'Test ledger'},React.createElement(EvidenceLedger,{events:events.slice(0,count)})))}
      ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(App));</script></body></html>`});
    if(url.pathname.endsWith('/src/lib/auth/AuthProvider.tsx'))return route.fulfill({contentType:'application/javascript',body:`export const AuthProvider=({children})=>children;export const useSession=()=>({userId:'demo',institutionId:'inst',role:'${mode==='instructor'?'instructor':'student'}',courseId:'course',displayName:'Demo learner'});export const useSetSession=()=>()=>{};`});
    if(url.pathname.endsWith('/src/lib/api/client.ts'))return route.fulfill({contentType:'application/javascript',body:`export async function api(path,init){const r=await fetch('/__twin_api'+path,init);if(!r.ok)throw new Error('API '+r.status);return r.json();}`});
    if(!url.pathname.startsWith('/__twin_api'))return route.continue();
    const path=url.pathname.slice('/__twin_api'.length);const reply=json=>route.fulfill({json});
    if(route.request().method()!=='GET'){state.mutations++;return route.abort();}
    if(path.endsWith('/evidence')){state.calls.push(path+'?'+url.searchParams.toString());if(state.nextStatus!==200){const status=state.nextStatus;state.nextStatus=200;return route.fulfill({status,json:{detail:'synthetic failure'}});}const cursor=url.searchParams.get('cursor');const offset=cursor?Number(cursor.slice(5)):0;const all=makeEvents(61);const evidence=all.slice(offset,offset+25);return reply({courseId:'course',evidence,nextCursor:offset+25<all.length?'page-'+(offset+25):null});}
    if(path==='/courses/course')return reply({id:'course',title:'AWS101'});
    if(path.endsWith('/twin'))return reply({courseId:'course',readiness:0.55,skills,evidence:makeEvents(20)});
    if(path.endsWith('/next-up'))return reply({courseId:'course',next:null});
    if(path.endsWith('/summary'))return reply({xp:0,attempts:0,correct:0,streakDays:0,badges:[]});
    if(path.endsWith('/diagnostic/status'))return reply({courseId:'course',due:false,dueSkillCount:0});
    if(path.endsWith('/diagnostic'))return reply({courseId:'course',status:'ready',readyCount:1,questions:[{id:'q',skillId:'storage',bloomLevel:'understand',prompt:'Which storage fits?',choices:[{id:'a',label:'Object storage'},{id:'b',label:'Temporary disk'}]}],pendingSkillIds:[],failedSkillIds:[],skippedSkillCount:0});
    if(path.endsWith('/at-risk'))return reply({courseId:'course',flags:[]});
    if(path.endsWith('/recommendations'))return reply({courseId:'course',userId:'learner',recommendations:[]});
    if(path.endsWith('/record'))return reply({courseId:'course',userId:'learner',displayName:'Demo learner',pseudonym:'Learner A',initials:'DL',readiness:0.55,band:'proficient',cohortReadiness:0.5,percentile:0.5,accuracy:0.6,momentum:null,attempts:20,evidenceCount:200,hintsUsed:0,lastActiveAt:'2026-10-24T12:00:00Z',daysInactive:0,status:'developing',skills,activityByType:[],activitySeries:[],readinessTrend:[],evidence:makeEvents(200)});
    return reply({});
  });
  await page.goto(`http://localhost:5173/${mode==='components'?'__twin_presentation':mode==='student'?'course/twin':'class/student/learner'}`);
  return {page,context,errors,state};
}
const rowNames=page=>page.getByRole('list',{name:'Evidence ledger',exact:true}).locator('li').allTextContents();
try {
  for(const width of [375,1440]) for(const reduced of ['reduce','no-preference']) for(const mode of ['student','instructor']) {
    const f=await fixture(width,{mode,reduced}),{page,state}=f;
    if(mode==='instructor') await page.getByRole('tab',{name:'Activity',exact:true}).click();
    const noun=mode==='student'?'your':"this learner's";
    await page.getByText(`Showing 25 of ${noun} activity`,{exact:true}).waitFor();
    check((await rowNames(page)).length===10,'history preserves ten-row presentation pages');
    check(await page.getByText('1–10 of 25 loaded events',{exact:true}).isVisible(),'loaded range is explicit');
    const older=page.getByRole('button',{name:'Load older activity',exact:true});
    check(await older.evaluate(el=>el.getBoundingClientRect().height>=40),'older control is at least 40px');
    state.nextStatus=500;
    await older.focus();await older.press('Enter');
    await page.getByRole('button',{name:'Retry activity',exact:true}).waitFor();
    check(mode==='student'?(await rowNames(page)).length===10:await page.getByRole('list',{name:'Evidence ledger',exact:true}).count()===0,'transient own history retains rows; failed staff history hides rows');
    await page.getByRole('button',{name:'Retry activity',exact:true}).click();
    await page.getByText(`Showing 50 of ${noun} activity`,{exact:true}).waitFor();
    state.nextStatus=422;
    await older.click();
    await page.getByRole('button',{name:'Reload activity',exact:true}).waitFor();
    check(await older.count()===0,'invalid cursor offers reload instead of replay');
    await page.getByRole('button',{name:'Reload activity',exact:true}).click();
    await page.getByText(`Showing 25 of ${noun} activity`,{exact:true}).waitFor();
    await older.click();await page.getByText(`Showing 50 of ${noun} activity`,{exact:true}).waitFor();
    await older.click();await page.getByText(`Showing 61 of ${noun} activity`,{exact:true}).waitFor();
    check(await older.count()===0,'final page has no older action');
    for(let i=0;i<6;i++) await page.getByRole('link',{name:'Go to next page',exact:true}).click();
    check((await rowNames(page)).length===1&&(await rowNames(page))[0].includes('Event 061'),'first event in history is reachable');
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'no horizontal overflow');
    check(state.calls.every(p=>p.includes('limit=25')),'fetch uses explicit page size');
    check(state.mutations===0&&f.errors.length===0,'views produce no mutations or browser errors');
    await page.screenshot({path:resolve(out,`${mode}-${width}-${reduced}.png`),fullPage:true});
    await f.context.close();
  }
  console.log(`WI-25 history browser checks: ${assertions} assertions passed`);
} finally { await browser.close(); }
