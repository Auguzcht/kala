/** DESIGN-REQ-001 / WI-34: native text selection, local Vite, external traffic blocked. */
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';

const requireBrowser = createRequire(resolve(process.env.KALA_BROWSER_TEST_DEPS ?? 'apps/web', 'package.json'));
const { chromium } = requireBrowser('playwright');
const browser = await chromium.launch({ headless: true, ...(process.env.KALA_BROWSER_EXECUTABLE ? { executablePath: process.env.KALA_BROWSER_EXECUTABLE } : {}) });
const out = resolve(process.env.KALA_UI_SCREENSHOTS ?? '/tmp/kala-approval09-selection');
await mkdir(out, { recursive: true });
let assertions = 0;
const check = (value, label) => { assert.ok(value, label); assertions++; };

try {
  for (const width of [375, 1440]) {
    const context = await browser.newContext({ viewport: { width, height: 700 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await context.route('**/*', route => {
      const url = new URL(route.request().url());
      if (url.hostname !== 'localhost' || url.port !== '5173') return route.abort();
      if (url.pathname !== '/__selection') return route.continue();
      return route.fulfill({ contentType: 'text/html', body: `<!doctype html><html><head><link rel="stylesheet" href="/src/styles/globals.css"></head><body><div id="root"></div>
        <script type="module">import RefreshRuntime from '/@react-refresh';RefreshRuntime.injectIntoGlobalHook(window);window.$RefreshReg$=()=>{};window.$RefreshSig$=()=>type=>type;window.__vite_plugin_react_preamble_installed__=true;</script>
        <script type="module">
        import React from '/node_modules/.vite/deps/react.js';import ReactDOM from '/node_modules/.vite/deps/react-dom_client.js';
        import {Input} from '/src/components/ui/input.tsx';import {Textarea} from '/src/components/ui/textarea.tsx';
        ReactDOM.createRoot(document.getElementById('root')).render(React.createElement('main',{className:'mx-auto max-w-lg space-y-5 p-6'},
          React.createElement('p',{id:'body-sample'},'Course-grounded learning with Kala'),
          React.createElement(Input,{'aria-label':'Chat title',defaultValue:'Understanding cloud storage'}),
          React.createElement(Textarea,{'aria-label':'Question',defaultValue:'How does object storage work?'})));
        </script></body></html>` });
    });
    await page.goto('http://localhost:5173/__selection');
    await page.locator('#body-sample').waitFor();
    for (const theme of ['light', 'dark']) {
      await page.evaluate(theme => document.documentElement.classList.toggle('dark', theme === 'dark'), theme);
      for (const selector of ['#body-sample', 'input', 'textarea']) {
        const target = page.locator(selector);
        const selection = await target.evaluate(el => {
          let selected;
          if (el.matches('input,textarea')) {
            el.focus();
            el.select();
            selected = el.value.slice(el.selectionStart, el.selectionEnd);
          } else {
            document.activeElement?.blur();
            const range = document.createRange();
            range.selectNodeContents(el);
            window.getSelection().removeAllRanges();
            window.getSelection().addRange(range);
            selected = window.getSelection().toString();
          }
          const css = getComputedStyle(el, '::selection');
          return { selected, expected: el.value ?? el.textContent, background: css.backgroundColor, color: css.color };
        });
        check(selection.selected === selection.expected, `DESIGN-REQ-001 native ${selector} selection preserved in ${theme} at ${width}`);
        check(selection.background === 'rgb(188, 211, 244)', `DESIGN-REQ-001 ${selector} uses BCD3F4 in ${theme} at ${width}`);
        check(selection.color === 'rgb(14, 27, 51)', `DESIGN-REQ-001 ${selector} retains dark ink contrast in ${theme} at ${width}`);
        await page.screenshot({ path: resolve(out, `${theme}-${selector.replace('#', '')}-${width}.png`), animations: 'disabled' });
      }
    }
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `DESIGN-REQ-001 no horizontal overflow at ${width}`);
    check(errors.length === 0, `DESIGN-REQ-001 no runtime errors at ${width}`);
    await context.close();
  }
  console.log(`WI-34 selection passed: ${assertions} assertions. Synthetic screenshots: ${out}`);
} finally {
  await browser.close();
}
