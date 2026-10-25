/** APPROVAL-06 Lane U: isolated real-UI regression checks, no hosted traffic. */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
const requireBrowser=createRequire(resolve(process.env.KALA_BROWSER_TEST_DEPS??'apps/web','package.json'));
const {chromium}=requireBrowser('playwright');
const browser=await chromium.launch({headless:true,...(process.env.KALA_BROWSER_EXECUTABLE?{executablePath:process.env.KALA_BROWSER_EXECUTABLE}:{})});
const out=resolve(process.env.KALA_UI_SCREENSHOTS??'/tmp/kala-frontend-closeout');await mkdir(out,{recursive:true});
let assertions=0;const check=(value,label)=>{assert.ok(value,label);assertions++;};
const skill=i=>({skillId:`skill-${i}`,name:`Cloud skill ${String(i).padStart(2,'0')}`,moduleRef:'Cloud basics',bloomLevel:'understand',estimate:0.5,attempts:2,band:'proficient'});
const question={id:'q',skillId:'skill-0',bloomLevel:'understand',prompt:'Which storage fits?',choices:[{id:'a',label:'Object storage'},{id:'b',label:'Temporary disk'}]};
async function fixture(width,{role='student',pagers=false,rootError=false}={}){
 const context=await browser.newContext({viewport:{width,height:950},reducedMotion:'reduce'}),page=await context.newPage();page.setDefaultTimeout(20000);
 const errors=[],state={failTwin:false,empty:false,failDiagnostic:false,failDeck:false,diagnosticCalls:0,twinCalls:0,status:{due:false,dueSkillCount:0},diagnosticResponse:null,mutations:0};
 page.on('pageerror',error=>{if(!rootError)errors.push(error.message);});
 await context.route('**/*',async route=>{
  const url=new URL(route.request().url());if(url.hostname!=='localhost'||url.port!=='5173')return route.abort();
  if(url.pathname.endsWith('/src/lib/auth/AuthProvider.tsx'))return route.fulfill({contentType:'application/javascript',body:`export const AuthProvider=({children})=>children;export const useSession=()=>(${role===null?'null':JSON.stringify({role,courseId:'course',userId:'demo',institutionId:'inst',displayName:'Demo learner'})});export const useSetSession=()=>()=>{};`});
  if(url.pathname.endsWith('/src/lib/api/client.ts'))return route.fulfill({contentType:'application/javascript',body:`export async function api(path,init){const r=await fetch('/__closeout_api'+path,init);if(!r.ok)throw new Error('Synthetic API failure');return r.json();}`});
  if(rootError&&url.pathname.endsWith('/src/routes/course/tutor.tsx')){
   const response=await route.fetch(),source=await response.text();
   return route.fulfill({response,body:source.replace('function TutorPage() {','function TutorPage() { throw new Error("Synthetic route failure");')});
  }
  if(pagers&&url.pathname==='/__closeout_pagers'){
   const src=await (await page.request.get('http://localhost:5173/src/features/instructor/hooks/use-instructor.ts')).text();
   const queryModule=src.match(/from "([^"]*\/@tanstack_react-query\.js[^\"]*)"/)[1];
   return route.fulfill({contentType:'text/html',body:`<link rel="stylesheet" href="/src/styles/globals.css"><div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;</script><script type="module">import React from '/node_modules/.vite/deps/react.js';import ReactDOM from '/node_modules/.vite/deps/react-dom_client.js';import {QueryClient,QueryClientProvider} from '${queryModule}';import {RosterTable} from '/src/features/instructor/components/RosterTable.tsx';import {SkillReviewPanel} from '/src/features/instructor/components/SkillReviewPanel.tsx';const client=new QueryClient({defaultOptions:{queries:{retry:false},mutations:{retry:false}}});ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(QueryClientProvider,{client},React.createElement('main',{style:{padding:16}},React.createElement('section',{'aria-label':'Roster'},React.createElement(RosterTable,{courseId:'course',filter:'all',deidentified:false,onSelect:()=>{},onFilterChange:()=>{}})),React.createElement('section',{'aria-label':'Proposals'},React.createElement(SkillReviewPanel,{courseId:'course'})))));</script>`});
  }
  if(!url.pathname.startsWith('/__closeout_api'))return route.continue();
  if(route.request().method()!=='GET'){state.mutations++;return route.fulfill({status:405,json:{}});}
  const path=url.pathname.slice('/__closeout_api'.length),reply=(json,status=200)=>route.fulfill({json,status});
  if(path.startsWith('/dashboard/')&&path.endsWith('/evidence'))return reply({courseId:'course',evidence:Array.from({length:25},(_,i)=>({id:`event-${i}`,type:'practice',correct:true,latencyMs:1000,skillName:'Cloud skill 00',createdAt:'2026-10-25T00:00:00Z'})),nextCursor:null});
  if(path==='/courses/course')return reply({id:'course',title:'AWS101'});
  if(path.endsWith('/twin')){state.twinCalls++;return reply({courseId:'course',readiness:0.5,skills:state.empty?[]:Array.from({length:17},(_,i)=>skill(i)),evidence:[]},state.failTwin?500:200);}
  if(path.endsWith('/next-up'))return reply({courseId:'course',next:null});
  if(path.endsWith('/summary'))return reply({xp:0,attempts:0,correct:0,streakDays:0,badges:[]});
  if(path.endsWith('/diagnostic/status'))return reply({courseId:'course',...state.status});
  if(path.endsWith('/diagnostic')){state.diagnosticCalls++;return reply({courseId:'course',status:'ready',readyCount:1,questions:[question],pendingSkillIds:[],failedSkillIds:[],skippedSkillCount:0,...state.diagnosticResponse},state.failDiagnostic?500:200);}
  if(path.endsWith('/bank/status'))return reply({courseId:'course',building:false,bankServing:true,skills:[]});
  if(path.endsWith('/plan'))return reply({plan:[]});
  if(path.endsWith('/at-risk'))return reply({courseId:'course',flags:[]});
  if(path.endsWith('/recommendations'))return reply({courseId:'course',userId:'learner',recommendations:[]});
  if(path.endsWith('/record'))return reply({courseId:'course',userId:'learner',displayName:'Demo learner',pseudonym:'Learner A',initials:'DL',readiness:0.5,band:'proficient',cohortReadiness:0.5,percentile:50,accuracy:0.5,momentum:null,attempts:200,evidenceCount:200,hintsUsed:0,lastActiveAt:'2026-10-25T00:00:00Z',daysInactive:0,status:'developing',skills:[skill(0)],activityByType:[],activitySeries:[],readinessTrend:[],evidence:Array.from({length:25},(_,i)=>({id:`event-${i}`,type:'practice',correct:true,latencyMs:1000,skillName:'Cloud skill 00',createdAt:'2026-10-25T00:00:00Z'}))});
  if(path.endsWith('/roster'))return reply({courseId:'course',students:Array.from({length:23},(_,i)=>({userId:`learner-${i}`,displayName:`Learner ${String(i).padStart(2,'0')}`,pseudonym:`Learner ${i}`,initials:'DL',readiness:null,band:'no-evidence',attempts:0,evidenceCount:0,accuracy:null,lastActiveAt:null,daysInactive:null,weakestSkillName:null,skillsWithEvidence:0,skillsTotal:17,status:'not-started'}))});
  if(path.endsWith('/skills/proposed'))return reply({courseId:'course',proposed:Array.from({length:19},(_,i)=>({id:`proposal-${i}`,name:`Proposed skill ${i}`,bloom_level:'understand',blueprint_weight:1,proposed_source:'Material'}))});
  if(path.includes('/flashcards'))return reply({courseId:'course',cards:[],stats:{tracked:0,due:0,learning:0,mastered:0},mode:'review',sessionId:'session',hasMore:false},state.failDeck?500:200);
  return reply({});
 });
 return {page,context,state,errors};
}
async function capture(page,name,width){await page.screenshot({path:resolve(out,`${name}-${width}.png`),animations:'disabled'});}
async function keyboardPage(scope,page){
 const next=scope.getByRole('link',{name:'Go to next page'}),prev=scope.getByRole('link',{name:'Go to previous page'});
 await next.waitFor();check(await prev.getAttribute('aria-disabled')==='true'&&await prev.getAttribute('tabindex')==='-1','first endpoint is explicitly disabled');
 check(await next.evaluate(el=>el.tabIndex===0&&Math.round(el.getBoundingClientRect().height)===40),'next is Tab-reachable and 40px');
 await next.focus();await next.press('Enter');
 await scope.locator('[aria-current=page]').filter({hasText:'2'}).waitFor();
 check(await page.evaluate(()=>location.hash)==='','keyboard page change does not jump to a hash');
 await next.focus();await next.press('Enter');await scope.locator('[aria-current=page]').filter({hasText:'3'}).waitFor();
 check(await next.getAttribute('aria-disabled')==='true'&&await next.getAttribute('tabindex')==='-1','last endpoint is explicitly disabled');
 await prev.focus();await prev.press('Enter');await scope.locator('[aria-current=page]').filter({hasText:'2'}).waitFor();
}
try{
 for(const width of [1440,375]){
  for(const activation of ['pointer','keyboard']){
   const f=await fixture(width),{page,state}=f;state.failDiagnostic=true;
   await page.goto('http://localhost:5173/course/diagnostic');await page.getByText('We could not load the diagnostic',{exact:true}).waitFor().catch(async e=>{throw new Error(`Diagnostic fixture: ${f.errors.join('; ')}; ${await page.locator('body').innerText()}; calls=${state.diagnosticCalls}; ${e.message}`);});
   if(activation==='pointer')await capture(page,'diagnostic-error',width);
   const calls=state.diagnosticCalls;state.failDiagnostic=false;const retry=page.getByRole('button',{name:'Retry',exact:true});
   if(activation==='keyboard'){await retry.focus();await retry.press('Enter');}else await retry.click();
   await page.getByRole('button',{name:'Submit diagnostic',exact:true}).waitFor();check(state.diagnosticCalls>calls,'Diagnostic Retry refetches and recovers by '+activation);
   check(state.mutations===0&&f.errors.length===0,'load Retry makes no submit and has no runtime error');await f.context.close();
  }
  for(const path of ['skills','lessons','flashcards']){
   const f=await fixture(width),{page,state}=f;state.failTwin=true;
   await page.goto('http://localhost:5173/course/'+path);await page.getByText('We could not load your skills',{exact:true}).waitFor();
   check(await page.getByText('No skills mapped yet',{exact:true}).count()===0,'failed '+path+' fetch is not an empty course');await capture(page,`${path}-error`,width);
   state.failTwin=false;const retry=page.getByRole('button',{name:'Retry',exact:true});await retry.focus();await retry.press('Enter');await page.getByRole('button').filter({hasText:'Cloud skill 00'}).waitFor();
   check(state.mutations===0&&f.errors.length===0,path+' Retry restores skills without writes');
   state.empty=true;await page.reload();await page.getByText('No skills mapped yet',{exact:true}).waitFor();check(await page.getByRole('button',{name:'Retry',exact:true}).count()===0,'genuine empty '+path+' is separate');await f.context.close();
  }
  for(const role of ['student','instructor',null])for(const rootError of [false,true]){
   const f=await fixture(width,{role,rootError}),{page}=f;
   // No-session error rendering is exercised by not-found; /course correctly redirects unauthenticated visits.
   if(rootError&&role===null){await f.context.close();continue;}
   await page.goto('http://localhost:5173/'+(rootError?'course/tutor':'missing-page'));
   await page.getByRole('heading',{name:rootError?"We couldn't open this page":"We couldn't find that page",exact:true}).waitFor();
   if(role){check(await page.getByRole('link',{name:'Back to workspace',exact:true}).getAttribute('href')===(role==='student'?'/course':'/class'),'recovery retains '+role+' workspace');}
   else {check(await page.getByRole('link',{name:'Back to workspace',exact:true}).count()===0,'no-session recovery has no dead destination');await page.getByText('Your session ended. Go back to your Blackboard course and open Kala again.',{exact:true}).waitFor();}
   await capture(page,`${rootError?'root-error':'not-found'}-${role??'no-session'}`,width);await f.context.close();
  }
  const f=await fixture(width),{page}=f;
  await page.goto('http://localhost:5173/');await page.getByText('Open Kala from your course in Blackboard.',{exact:true}).waitFor();check(await page.getByText('Scaffold ready',{exact:true}).count()===0,'public root has no scaffold');await capture(page,'public-root',width);
  await page.goto('http://localhost:5173/session-expired');await page.getByText('Your session ended. Go back to your Blackboard course and open Kala again.',{exact:true}).waitFor();check(await page.getByRole('button',{name:'Re-launch',exact:true}).count()===0,'expiry has no dead relaunch');await capture(page,'session-expired',width);
  await page.goto('http://localhost:5173/course/practice');await page.waitForURL('**/course/skills');check(!page.url().includes('practice'),'unscoped Practice bridges to Skills');
  await page.goto('http://localhost:5173/course/practice?skillId=skill-0&setId=saved');await page.waitForURL('**/course/skill/skill-0?**');const dest=new URL(page.url());check(dest.searchParams.get('setId')==='saved'&&dest.searchParams.get('tab')==='test'&&!dest.searchParams.has('start'),'legacy saved link preserves skill/set and does not start');
  await page.goto('http://localhost:5173/course/twin');await page.getByRole('button',{name:'Practice this',exact:true}).click();await page.waitForURL('**/course/skill/skill-0?tab=test');check(!new URL(page.url()).searchParams.has('start'),'Focus action keeps skill in Test browse');
  await page.goto('http://localhost:5173/course/twin');await page.getByText('Last 20 events',{exact:true}).waitFor();
  const group=page.getByRole('button',{name:/Understand/i});await group.click();const twinPager=page.locator('[data-slot=accordion-content]').filter({has:page.locator('[data-slot=pagination]')});await keyboardPage(twinPager,page);
  check(f.errors.length===0,'navigation/Twin has no runtime error');await f.context.close();
  const d=await fixture(width);d.state.failDeck=true;await d.page.goto('http://localhost:5173/course/flashcards');await d.page.locator('#tour-flashcards-recommended').click();await d.page.getByText('We could not load flashcards',{exact:true}).waitFor();d.state.failDeck=false;await d.page.getByRole('button',{name:'Retry',exact:true}).click();await d.page.getByText('No cards yet',{exact:true}).waitFor();check(d.state.mutations===0&&d.errors.length===0,'course-wide legacy deck retains error Retry and genuine empty state');await d.context.close();
  const p=await fixture(width,{pagers:true});await p.page.goto('http://localhost:5173/__closeout_pagers');for(const name of ['Roster','Proposals'])await keyboardPage(p.page.getByRole('region',{name,exact:true}),p.page);check(p.errors.length===0,'instructor pager fixtures have no runtime errors');await p.context.close();
  const a=await fixture(width);for(const [status,due,waiting,label] of [
   [{due:true},true,null,'Find your starting point'],
   [{due:true,dueSkillCount:0,waitingForMaterialCount:3},false,3,null],
   [{due:false,dueSkillCount:2,waitingForMaterialCount:1},true,1,'2 skills need a baseline'],
   [{due:false,dueSkillCount:0,waitingForMaterialCount:0},false,null,null],
  ]){
   a.state.status=status;await a.page.goto('http://localhost:5173/course');await a.page.getByRole('heading',{name:'Welcome back, Demo',exact:true}).waitFor();
   if(due){await a.page.getByRole('button',{name:'Take diagnostic',exact:true}).waitFor();await a.page.getByText(label,{exact:true}).waitFor();}
   else {await a.page.getByText('AWS101',{exact:true}).first().waitFor();await a.page.waitForTimeout(150);check(await a.page.getByRole('button',{name:'Take diagnostic',exact:true}).count()===0,'non-actionable status hides workspace action');}
   check((await a.page.locator('#nav-diagnostic').getAttribute('aria-label')).includes('new baseline due')===due,'rail and workspace agree on actionable status');
   if(waiting)await a.page.getByText(`${waiting} ${waiting===1?'topic is':'topics are'} waiting for course material`,{exact:true}).waitFor();else check(await a.page.getByText(/topics? (is|are) waiting for course material/).count()===0,'absent or zero waiting count has no line');
  }
  const parse=await a.page.evaluate(async()=>{const {diagnosticStatusSchema,diagnosticSchema}=await import('/src/features/diagnostic/schema/diagnostic.schema.ts');return [diagnosticStatusSchema.safeParse({courseId:'course',due:true}).success,diagnosticStatusSchema.safeParse({courseId:'course',due:false,waitingForMaterialCount:-1}).success,diagnosticSchema.safeParse({courseId:'course',status:'ready',questions:[],readyCount:0,pendingSkillIds:[],failedSkillIds:[],skippedSkillCount:0,waitingForMaterialCount:2}).success];});check(JSON.stringify(parse)==='[true,false,true]','legacy status and optional question fields validate; negative waiting rejects');
  for(const [response,label] of [
   [{questions:[],readyCount:0,waitingForMaterialCount:2},'Waiting for course material'],
   [{questions:[],readyCount:0,status:'failed',waitingForMaterialCount:2},'Your baseline is not ready yet'],
   [{questions:[],readyCount:0,status:'generating',pendingSkillIds:['pending'],waitingForMaterialCount:2},'Waiting for baseline questions. 0 questions are ready.'],
   [{waitingForMaterialCount:2},'Submit diagnostic'],
   [{questions:[],readyCount:0},"You're all caught up"],
  ]){a.state.diagnosticResponse=response;await a.page.goto('http://localhost:5173/course/diagnostic');await a.page.getByText(label,{exact:true}).waitFor();check(true,'question availability/material/preparation precedence: '+label);}
  check(a.state.mutations===0&&a.errors.length===0,'availability changes never write or cause runtime errors');await a.context.close();
  const record=await fixture(width,{role:'instructor'});await record.page.goto('http://localhost:5173/class/student/learner');await record.page.getByText('Based on recent activity',{exact:true}).waitFor();check(await record.page.getByText(/200 recent evidence events \(up to 200\)/).isVisible(),'record statistics label their bounded recent sample');await record.page.getByRole('tab',{name:'Activity',exact:true}).click();await record.page.getByText("Showing 25 of this learner's activity",{exact:true}).waitFor();await record.page.getByText('1–10 of 25 loaded events',{exact:true}).waitFor();check(record.errors.length===0&&record.state.mutations===0,'instructor record labels 25 returned rows without writes');await record.context.close();
 }
 console.log(`Frontend close-out passed: ${assertions} assertions; screenshots: ${out}`);
}finally{await browser.close();}
