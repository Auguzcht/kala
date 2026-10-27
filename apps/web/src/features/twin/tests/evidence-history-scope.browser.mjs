/** TWIN-REQ-010: session/role/course/target cache isolation and access revocation. */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
const requireBrowser=createRequire(resolve(process.env.KALA_BROWSER_TEST_DEPS??'apps/web','package.json'));
const {chromium}=requireBrowser('playwright');
const browser=await chromium.launch({headless:true,...(process.env.KALA_BROWSER_EXECUTABLE?{executablePath:process.env.KALA_BROWSER_EXECUTABLE}:{})});
let assertions=0;const check=(value,label)=>{assert.ok(value,label);assertions++;};
try {
  for(const width of [375,1440]) {
    const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});
    const page=await context.newPage();page.setDefaultTimeout(10000);
    const hookSource=await (await page.request.get('http://localhost:5173/src/features/twin/hooks/use-evidence-history.ts')).text();
    const queryUrl=hookSource.match(/from ["']([^"']*@tanstack_react-query[^"']*)["']/)?.[1];
    assert.ok(queryUrl,'resolve the exact Vite query module so provider and hook share context');
    const state={actor:'account-a',denial:null,calls:0,mutations:0};const errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await context.route('**/*',async route=>{
      const url=new URL(route.request().url());
      if(url.hostname!=='localhost'||url.port!=='5173')return route.abort();
      if(url.pathname==='/__history_scope')return route.fulfill({contentType:'text/html',body:`<!doctype html><html><head><link rel="stylesheet" href="/src/styles/globals.css"></head><body><div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;</script><script type="module">
import React from '/node_modules/.vite/deps/react.js';import ReactDOM from '/node_modules/.vite/deps/react-dom_client.js';
import {QueryClient,QueryClientProvider} from '${queryUrl}';
import {EvidenceHistoryLedger} from '/src/features/twin/components/EvidenceHistoryLedger.tsx';
const client=new QueryClient({defaultOptions:{queries:{retry:false}}});window.__historyClient=client;
function App(){const [course,setCourse]=React.useState('course-a');const [target,setTarget]=React.useState(undefined);return React.createElement('main',{style:{padding:24}},React.createElement('button',{onClick:()=>setCourse('course-b')},'Switch course'),React.createElement('button',{onClick:()=>setTarget('learner-a')},'Choose learner'),React.createElement('button',{onClick:()=>setTarget('learner-b')},'Switch learner'),React.createElement(EvidenceHistoryLedger,{courseId:course,targetId:target,fallbackEvents:[],fallbackLabel:'Legacy activity'}));}
ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(QueryClientProvider,{client},React.createElement(App)));
</script></body></html>`});
      if(url.pathname.endsWith('/src/lib/auth/AuthProvider.tsx'))return route.fulfill({contentType:'application/javascript',body:`import React from '/node_modules/.vite/deps/react.js';window.__scopeSession={userId:'account-a',institutionId:'synthetic-institution',role:'student'};const subscribe=fn=>{window.addEventListener('scope-session',fn);return()=>window.removeEventListener('scope-session',fn)};export function useSession(){return React.useSyncExternalStore(subscribe,()=>window.__scopeSession)};export const AuthProvider=({children})=>children;export const useSetSession=()=>()=>{};`});
      if(url.pathname.endsWith('/src/lib/api/client.ts'))return route.fulfill({contentType:'application/javascript',body:`export async function api(path,init){const r=await fetch('/__scope_api'+path,init);if(!r.ok)throw new Error('API '+r.status+': synthetic');return r.json();}`});
      if(!url.pathname.startsWith('/__scope_api'))return route.continue();
      if(route.request().method()!=='GET'){state.mutations++;return route.abort();}
      state.calls++;
      if(state.denial)return route.fulfill({status:state.denial,json:{detail:'synthetic'}});
      const path=url.pathname.slice('/__scope_api'.length);const course=path.split('/')[2];
      const label=`${state.actor} ${course} ${path.includes('/students/')?path.split('/')[4]:'own'}`;
      const offset=Number(url.searchParams.get('cursor')??0);
      const evidence=Array.from({length:25},(_,i)=>{const n=offset&&i===0?24:offset+i;return {id:label+'-'+n,type:'practice',correct:true,skillName:label+' event '+n,createdAt:'2026-10-25T00:00:00Z'}});
      return route.fulfill({json:{courseId:course,evidence,nextCursor:offset===0?'25':null}});
    });
    await page.goto('http://localhost:5173/__history_scope');
    const loaded=n=>page.getByText(`Showing ${n} of your activity`,{exact:true});
    await loaded(25).waitFor();for(let i=0;i<3;i++) await page.getByRole('link',{name:'Go to next page',exact:true}).click();await loaded(49).waitFor();check(await loaded(49).isVisible(),'overlapping pages deduplicate IDs without inflating the loaded count');
    await page.getByRole('link',{name:'Go to next page',exact:true}).click();
    const changeSession=async patch=>page.evaluate(patch=>{window.__scopeSession={...window.__scopeSession,...patch};window.dispatchEvent(new Event('scope-session'));},patch);
    state.actor='account-b';await changeSession({userId:'account-b'});await page.getByText('account-b course-a own event 0',{exact:true}).waitFor();await loaded(25).waitFor();
    const rows=page.getByRole('list',{name:'Evidence ledger',exact:true}).locator('li');
    check((await rows.allTextContents()).every(t=>t.includes('account-b')&&!t.includes('account-a')),'account change hides prior account and resets page');
    await page.getByRole('button',{name:'Switch course',exact:true}).click();await page.getByText('account-b course-b own event 0',{exact:true}).waitFor();
    check(await loaded(25).isVisible(),'course change starts its own chain');
    let calls=state.calls;await changeSession({role:'instructor'});await page.getByText('Activity unavailable',{exact:true}).waitFor();
    check(await rows.count()===0&&state.calls===calls,'instructor cannot enable own student feed or see cached rows');
    await page.getByRole('button',{name:'Choose learner',exact:true}).click();await page.getByText("Showing 25 of this learner's activity",{exact:true}).waitFor();
    await page.getByRole('button',{name:'Switch learner',exact:true}).click();await page.getByText('account-b course-b learner-b event 0',{exact:true}).waitFor();
    calls=state.calls;await changeSession({role:'student'});await page.getByText('Activity unavailable',{exact:true}).waitFor();
    check(await rows.count()===0&&state.calls===calls,'student cannot enable staff target or see cached staff rows');
    await changeSession({role:'admin'});await page.getByText("Showing 25 of this learner's activity",{exact:true}).waitFor();
    for(const denial of [403,404]){
      state.denial=denial;await page.evaluate(()=>window.__historyClient.invalidateQueries({queryKey:['evidence-history']}));
      await page.getByText('Activity unavailable',{exact:true}).waitFor();check(await rows.count()===0,'denial hides previously cached protected rows');
      state.denial=null;await page.evaluate(()=>window.__historyClient.resetQueries({queryKey:['evidence-history']}));
      await page.getByText("Showing 25 of this learner's activity",{exact:true}).waitFor();
    }
    check(errors.length===0&&state.mutations===0,'scope switching causes no crash or mutation');
    await context.close();
  }
  console.log(`TWIN-REQ-010 scope browser checks: ${assertions} assertions passed`);
} finally {await browser.close();}
