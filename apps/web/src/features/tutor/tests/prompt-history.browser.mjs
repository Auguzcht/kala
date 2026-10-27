/** TUTOR-REQ-022: real composer, synthetic local props, no service calls. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {resolve} from 'node:path';
const requireBrowser=createRequire(resolve(process.env.KALA_BROWSER_TEST_DEPS??'apps/web','package.json'));
const {chromium}=requireBrowser('playwright');
const browser=await chromium.launch({headless:true,...(process.env.KALA_BROWSER_EXECUTABLE?{executablePath:process.env.KALA_BROWSER_EXECUTABLE}:{})});
let assertions=0;const check=(value,label)=>{assert.ok(value,label);assertions++;};
try{
 for(const width of [375,1440]){
  const context=await browser.newContext({viewport:{width,height:950},reducedMotion:'reduce'});
  const page=await context.newPage();page.setDefaultTimeout(10000);let mutations=0;const errors=[];
  page.on('pageerror',error=>errors.push(error.message));page.on('request',request=>{if(!['GET','HEAD','OPTIONS'].includes(request.method()))mutations++;});
  await context.route('**/*',async route=>{
   const url=new URL(route.request().url());if(url.hostname!=='localhost'||url.port!=='5173')return route.abort();
   if(url.pathname==='/__prompt_history')return route.fulfill({contentType:'text/html',body:`<!doctype html><html><head><link rel="stylesheet" href="/src/styles/globals.css"></head><body><div id="root"></div><script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;</script><script type="module">
    import React from '/node_modules/.vite/deps/react.js';import ReactDOM from '/node_modules/.vite/deps/react-dom_client.js';
    import {TutorComposer} from '/src/features/tutor/components/TutorComposer.tsx';import {TooltipProvider} from '/src/components/ui/tooltip.tsx';
    window.__submitted=[];
    function App(){const [history,setHistory]=React.useState(['First saved prompt','Latest saved prompt']);const [chat,setChat]=React.useState('first');const [pending,setPending]=React.useState(false);const ref=React.useRef(null);
    return React.createElement(TooltipProvider,null,React.createElement('main',{ref,style:{padding:16,maxWidth:752,margin:'auto'}},React.createElement('button',{onClick:()=>{setChat('other');setHistory(['Other chat prompt']);}},'Other chat'),React.createElement('button',{onClick:()=>{setChat('new');setHistory([]);}},'New chat'),React.createElement('button',{onClick:()=>setPending(value=>!value)},'Toggle pending'),React.createElement(TutorComposer,{key:chat,dropTarget:ref,promptHistory:history,attachments:[],onDragChange:()=>{},onFiles:async()=>({uploaded:[],failed:[]}),onRemove:()=>{},removingId:null,onAsk:text=>{window.__submitted.push(text);setHistory(previous=>[...previous,text]);},onTyping:()=>{},pending,uploading:false})));}
    ReactDOM.createRoot(document.getElementById('root')).render(React.createElement(App));
   </script></body></html>`});
   if(url.pathname.endsWith('/src/lib/api/client.ts'))return route.fulfill({contentType:'application/javascript',body:`export async function api(){throw new Error('Prompt history must not call a service');}`});
   return route.continue();
  });
  await page.goto('http://localhost:5173/__prompt_history');
  const input=page.getByPlaceholder('Ask Kala…');await input.waitFor();await input.focus();
  const expect=async(value,label)=>{await page.waitForFunction(expected=>document.querySelector('textarea')?.value===expected,value);check(await input.inputValue()===value,'TUTOR-REQ-022 '+label+' '+width);};
  await input.press('ArrowUp');await expect('Latest saved prompt','Up recalls newest');
  await input.press('ArrowUp');await expect('First saved prompt','Up recalls older');
  await input.press('ArrowUp');await expect('First saved prompt','oldest boundary clamps');
  await input.press('ArrowDown');await expect('Latest saved prompt','Down recalls newer');
  await input.press('ArrowDown');await expect('','Down restores original empty draft');
  await input.fill('My unsent draft');await input.evaluate(el=>el.setSelectionRange(3,3));
  await input.press('ArrowUp');await expect('Latest saved prompt','typed draft temporarily recalls history');
  await input.press('ArrowDown');await expect('My unsent draft','Down restores original draft exactly');
  await page.waitForFunction(()=>document.querySelector('textarea').selectionStart===3);
  check(await input.evaluate(el=>el.selectionStart===3&&el.selectionEnd===3),'TUTOR-REQ-022 restores original caret');
  await input.press('ArrowUp');await input.fill('Edited recalled prompt');await input.press('ArrowDown');await expect('Edited recalled prompt','editing leaves history mode');
  await input.press('ArrowUp');await expect('Latest saved prompt','edited prompt can browse again');await input.press('ArrowDown');await expect('Edited recalled prompt','edited prompt becomes the restored draft');
  await input.fill('first\nsecond');await input.evaluate(el=>el.setSelectionRange(12,12));
  await input.press('ArrowUp');check(await input.inputValue()==='first\nsecond','TUTOR-REQ-022 multiline inner arrows preserve editing');
  await input.evaluate(el=>el.setSelectionRange(0,0));await input.press('ArrowUp');await expect('Latest saved prompt','first logical line can recall');
  await input.press('ArrowDown');await expect('first\nsecond','multiline draft restores');
  for(const init of [{shiftKey:true},{ctrlKey:true},{altKey:true},{metaKey:true},{isComposing:true}]){
   await input.fill('Keep this draft');
   const prevented=await input.evaluate((el,init)=>{const event=new KeyboardEvent('keydown',{key:'ArrowUp',bubbles:true,cancelable:true,...init});el.dispatchEvent(event);return event.defaultPrevented;},init);
   check(!prevented&&await input.inputValue()==='Keep this draft','TUTOR-REQ-022 modified/IME arrow stays native '+JSON.stringify({init,prevented,value:await input.inputValue()}));
  }
  await input.fill('Selected text');await input.evaluate(el=>el.setSelectionRange(0,8));await input.press('ArrowUp');check(await input.inputValue()==='Selected text','TUTOR-REQ-022 selections are not replaced by history');
  await page.getByRole('button',{name:'Toggle pending',exact:true}).click();await input.fill('Pending draft');await input.press('ArrowUp');check(await input.inputValue()==='Pending draft','TUTOR-REQ-022 pending submission keeps its lock');
  await page.getByRole('button',{name:'Toggle pending',exact:true}).click();
  check(await page.evaluate(()=>window.__submitted.length)===0&&mutations===0,'TUTOR-REQ-022 browsing has never submitted or sent a request');
  await input.fill('Draft before sending');await input.press('ArrowUp');await input.press('ArrowUp');await input.press('Enter');await expect('','explicit Enter clears accepted draft');
  check(await page.evaluate(()=>window.__submitted.length===1&&window.__submitted[0]==='First saved prompt'),'TUTOR-REQ-022 Enter sends exactly the chosen prompt');
  await input.press('ArrowUp');await expect('First saved prompt','history position resets after submit');await input.press('ArrowDown');await expect('','submit starts a fresh empty draft');
  await page.getByRole('button',{name:'Other chat',exact:true}).click();await input.press('ArrowUp');await expect('Other chat prompt','new chat has only its own history');await input.press('ArrowUp');await expect('Other chat prompt','other chat cannot reach the prior history');
  await page.getByRole('button',{name:'New chat',exact:true}).click();await input.press('ArrowUp');await expect('','fresh chat has no previous prompt');
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'TUTOR-REQ-022 recalled drafts fit viewport');
  check(mutations===0&&errors.length===0,'TUTOR-REQ-022 has zero service writes or runtime errors');
  await context.close();
 }
 console.log(`TUTOR-REQ-022 prompt history checks: ${assertions} assertions passed`);
}finally{await browser.close();}
