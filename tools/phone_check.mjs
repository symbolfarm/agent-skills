// Check a built page as a phone or desktop reader would see it, with page
// JavaScript disabled: usage `node phone_check.mjs <file-url> <out-prefix> [width]`.
// Taps the first glossary term with a real touch (or mouse) event, reports
// horizontal overflow and whether the definition opened, and saves screenshots.
import { spawn } from 'node:child_process';
import { writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const [url, out, widthArg] = process.argv.slice(2);
const width = Number(widthArg || 390), mobile = width < 600, height = mobile ? 844 : 900;
const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn('google-chrome', ['--headless=new', '--no-sandbox', '--disable-gpu', `--remote-debugging-port=${port}`,
  `--user-data-dir=${mkdtempSync(join(tmpdir(), 'cdp-'))}`, 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let target;
for (let i = 0; i < 50 && !target; i++) {
  await sleep(200);
  try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === 'page'); } catch {}
}
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r));
let id = 0; const waiting = new Map();
ws.addEventListener('message', (e) => { const m = JSON.parse(e.data); if (waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id); } });
const send = (method, params = {}) => new Promise((r) => { const n = ++id; waiting.set(n, r); ws.send(JSON.stringify({ id: n, method, params })); });
await send('Page.enable'); await send('DOM.enable');
await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: mobile ? 2 : 1, mobile });
if (mobile) await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 1 });
await send('Emulation.setScriptExecutionDisabled', { value: true });
await send('Page.navigate', { url }); await sleep(1200);
const metrics = (await send('Page.getLayoutMetrics')).result;
const content = metrics.cssContentSize, view = metrics.cssLayoutViewport;
const shot = async (name) => { const r = await send('Page.captureScreenshot', { format: 'png' }); writeFileSync(`${out}-${width}-${name}.png`, Buffer.from(r.result.data, 'base64')); };
await shot('closed');
const doc = (await send('DOM.getDocument')).result.root;
const q = async (sel) => (await send('DOM.querySelector', { nodeId: doc.nodeId, selector: sel })).result.nodeId;
const label = await q('.term-label'), def = await q('.term-def');
const before = (await send('DOM.getBoxModel', { nodeId: def })).error ? 'hidden' : 'visible';
await send('DOM.scrollIntoViewIfNeeded', { nodeId: label }); await sleep(200);
const box = (await send('DOM.getBoxModel', { nodeId: label })).result.model.content;
const x = (box[0] + box[2]) / 2, y = (box[1] + box[5]) / 2;
if (mobile) {
  await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
  await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
} else {
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
}
await sleep(400);
const after = (await send('DOM.getBoxModel', { nodeId: def })).error ? 'hidden' : 'visible';
const after2 = (await send('Page.getLayoutMetrics')).result.cssContentSize;
await shot('open');
console.log(JSON.stringify({ width, js: 'disabled', input: mobile ? 'touch' : 'mouse', contentWidth: content.width, viewportWidth: view.clientWidth,
  horizontalOverflow: content.width > view.clientWidth + 0.5, contentWidthWithDefinitionOpen: after2.width, definitionBefore: before, definitionAfterTap: after }));
ws.close(); chrome.kill();
