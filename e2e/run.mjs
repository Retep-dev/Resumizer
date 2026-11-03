// End-to-end test of the deployed preview (Vercel frontend + Render backend) with fictional resumes only.
// Drives the real UI with Playwright, records every tab's text, screenshots (desktop and phone), the hosts
// the browser talked to, and the backend's /status before and after. Writes e2e_out/report.json.
import { chromium } from 'playwright';
import fs from 'node:fs';

const FRONTEND = process.env.E2E_FRONTEND;
const BACKEND = process.env.E2E_BACKEND;
const OUT = 'e2e_out';
fs.mkdirSync(`${OUT}/shots`, { recursive: true });
const postings = JSON.parse(fs.readFileSync('e2e/fixtures/postings.json', 'utf8'));
const report = { started: new Date().toISOString(), frontend: FRONTEND, backend: BACKEND, runs: [], hosts: {}, problems: [] };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const save = () => fs.writeFileSync(`${OUT}/report.json`, JSON.stringify(report, null, 1));

async function status() {
  const s = await (await fetch(`${BACKEND}/api/v1/status`)).json();
  return {
    mode: s.ai_deployment, paid: s.paid_providers, commit: s.commit,
    chains: Object.fromEntries(Object.entries(s.tasks).map(([k, v]) => [k, v.map((e) => `${e.provider}:${e.model} ${e.ready ? 'ready' : e.note}`)])),
    limits: s.limits, usage: s.usage,
  };
}

function watchHosts(page) {
  page.on('request', (req) => {
    const h = new URL(req.url()).host;
    report.hosts[h] = (report.hosts[h] || 0) + 1;
  });
}

const mainText = (page) => page.evaluate(() => (document.querySelector('main') || document.body).innerText);

async function openTab(page, id) {
  await page.click(`#tab-${id}`);
  await sleep(1200);
  await page.evaluate(() => document.querySelectorAll('details').forEach((d) => { d.open = true; }));
  await sleep(300);
}

async function analyze(page, file, jd) {
  await page.goto(`${FRONTEND}/#/analyze`, { waitUntil: 'networkidle' });
  await page.setInputFiles('input[type=file]', file);
  await page.fill('#job-description', jd);
  const t0 = Date.now();
  await page.getByRole('button', { name: /start the analysis/i }).click();
  while (Date.now() - t0 < 300000) {
    const hash = await page.evaluate(() => location.hash);
    if (hash.startsWith('#/results')) break;
    const alert = await page.locator('[role=alert]').allInnerTexts();
    if (alert.length && alert.join(' ').trim()) return { error: alert.join(' | '), seconds: (Date.now() - t0) / 1000 };
    await sleep(1500);
  }
  return { seconds: (Date.now() - t0) / 1000 };
}

async function ask(page, msg) {
  await page.fill('textarea', msg);
  const t0 = Date.now();
  await page.getByRole('button', { name: /send/i }).click();
  let last = '', stable = 0;
  while (Date.now() - t0 < 120000) {
    await sleep(2000);
    const t = await mainText(page);
    const tail = t.slice(t.lastIndexOf(msg) + msg.length).replace(/Message your career coach[\s\S]*$/, '').trim();
    if (tail.length > 20 && tail === last) { if (++stable >= 1) return { message: msg, reply: tail, seconds: (Date.now() - t0) / 1000 }; }
    else stable = 0;
    last = tail;
  }
  return { message: msg, reply: last, seconds: (Date.now() - t0) / 1000, timeout: true };
}

async function fullRun(browser, id, file, jd, questions, { mobile = false } = {}) {
  const ctx = await browser.newContext(mobile
    ? { viewport: { width: 375, height: 812 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true }
    : { viewport: { width: 1366, height: 900 } });
  const page = await ctx.newPage();
  watchHosts(page);
  const tag = `${id}${mobile ? '-mobile' : ''}`;
  const run = { id: tag, file };
  try {
    if (mobile) {
      await page.goto(`${FRONTEND}/#/analyze`, { waitUntil: 'networkidle' });
      await page.screenshot({ path: `${OUT}/shots/${tag}-0-upload.png`, fullPage: true });
    }
    Object.assign(run, await analyze(page, file, jd));
    if (run.error) { report.runs.push(run); save(); await ctx.close(); return; }
    const overflow = async () => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    run.score = await mainText(page);
    await page.screenshot({ path: `${OUT}/shots/${tag}-1-score.png`, fullPage: true });
    run.overflow = { score: await overflow() };
    for (const name of ['rewrite', 'interview']) {
      await openTab(page, name);
      if (name === 'interview') {
        const all = page.locator('button, [role=tab]').filter({ hasText: /^All questions$/ });
        if (await all.count()) { await all.first().click(); await sleep(800); await page.evaluate(() => document.querySelectorAll('details').forEach((d) => { d.open = true; })); }
      }
      run[name] = await mainText(page);
      run.overflow[name] = await overflow();
      await page.screenshot({ path: `${OUT}/shots/${tag}-2-${name}.png`, fullPage: true });
    }
    await openTab(page, 'coach');
    run.coach = [];
    for (const q of questions) {
      run.coach.push(await ask(page, q));
      save();
    }
    run.overflow.coach = await overflow();
    await page.screenshot({ path: `${OUT}/shots/${tag}-3-coach.png`, fullPage: true });
  } catch (e) {
    run.exception = String(e).slice(0, 500);
    await page.screenshot({ path: `${OUT}/shots/${tag}-error.png`, fullPage: true }).catch(() => {});
  }
  report.runs.push(run);
  save();
  await ctx.close();
}

report.status_before = await status();
save();
const browser = await chromium.launch();

// Which backend does the deployed frontend call? Read it from the shipped bundle.
{
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await page.goto(FRONTEND, { waitUntil: 'networkidle' });
  report.bundle_backends = await page.evaluate(async () => {
    const found = new Set();
    for (const s of [...document.scripts].map((x) => x.src).filter(Boolean)) {
      const t = await (await fetch(s)).text();
      (t.match(/https:\/\/[a-z0-9.-]*onrender\.com/g) || []).forEach((m) => found.add(m));
    }
    return [...found];
  });
  await ctx.close();
}

const F = 'e2e/fixtures';
await fullRun(browser, 'aisha', `${F}/aisha_bello_resume.txt`, postings.aisha, [
  "Rewrite my SLA bullet so it's stronger.",
  'I also trained 3 new agents a month during 2023. How should I add that to my resume?',
  'So can I say I have team lead experience?',
]);
await fullRun(browser, 'priya', `${F}/priya_raman_resume.pdf`, postings.priya, [
  'Do I have Kafka experience? Yes or no first.',
  "Rewrite my Airflow bullet so it's stronger for this job.",
  'Write a two-sentence pitch I could use at the start of the interview.',
]);
await fullRun(browser, 'tomas', `${F}/tomas_okafor_resume.docx`, postings.tomas, [
  'How should I handle the TypeScript gap in an interview?',
  'Rewrite my checkout bullet to fit this job better.',
]);
await fullRun(browser, 'marcus', `${F}/marcus_bell_resume.txt`, postings.marcus, [
  'Do I have Six Sigma experience? Yes or no first.',
]);
// A fourth new analysis from the same address should be refused by the 3-a-day limit, before any AI call.
await fullRun(browser, 'limit-check', `${F}/marcus_bell_resume.txt`, postings.tomas, []);
// Phone-size pass on a repeat of Aisha's analysis (served from the cache: no AI call, not counted).
await fullRun(browser, 'aisha', `${F}/aisha_bello_resume.txt`, postings.aisha, ['What should I fix first?'], { mobile: true });

await browser.close();
report.status_after = await status();
report.finished = new Date().toISOString();
save();
console.log(`::notice title=e2e::${report.runs.map((r) => `${r.id}: ${r.error ? 'ERROR ' + r.error.slice(0, 80) : r.exception ? 'EXCEPTION' : 'ok ' + r.seconds + 's'}`).join(' | ')}`);
console.log(`::notice title=e2e hosts::${JSON.stringify(report.hosts)}`);
