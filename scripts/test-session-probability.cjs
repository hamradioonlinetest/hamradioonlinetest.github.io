const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { test } = require('node:test');
const { runInNewContext } = require('node:vm');

const html = readFileSync(join(__dirname, '../sessions/index.html'), 'utf8');
const inline = html.split('<script>')[1]?.split('</script>')[0];
assert.ok(inline, 'sessions page must have its controller');

const HEADER = 'Exam Date,Exam Time,Exam Level,VEs Attending,VEs Participating,VEC';
const clockAt = '2026-11-01T17:00:00Z';

async function page(lines, clock = clockAt) {
  const now = Date.parse(clock);
  class FixedDate extends Date {
    constructor(...args) { super(...(args.length ? args : [now])); }
    static now() { return now; }
  }
  const elements = Object.fromEntries(
    ['tbody', 'statusText', 'refreshBtn', 'showPast', 'sortBadge',
     'probabilityWrap', 'registrationSummary', 'probStatusText', 'probRangeBadge',
     'timeZoneLabel', 'ind0', 'ind1', 'ind2', 'ind3', 'ind4'].map(id =>
       [id, { textContent: '', innerHTML: '', disabled: false, checked: false,
         addEventListener() {}, querySelectorAll() { return []; } }])
  );
  runInNewContext(inline, {
    document: {
      getElementById: id => elements[id],
      querySelectorAll: () => [],
      addEventListener() {}
    },
    window: { requestIdleCallback: callback => callback() },
    fetch: async () => ({ ok: true, text: async () => lines.join('\n') }),
    AbortController,
    Date: FixedDate,
    Intl,
    console,
    setTimeout
  });
  await new Promise(resolve => setImmediate(resolve));
  return elements;
}

test('registration shares count records, and weekday probability counts distinct days', async () => {
  const nodes = await page([
    HEADER,
    '2026-08-02,19:00,Technician,2,K2ABC,ARRL', // outside window
    '2026-08-03,19:00,Technician,2,K2ABC,ARRL',
    '2026-08-03,19:30,General,2,K2ABC,ARRL',
    '2026-08-04,19:00,Technician,2,K2ABC,SANDARC',
    '2026-08-04,19:30,General,2,K2ABC,SANDARC',
    '2026-10-31,19:00,Technician,2,K2ABC,ARRL',
    '2026-10-31,19:30,General,2,K2ABC,SANDARC',
    '2026-11-01,19:00,Technician,2,K2ABC,ARRL', // today, excluded
    '2026-11-02,19:00,Technician,2,K2ABC,ARRL', // future, excluded
    '2026-08-05,19:00,RESKED: General,2,K2ABC,ARRL',
    '2026-08-06,19:00,General,2,K2ABC,UNKNOWN'
  ]);
  assert.match(nodes.probRangeBadge.textContent, /Aug 3, 2026 to Oct 31, 2026/);
  assert.match(nodes.registrationSummary.innerHTML, /ARRL<\/th><td class="numeric">3<\/td><td class="numeric">50%/);
  assert.match(nodes.registrationSummary.innerHTML, /SANDARC<\/th><td class="numeric">3<\/td><td class="numeric">50%/);
  assert.match(nodes.registrationSummary.innerHTML, /Total<\/th><td class="numeric"><strong>6<\/strong>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Monday<\/th><td class="numeric">8%.*?\(1\/13\)/);
  assert.match(nodes.probabilityWrap.innerHTML, /Tuesday<\/th><td class="numeric">0%.*?\(0\/13\).*?8%.*?\(1\/13\)/);
  assert.match(nodes.probabilityWrap.innerHTML, /Sunday<\/th><td class="numeric">0%.*?\(0\/12\)/);
  assert.match(nodes.probStatusText.textContent, /1 unclassified record/);
  assert.doesNotMatch(html, /\$15|\bFree\b/);
});

test('zero registrations show zero weekday notification likelihood, not a made-up sample', async () => {
  const nodes = await page([HEADER, '2026-11-02,19:00,General,2,K2ABC,ARRL']);
  assert.match(nodes.registrationSummary.innerHTML, /ARRL<\/th><td class="numeric">0<\/td>/);
  assert.match(nodes.registrationSummary.innerHTML, /SANDARC<\/th><td class="numeric">0<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Monday<\/th><td class="numeric">0%.*?\(0\/13\)/);
  assert.match(nodes.probStatusText.textContent, /past 90 completed days/);
});

test('missing VEC header does not assign old records to ARRL', async () => {
  const nodes = await page([
    'Exam Date,Exam Time,Exam Level,VEs Attending,VEs Participating',
    '2026-10-31,19:00,Technician,2,K2ABC'
  ]);
  assert.match(nodes.registrationSummary.innerHTML, /VEC column unavailable/);
  assert.match(nodes.probabilityWrap.innerHTML, /VEC column unavailable/);
});

test('lookback uses Eastern calendar date even before midnight in another time zone', async () => {
  const nodes = await page([
    HEADER,
    '2026-10-30,19:00,Technician,2,K2ABC,ARRL',
    '2026-10-31,19:00,Technician,2,K2ABC,SANDARC'
  ], '2026-11-01T02:00:00Z'); // Still Oct 31 in New York
  assert.match(nodes.probRangeBadge.textContent, /Oct 30, 2026/);
  assert.match(nodes.registrationSummary.innerHTML, /ARRL<\/th><td class="numeric">1<\/td>/);
  assert.match(nodes.registrationSummary.innerHTML, /SANDARC<\/th><td class="numeric">0<\/td>/);
});
