"""Read the public WEARC remote listing. No login or private candidate data.

HamStudy publishes epoch-millisecond timestamps in its server-rendered HTML.
This adapter deliberately fails closed when that page contract changes.
"""
from datetime import datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from http.client import IncompleteRead
import json
import re
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from time import sleep
from zoneinfo import ZoneInfo

SOURCE = 'https://hamstudy.org/sessions/WEARC/remote'
SANDARC_SOURCE = 'https://hamstudy.org/sessions/W2EF/remote'
SOURCES = {'ARRL VEC': SOURCE, 'SANDARC VEC': SANDARC_SOURCE}
TEAM_IDS = {'ARRL VEC': 'WEARC', 'SANDARC VEC': 'W2EF'}
FRESH_AGE = timedelta(hours=6)
MAX_AGE = timedelta(hours=48)
EASTERN = ZoneInfo('America/New_York')


class ScheduleParser(HTMLParser):
    def __init__(self, team_id='WEARC'):
        super().__init__()
        self.team_id = team_id
        self.stack = []
        self.active = None
        self.entries = []
        self.headings = []
        self.in_heading = False
        self.saw_schedule = False
        self.entry_count = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get('class', '').split()
        if tag == 'div':
            self.stack.append(attrs)
            if 'schedule' in classes:
                self.saw_schedule = True
        if tag == 'h1':
            self.in_heading = True
        if tag == 'a' and 'session-entry' in classes:
            self.entry_count += 1
            team = next((a.get('data-teamid') for a in reversed(self.stack) if 'data-teamid' in a), None)
            href = attrs.get('href', '')
            if team != self.team_id or not re.fullmatch(r'/sessions/[a-f0-9]{24}(?:/\d+)?', href):
                raise ValueError('Unexpected team or session URL in HamStudy listing')
            self.active = {'url': 'https://hamstudy.org' + href, 'open': 'open' in classes and 'full' not in classes}
        if tag == 'span' and 'session-time' in classes and self.active is not None:
            start = int(attrs['data-time'])
            duration = int(attrs['data-duration'])
            if not 0 < duration <= 86400:
                raise ValueError('Invalid session duration')
            datetime.fromtimestamp(start / 1000, timezone.utc)  # validate timestamp
            self.active.update(start=start, duration=duration)

    def handle_data(self, value):
        if self.in_heading:
            self.headings.append(value)

    def handle_endtag(self, tag):
        if tag == 'div' and self.stack:
            self.stack.pop()
        if tag == 'h1':
            self.in_heading = False
        if tag == 'a' and self.active is not None:
            if 'start' not in self.active:
                raise ValueError('Missing HamStudy machine-readable session time')
            self.entries.append(self.active)
            self.active = None


def parse_listing(html, team_id='WEARC'):
    parser = ScheduleParser(team_id)
    parser.feed(html)
    parser.close()
    if f'Upcoming online / remote sessions from {team_id}' not in ' '.join(parser.headings):
        raise ValueError('Unexpected HamStudy page (missing WEARC remote heading)')
    if not parser.saw_schedule or parser.active is not None:
        raise ValueError('Incomplete HamStudy schedule')
    # An empty/changed response must never overwrite a working cache.
    # Fallback wording deliberately does not claim there are no sessions.
    if not parser.entries:
        raise ValueError('No recognizable session entries; use HamStudy directly')
    unique = {entry['url']: entry for entry in parser.entries}
    return sorted(unique.values(), key=lambda entry: entry['start'])


def validate_snapshot(snapshot, now, source=SOURCE):
    fetched = datetime.fromisoformat(snapshot['fetched_at'])
    if fetched.tzinfo is None or not timedelta(0) <= now - fetched < MAX_AGE:
        raise ValueError('Schedule snapshot is stale or future-dated')
    if snapshot.get('source') != source or snapshot.get('version') != 1:
        raise ValueError('Unexpected schedule cache format')
    for entry in snapshot['sessions']:
        if not re.fullmatch(r'https://hamstudy.org/sessions/[a-f0-9]{24}(?:/\d+)?', entry['url']):
            raise ValueError('Unexpected cached link')
        if type(entry['start']) is not int or type(entry['duration']) is not int or type(entry['open']) is not bool:
            raise ValueError('Invalid cached session')
        if not 0 < entry['duration'] <= 86400:
            raise ValueError('Invalid cached duration')
    return snapshot


def fetch_listing(source=SOURCE):
    request = Request(source, headers={'User-Agent': 'WEARC-Schedule/1.0 (+https://hamradioonlinetest.com/)', 'Accept': 'text/html'})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=25) as response:
                if response.status != 200 or 'text/html' not in response.headers.get('Content-Type', ''):
                    raise ValueError('Unexpected HamStudy HTTP response')
                body = response.read(2_000_001)
                if len(body) > 2_000_000:
                    raise ValueError('HamStudy response too large')
                return body.decode('utf-8')
        except (URLError, TimeoutError, ConnectionError, IncompleteRead) as exc:
            if isinstance(exc, HTTPError) and exc.code != 429 and not 500 <= exc.code < 600:
                raise
            if attempt == 2:
                raise
            sleep(attempt + 1)


def load_snapshot(cache, now, fixture=None, source=SOURCE, team_id='WEARC'):
    try:
        if fixture:
            html = fixture.read_text(encoding='utf-8')
        else:
            html = fetch_listing(source) if source != SOURCE else fetch_listing()
        snapshot = {'version': 1, 'source': source, 'fetched_at': now.isoformat(), 'sessions': parse_listing(html, team_id)}
        validate_snapshot(snapshot, now, source)
        cache.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache.with_suffix('.tmp')
        temporary.write_text(json.dumps(snapshot), encoding='utf-8')
        temporary.replace(cache)
        print(f"HamStudy: refreshed {len(snapshot['sessions'])} published session entries")
        return snapshot
    except Exception as exc:
        print(f'HamStudy refresh unavailable: {exc}', file=sys.stderr)
        try:
            snapshot = validate_snapshot(json.loads(cache.read_text(encoding='utf-8')), now, source)
            print(f"HamStudy: using cached schedule checked {snapshot['fetched_at']}", file=sys.stderr)
            return snapshot
        except (OSError, ValueError, KeyError, TypeError):
            print('HamStudy: displaying direct schedule link only', file=sys.stderr)
            return None


def render_schedule(snapshot, now):
    fallback = 'For current dates and availability, view the online session list on HamStudy.'
    if snapshot is None:
        return f'<p>{fallback}</p>'
    try:
        validate_snapshot(snapshot, now)
    except (ValueError, KeyError, TypeError):
        return f'<p>{fallback}</p>'
    fetched = datetime.fromisoformat(snapshot['fetched_at'])
    fresh_until = int((fetched + FRESH_AGE).timestamp() * 1000)
    expires = int((fetched + MAX_AGE).timestamp() * 1000)
    sessions = [s for s in snapshot['sessions'] if s['open'] and s['start'] > now.timestamp()*1000][:6]
    rows = []
    for session in sessions:
        start = datetime.fromtimestamp(session['start']/1000, EASTERN)
        end = start + timedelta(seconds=session['duration'])
        date = start.strftime('%A, %B ') + str(start.day) + start.strftime(', %Y')
        clock = start.strftime('%I:%M %p').lstrip('0') + '–' + end.strftime('%I:%M %p %Z').lstrip('0')
        rows.append(f'<li data-session-start="{session["start"]}"><div><time datetime="{start.isoformat()}">{date}</time><span class="session-clock">{clock}</span></div><a class="cta secondary" href="{escape(session["url"], quote=True)}" target="_blank" rel="noopener" aria-label="View session on {date} at {escape(clock)}">View session</a></li>')
    hidden = ' hidden' if sessions else ''
    checked = fetched.astimezone(EASTERN).strftime('%b %d, %Y at %I:%M %p %Z')
    warning_hidden = ' hidden' if now - fetched < FRESH_AGE else ''
    return f'''<div data-session-schedule data-fresh-until="{fresh_until}" data-expires-at="{expires}">
      <ul class="session-list" data-session-list>{''.join(rows)}</ul>
      <p data-session-fallback{hidden}>{fallback}</p>
      <p class="notice" data-session-checked>Schedule checked {checked}. Registration and availability are confirmed on HamStudy. <span data-session-stale-warning{warning_hidden}>These dates may have changed since the last check. Confirm current dates and availability on HamStudy.</span></p>
    </div>'''


def render_combined_schedule(snapshots, now, limit=6):
    """Merge two independently validated HamStudy feeds without hiding a healthy feed.

    Keep `limit` per source in chronological order; JavaScript initially shows
    only the first `limit` rows and promotes healthy hidden candidates when
    another source expires or its sessions start. Each entry carries its VEC
    and independent cache expiry. Registration links to the HamStudy session.
    """
    entries = {}
    checks = []
    for vec in ('ARRL VEC', 'SANDARC VEC'):
        source = SOURCES[vec]
        snapshot = snapshots.get(vec)
        if snapshot is None:
            continue
        try:
            validate_snapshot(snapshot, now, source)
        except (ValueError, KeyError, TypeError, OverflowError):
            continue
        fetched = datetime.fromisoformat(snapshot['fetched_at'])
        expiry = int((fetched + MAX_AGE).timestamp() * 1000)
        fresh = int((fetched + FRESH_AGE).timestamp() * 1000)
        checks.append((vec, fetched, expiry, fresh))
        for item in snapshot['sessions']:
            if not item['open'] or item['start'] <= now.timestamp() * 1000:
                continue
            # Deduplicate by actual HamStudy appointment, never by date/time:
            # multiple distinct sessions can legitimately start together.
            entries.setdefault(item['url'], {**item, 'vec': vec, 'expiry': expiry})
    # Keep up to `limit` candidates from *each* VEC. If the first `limit`
    # chronological rows all come from the older cache, the other feed still
    # needs its later sessions in the HTML when those first rows expire.
    # The browser shows no more than `limit` currently eligible rows.
    ordered = sorted(entries.values(), key=lambda s: (s['start'], s['vec'], s['url']))
    candidates = []
    by_vec = {vec: 0 for vec in SOURCES}
    for item in ordered:
        vec = item['vec']
        if by_vec[vec] < limit:
            candidates.append(item)
            by_vec[vec] += 1
    fallback = ('For current dates and availability, choose the '
                '<a href="https://hamstudy.org/sessions/WEARC/remote" target="_blank" rel="noopener">ARRL VEC</a> '
                'or <a href="https://hamstudy.org/sessions/W2EF/remote" target="_blank" rel="noopener">SANDARC VEC</a> '
                'listing on HamStudy.')
    rows = []
    for index, session in enumerate(candidates):
        start = datetime.fromtimestamp(session['start'] / 1000, EASTERN)
        end = start + timedelta(seconds=session['duration'])
        date = start.strftime('%A, %B ') + str(start.day) + start.strftime(', %Y')
        clock = start.strftime('%I:%M %p').lstrip('0') + '–' + end.strftime('%I:%M %p %Z').lstrip('0')
        label = session['vec']
        fee = '$15 standard / $5 under 18' if label == 'ARRL VEC' else 'Free exam'
        rows.append(
            f'<li data-session-start="{session["start"]}" data-session-expires-at="{session["expiry"]}"'
            f'{" hidden" if index >= limit else ""}>'
            f'<div><time datetime="{start.isoformat()}">{date}</time>'
            f'<span class="session-clock">{clock}</span>'
            f'<span class="session-vec">{label} · {fee}</span></div>'
            f'<a class="cta secondary" href="{escape(session["url"], quote=True)}" '
            f'target="_blank" rel="noopener" '
            f'aria-label="Register with {label} on {date} at {escape(clock)}">View session</a></li>')
    # Per-feed expiry is applied to each row on the client, so a stale or
    # unavailable W2EF feed can never hide otherwise healthy WEARC sessions.
    latest_expiry = max((x[2] for x in checks), default=0)
    earliest_fresh = min((x[3] for x in checks), default=0)
    checked = ' · '.join(
        vec + ': ' + fetched.astimezone(EASTERN).strftime('%b %d at %I:%M %p %Z')
        for vec, fetched, _, _ in checks
    )
    warning_hidden = ' hidden' if checks and now.timestamp() * 1000 < earliest_fresh else ''
    no_rows = ' hidden' if candidates else ''
    return (f'<div data-session-schedule data-session-limit="{limit}" '
            f'data-fresh-until="{earliest_fresh}" data-expires-at="{latest_expiry}">'
            f'<ul class="session-list" data-session-list{"" if candidates else " hidden"}>{"".join(rows)}</ul>'
            f'<p data-session-fallback{no_rows}>{fallback}</p>'
            f'<p class="notice" data-session-checked{"" if checks else " hidden"}>'
            f'Schedule checked: {escape(checked)}. Registration and availability are confirmed on HamStudy. '
            f'<span data-session-stale-warning{warning_hidden}>Some dates may have changed since the last check. '
            f'Confirm availability on HamStudy.</span></p>'
            f'</div>')
