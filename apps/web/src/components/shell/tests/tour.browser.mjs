/** WI-33 / Amendment7a: hidden student entry and retained instructor walkthrough.
 * Real app/router/Driver.js, isolated synthetic APIs only. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {mkdir} from 'node:fs/promises';
import {resolve} from 'node:path';
const requireBrowser=createRequire(resolve(process.env.KALA_BROWSER_TEST_DEPS??'apps/web','package.json'));
const {chromium}=requireBrowser('playwright');
const browser=await chromium.launch({headless:true,...(process.env.KALA_BROWSER_EXECUTABLE?{executablePath:process.env.KALA_BROWSER_EXECUTABLE}:{})});
const out=resolve(process.env.KALA_UI_SCREENSHOTS??'/tmp/kala-disable-student-tour');await mkdir(out,{recursive:true});
let assertions=0;const check=(condition,label)=>{assert.ok(condition,label);assertions++;};
const skill={skillId:'storage',name:'Cloud storage',moduleRef:'Cloud basics',bloomLevel:'understand',estimate:0.5,attempts:2,band:'proficient'};
const ident={userId:'learner',displayName:'Demo learner',pseudonym:'Learner A',initials:'DL'};
const evidence=Array.from({length:20},(_,i)=>({id:'event-'+i,type:'practice',correct:true,latencyMs:1000,skillName:'Cloud storage',createdAt:'2026-10-25T00:00:00Z'}));
async function fixture(width,{role='student',completed=false,empty=false,noMaterial=false,reduced='reduce',dismissal=null,step15Layout='normal'}={}){
 const context=await browser.newContext({viewport:{width,height:950},reducedMotion:reduced});const page=await context.newPage();page.setDefaultTimeout(15000);
 if(dismissal!==null)await context.addInitScript(({role,dismissal})=>localStorage.setItem(`kala.${role}.tour.demo`,dismissal),{role,dismissal});
 await context.addInitScript(()=>{
  window.__tourWriteClicks=[];
  document.addEventListener('click',event=>{
   if(event.target instanceof Element&&event.target.closest('#tour-skill-approve,#live-skill-approval,#tour-run-analysis,#tour-decision-buttons button,#tour-record-intervene button'))window.__tourWriteClicks.push(event.target.textContent);
  },true);
 });
 const errors=[],state={mutations:[],gets:[],skipped:[],visited:[],choosers:0};page.on('pageerror',e=>errors.push(e.message));page.on('filechooser',()=>state.choosers++);
 page.on('request',request=>{if(!['GET','HEAD','OPTIONS'].includes(request.method()))state.mutations.push({path:new URL(request.url()).pathname,method:request.method()});});
 await context.route('**/*',async route=>{
  const url=new URL(route.request().url());if(url.hostname!=='localhost'||url.port!=='5173')return route.abort();
  if(step15Layout==='alternate'&&url.pathname.endsWith('/src/features/instructor/components/SkillReviewPanel.tsx')){
   const response=await route.fetch();return route.fulfill({response,body:(await response.text()).replaceAll('tour-skill-approve','live-skill-approval')});
  }
  if(url.pathname.endsWith('/src/lib/auth/AuthProvider.tsx'))return route.fulfill({contentType:'application/javascript',body:`export const AuthProvider=({children})=>children;export const useSession=()=>(${JSON.stringify({userId:'demo',institutionId:'inst',role,courseId:'course',displayName:'Demo learner'})});export const useSetSession=()=>()=>{};`});
  if(url.pathname.endsWith('/src/lib/api/client.ts'))return route.fulfill({contentType:'application/javascript',body:`export async function api(path,init){const r=await fetch('/__tour_api'+path,init);if(!r.ok)throw new Error('Synthetic API failure');return r.json();}`});
  if(!url.pathname.startsWith('/__tour_api'))return route.continue();
  const path=url.pathname.slice('/__tour_api'.length),reply=json=>route.fulfill({json});
  if(!['GET','HEAD'].includes(route.request().method()))return route.fulfill({status:405,json:{}});
  state.gets.push(path);
  if(path==='/courses/course')return reply({id:'course',title:'AWS101'});
  if(path.endsWith('/twin'))return reply({courseId:'course',pseudonym:'Learner A',readiness:0.5,skills:[skill],evidence});
  if(path.endsWith('/next-up'))return reply({courseId:'course',next:null});
  if(path.endsWith('/summary'))return reply({xp:0,attempts:0,correct:0,streakDays:0,badges:[]});
  if(path.endsWith('/diagnostic/status'))return reply({courseId:'course',due:!completed,dueSkillCount:completed?0:1});
  if(path.endsWith('/diagnostic'))return reply({courseId:'course',status:'ready',readyCount:completed?0:1,questions:completed?[]:[{id:'q',skillId:'storage',bloomLevel:'understand',prompt:'Which storage fits?',choices:[{id:'a',label:'Object storage'},{id:'b',label:'Temporary disk'}]}],pendingSkillIds:[],failedSkillIds:[],skippedSkillCount:0,waitingForMaterialCount:noMaterial?1:0});
  if(path.endsWith('/bank/status'))return reply({courseId:'course',building:false,bankServing:true,skills:[{skillId:'storage',status:noMaterial?'no_material':'ready',mcqReady:noMaterial?0:10,mcqTarget:10,depth:1,usable:!noMaterial}]});
  if(path.startsWith('/lessons/'))return reply({lessonId:'lesson',skillId:'storage',moduleRef:'Cloud basics',title:'Cloud storage',status:noMaterial?'failed':'ready',steps:noMaterial?[]:[{id:'step',position:1,summary:'Choose durable storage.',detailPoints:['Objects hold data and metadata.'],misconception:null,keyTakeaway:null,bloomLevel:'understand',check:null}]});
  if(path.includes('/practice/')&&path.includes('/sets'))return reply({courseId:'course',sets:[]});
  if(path.includes('/membership'))return reply({skillId:'storage',counts:{new:1,learning:0,slipping:0,known:0,dueToday:0},cards:noMaterial?[]:[{itemId:'card',prompt:'What is object storage?',back:{label:'Durable objects',explanation:'An object contains data.'},state:'new',due:false,dueAt:null}]});
  if(path.startsWith('/flashcards/'))return reply({courseId:'course',cards:[],stats:{tracked:0,due:0,learning:0,mastered:0},mode:'review',sessionId:'session',hasMore:false});
  if(path==='/tutor/conversations')return reply({conversations:[{id:'chat',courseId:'course',skillId:null,title:'Cloud storage',createdAt:'2026-10-25T00:00:00Z',updatedAt:'2026-10-25T00:00:00Z',pinnedAt:null}]});
  if(path.endsWith('/plan'))return reply({plan:[]});
  if(path.endsWith('/skills/proposed'))return reply({courseId:'course',proposed:empty||step15Layout==='absent'?[]:[{id:'proposal',name:'Explain cloud storage',bloom_level:'understand',blueprint_weight:1,proposed_source:'Course material'}]});
  if(path.endsWith('/skills/auto-matched'))return reply({courseId:'course',autoMatched:[]});
  if(path.endsWith('/roster'))return reply({courseId:'course',students:empty?[]:[{...ident,readiness:0.5,band:'proficient',attempts:20,evidenceCount:20,accuracy:0.5,lastActiveAt:'2026-10-25T00:00:00Z',daysInactive:0,weakestSkillName:'Cloud storage',skillsWithEvidence:1,skillsTotal:1,status:'needs-support'}]});
  if(path.endsWith('/stats'))return reply({courseId:'course',learners:empty?0:1,activeLearners:0,startedLearners:empty?0:1,notStartedLearners:0,cohortReadiness:0.5,medianReadiness:0.5,accuracy:0.5,evidenceCount:20,medianLatencyMs:1000,hintsUsed:0,skillsTracked:1,skillsCovered:1,bandDistribution:[{band:'proficient',count:1}],bloomCoverage:[],skillBreakdown:[],readinessTrend:[],activitySeries:[],decisions:{pending:0,approved:0,rejected:0,completed:0}});
  if(path.endsWith('/heatmap'))return reply({courseId:'course',cohortReadiness:0.5,skills:[{skillId:'storage',name:'Cloud storage',bloomLevel:'understand',cohortBand:'proficient',cohortEstimate:0.5}],students:empty?[]:[ident],cells:empty?[]:[{userId:'learner',skillId:'storage',estimate:0.5,attempts:20,band:'proficient'}]});
  if(path.endsWith('/at-risk'))return reply({courseId:'course',flags:empty?[]:[{...ident,reason:'Practice can reinforce storage concepts.',daysInactive:0,evidenceCount:20,weakestSkillNames:['Cloud storage']}]});
  if(path.endsWith('/record'))return reply({courseId:'course',...ident,readiness:0.5,band:'proficient',cohortReadiness:0.5,percentile:50,accuracy:0.5,momentum:null,attempts:20,evidenceCount:20,hintsUsed:0,lastActiveAt:'2026-10-25T00:00:00Z',daysInactive:0,status:'developing',skills:[skill],activityByType:[],activitySeries:[],readinessTrend:[],evidence});
  if(path.endsWith('/evidence'))return reply({courseId:'course',evidence,nextCursor:null});
  if(path.endsWith('/recommendations'))return reply({courseId:'course',userId:'learner',recommendations:empty?[]:[{id:'recommendation',userId:'learner',courseId:'course',skillId:'storage',skillName:'Cloud storage',title:'Review cloud storage',kind:'practice',priority:'medium',rationale:'Review reinforces this concept.',evidence:[{label:'Practice',detail:'Two recent checks show room to improve.'}],status:'suggested',confidence:0.5,expectedGain:null,source:'heuristic',decidedBy:null,decidedAt:null,decisionNote:null,instructorNote:null,createdAt:'2026-10-25T00:00:00Z'}]});
  return reply({});
 });
 await page.goto('http://localhost:5173/'+(role==='student'?'course':'class'));
 await page.evaluate(async role=>{window.__tourStore=(await import('/src/stores/ui-store.ts')).useUI;window.__tourSteps=role==='student'?(await import('/src/components/shell/student-tour.ts')).createStudentTour({skillId:'storage'}):(await import('/src/components/shell/instructor-tour.ts')).INSTRUCTOR_TOUR_STEPS;},role);
 return {context,page,state,errors};
}
async function start(f,{direct=false,blocked=false}={}){
 if(direct){await f.page.evaluate(()=>{window.__tourStore.getState().setTourContext({skillId:'storage'});window.__tourStore.getState().setTourStep(0);});return;}
 await f.page.getByRole('button',{name:'Take the tour',exact:true}).first().click();await f.page.getByRole('button',{name:'Start tour',exact:true}).click();
 if(!blocked)await f.page.waitForFunction(()=>window.__tourStore.getState().tourStep!==null);
}
async function walk(f,{back=false,width,role}={}){
 const {page,state}=f;let didBack=false;const totalSteps=await page.evaluate(()=>window.__tourSteps.length);
 for(let turns=0;turns<70;turns++){
  const ready=await page.waitForFunction(()=>{const index=window.__tourStore.getState().tourStep;if(index===null)return {done:true};const el=document.querySelector(`.driver-popover[data-tour-step="${index}"]`);if(el&&el.getBoundingClientRect().height>0&&getComputedStyle(el).visibility!=='hidden')return {index};return false;});
  const stateAtReady=await ready.jsonValue();if(stateAtReady.done)break;const index=stateAtReady.index;
  const popover=page.locator(`.driver-popover[data-tour-step="${index}"]`);await popover.waitFor();
  const title=await popover.locator('.driver-popover-title').innerText();const fallback=await popover.getAttribute('data-tour-fallback')==='true';state.visited.push({index,title,fallback,path:new URL(page.url()).pathname});
  if(fallback){
   check(await popover.evaluate(el=>{const b=el.getBoundingClientRect();return Math.abs(b.left+b.width/2-innerWidth/2)<=2&&Math.abs(b.top+b.height/2-innerHeight/2)<=2;}),'TOUR-REQ-009 step '+index+' has a centered fallback');
  }else check(await page.evaluate(index=>[...document.querySelectorAll('.driver-active-element')].some(el=>el.matches(window.__tourSteps[index].selector)),index),'step '+index+' highlights its actual configured target');
  check(await popover.getByText(`${index+1} of ${totalSteps}`,{exact:true}).count()===1,'TOUR-REQ-009 progress stays fixed at step '+index);
  check(await popover.locator('.driver-popover-next-btn').innerText()===(index===totalSteps-1?'Done':'Next'),'TOUR-REQ-009 every instructor step advances with Next or final Done');
  check(await popover.evaluate(el=>{const b=el.getBoundingClientRect();return b.left>=0&&b.right<=innerWidth+1&&b.top>=0&&b.bottom<=innerHeight+1;}),'popover fits viewport '+width);
  check(state.mutations.length===0,'tour has sent zero mutating requests at step '+index);
  check(await page.evaluate(()=>window.__tourWriteClicks.length===0),'TOUR-REQ-009 no write/model control click at step '+index);
  check(!page.url().includes('$uid'),'never navigates to a literal learner placeholder');
  const previous=popover.getByRole('button',{name:'Back',exact:true});
  if(back&&!didBack&&await previous.isEnabled()){
   didBack=true;if(width===375){await previous.focus();await previous.press('Enter');}else await previous.click();await page.waitForFunction(previousIndex=>window.__tourStore.getState().tourStep<previousIndex,index);continue;
  }
  if(state.visited.length===1||index===14||title==='Keep track of your chats')await page.screenshot({path:resolve(out,`${role}-${width}-${index}-${fallback?'fallback':'target'}.png`),animations:'disabled'});
  await popover.locator('.driver-popover-next-btn').click();
  await page.waitForFunction(previousIndex=>window.__tourStore.getState().tourStep!==previousIndex,index).catch(async e=>{throw new Error(`Stuck after ${role} step ${index} ${title}; path=${new URL(page.url()).pathname}; errors=${f.errors.join('; ')}; ${e.message}`);});
 }
 check(await page.evaluate(()=>window.__tourStore.getState().tourStep)===null,'tour reaches completion through missing steps');
 check(await page.evaluate(()=>document.querySelector('.driver-popover')===null),'completion removes obsolete overlay');
 check(f.errors.length===0,'tour has no browser runtime errors: '+f.errors.join('; '));
 check(await page.evaluate(role=>localStorage.getItem(`kala.${role}.tour.demo`)==='dismissed',role),'conditional skips finish rather than silently aborting');
 check(state.choosers===0,'attachment highlight never opens a file chooser');
 return didBack;
}
const instructorReads = new Set([
 '/courses/course', '/dashboard/course/skills/proposed',
 '/dashboard/course/skills/auto-matched', '/dashboard/course/roster',
 '/dashboard/course/stats', '/dashboard/course/heatmap', '/dashboard/course/at-risk',
 '/dashboard/course/students/learner/record',
 '/dashboard/course/students/learner/recommendations',
 '/dashboard/course/students/learner/evidence',
]);
async function studentEntryAbsent(f, label) {
 const {page} = f;
 check(await page.getByRole('button', {name:'Take the tour', exact:true}).count() === 0, label+' has no manual or banner tour button');
 check(await page.getByText('First time here?', {exact:true}).count() === 0, label+' has no auto-offer');
 check(await page.getByRole('dialog', {name:'Take the tour?', exact:true}).count() === 0, label+' has no confirmation');
 check(await page.getByRole('button', {name:'Start tour', exact:true}).count() === 0, label+' has no start control');
 check(await page.locator('.driver-popover').count() === 0, label+' has no student runner overlay');
}
try {
 for (const width of [1440,375]) {
  for (const dismissal of [null,'dismissed','started']) {
   const f = await fixture(width, {dismissal});
   const label = `student ${width} ${dismissal??'fresh'}`;
   await f.page.getByRole('heading', {name:'Welcome back, Demo', exact:true}).waitFor();
   await studentEntryAbsent(f, label);
   check(!f.state.gets.some(path=>path.endsWith('/bank/status')||path.includes('/practice/')), label+' entry does not plan a tour');
   check(await f.page.evaluate(()=>localStorage.getItem('kala.student.tour.demo')) === dismissal, label+' preserves prior local dismissal');
   // A stale ephemeral step must not mount a disabled student runner either.
   await f.page.evaluate(()=>{
    window.__tourStore.getState().setTourContext({skillId:'storage'});
    window.__tourStore.getState().setTourStep(0);
   });
   await f.page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
   await studentEntryAbsent(f, label+' stale step');
   check(new URL(f.page.url()).pathname==='/course', label+' stale step cannot navigate');
   await f.page.evaluate(()=>window.__tourStore.getState().setTourStep(null));
   if(dismissal===null)await f.page.screenshot({path:resolve(out,`student-hidden-${width}.png`),animations:'disabled'});
   for (const [id,path] of [['skills','/course/skills'],['tutor','/course/tutor'],['twin','/course/twin'],['diagnostic','/course/diagnostic'],['workspace','/course']]) {
    await f.page.locator('#nav-'+id).click();
    await f.page.waitForURL(url=>url.pathname===path);
    check(new URL(f.page.url()).pathname===path, label+' ordinary '+id+' navigation works');
    await studentEntryAbsent(f, label+' '+id);
   }
   check(f.state.mutations.length===0 && f.errors.length===0, label+' no mutation or runtime error');
   await f.context.close();
  }
  for (const empty of [false,true]) {
   const f = await fixture(width, {role:'instructor',empty});
   await f.page.getByRole('button',{name:'Take the tour',exact:true}).first().waitFor();
   check(await f.page.getByRole('button',{name:'Take the tour',exact:true}).count()===2,'instructor retains manual entry and fresh offer '+width);
   await start(f);
   check(await walk(f,{width,role:'instructor',back:true}),'retained instructor Back works '+width);
   const visited = new Set(f.state.visited.map(step=>step.index));
   check(visited.size===27,'TOUR-REQ-009 instructor visits all 27 steps including fallbacks '+width);
   if(empty)check(!f.state.visited.some(step=>step.path.startsWith('/class/student/')),'empty instructor roster invents no learner');
   else {
    check(visited.size===27,'instructor visits all 27 retained steps '+width);
    check(f.state.visited.some(step=>step.path==='/class/student/learner'),'instructor reaches actual learner route '+width);
   }
   check(f.state.gets.every(path=>instructorReads.has(path)),'instructor GETs match source-audited read chains '+width);
   check(f.state.mutations.length===0,'instructor sends no mutating request '+width);
   await f.page.getByText('First time here?',{exact:true}).waitFor({state:'detached'});
   check(await f.page.getByRole('button',{name:'Take the tour',exact:true}).count()===1,'instructor completion retains manual restart '+width);
   console.log(`instructor ${width} empty=${empty}: ${visited.size} distinct steps; mutations=${f.state.mutations.length}`);
   await f.context.close();
  }
  for(const step15Layout of ['absent','alternate']){
   const f=await fixture(width,{role:'instructor',step15Layout});await start(f);
   await walk(f,{width,role:'instructor',back:true});
   check(new Set(f.state.visited.map(step=>step.index)).size===27,'TOUR-REQ-009 live-like '+step15Layout+' visits all 27 steps '+width);
   check(f.state.visited.some(step=>step.index===14&&step.fallback),'TOUR-REQ-009 step 15 has fallback for '+step15Layout+' target '+width);
   check(f.state.gets.every(path=>instructorReads.has(path)),'TOUR-REQ-009 live-like '+step15Layout+' stays on audited read chains '+width);
   check(f.state.mutations.length===0&&await f.page.evaluate(()=>window.__tourWriteClicks.length===0),'TOUR-REQ-009 live-like '+step15Layout+' has zero mutations or write-control clicks '+width);
   await f.context.close();
  }
  for (const exit of ['Escape','Skip']) {
   const f = await fixture(width,{role:'instructor',reduced:'no-preference',dismissal:'dismissed'});
   await f.page.getByRole('button',{name:'Take the tour',exact:true}).waitFor();
   check(await f.page.getByRole('button',{name:'Take the tour',exact:true}).count()===1,'dismissed instructor keeps manual entry '+width);
   await start(f);
   await f.page.locator('.driver-popover').waitFor();
   if(exit==='Escape')await f.page.keyboard.press('Escape');
   else await f.page.getByRole('button',{name:'Skip tour',exact:true}).click();
   await f.page.waitForFunction(()=>window.__tourStore.getState().tourStep===null);
   check(f.state.mutations.length===0 && f.errors.length===0,'instructor '+exit+' exits without mutation '+width);
   await f.context.close();
  }
 }
 console.log(`WI-33 passed: ${assertions} assertions; historical TOUR-REFRESH: 616 assertions; screenshots: ${out}`);
} finally { await browser.close(); }
