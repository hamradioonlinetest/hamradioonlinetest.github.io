const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { test } = require('node:test');
const { runInNewContext } = require('node:vm');

const main = readFileSync(join(__dirname, '../assets/js/main.js'), 'utf8');
const HOUR = 60 * 60 * 1000;
const fetchedAt = Date.parse('2026-10-06T10:26:05Z');

function display(age, starts = [fetchedAt + 13 * HOUR, fetchedAt + 60 * HOUR], expiries = []) {
  let now = fetchedAt + age * HOUR;
  const rows = starts.map((start, index) => ({ dataset: { sessionStart: String(start), ...(expiries[index] === undefined ? {} : { sessionExpiresAt: String(expiries[index]) }) }, hidden: false }));
  const elements = Object.fromEntries(['list', 'fallback', 'checked', 'stale-warning'].map(name => [name, { hidden: false }]));
  const schedule = {
    dataset: { freshUntil: String(fetchedAt + 6 * HOUR), expiresAt: String(fetchedAt + 48 * HOUR) },
    querySelectorAll: () => rows,
    querySelector: selector => elements[selector.slice('[data-session-'.length, -1)],
  };
  let refresh;
  let onVisibility;
  runInNewContext(main, {
    Date: { now: () => now },
    document: {
      querySelector: selector => selector === '[data-session-schedule]' ? schedule : null,
      addEventListener: (event, callback) => { onVisibility = callback; },
    },
    setInterval: callback => { refresh = callback; },
  });
  return { rows, elements, schedule, advance(hours, visibility = false) {
    now = fetchedAt + hours * HOUR;
    (visibility ? onVisibility : refresh)();
  } };
}

test('six-hour boundary adds notice without hiding upcoming sessions', () => {
  const view = display(5);
  assert.equal(view.elements['stale-warning'].hidden, true);
  view.advance(6);
  assert.equal(view.elements['stale-warning'].hidden, false);
  assert.equal(view.elements.checked.hidden, false);
  assert.equal(view.elements.fallback.hidden, true);
  assert.ok(view.rows.every(row => !row.hidden));
});

test('delayed builds retain future dates and hide started sessions', () => {
  const view = display(7);
  assert.ok(view.rows.every(row => !row.hidden));
  view.advance(13, true);
  assert.equal(view.rows[0].hidden, true);
  assert.equal(view.rows[1].hidden, false);
  assert.equal(view.elements.list.hidden, false);
  assert.equal(view.elements.fallback.hidden, true);
});

test('48-hour boundary hides entire snapshot and shows fallback', () => {
  const view = display(47);
  assert.equal(view.rows[1].hidden, false);
  view.advance(48);
  assert.ok(view.rows.every(row => row.hidden));
  assert.equal(view.elements.list.hidden, true);
  assert.equal(view.elements.fallback.hidden, false);
  assert.equal(view.elements.checked.hidden, true);
  assert.equal(view.elements['stale-warning'].hidden, true);
});

test('all started sessions show fallback even with fresh snapshot', () => {
  const view = display(1, [fetchedAt]);
  assert.equal(view.elements.list.hidden, true);
  assert.equal(view.elements.fallback.hidden, false);
});

test('invalid expiry fails closed', () => {
  const view = display(1);
  view.schedule.dataset.expiresAt = 'invalid';
  view.advance(2);
  assert.ok(view.rows.every(row => row.hidden));
  assert.equal(view.elements.fallback.hidden, false);
});

test('one expired VEC feed does not hide sessions from the healthy feed', () => {
  const view = display(24,
    [fetchedAt + 60 * HOUR, fetchedAt + 60 * HOUR],
    [fetchedAt + 12 * HOUR, fetchedAt + 48 * HOUR]);
  assert.equal(view.rows[0].hidden, true);
  assert.equal(view.rows[1].hidden, false);
  assert.equal(view.elements.fallback.hidden, true);
});

test('all source-specific expiries hide schedule and display direct fallback', () => {
  const view = display(24,
    [fetchedAt + 60 * HOUR, fetchedAt + 60 * HOUR],
    [fetchedAt + 12 * HOUR, fetchedAt + 18 * HOUR]);
  assert.equal(view.rows[0].hidden, true);
  assert.equal(view.rows[1].hidden, true);
  assert.equal(view.elements.fallback.hidden, false);
});
