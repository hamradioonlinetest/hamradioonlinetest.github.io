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
  '/in-person-sessions/', '/404.html',
];
const widths = [320, 390, 768, 1280];
let browser;
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
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
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
      assert.deepEqual(errors, [], 'Uncaught browser errors: ' + label);
      if (pathname === '/' || pathname === '/online-ham-radio-exam-checklist/') {
        await page.screenshot({
          path: screenshots + '/' + (pathname === '/' ? 'home' : 'checklist') + '-' + width + '.png',
          fullPage: true,
        });
      }
      await page.close();
    }
    await context.close();
  }
  console.log('Browser audit passed: ' + paths.length + ' pages at ' + widths.join(', ') + 'px.');
} finally {
  if (browser) await browser.close();
  server.close();
}
