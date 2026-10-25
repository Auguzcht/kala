/** WI-22 / TWIN-REQ-001..003: synthetic-only shared and integrated UI checks. */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
const requireBrowser=createRequire(resolve(process.env.KALA_BROWSER_TEST_DEPS??'apps/web','package.json'));
const {chromium}=requireBrowser('playwright');
const browser=await chromium.launch({headless:true,...(process.env.KALA_BROWSER_EXECUTABLE?{executablePath:process.env.KALA_BROWSER_EXECUTABLE}:{})});
const out=resolve(process.env.KALA_UI_SCREENSHOTS??'/tmp/kala-twin-presentation');await mkdir(out,{recursive:true});
let assertions=0;const check=(v,label)=>{assert.ok(v,label);assertions++;};
const makeEvents=n=>Array.from({length:n},(_,i)=>({id:`event-${i}`,type:['practice','diagnostic','flashcard','tutor'][i%4],correct:i%2===0,latencyMs:i%3?1250:null,skillName:`Event ${String(i+1).padStart(3,'0')}: Explain durable cloud storage and access controls`,createdAt:new Date(Date.UTC(2026,9,24,12,0)-i*60000).toISOString()}));
const skills=[{skillId:'storage',name:'Cloud storage',bloomLevel:'understand',moduleRef:'Cloud basics',estimate:0.55,attempts:5,band:'proficient'}];
async function fixture(width,{mode='components',reduced='reduce'}={}){
  const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:reduced});const page=await context.newPage();page.setDefaultTimeout(10000);
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
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
    if(route.request().method()!=='GET')throw new Error('Unexpected mutation in presentation test');
    if(path.endsWith('/evidence'))return reply({courseId:'course',evidence:makeEvents(mode==='student'?20:25),nextCursor:null});
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
  return {page,context,errors};
}
const rowNames=page=>page.getByRole('list',{name:'Evidence ledger',exact:true}).locator('li').allTextContents();
try{
  for(const width of [1440,375])for(const reduced of ['reduce','no-preference']){
    const f=await fixture(width,{reduced}),{page}=f;
    await page.getByRole('list',{name:'Evidence ledger',exact:true}).waitFor();
    for(const id of ['student-ring','instructor-ring','null-ring','zero-ring','full-ring']){
      const slot=page.locator(`#${id} [data-slot=mastery-ring-value]`);
      check(await slot.evaluate(el=>getComputedStyle(el).fontSize)==='48px','TWIN-REQ-001 large readiness values use 48px');
      check(await slot.evaluate(el=>{const v=el.getBoundingClientRect(),r=el.parentElement.getBoundingClientRect();return v.left>r.left&&v.right<r.right&&v.top>r.top&&v.bottom<r.bottom;}),'TWIN-REQ-001 null/zero/100 fit inside readiness ring');
    }
    check(await page.locator('#compact-ring [data-slot=mastery-ring-value]').evaluate(el=>getComputedStyle(el).fontSize)==='12px','TWIN-REQ-001 small skill rings remain compact');
    check(await page.getByRole('img',{name:'Board readiness: Proficient, 55 percent',exact:true}).isVisible(),'TWIN-REQ-001 accessible label exposes readiness value');
    check((await rowNames(page)).length===10,'TWIN-REQ-003 initial page has ten events');
    check(await page.getByText('1–10 of 23 recent events',{exact:true}).isVisible(),'TWIN-REQ-003 range labels recent window');
    check(await page.getByRole('link',{name:'Go to previous page'}).getAttribute('aria-disabled')==='true','TWIN-REQ-003 previous endpoint is explicitly disabled');
    const next=page.getByRole('link',{name:'Go to next page'});await next.focus();await next.press('Enter');
    await page.getByText('11–20 of 23 recent events',{exact:true}).waitFor();
    check((await rowNames(page))[0].includes('Event 011'),'TWIN-REQ-003 keyboard navigation preserves server order');
    check(await page.getByRole('list',{name:'Evidence ledger',exact:true}).locator('li').evaluateAll(rows=>rows.every(row=>getComputedStyle(row).opacity==='1')),'TWIN-REQ-003 page replacement does not replay entry animation');
    check(await page.getByRole('link',{name:'Page 2',exact:true}).getAttribute('aria-current')==='page','TWIN-REQ-003 active page is exposed');
    check(await page.evaluate(()=>location.hash)==='','TWIN-REQ-003 navigation does not jump to an anchor');
    await next.click();await page.getByText('21–23 of 23 recent events',{exact:true}).waitFor();
    check((await rowNames(page)).length===3,'TWIN-REQ-003 last page shows remaining three events');
    check(await next.getAttribute('aria-disabled')==='true','TWIN-REQ-003 next endpoint is explicitly disabled');
    check(await page.locator('[data-slot=pagination-link]:visible').evaluateAll(els=>els.every(el=>Math.abs(el.getBoundingClientRect().height-40)<1)),'TWIN-REQ-003 controls match instructor 40px sizing');
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'TWIN-REQ-003 ledger fits mobile and desktop without horizontal overflow');
    await page.getByRole('button',{name:'Use 3 events',exact:true}).click();
    check((await rowNames(page)).length===3&&(await rowNames(page))[0].includes('Event 001'),'TWIN-REQ-003 shrinking data clamps current page');
    check(await page.getByRole('navigation',{name:/Evidence pages/}).count()===0,'TWIN-REQ-003 one-page data hides pager');
    for(const count of [0,1,10,11]){
      await page.getByRole('button',{name:`Use ${count} events`,exact:true}).click();
      if(count===0){check(await page.getByText(/No evidence yet/).isVisible(),'TWIN-REQ-003 empty state remains clear');continue;}
      check((await rowNames(page)).length===Math.min(count,10),'TWIN-REQ-003 finite page size at boundary');
      check(await page.getByRole('navigation',{name:/Evidence pages/}).count()===(count>10?1:0),'TWIN-REQ-003 pager threshold at ten events');
    }
    await page.getByRole('button',{name:'Use 200 events',exact:true}).click();
    if(width>600){await page.getByRole('link',{name:'Page 20',exact:true}).click();await page.getByText('191–200 of 200 recent events',{exact:true}).waitFor();check(await page.locator('[data-slot=pagination-link]').count()<=9,'TWIN-REQ-003 large history uses windowed page links');}
    else{check(await page.locator('[data-slot=pagination-link]:visible').count()===3,'TWIN-REQ-003 mobile keeps full-size previous/current/next controls');}
    if(reduced==='reduce')await page.screenshot({path:resolve(out,`ledger-${width}.png`),fullPage:true,animations:'disabled'});
    check(f.errors.length===0,'shared presentation has no runtime errors');await f.context.close();
  }
  for(const mode of ['student','instructor']){
    const f=await fixture(1440,{mode}),{page}=f;
    if(mode==='student'){
      await page.getByRole('img',{name:/Board readiness:.*55 percent/}).waitFor();
      check(await page.locator('#tour-twin-readiness [data-slot=mastery-ring-value]').evaluate(el=>getComputedStyle(el).fontSize)==='48px','TWIN-REQ-001 student Twin uses prominent readiness value');
      check(await page.locator('[data-slot=card-title]').filter({hasText:'Focus area'}).locator('svg').count()===0,'TWIN-REQ-002 Focus area heading has no icon');
      await page.screenshot({path:resolve(out,'student-twin-1440.png'),animations:'disabled'});
    }else{
      await page.getByRole('tab',{name:'Mastery',exact:true}).click();
      await page.getByRole('img',{name:/Readiness:.*55 percent/}).waitFor();
      check(await page.getByRole('img',{name:/Readiness:.*55 percent/}).locator('[data-slot=mastery-ring-value]').evaluate(el=>getComputedStyle(el).fontSize)==='48px','TWIN-REQ-001 instructor record uses the same prominent value');
      await page.screenshot({path:resolve(out,'instructor-readiness-1440.png'),animations:'disabled'});
      await page.getByRole('tab',{name:'Activity',exact:true}).click();
    }
    check((await rowNames(page)).length===10,'TWIN-REQ-003 integrated student/instructor view pages shared ledger');
    await page.getByRole('link',{name:'Go to next page'}).click();
    await page.getByText(`11–20 of ${mode==='student'?20:25} loaded events`,{exact:true}).waitFor();
    check((await rowNames(page))[0].includes('Event 011'),'TWIN-REQ-003 integrated ledger navigation works');
    if(mode==='instructor')await page.screenshot({path:resolve(out,'instructor-ledger-1440.png'),animations:'disabled'});
    check(f.errors.length===0,'integrated presentation has no runtime errors');await f.context.close();
  }
  const wide=await fixture(1920,{mode:'student'}),{page}=wide;
  const box=async()=>{await page.getByRole('heading',{level:1}).waitFor();return page.getByRole('heading',{level:1}).boundingBox();};
  const twinBox=await box();await page.goto('http://localhost:5173/course/skills');const skillsBox=await box();
  await page.goto('http://localhost:5173/course/diagnostic');await page.getByRole('button',{name:'Submit diagnostic',exact:true}).waitFor();const diagBox=await box();
  check(Math.abs(diagBox.x-skillsBox.x)<1&&Math.abs(diagBox.y-skillsBox.y)<1&&Math.abs(diagBox.x-twinBox.x)<1,`DIAG-REQ-001 wide viewport matches centered Skills/Twin margins: ${JSON.stringify({diagBox,skillsBox,twinBox})}`);
  await page.screenshot({path:resolve(out,'diagnostic-1920.png'),animations:'disabled'});
  await page.goto('http://localhost:5173/course/skill/storage');await page.getByRole('heading',{name:'Cloud storage',exact:true}).waitFor();
  check(await page.locator('main').evaluate(el=>getComputedStyle(el).maxWidth)==='none','DIAG-REQ-001 singular skill session retains its full-width shell');
  check(wide.errors.length===0,'wide margin fixture has no runtime errors');await wide.context.close();
  console.log(`Twin presentation checks passed: ${assertions} assertions; screenshots: ${out}`);
}finally{await browser.close();}
