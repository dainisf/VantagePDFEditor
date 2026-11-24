// End-to-end test of the browser build (dist-web) served under a sub-path.
//   node tests/e2e/web_e2e.js <sample.pdf> <url> <out-dir>
// Fails (exit 1) on page errors, network use after load, or wrong output.
const { chromium } = require('playwright');
const fs = require('fs');

const [, , SAMPLE, URL, OUT] = process.argv;
const fail = (msg) => { console.error('FAIL: ' + msg); process.exit(1); };

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1300, height: 1250 }, acceptDownloads: true });
  const pg = await ctx.newPage();
  const errs = [], requests = [];
  pg.on('pageerror', (e) => errs.push(String(e)));
  pg.on('console', (m) => m.type() === 'error' && errs.push(m.text()));
  ctx.on('request', (r) => requests.push(`${r.method()} ${r.url()}`));

  const t0 = Date.now();
  await pg.goto(URL);
  // Wait for the worker's explicit ready signal (the status line starts hidden, so it can't be used).
  await pg.waitForFunction(() => document.body.dataset.engine === 'ready' || document.body.dataset.engine === 'error', null, { timeout: 180000 });
  if (await pg.evaluate(() => document.body.dataset.engine) !== 'ready') fail('engine failed: ' + await pg.textContent('#engineText'));
  console.log(`engine ready after ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  const loaded = requests.length;

  await pg.setInputFiles('#fileOpen', SAMPLE);
  await pg.waitForFunction(() => { const i = document.querySelector('.page img'); return i && i.complete && i.naturalWidth > 0; }, null, { timeout: 60000 });

  await pg.click('.tool[data-tool="edittext"]');
  await pg.waitForSelector('.mark.textline');
  const lb = await (await pg.$$('.page[data-page="0"] .mark.textline'))[3].boundingBox();
  await pg.mouse.click(lb.x + 5, lb.y + lb.height / 2);
  await pg.fill('.inline-editor', 'Revenue grew 33% compared with last quarter.');
  await pg.keyboard.press('Enter');
  await pg.waitForFunction(() => !document.querySelector('.inline-editor'));
  await pg.waitForTimeout(1500);

  await pg.click('.tool[data-tool="redact"]');
  await pg.click('.chip[data-preset="email"]');
  await pg.click('.chip[data-preset="ssn"]');
  await pg.click('#panelBody form button[type="submit"]');
  await pg.waitForSelector('.mark.redact');
  await pg.click('[data-apply]');
  await pg.click('.modal [data-ok]');
  await pg.waitForFunction(() => !document.querySelector('.mark.redact'), null, { timeout: 30000 });
  await pg.click('.tool[data-tool="select"]');
  await pg.waitForTimeout(1000);
  if (OUT) await pg.screenshot({ path: OUT + '/web-editor.png' });

  const [dl] = await Promise.all([pg.waitForEvent('download'), pg.click('[data-action="save"]')]);
  const pdfPath = (OUT || '.') + '/web-out.pdf';
  await dl.saveAs(pdfPath);

  const host = new globalThis.URL(URL).host;
  const network = requests.slice(loaded).filter((r) => !r.startsWith('GET blob:'));
  const external = requests.filter((r) => !r.includes(host) && !r.startsWith('GET blob:') && !r.startsWith('GET data:'));
  console.log('network requests after load:', JSON.stringify(network));
  await b.close();

  if (errs.length) fail('page errors: ' + JSON.stringify(errs));
  if (network.length) fail('network used after the engine loaded (document may have left the browser)');
  if (external.length) fail('requests to other hosts: ' + JSON.stringify(external));
  if (!fs.existsSync(pdfPath) || fs.statSync(pdfPath).size < 500) fail('no PDF downloaded');
  console.log('PASS: browser build edited, redacted and saved a PDF with no network use');
})().catch((e) => fail(e.stack || String(e)));
