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



test('ARRL uses the full 90 days, SANDARC starts October 15, and cells contain percentages only', async () => {
  const nodes = await page([
    HEADER,
    '2026-08-02,19:00,Technician,2,K2ABC,ARRL', // before 90-day window
    '2026-08-03,19:00,Technician,2,K2ABC,ARRL', // older ARRL Monday: included for weekday probability
    '2026-08-03,19:30,General,2,K2ABC,ARRL', // two registrations but one active Monday
    '2026-10-17,19:00,Technician,2,K2ABC,ARRL',
    '2026-10-17,19:30,General,2,K2ABC,ARRL',
    '2026-10-20,19:00,Technician,2,K2ABC,SANDARC',
    '2026-10-20,19:30,General,2,K2ABC,SANDARC',
    '2026-10-30,19:00,Technician,2,K2ABC,SANDARC',
    '2026-10-31,19:00,Technician,2,K2ABC,ARRL',
    '2026-10-31,19:30,General,2,K2ABC,SANDARC', // off-schedule SANDARC
    '2026-10-22,19:30,General,2,K2ABC,ARRL', // off-schedule ARRL
    '2026-10-24,19:00,RESKED: General,2,K2ABC,ARRL',
    '2026-10-23,19:00,General,2,K2ABC,UNKNOWN',
    '2026-11-01,19:00,Technician,2,K2ABC,ARRL', // current day excluded
    '2026-11-02,19:00,Technician,2,K2ABC,ARRL' // future excluded
  ]);
  assert.match(nodes.probRangeBadge.textContent, /Registration share: Oct 15, 2026 to Oct 31, 2026/);
  assert.doesNotMatch(nodes.probStatusText.textContent, /Weekday history/);
  // Registration shares remain on the common post-launch window, not the older ARRL-only data.
  assert.match(nodes.registrationSummary.innerHTML, /ARRL<\/th><td class="numeric">3<\/td><td class="numeric">50%/);
  assert.match(nodes.registrationSummary.innerHTML, /SANDARC<\/th><td class="numeric">3<\/td><td class="numeric">50%/);
  assert.match(nodes.registrationSummary.innerHTML, /Total<\/th><td class="numeric"><strong>6<\/strong>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Sunday<\/th><td class="numeric">0%<\/td><td class="numeric">—<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Monday<\/th><td class="numeric">8%<\/td><td class="numeric">—<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Tuesday<\/th><td class="numeric">—<\/td><td class="numeric">50%<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Wednesday<\/th><td colspan="2" class="center">No testing<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Thursday<\/th><td class="numeric">—<\/td><td class="numeric">0%<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Friday<\/th><td class="numeric">—<\/td><td class="numeric">33%<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Saturday<\/th><td class="numeric">15%<\/td><td class="numeric">—<\/td>/);
  assert.doesNotMatch(nodes.probabilityWrap.innerHTML, /\(\d+\/\d+\)|trend-hint/);
  assert.match(nodes.probStatusText.textContent, /1 unclassified record/);
  assert.match(nodes.probStatusText.textContent, /2 off-schedule record/);
  assert.doesNotMatch(html, /\$15|\bFree\b/);
});

test('old ARRL Mondays count toward weekday probability, but not current registration share', async () => {
  const nodes = await page([
    HEADER,
    '2026-08-02,19:00,General,2,K2ABC,ARRL', // outside lookback
    '2026-08-03,19:00,General,2,K2ABC,ARRL', // first day of lookback
    '2026-09-01,19:00,General,2,K2ABC,ARRL', // off-schedule before schedule started, ignored
    '2026-10-15,19:00,General,2,K2ABC,SANDARC'
  ]);
  assert.match(nodes.probabilityWrap.innerHTML, /Monday<\/th><td class="numeric">8%<\/td><td class="numeric">—<\/td>/);
  assert.match(nodes.registrationSummary.innerHTML, /ARRL<\/th><td class="numeric">0<\/td><td class="numeric">0%/);
  assert.match(nodes.registrationSummary.innerHTML, /SANDARC<\/th><td class="numeric">1<\/td><td class="numeric">100%/);
  assert.doesNotMatch(nodes.probStatusText.textContent, /off-schedule/);
});

test('zero activity reports zero percent only on the assigned testing weekdays', async () => {
  const nodes = await page([HEADER, '2026-11-02,19:00,General,2,K2ABC,ARRL']);
  assert.match(nodes.registrationSummary.innerHTML, /ARRL<\/th><td class="numeric">0<\/td>/);
  assert.match(nodes.registrationSummary.innerHTML, /SANDARC<\/th><td class="numeric">0<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Monday<\/th><td class="numeric">0%<\/td><td class="numeric">—<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Tuesday<\/th><td class="numeric">—<\/td><td class="numeric">0%<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Wednesday<\/th><td colspan="2" class="center">No testing<\/td>/);
  assert.doesNotMatch(nodes.probabilityWrap.innerHTML, /\(\d+\/\d+\)/);
});

test('missing VEC header refuses to assign old records to ARRL', async () => {
  const nodes = await page([
    'Exam Date,Exam Time,Exam Level,VEs Attending,VEs Participating',
    '2026-10-31,19:00,Technician,2,K2ABC'
  ]);
  assert.match(nodes.registrationSummary.innerHTML, /VEC column unavailable/);
  assert.match(nodes.probabilityWrap.innerHTML, /VEC column unavailable/);
});

test('lookback uses Eastern dates near UTC midnight', async () => {
  const nodes = await page([
    HEADER,
    '2026-10-25,19:00,Technician,2,K2ABC,ARRL',
    '2026-10-30,19:00,Technician,2,K2ABC,SANDARC',
    '2026-10-31,19:00,Technician,2,K2ABC,ARRL'
  ], '2026-11-01T02:00:00Z'); // October 31 in New York
  assert.match(nodes.probRangeBadge.textContent, /Registration share: Oct 15, 2026 to Oct 30, 2026/);
  assert.equal(nodes.probStatusText.textContent, "");
  assert.match(nodes.registrationSummary.innerHTML, /ARRL<\/th><td class="numeric">1<\/td>/);
  assert.match(nodes.registrationSummary.innerHTML, /SANDARC<\/th><td class="numeric">1<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Saturday<\/th><td class="numeric">0%<\/td>/);
});

test('once SANDARC has 90 days both probability windows roll forward equally', async () => {
  const nodes = await page([
    HEADER,
    '2026-10-15,19:00,Technician,2,K2ABC,SANDARC', // aged out
    '2026-10-17,19:00,Technician,2,K2ABC,ARRL', // aged out
    '2027-02-26,19:00,General,2,K2ABC,SANDARC',
    '2027-02-27,19:00,General,2,K2ABC,ARRL'
  ], '2027-03-01T17:00:00Z');
  assert.match(nodes.probRangeBadge.textContent, /Registration share: Dec 1, 2026 to Feb 28, 2027/);
  assert.equal(nodes.probStatusText.textContent, "");
  assert.match(nodes.registrationSummary.innerHTML, /SANDARC<\/th><td class="numeric">1<\/td>/);
  assert.match(nodes.registrationSummary.innerHTML, /ARRL<\/th><td class="numeric">1<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Friday<\/th><td class="numeric">—<\/td><td class="numeric">8%<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Saturday<\/th><td class="numeric">8%<\/td><td class="numeric">—<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Wednesday<\/th><td colspan="2" class="center">No testing<\/td>/);
});

test('unobserved weekdays have a dash, and Wednesday always has no testing', async () => {
  const nodes = await page([
    HEADER,
    '2026-10-15,19:00,General,2,K2ABC,SANDARC',
    '2026-10-14,19:00,General,2,K2ABC,ARRL'
  ], '2026-10-16T16:00:00Z');
  assert.match(nodes.probRangeBadge.textContent, /Registration share: Oct 15, 2026 to Oct 15, 2026/);
  assert.match(nodes.probabilityWrap.innerHTML, /Thursday<\/th><td class="numeric">—<\/td><td class="numeric">100%<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Wednesday<\/th><td colspan="2" class="center">No testing<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Friday<\/th><td class="numeric">—<\/td><td class="numeric">—<\/td>/);
  assert.doesNotMatch(nodes.probabilityWrap.innerHTML, /\(\d+\/\d+\)/);
});

test('public historical ARRL dates validate 25% Sunday, 31% Monday, 31% Saturday', async () => {
  // Exact distinct exam dates from the published VE Public dataset as of Nov 1, 2026.
  // Prior-to-Oct-15 ARRL Tuesday, Thursday, and Friday exams are present in the
  // fixture but must not change the three currently scheduled weekday rates.
  const arrlDates = [
    'Thursday, August 6, 2026',
    'Friday, August 7, 2026',
    'Saturday, August 8, 2026',
    'Tuesday, August 11, 2026',
    'Sunday, August 23, 2026',
    'Thursday, August 27, 2026',
    'Monday, August 31, 2026',
    'Thursday, September 3, 2026',
    'Saturday, September 5, 2026',
    'Thursday, September 10, 2026',
    'Saturday, September 12, 2026',
    'Sunday, September 20, 2026',
    'Friday, September 25, 2026',
    'Thursday, October 1, 2026',
    'Friday, October 2, 2026',
    'Monday, October 5, 2026',
    'Thursday, October 8, 2026',
    'Monday, October 12, 2026',
    'Tuesday, October 13, 2026',
    'Saturday, October 17, 2026',
    'Sunday, October 18, 2026',
    'Monday, October 19, 2026'
  ];
  assert.equal(arrlDates.length, 22);
  const nodes = await page([
    HEADER,
    ...arrlDates.map(date => '"' + date + '",7:30 PM,Technician,2,K2ABC,ARRL')
  ]);
  assert.match(nodes.probabilityWrap.innerHTML, /Sunday<\/th><td class="numeric">25%<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Monday<\/th><td class="numeric">31%<\/td>/);
  assert.match(nodes.probabilityWrap.innerHTML, /Saturday<\/th><td class="numeric">31%<\/td>/);
  assert.equal(nodes.probStatusText.textContent, "");
  assert.doesNotMatch(html, /Registration shares reflect the current schedule/);
  assert.doesNotMatch(html, /Weekday history:/);
  assert.match(html, /ARRL: Saturday, Sunday, and Monday/);
});
