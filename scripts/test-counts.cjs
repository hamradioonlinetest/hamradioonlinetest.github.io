const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { test } = require('node:test');
const { runInNewContext } = require('node:vm');

const html = readFileSync(join(__dirname, '../counts/index.html'), 'utf8');
const inline = html.split('<script>')[1]?.split('</script>')[0];
assert.ok(inline, 'counts page must contain the inline counts controller');

const header = 'Exam Date,Exam Time,Exam Level,VEs Attending,VEs Participating,VEC';
const fixture = [
  header,
  '2026-02-03,19:00,Technician,2,K2ABC;N2XYZ,ARRL',
  '2026-02-03,19:30,Technician,2,K2ABC;N2XYZ,ARRL',
  '2026-02-03,20:00,Technician,1,K2ABC,SANDARC',
  '2026-02-04,19:00,Technician,1,K2ABC,SANDARC',
  '2026-02-05,19:00,Technician,1,N2XYZ,ARRL',
  '2026-02-05,22:30,Technician,1,N2XYZ,ARRL',
  '2026-02-09,19:00,Technician,1,K3AAA,ARRL',
  '2026-10-20,19:00,Technician,1,K3AAA,SANDARC'
].join('\n');

async function load(csv) {
  const elements = Object.fromEntries(
    ['tbody', 'status', 'fetchedAt', 'veCount', 'totalSessions', 'refreshBtn']
      .map(id => [id, { textContent: '', innerHTML: '', addEventListener() {} }])
  );
  const fixedNow = Date.parse('2026-10-15T16:00:00Z');
  class Clock extends Date {
    constructor(...args) { super(...(args.length ? args : [fixedNow])); }
    static now() { return fixedNow; }
  }
  runInNewContext(inline, {
    document: { getElementById: id => elements[id] },
    fetch: async () => ({ ok: true, text: async () => csv }),
    Date: Clock,
    console
  });
  await new Promise(resolve => setImmediate(resolve));
  return elements;
}

function displayedRows(nodes) {
  const pattern = /<tr><td class="mono">([^<]+)<\/td><td class="center mono">(\d+)<\/td><td class="center mono">(\d+)<\/td><td class="center mono">(\d+)<\/td><\/tr>/g;
  return [...nodes.tbody.innerHTML.matchAll(pattern)].map(([, call, arrl, sandarc, total]) =>
    [call, Number(arrl), Number(sandarc), Number(total)]);
}

test('ARRL and SANDARC each count one VE session per three-hour cluster', async () => {
  const nodes = await load(fixture);
  assert.deepEqual(displayedRows(nodes), [
    ['N2XYZ', 3, 0, 3],
    ['K2ABC', 1, 2, 3],
    ['K3AAA', 1, 0, 1]
  ]);
  assert.equal(nodes.veCount.textContent, '3');
  assert.equal(nodes.totalSessions.textContent, '6');
  assert.equal(nodes.status.textContent, 'Loaded.');
  assert.match(html, /aria-sort="descending">Total Sessions/);
  assert.doesNotMatch(html, /data-col=/);
});

test('VEC headers and names are case-insensitive; unrecognized VECs warn', async () => {
  const nodes = await load([
    header.replace('VEC', 'Volunteer Examiner Coordinator'),
    '2026-02-03,19:00,General,1,K2ABC,arrl vec',
    '2026-02-04,19:00,General,1,K2ABC,SANDARC VEC',
    '2026-02-05,19:00,General,1,K2ABC,UNKNOWN'
  ].join('\n'));
  assert.deepEqual(displayedRows(nodes), [['K2ABC', 1, 1, 2]]);
  assert.match(nodes.status.textContent, /Warning: 1 row\(s\).*excluded/);
});

test('missing VEC column does not mislabel or attribute sessions', async () => {
  const nodes = await load([
    'Exam Date,Exam Time,Exam Level,VEs Attending,VEs Participating',
    '2026-02-03,19:00,General,1,K2ABC'
  ].join('\n'));
  assert.equal(displayedRows(nodes).length, 0);
  assert.match(nodes.status.textContent, /Could not locate the VEC column/);
});

test('future sessions do not receive VE credit', async () => {
  const nodes = await load([
    header,
    '2026-10-20,19:00,General,1,K2ABC,ARRL'
  ].join('\n'));
  assert.equal(displayedRows(nodes).length, 0);
  assert.equal(nodes.totalSessions.textContent, '0');
});
