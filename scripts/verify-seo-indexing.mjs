#!/usr/bin/env node
import { readFile } from 'node:fs/promises';

const baseUrl = (process.env.SEO_BASE_URL || 'https://hamradioonlinetest.com').replace(/\/$/, '');
const redirectPairs = [
  ['/community/', '/ham-radio-mentoring-community/'],
  ['/after-you-pass/', '/after-you-pass-ham-radio-exam/'],
  ['/faq/', '/online-ham-radio-exam-faq/'],
  ['/checklist/', '/online-ham-radio-exam-checklist/'],
  ['/new-ham-starter-kit/', '/new-ham-radio-operator-starter-kit/'],
  ['/youth/', '/youth-ham-radio-exam/'],
  ['/fcc-frn-how-to/', '/how-to-get-fcc-frn-ham-radio/'],
  ['/online-exam-troubleshooting/', '/online-ham-radio-exam-troubleshooting/'],
];

const rootDir = new URL('../', import.meta.url);
const canonicalPaths = new Set(redirectPairs.map(([, destination]) => destination));
const expectedRedirects = new Map(redirectPairs);
const checkedPaths = [...new Set(redirectPairs.flat())];

async function loadSitemapUrls() {
  return extractLocs(await readFile(new URL('sitemap.xml', rootDir), 'utf8'));
}

async function loadRedirects() {
  const redirects = new Map();
  const text = await readFile(new URL('_redirects', rootDir), 'utf8');

  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    const [from, to, status] = trimmed.split(/\s+/);
    redirects.set(normalizePath(from), { to: normalizePath(to), status });
  }

  return redirects;
}

async function loadHtml(path) {
  const filePath = path === '/' ? 'index.html' : `${path.replace(/^\//, '')}index.html`;
  return readFile(new URL(filePath, rootDir), 'utf8');
}

function extractLocs(xml) {
  return new Set([...xml.matchAll(/<loc>\s*([^<]+?)\s*<\/loc>/gi)].map((match) => match[1].trim()));
}

function absoluteUrl(pathOrUrl) {
  return new URL(pathOrUrl, `${baseUrl}/`).toString();
}

function normalizePath(path) {
  return `/${String(path).replace(/^\//, '').replace(/\/?$/, '/')}`;
}

function canonicalFromHtml(html) {
  return html.match(/<link\s+[^>]*rel=["']canonical["'][^>]*href=["']([^"']+)["'][^>]*>/i)?.[1]
    || html.match(/<link\s+[^>]*href=["']([^"']+)["'][^>]*rel=["']canonical["'][^>]*>/i)?.[1]
    || '';
}

function hasNoindex(html, xRobotsTag = '') {
  return /<meta\s+[^>]*(?:name=["'](?:robots|googlebot)["'][^>]*content=["'][^"']*noindex|content=["'][^"']*noindex[^"']*["'][^>]*name=["'](?:robots|googlebot)["'])/i.test(html)
    || /(?:^|,)\s*(?:noindex|none)\s*(?:,|$)/i.test(xRobotsTag);
}

let failures = 0;
const sitemapUrls = await loadSitemapUrls();
const redirects = await loadRedirects();

for (const path of checkedPaths) {
  const requestedUrl = absoluteUrl(path);
  const isCanonicalPath = canonicalPaths.has(path);

  console.log(`${requestedUrl}`);

  if (isCanonicalPath) {
    const expectedCanonical = absoluteUrl(path);
    const html = await loadHtml(path);
    const canonical = canonicalFromHtml(html);
    const noindex = hasNoindex(html);
    const inSitemap = sitemapUrls.has(expectedCanonical);

    console.log('  Source: local HTML');
    console.log('  Expected status: 200');
    console.log(`  Contains noindex: ${noindex ? 'YES' : 'no'}`);
    console.log(`  Canonical: ${canonical || '(none)'}`);
    console.log(`  Appears in sitemap.xml: ${inSitemap ? 'yes' : 'no'}`);

    if (noindex) failures++;
    if (canonical !== expectedCanonical) failures++;
    if (!inSitemap) failures++;
  } else {
    const expectedDestination = expectedRedirects.get(path);
    const redirect = redirects.get(path);
    const redirectMatches = redirect?.to === expectedDestination && redirect?.status === '301';
    const inSitemap = sitemapUrls.has(requestedUrl);

    console.log('  Source: local _redirects');
    console.log(`  Redirect: ${redirect ? `${redirect.to} ${redirect.status || ''}`.trim() : '(none)'}`);
    console.log(`  Expected redirect: ${expectedDestination} 301`);
    console.log(`  Appears in sitemap.xml: ${inSitemap ? 'yes' : 'no'}`);

    if (!redirectMatches) failures++;
    if (inSitemap) failures++;
  }
}

if (failures) {
  console.error(`SEO indexing verification failed with ${failures} issue(s).`);
  process.exit(1);
}

console.log('SEO indexing verification passed.');
