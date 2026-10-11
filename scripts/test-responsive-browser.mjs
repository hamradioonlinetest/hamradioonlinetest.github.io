#!/usr/bin/env node
// Browser-level responsive smoke tests of the locally built _site directory.
// Runs in PR validation only. No hosted preview or production URL is requested.
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';
import { chromium } from 'playwright';

const root = resolve(process.argv[2] ?? '_site');
const screenshots = resolve('.browser-audit');
const mime = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8', '.json': 'application/json',
  '.png': 'image/png', '.webp': 'image/webp', '.ico': 'image/x-icon',
  '.svg': 'image/svg+xml',
};
let origin = '';
const server = createServer(async (request, response) => {
  try {
    const raw = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    const relative = (raw.endsWith('/') ? raw + 'index.html' : raw).replace(/^\/+/, '');
    const filename = resolve(root, relative);
    if (!filename.startsWith(root + sep)) throw new Error('Invalid path');
    let data = await readFile(filename);
    if (extname(filename) === '.html') {
      // The production source uses absolute asset paths; remap only in-memory
      // for this local test server, leaving the released site untouched.
      data = Buffer.from(data.toString().replaceAll('https://hamradioonlinetest.com/', origin + '/'));
    }
    response.writeHead(200, {'Content-Type': mime[extname(filename)] ?? 'application/octet-stream'});
    response.end(data);
  } catch {
    response.writeHead(404, {'Content-Type': 'text/plain'});
    response.end('Not found');
  }
});

const paths = [
  '/', '/exam-instructions/', '/find-a-session/', '/sandarc-online-exam/',
  '/online-ham-radio-exam-checklist/', '/payment/', '/frn/',
  '/in-person-sessions/', '/sessions/', '/404.html',
];
const widths = [320, 390, 768, 1280];
let browser;
const failures = [];
try {
  await new Promise(ok => server.listen(0, '127.0.0.1', ok));
  origin = 'http://127.0.0.1:' + server.address().port;
  await mkdir(screenshots, { recursive: true });
  browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });

  for (const width of widths) {
    const context = await browser.newContext({
      viewport: { width, height: 800 }, deviceScaleFactor: 1,
      reducedMotion: 'reduce',
    });
    for (const pathname of paths) {
      const page = await context.newPage();
      try {
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      if (pathname === '/sessions/') {
        // The operational staffing page reads a live public CSV; use a safe,
        // deterministic fixture to verify both VEC values and a blank value.
        const publicCsv = [
          'Exam Date,Exam Time,Exam Level,VEs Attending,VEs Participating,VEC',
          '2099-01-01,7:30 PM,Technician,6,KC2NJ,ARRL',
          '2099-01-01,8:00 PM,General,4,KC3PAP,SANDARC',
          '2099-01-02,8:30 PM,General,5,KC3PAP,SANDARC',
          '2099-01-03,9:00 PM,Extra,3,KE2KE,',
        ].join('\n');
        await page.route('https://docs.google.com/spreadsheets/**', route =>
          route.fulfill({
            status: 200, contentType: 'text/csv',
            headers: { 'access-control-allow-origin': '*' },
            body: publicCsv,
          }));
      }
      const response = await page.goto(origin + pathname, {
        waitUntil: 'load', timeout: 30000,
      });
      assert.equal(response.status(), 200, pathname + ' failed to load');
      const report = await page.evaluate(() => {
        const header = document.querySelector('.header');
        const nav = [...document.querySelectorAll('.navlinks a')];
        return {
          actualWidth: window.innerWidth,
          documentWidth: document.documentElement.scrollWidth,
          h1Count: document.querySelectorAll('main h1').length,
          headerPosition: header ? getComputedStyle(header).position : null,
          minNavHeight: nav.length ? Math.min(...nav.map(a => a.getBoundingClientRect().height)) : 0,
          brokenImages: [...document.images].filter(img => img.complete && img.naturalWidth === 0).map(img => img.src),
          overflowElements: [...document.querySelectorAll('body *')]
            .filter(el => {
              const rect = el.getBoundingClientRect();
              return getComputedStyle(el).position !== 'fixed' && (rect.right > innerWidth + 1 || rect.left < -1);
            })
            .slice(0, 12)
            .map(el => ({
              tag: el.tagName.toLowerCase(),
              className: String(el.className?.baseVal ?? el.className ?? '').slice(0, 90),
              text: el.textContent?.trim().slice(0, 50),
            })),
        };
      });
      const label = pathname + ' at ' + width + 'px';
      assert.equal(report.actualWidth, width, 'Wrong viewport: ' + label);
      assert.equal(report.h1Count, 1, 'Expected one H1: ' + label);
      assert.ok(report.documentWidth <= width + 2,
        'Horizontal document overflow: ' + label + ' (' + report.documentWidth + 'px). Candidates: ' + JSON.stringify(report.overflowElements));
      assert.deepEqual(report.brokenImages, [], 'Broken images: ' + label);
      if (width <= 390) {
        assert.equal(report.headerPosition, 'static', 'Mobile header obstructs viewport: ' + label);
        assert.ok(report.minNavHeight >= 43.5, 'Mobile navigation tap target too small: ' + label);
      }
      if (width === 1280) {
        assert.equal(report.headerPosition, 'sticky', 'Desktop header should remain sticky: ' + label);
      }
      if (pathname === '/online-ham-radio-exam-checklist/' && width <= 390) {
        const trigger = page.locator('.zoom-audio-help__trigger').first();
        const box = await trigger.boundingBox();
        assert.ok(box && box.width >= 43.5 && box.height >= 43.5,
          'Zoom help tap target below 44px: ' + label);
        await trigger.focus();
        const panel = page.locator('.zoom-audio-help__panel').first();
        const modal = await panel.boundingBox();
        assert.ok(modal && modal.x >= -1 && modal.x + modal.width <= width + 1,
          'Zoom help popup extends beyond phone viewport: ' + label);
      }
      if (pathname === '/sessions/') {
        const rows = page.locator('#tbody tr');
        await rows.nth(3).waitFor({ timeout: 10000 });
        assert.deepEqual(await page.locator('thead th').allTextContents().then(
          headers => headers.map(h => h.trim().replace(/[▲▼]/g, '').trim())),
          ['Exam Date', 'Exam Time', 'Exam Level', 'VEC', 'VEs Attending', 'Add To Calendar'],
          'Sessions table headers are out of order: ' + label);
        assert.deepEqual(await page.locator('#tbody td[data-label="VEC"]').allTextContents(),
          ['ARRL', 'SANDARC', 'SANDARC', '—'], 'VEC values must match public CSV, not default to ARRL: ' + label);
        const readGroups = () => rows.evaluateAll(trs => trs.map(tr => {
          const dateCell = tr.querySelector('td[data-label="Exam Date"]');
          return {
            date: dateCell.textContent.trim(),
            background: getComputedStyle(dateCell).backgroundColor,
            cardBackground: getComputedStyle(tr).backgroundColor,
            newDate: tr.classList.contains('date-group-start'),
            cellBorder: parseFloat(getComputedStyle(dateCell).borderTopWidth),
            cardBorder: parseFloat(getComputedStyle(tr).borderTopWidth),
          };
        }));
        const initialGroups = await readGroups();
        assert.deepEqual(initialGroups.map(row => row.background),
          ['rgb(255, 255, 255)', 'rgb(255, 255, 255)', 'rgb(248, 244, 244)', 'rgb(255, 255, 255)'],
          'Alternation must follow distinct dates rather than row parity: ' + label);
        assert.deepEqual(initialGroups.map(row => row.newDate),
          [false, false, true, true], 'Date separators should appear only at date boundaries: ' + label);
        if (width <= 390) {
          assert.deepEqual(initialGroups.map(row => row.cardBackground),
            initialGroups.map(row => row.background), 'Mobile card background must match its date: ' + label);
          assert.ok(initialGroups[2].cardBorder >= 2, 'Missing mobile date divider: ' + label);
        } else {
          assert.ok(initialGroups[2].cellBorder >= 2, 'Missing desktop date divider: ' + label);
        }
        const assertTintSurvivesSort = async () => {
          const sortedGroups = await readGroups();
          const backgroundForDate = new Map(initialGroups.map(row => [row.date, row.background]));
          for (const row of sortedGroups) {
            assert.equal(row.background, backgroundForDate.get(row.date),
              'Sorting must preserve shading assigned to each date: ' + label);
          }
          assert.deepEqual(sortedGroups.map((row, index) =>
            row.newDate === (index > 0 && row.date !== sortedGroups[index - 1].date)),
            sortedGroups.map(() => true), 'Date dividers must follow displayed row order: ' + label);
        };
        if (width <= 390) {
          assert.ok(await page.locator('#tbody td[data-label="VEC"]').first().isVisible(),
            'VEC should remain visible in the mobile card layout: ' + label);
        }
        if (width === 1280) {
          await page.locator('thead th[data-col="3"]').click();
          assert.match(await page.locator('#sortBadge').innerText(), /Sort: VEC \(asc\)/);
          const sortedVecs = await page.locator('#tbody td[data-label="VEC"]').allTextContents();
          await page.locator('thead th[data-col="3"]').click();
          assert.match(await page.locator('#sortBadge').innerText(), /Sort: VEC \(desc\)/);
          assert.deepEqual(await page.locator('#tbody td[data-label="VEC"]').allTextContents(),
            [...sortedVecs].reverse(), 'VEC header does not toggle sort direction');
          await assertTintSurvivesSort();
          await page.locator('thead th[data-col="4"]').click();
          assert.match(await page.locator('#sortBadge').innerText(), /Sort: VEs Attending \(asc\)/);
          assert.equal((await page.locator('#tbody td[data-label="VEs Attending"]').first().innerText()).trim(), '3');
          await assertTintSurvivesSort();
        }
      }
      assert.deepEqual(errors, [], 'Uncaught browser errors: ' + label);
      if (pathname === '/' || pathname === '/online-ham-radio-exam-checklist/') {
        await page.screenshot({
          path: screenshots + '/' + (pathname === '/' ? 'home' : 'checklist') + '-' + width + '.png',
          fullPage: true,
        });
      }
      } catch (error) {
        failures.push(error.message);
      } finally {
        await page.close();
      }
    }
    await context.close();
  }
  // Exercise real browser Intl/zone conversion independently of HamStudy availability
  // and without loading a hosted preview or a live schedule.
  const springStart = Date.parse('2027-03-14T08:30:00Z'); // LA 00:30 PST
  const springEnd = Date.parse('2027-03-14T11:30:00Z');   // LA 04:30 PDT
  const midnightStart = Date.parse('2027-03-14T14:30:00Z');
  const midnightEnd = Date.parse('2027-03-14T16:30:00Z'); // JST crosses midnight
  for (const zone of ['America/Los_Angeles', 'Asia/Tokyo']) {
    const context = await browser.newContext({ timezoneId: zone, locale: 'en-US' });
    const page = await context.newPage();
    try {
      await page.setContent(`
        <p data-session-timezone-label>Eastern Time (America/New_York).</p>
        <div data-session-schedule data-expires-at="9999999999999"
          data-fresh-until="9999999999999">
          <ul data-session-list>
            <li data-session-start="${springStart}" data-session-end="${springEnd}">
              <div><time datetime="2027-03-14T04:30:00-04:00">Eastern fallback date</time>
                <span class="session-clock">Eastern fallback clock</span>
                <span class="session-vec">SANDARC VEC · Free exam</span></div>
              <a aria-label="Eastern fallback link" href="#">View session</a>
            </li>
            <li data-session-start="${midnightStart}" data-session-end="${midnightEnd}">
              <div><time datetime="2027-03-14T10:30:00-04:00">Eastern fallback date</time>
                <span class="session-clock">Eastern fallback clock</span></div>
              <a aria-label="Eastern fallback link" href="#">View session</a>
            </li>
          </ul>
          <p data-session-checked>Schedule checked:
            <span data-session-checked-at="${springStart}" data-session-checked-vec="SANDARC VEC">Eastern time</span>
          </p>
          <p data-session-fallback hidden>fallback</p>
          <span data-session-stale-warning hidden>stale</span>
        </div>`);
      // Without JavaScript, the explicit Eastern-marked server fallback remains.
      assert.match(await page.locator('[data-session-timezone-label]').innerText(),
        /Eastern Time \(America\/New_York\)/);
      assert.equal(await page.locator('.session-clock').first().innerText(),
        'Eastern fallback clock');
      await page.addScriptTag({ url: origin + '/assets/js/main.js' });
      assert.match(await page.locator('[data-session-timezone-label]').innerText(),
        new RegExp(zone.replaceAll('/', '\\/')));
      const clocks = await page.locator('.session-clock').allTextContents();
      const dates = await page.locator('li time').allTextContents();
      const linkLabel = await page.locator('li a[aria-label]').first().getAttribute('aria-label');
      const checked = await page.locator('[data-session-checked-at]').innerText();
      if (zone === 'America/Los_Angeles') {
        assert.match(clocks[0], /PST.*PDT/, 'Show both DST offsets on spring transition');
        assert.match(dates[0], /March 14, 2027/);
        assert.match(clocks[1], /PDT/, 'Later exam must use date-specific daylight time');
      } else {
        assert.match(clocks[0], /JST|GMT\+9/, 'Tokyo should show its local time zone');
        assert.match(clocks[1], /ends Mar 15/, 'Local midnight must show end date');
      }
      assert.match(linkLabel, /SANDARC VEC/, 'Local accessible registration label lost VEC');
      assert.match(linkLabel, new RegExp(clocks[0].replace(/[.*+?^${}()|[\]\\]/g, '\\  assert.deepEqual(failures, [], 'Browser audit found ' + failures.length + ' issue(s) across the viewport matrix');')));
      assert.match(checked, /SANDARC VEC:.*(?:PST|JST|GMT\+9)/,
        'Schedule-check time should be converted and labeled');
      assert.equal(await page.locator('li time').first().getAttribute('datetime'),
        new Date(springStart).toISOString());
    } catch (err) {
      failures.push('Local time zone ' + zone + ': ' + err.message);
    } finally {
      await context.close();
    }
  }
  assert.deepEqual(failures, [], 'Browser audit found ' + failures.length + ' issue(s) across the viewport matrix');
  console.log('Browser audit passed: ' + paths.length + ' pages at ' + widths.join(', ') + 'px.');
} finally {
  if (browser) await browser.close();
  server.close();
}
