/** INSTR-REQ-011 / APPROVAL-07 Amendment 6: synthetic failure-state matrix. */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
const requireBrowser=createRequire(resolve(process.env.KALA_BROWSER_TEST_DEPS??'apps/web','package.json'));
const {chromium}=requireBrowser('playwright');
const browser=await chromium.launch({headless:true,...(process.env.KALA_BROWSER_EXECUTABLE?{executablePath:process.env.KALA_BROWSER_EXECUTABLE}:{})});
const out=resolve(process.env.KALA_UI_SCREENSHOTS??'/tmp/kala-instructor-read-states');await mkdir(out,{recursive:true});
let assertions=0;const check=(v,label)=>{assert.ok(v,label);assertions++;};
const makeEvents=n=>Array.from({length:n},(_,i)=>({id:`event-${i}`,type:['practice','diagnostic','flashcard','tutor'][i%4],correct:i%2===0,latencyMs:i%3?1250:null,skillName:`Event ${String(i+1).padStart(3,'0')}: Explain durable cloud storage and access controls`,createdAt:new Date(Date.UTC(2026,9,24,12,0)-i*60000).toISOString()}));
const skills=[{skillId:'storage',name:'Cloud storage',bloomLevel:'understand',moduleRef:'Cloud basics',estimate:0.55,attempts:5,band:'proficient'}];
async function fixture(width,{mode='instructor',reduced='reduce',failure='empty',surface='class',metrics=false}={}){
  const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:reduced});const page=await context.newPage();page.setDefaultTimeout(10000);
  let release;const gate=new Promise(resolve=>release=resolve);const state={calls:[],mode:failure,release,mutations:0,rosterFailed:false,metricMomentum:0,metricRoster:{courseId:'course',students:Array.from({length:25},(_,i)=>({userId:i===0?'learner':'peer-'+i,displayName:i===0?'Demo learner':'Synthetic peer '+i,pseudonym:'Learner '+i,initials:'SL',readiness:i===0?0.739:i===1?0.55:null,band:'no-evidence',attempts:i===0?381:0,evidenceCount:i===0?396:0,accuracy:i===0?0.75:null,lastActiveAt:null,daysInactive:null,weakestSkillName:null,skillsWithEvidence:i===0?11:0,skillsTotal:15,status:i===0?'on-track':'not-started'}))}};const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await context.route('**/*',async route=>{
    const url=new URL(route.request().url());if(url.hostname!=='localhost'||url.port!=='5173')return route.abort();
    if(url.pathname==='/__twin_presentation')return route.fulfill({contentType:'text/html',body:`<!doctype html><html><head><link rel="stylesheet" href="/src/styles/globals.css"></head><body><div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;</script><script type="module">
      import React from '/node_modules/.vite/deps/react.js';import ReactDOM from '/node_modules/.vite/deps/react-dom_client.js';
      import {MasteryRing} from '/src/components/kala/mastery-ring.tsx';import {EvidenceLedger} from '/src/components/kala/evidence-ledger.tsx';
      const events=${JSON.stringify(makeEvents(200))};
      function App(){const [count,setCount]=React.useState(23);return React.createElement('main',{style:{padding:24,maxWidth:1100,margin:'auto'}},React.createElement('div',{className:'flex flex-wrap items-center gap-6'},...[['student-ring',176,0.55,'Board readiness'],['instructor-ring',144,0.55,'Readiness'],['compact-ring',56,0.55,'Skill'],['null-ring',144,null,'No estimate'],['zero-ring',144,0,'Zero'],['full-ring',144,1,'Full']].map(([id,size,estimate,label])=>React.createElement('div',{id,key:id},React.createElement(MasteryRing,{size,estimate,label})))),React.createElement('div',{className:'my-6 flex flex-wrap gap-2'},...[0,1,10,11,23,200,3].map(n=>React.createElement('button',{key:n,onClick:()=>setCount(n),className:'border p-2'},'Use '+n+' events'))),React.createElement('section',{'aria-label':'Test ledger'},React.createElement(EvidenceLedger,{events:events.slice(0,count)})))}
      ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(App));</script></body></html>`});
    if(url.pathname.endsWith('/src/app/providers.tsx')){const response=await route.fetch();const body=await response.text();return route.fulfill({response,body:body+'\nwindow.__readStateClient=queryClient;'});}
    if(url.pathname.endsWith('/src/lib/auth/AuthProvider.tsx'))return route.fulfill({contentType:'application/javascript',body:`export const AuthProvider=({children})=>children;export const useSession=()=>({userId:'demo',institutionId:'inst',role:'${mode==='instructor'?'instructor':'student'}',courseId:'course',displayName:'Demo learner'});export const useSetSession=()=>()=>{};`});
    if(url.pathname.endsWith('/src/lib/api/client.ts'))return route.fulfill({contentType:'application/javascript',body:`export async function api(path,init){const r=await fetch('/__twin_api'+path,init);if(!r.ok)throw new Error('API '+r.status+': synthetic failure');return r.json();}`});
    if(!url.pathname.startsWith('/__twin_api'))return route.continue();
    const path=url.pathname.slice('/__twin_api'.length);const reply=json=>route.fulfill({json});
    if(route.request().method()!=='GET'){state.mutations++;return route.abort();}
    const guarded=surface==='class'?['/roster','/stats','/at-risk','/heatmap'].some(end=>path.endsWith(end)):path.endsWith('/record');
    if(guarded){
      state.calls.push(path);
      if(state.mode==='slow')await gate;
      if(state.mode==='network')return route.abort('failed');
      if(typeof state.mode==='number')return route.fulfill({status:state.mode,json:{detail:'synthetic failure'}});
    }
    if(path.endsWith('/evidence'))return reply({courseId:'course',evidence:[],nextCursor:null});
    if(metrics&&path.endsWith('/roster'))return state.rosterFailed?route.fulfill({status:403,json:{detail:'synthetic denial'}}):reply(state.metricRoster);
    if(path.endsWith('/roster'))return reply({courseId:'course',students:surface==='sheet'?[{userId:'learner',displayName:'Synthetic sheet learner',pseudonym:'Synthetic learner',initials:'SL',readiness:null,band:'no-evidence',attempts:0,evidenceCount:0,accuracy:null,lastActiveAt:null,daysInactive:null,weakestSkillName:null,skillsWithEvidence:0,skillsTotal:0,status:'not-started'}]:[]});
    if(path.endsWith('/heatmap'))return reply({courseId:'course',cohortReadiness:null,skills:[],students:[],cells:[]});
    if(path.endsWith('/stats'))return reply({courseId:'course',learners:0,activeLearners:0,startedLearners:0,notStartedLearners:0,cohortReadiness:null,medianReadiness:null,accuracy:null,evidenceCount:0,medianLatencyMs:null,hintsUsed:0,skillsTracked:0,skillsCovered:0,bandDistribution:[],bloomCoverage:[],skillBreakdown:[],readinessTrend:[],activitySeries:[],decisions:{pending:0,approved:0,rejected:0,completed:0}});
    if(path.endsWith('/proposed'))return reply({courseId:'course',proposed:[]});
    if(path.endsWith('/auto-matched'))return reply({courseId:'course',autoMatched:[]});
    if(path==='/courses/course')return reply({id:'course',title:'AWS101'});
    if(path.endsWith('/twin'))return reply({courseId:'course',readiness:0.55,skills,evidence:makeEvents(20)});
    if(path.endsWith('/next-up'))return reply({courseId:'course',next:null});
    if(path.endsWith('/summary'))return reply({xp:0,attempts:0,correct:0,streakDays:0,badges:[]});
    if(path.endsWith('/diagnostic/status'))return reply({courseId:'course',due:false,dueSkillCount:0});
    if(path.endsWith('/diagnostic'))return reply({courseId:'course',status:'ready',readyCount:1,questions:[{id:'q',skillId:'storage',bloomLevel:'understand',prompt:'Which storage fits?',choices:[{id:'a',label:'Object storage'},{id:'b',label:'Temporary disk'}]}],pendingSkillIds:[],failedSkillIds:[],skippedSkillCount:0});
    if(path.endsWith('/at-risk'))return reply({courseId:'course',flags:[]});
    if(path.endsWith('/recommendations'))return reply({courseId:'course',userId:'learner',recommendations:[]});
    if(metrics&&path.endsWith('/record'))return reply({courseId:'course',userId:'learner',displayName:'Demo learner',pseudonym:'Learner A',initials:'DL',readiness:0.739,band:'proficient',cohortReadiness:0.644,percentile:200,accuracy:0.69,momentum:state.metricMomentum,attempts:381,evidenceCount:200,hintsUsed:0,lastActiveAt:null,daysInactive:0,status:'on-track',skills:[],activityByType:[],activitySeries:[],readinessTrend:[],evidence:[]});
    if(path.endsWith('/record'))return reply({courseId:'course',userId:'learner',displayName:'Demo learner',pseudonym:'Learner A',initials:'DL',readiness:null,band:'no-evidence',cohortReadiness:null,percentile:null,accuracy:null,momentum:null,attempts:0,evidenceCount:0,hintsUsed:0,lastActiveAt:null,daysInactive:null,status:'not-started',skills:[],activityByType:[],activitySeries:[],readinessTrend:[],evidence:[]});
    return reply({});
  });
  await page.goto(`http://localhost:5173/${mode==='components'?'__twin_presentation':surface==='class'||surface==='sheet'?'class':'class/student/learner'}`);
  return {page,context,errors,state};
}

try {
  for(const width of [375,1440]) for(const surface of ['class','learner']) for(const failure of [403,404,500,'network','slow','empty']) {
    const f=await fixture(width,{surface,failure}),{page,state}=f;
    const denied=failure===403||failure===404;
    if(failure==='slow'){
      await page.locator('[aria-busy=true]').first().waitFor();
      check(await page.getByText('No students enrolled yet',{exact:true}).count()===0,'slow response does not pretend empty');
      state.mode='empty';state.release();
    }
    if(denied||failure===500||failure==='network'){
      const title=denied?(surface==='class'?"This class isn't available to you":'Learner unavailable')
        :(surface==='class'?"Couldn't load the class, try again":"Couldn't load the learner, try again");
      await page.getByRole('heading',{name:title,exact:true}).first().waitFor();
      if(surface==='class'){
        for(const [label,region] of [['roster','#roster-panel'],['at-risk','#at-risk-list'],['charts','#cohort-analytics']]){
          await page.locator(region).getByRole('heading',{name:title,exact:true}).waitFor();
          check(await page.locator(region).getByRole('alert').isVisible(),`${label} independently exposes its expected settled error`);
        }
        // The statistics strip precedes those three regions in the actual dashboard.
        const stats=page.getByRole('alert').first();
        check(await stats.getByRole('heading',{name:title,exact:true}).isVisible(),'cohort statistics independently exposes its expected error');
        check(await page.getByRole('alert').count()===4,'all four class panels expose errors, not just the first completed request');
      }

      check(await page.getByText('No students enrolled yet',{exact:true}).count()===0,'failure does not claim an empty roster');
      check(await page.getByText('No one needs support right now. Check back after the next activity.',{exact:true}).count()===0,'failure does not claim no support needed');
      check(await page.locator('#tour-cohort-kpis').count()===0,'failure does not show zero statistics');
      await page.waitForFunction(()=>document.querySelectorAll('[aria-busy=true]').length===0);
      check(await page.locator('[aria-busy=true]').count()===0,'settled failure has no stuck loading indicator');
      if(denied&&surface==='learner'){
        check(await page.getByRole('link',{name:'Back to class',exact:true}).getAttribute('href')==='/class','unavailable learner has class navigation');
      }
      if(!denied){
        state.mode='empty';
        for(const region of surface==='class'?['#roster-panel','#at-risk-list','#cohort-analytics']:['main']){
          const retry=page.locator(region).getByRole('button',{name:'Retry',exact:true});
          if(await retry.count())await retry.first().click();
        }
        // The KPI retry shares the charts query and recovers with it.
      }
    }
    if(!denied){
      if(surface==='class'){
        await page.getByText('No students enrolled yet',{exact:true}).waitFor();
        await page.getByText('No one needs support right now. Check back after the next activity.',{exact:true}).waitFor();
        await page.locator('#tour-cohort-kpis').waitFor();
        check(await page.getByRole('alert').count()===0,'successful empty class recovers without error states');
      }else{
        await page.locator('#tour-standing').getByRole('heading',{name:'Demo learner',exact:true}).waitFor();
        check(await page.getByRole('alert').count()===0,'learner retry recovers');
        check(await page.locator('#tour-standing').getByText('Graded outcomes in last 200 events · 0 hints used',{exact:true}).isVisible(),'INSTR-REQ-012 drawer accuracy names the bounded graded window');
        await page.getByRole('tab',{name:'Activity',exact:true}).click();
        await page.getByText("Showing 0 of this learner's activity",{exact:true}).waitFor();
        await page.getByText(/No evidence yet\. Your recent answers/).waitFor();
        check(await page.getByRole('list',{name:'Evidence ledger',exact:true}).count()===0,'successful learner with zero attempts/evidence has a genuine empty ledger');
      }
    }
    if(surface==='class'&&denied){
      await page.getByRole('tab',{name:"Skills × Bloom's",exact:true}).click();
      await page.locator('#heatmap-panel').getByRole('heading',{name:"This class isn't available to you",exact:true}).waitFor();
    }
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'failure/empty UI fits viewport');
    check(f.errors.length===0&&state.mutations===0,'no browser crash or mutations');
    await f.context.close();
  }
  for(const width of [375,1440]) for(const surface of ['class','learner']) {
    const f=await fixture(width,{surface,failure:'empty'}),{page,state}=f;
    if(surface==='class')await page.getByText('No students enrolled yet',{exact:true}).waitFor();
    else await page.locator('#tour-standing').getByRole('heading',{name:'Demo learner',exact:true}).waitFor();
    state.mode=500;await page.evaluate(()=>window.__readStateClient.invalidateQueries());
    await page.getByRole('heading',{name:surface==='class'?"Couldn't load the class, try again":"Couldn't load the learner, try again",exact:true}).first().waitFor();
    check(await page.getByText('No students enrolled yet',{exact:true}).count()===0,'cached success does not mask a failed refetch as empty');
    check(await page.locator('#tour-cohort-kpis').count()===0,'cached statistics hidden after refetch failure');
    check(await page.locator('[aria-busy=true]').count()===0,'failed refetch is not permanent loading');
    if(surface==='learner')check(await page.locator('#tour-standing').count()===0,'cached learner standing hidden after failed refetch');
    check(f.errors.length===0&&state.mutations===0,'refetch failure causes no crash or write');
    await f.context.close();
  }
  for(const width of [375,1440]) for(const failure of [403,404]) {
    const f=await fixture(width,{surface:'sheet',failure}),{page,state}=f;
    const row=page.locator('#tour-roster-first-row');await row.waitFor();await row.focus();await row.press('Enter');
    const sheet=page.getByRole('dialog');await sheet.waitFor();
    await sheet.getByRole('heading',{name:'Learner unavailable',exact:true}).waitFor();
    check(await sheet.getByText('Check your connection and try again.',{exact:true}).count()===0,'roster-sheet denial does not claim a connection error');
    check(await sheet.getByRole('link',{name:'Back to class',exact:true}).getAttribute('href')==='/class','roster-sheet unavailable state retains class navigation');
    check(await sheet.locator('[aria-busy=true]').count()===0,'roster-sheet denial settles its loading state');
    check(state.mutations===0&&f.errors.length===0,'denied roster sheet never mutates or crashes');
    await page.keyboard.press('Escape');await sheet.waitFor({state:'hidden'});
    check(await row.isVisible(),'keyboard close returns to the actual roster');
    await f.context.close();
  }
  for(const width of [375,1440]) for(const surface of ['sheet','learner']) {
    const f=await fixture(width,{surface,metrics:true}),{page,state}=f;
    if(surface==='sheet'){await page.getByRole('textbox',{name:'Search the roster',exact:true}).fill('Demo learner');await page.getByRole('row').filter({hasText:'Demo learner'}).click();}
    const standing=page.locator('#tour-standing');await standing.waitFor();
    await standing.getByText('1st of 2',{exact:true}).waitFor();
    check(await standing.getByText('Learners with measured readiness',{exact:true}).isVisible(),'INSTR-REQ-012 rank denominator labels only measured course learners');
    check(await standing.getByText('200th',{exact:true}).count()===0,'INSTR-REQ-012 never renders the invalid percentile as ordinal');
    check(await standing.getByText('69%',{exact:true}).isVisible(),'INSTR-REQ-012 keeps the learner record accuracy');
    check(await standing.getByText('Graded outcomes in last 200 events · 0 hints used',{exact:true}).isVisible(),'INSTR-REQ-012 accuracy window visible on '+surface);
    const momentumCard=standing.getByText('Momentum',{exact:true}).locator('..');
    check((await momentumCard.getByText('0 pts',{exact:true}).getAttribute('class')).includes('text-foreground'),'INSTR-REQ-012 true zero momentum is neutral');
    check(await momentumCard.getByText('Last 10 vs previous 10 graded',{exact:true}).isVisible(),'INSTR-REQ-012 momentum identifies graded windows');
    for(const [momentum,text,tone] of [[0.02,'+2 pts','text-brand-green'],[-0.02,'-2 pts','text-destructive'],[0.004,'0 pts','text-foreground'],[-0.004,'0 pts','text-foreground'],[null,'—','text-foreground']]) {
      state.metricMomentum=momentum;
      await page.evaluate(()=>window.__readStateClient.invalidateQueries({queryKey:['learner-record','course','learner']}));
      const value=momentumCard.locator('p').nth(1);await value.filter({hasText:text}).waitFor();
      check(await value.innerText()===text,'INSTR-REQ-012 momentum retains rounded points '+momentum);
      check((await value.getAttribute('class')).includes(tone),'INSTR-REQ-012 momentum tone follows displayed points '+momentum);
    }
    state.metricRoster.students[1].readiness=0.739;
    await page.evaluate(()=>window.__readStateClient.invalidateQueries({queryKey:['roster','course']}));
    await standing.getByText('Tied 1st of 2',{exact:true}).waitFor();
    check(await standing.getByText('Tied 1st of 2',{exact:true}).isVisible(),'INSTR-REQ-012 equal readiness gives an explicit shared rank');
    state.rosterFailed=true;
    await page.evaluate(()=>window.__readStateClient.invalidateQueries({queryKey:['roster','course']}));
    await standing.getByText('Course rank unavailable',{exact:true}).waitFor();
    check(await standing.getByText('Tied 1st of 2',{exact:true}).count()===0,'INSTR-REQ-012 failed roster never retains a stale rank');
    check(await standing.getByText('69%',{exact:true}).isVisible(),'INSTR-REQ-012 unavailable course rank preserves own record');
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'INSTR-REQ-012 standing fits viewport');
    check(state.mutations===0&&f.errors.length===0,'INSTR-REQ-012 standing reads never write or crash');
    await f.context.close();
  }
  console.log(`INSTR-REQ-011 browser checks: ${assertions} assertions passed`);
} finally { await browser.close(); }
