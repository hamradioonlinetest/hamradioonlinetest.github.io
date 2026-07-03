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

const canonicalPaths = new Set(redirectPairs.map(([, destination]) => destination));
const expectedRedirects = new Map(redirectPairs);
const checkedPaths = [...new Set(redirectPairs.flat())];

async function loadSitemapUrls() {
  if (process.env.SEO_SITEMAP_URL) {
    const res = await fetch(process.env.SEO_SITEMAP_URL);
    return extractLocs(await res.text());
  }

  try {
    return extractLocs(await readFile(new URL('../sitemap.xml', import.meta.url), 'utf8'));
  } catch {
    const res = await fetch(`${baseUrl}/sitemap.xml`);
    return extractLocs(await res.text());
  }
}

function extractLocs(xml) {
  return new Set([...xml.matchAll(/<loc>\s*([^<]+?)\s*<\/loc>/gi)].map((match) => match[1].trim()));
}

function absoluteUrl(pathOrUrl) {
  return new URL(pathOrUrl, `${baseUrl}/`).toString();
}

function pathFromUrl(url) {
  return new URL(url).pathname;
}

function canonicalFromHtml(html) {
  return html.match(/<link\s+[^>]*rel=["']canonical["'][^>]*href=["']([^"']+)["'][^>]*>/i)?.[1]
    || html.match(/<link\s+[^>]*href=["']([^"']+)["'][^>]*rel=["']canonical["'][^>]*>/i)?.[1]
    || '';
}

function hasNoindex(html, xRobotsTag) {
  return /<meta\s+[^>]*(?:name=["'](?:robots|googlebot)["'][^>]*content=["'][^"']*noindex|content=["'][^"']*noindex[^"']*["'][^>]*name=["'](?:robots|googlebot)["'])/i.test(html)
    || /(?:^|,)\s*(?:noindex|none)\s*(?:,|$)/i.test(xRobotsTag || '');
}

let failures = 0;
const sitemapUrls = await loadSitemapUrls();

for (const path of checkedPaths) {
  const requestedUrl = absoluteUrl(path);
  const res = await fetch(requestedUrl, { redirect: 'follow' });
  const html = await res.text();
  const finalUrl = res.url;
  const finalPath = pathFromUrl(finalUrl);
  const xRobotsTag = res.headers.get('x-robots-tag') || '';
  const canonical = canonicalFromHtml(html);
  const noindex = hasNoindex(html, xRobotsTag);
  const inSitemap = sitemapUrls.has(requestedUrl) || sitemapUrls.has(finalUrl);
  const isCanonicalPath = canonicalPaths.has(path);

  console.log(`${requestedUrl}`);
  console.log(`  HTTP status: ${res.status}`);
  console.log(`  Final URL: ${finalUrl}`);
  console.log(`  Contains noindex / X-Robots-Tag none: ${noindex ? 'YES' : 'no'}`);
  console.log(`  X-Robots-Tag: ${xRobotsTag || '(none)'}`);
  console.log(`  Canonical: ${canonical || '(none)'}`);
  console.log(`  Appears in sitemap.xml: ${inSitemap ? 'yes' : 'no'}`);

  if (isCanonicalPath) {
    const expectedCanonical = absoluteUrl(path);
    if (res.status !== 200) failures++;
    if (finalPath !== path) failures++;
    if (noindex) failures++;
    if (canonical !== expectedCanonical) failures++;
    if (!sitemapUrls.has(expectedCanonical)) failures++;
  } else {
    const expectedDestination = expectedRedirects.get(path);
    if (finalPath !== expectedDestination) failures++;
    if (sitemapUrls.has(requestedUrl)) failures++;
  }
}

if (failures) {
  console.error(`SEO indexing verification failed with ${failures} issue(s).`);
  process.exit(1);
}

console.log('SEO indexing verification passed.');
