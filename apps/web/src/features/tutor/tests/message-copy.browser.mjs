/** TUTOR-REQ-017: synthetic clipboard-only UI, no service or permission prompts. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {resolve} from 'node:path';
const requireBrowser=createRequire(resolve(process.env.KALA_BROWSER_TEST_DEPS??'apps/web','package.json'));
const {chromium}=requireBrowser('playwright');
const browser=await chromium.launch({headless:true,...(process.env.KALA_BROWSER_EXECUTABLE?{executablePath:process.env.KALA_BROWSER_EXECUTABLE}:{})});
let assertions=0;const check=(value,label)=>{assert.ok(value,label);assertions++;};
const cases=[['saved-user','user','Saved question\nsecond line'],['saved-answer','assistant','**Saved answer**\n\n`code()`'],['local-user','user','Unpersisted question'],['local-answer','assistant','Returned answer with <em>literal markup</em>'],['pending-user','user','Question currently being sent']];
try{
 for(const width of [375,1440]){
  const context=await browser.newContext({viewport:{width,height:950},reducedMotion:'reduce',hasTouch:width===375});
  await context.addInitScript(()=>{
   window.__copies=[];window.__clipboardMode='success';window.__installClipboard=()=>Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText(text){window.__copies.push(text);if(window.__clipboardMode==='deny')return Promise.reject(new DOMException('Synthetic denial','NotAllowedError'));if(window.__clipboardMode==='defer')return new Promise(resolve=>window.__resolveCopy=resolve);return Promise.resolve();}}});window.__installClipboard();
  });
  const page=await context.newPage();page.setDefaultTimeout(10000);let mutations=0;const errors=[];
  page.on('pageerror',error=>errors.push(error.message));page.on('request',request=>{if(!['GET','HEAD','OPTIONS'].includes(request.method()))mutations++;});
  await context.route('**/*',async route=>{
   const url=new URL(route.request().url());if(url.hostname!=='localhost'||url.port!=='5173')return route.abort();
   if(url.pathname==='/__message_copy')return route.fulfill({contentType:'text/html',body:`<!doctype html><html><head><link rel="stylesheet" href="/src/styles/globals.css"></head><body><div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;</script><script type="module">
    import React from '/node_modules/.vite/deps/react.js';import ReactDOM from '/node_modules/.vite/deps/react-dom_client.js';
    import {TutorMessage} from '/src/features/tutor/components/TutorMessage.tsx';import {AssistantBlock} from '/src/components/study/AssistantBlock.tsx';
    const rows=${JSON.stringify(cases)};
    ReactDOM.createRoot(document.getElementById('root')).render(React.createElement('main',{style:{padding:16,maxWidth:752,margin:'auto'}},...rows.map(([key,role,text])=>React.createElement('section',{'data-copy-case':key,key},React.createElement(TutorMessage,{role,text,animate:false}),key==='local-answer'?React.createElement('p',null,'This answer may not have been saved.'):null)),React.createElement('section',{'data-copy-case':'pending-answer'},React.createElement(AssistantBlock,{pending:true})),React.createElement('section',{'data-copy-case':'study-default'},React.createElement(AssistantBlock,{text:'Shared study reference',animate:false}))));
   </script></body></html>`});
   return route.continue();
  });
  await page.goto('http://localhost:5173/__message_copy');
  for(const [key,role,text] of cases){
   const section=page.locator(`[data-copy-case="${key}"]`),button=section.getByRole('button',{name:role==='user'?'Copy your message':"Copy Kala's reply",exact:true});
   await button.waitFor();
   if(width===375)await button.tap();else{await button.focus();await button.press('Enter');}
   await button.filter({hasText:'Copied'}).waitFor();
   check(await page.evaluate(()=>window.__copies.at(-1))===text,'TUTOR-REQ-017 exact isolated message content '+key+' '+width);
   check(await section.getByRole('status').innerText()==='Copied','TUTOR-REQ-017 success announced after clipboard resolves '+key);
   check(await button.evaluate(el=>el.getBoundingClientRect().height>=44),'TUTOR-REQ-017 touch target stays accessible');
  }
  check(await page.locator('[data-copy-case="pending-answer"]').getByRole('button').count()===0,'TUTOR-REQ-017 pending Kala placeholder has nothing to copy');
  check(await page.locator('[data-copy-case="study-default"]').getByRole('button').count()===0,'TUTOR-REQ-017 shared Study default has no new copy action');
  const section=page.locator('[data-copy-case="saved-user"]'),button=section.getByRole('button',{name:'Copy your message',exact:true});
  const before=await page.evaluate(()=>window.__copies.length);
  await page.evaluate(()=>window.__clipboardMode='defer');await button.click();
  check(await button.isDisabled()&&await button.getAttribute('aria-busy')==='true','TUTOR-REQ-017 pending clipboard action is locked');
  check(!((await button.innerText()).includes('Copied')),'TUTOR-REQ-017 unresolved clipboard promise never claims success');
  await button.evaluate(el=>el.click());
  check(await page.evaluate(()=>window.__copies.length)===before+1,'TUTOR-REQ-017 double activation does not duplicate a pending write');
  await page.evaluate(()=>window.__resolveCopy());await button.filter({hasText:'Copied'}).waitFor();
  await page.evaluate(()=>window.__clipboardMode='deny');await button.click();
  await section.getByRole('status').filter({hasText:"Couldn't copy"}).waitFor();
  check(!((await button.innerText()).includes('Copied')),'TUTOR-REQ-017 denied clipboard never claims success');
  await page.evaluate(()=>Object.defineProperty(navigator,'clipboard',{configurable:true,value:undefined}));await button.click();
  check((await section.getByRole('status').innerText()).startsWith("Couldn't copy"),'TUTOR-REQ-017 unavailable clipboard gives retry/manual-copy direction');
  await page.evaluate(()=>{window.__clipboardMode='success';window.__installClipboard();});await button.click();await button.filter({hasText:'Copied'}).waitFor();
  check(await page.evaluate(()=>window.__copies.at(-1))===cases[0][2],'TUTOR-REQ-017 retry copies the same exact message');
  check(await page.getByRole('button',{name:/edit/i}).count()===0,'TUTOR-REQ-017 adds no sent-message editing');
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'TUTOR-REQ-017 controls fit viewport');
  check(mutations===0&&errors.length===0,'TUTOR-REQ-017 copying sends no mutating request or runtime error');
  await context.close();
 }
 console.log(`TUTOR-REQ-017 clipboard checks: ${assertions} assertions passed`);
}finally{await browser.close();}
