#!/usr/bin/env python3
"""Two independent HamStudy VEC feeds, merged scheduling, and safe fallbacks."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

from hamstudy_sessions import (
    SOURCE, SANDARC_SOURCE, parse_listing, validate_snapshot, load_snapshot,
    render_combined_schedule,
)

NOW = datetime(2026, 10, 9, 22, tzinfo=timezone.utc)
BASE = int((NOW + timedelta(days=3)).timestamp() * 1000)


def markup(team, start=BASE, url_id='abcdefabcdefabcdefabcdef', state='open'):
    return (f'<h1>Upcoming online / remote sessions from {team}</h1>'
            f'<div class="schedule"><div data-teamId="{team}">'
            f'<a class="session-entry {state}" href="/sessions/{url_id}/1">'
            f'<span class="session-time" data-time="{start}" data-duration="7200">Test</span>'
            '</a></div></div>')


def cache(team='WEARC', start=BASE, url_id='abcdefabcdefabcdefabcdef', checked=NOW):
    source = SOURCE if team == 'WEARC' else SANDARC_SOURCE
    return {'version': 1, 'source': source, 'fetched_at': checked.isoformat(),
            'sessions': parse_listing(markup(team, start, url_id), team)}


class CombinedSessionTests(unittest.TestCase):
    def test_parse_both_teams_and_reject_cross_team_entries(self):
        self.assertEqual(len(parse_listing(markup('WEARC'))), 1)
        self.assertEqual(len(parse_listing(markup('W2EF'), 'W2EF')), 1)
        for team, other in [('WEARC', 'W2EF'), ('W2EF', 'WEARC')]:
            with self.subTest(team=team), self.assertRaises(ValueError):
                parse_listing(markup(other), team)

    def test_two_feeds_sorted_labelled_and_still_distinct_same_datetime(self):
        one = cache(start=BASE + 10_000, url_id='aaaaaaaaaaaaaaaaaaaaaaaa')
        two = cache('W2EF', BASE, url_id='bbbbbbbbbbbbbbbbbbbbbbbb')
        output = render_combined_schedule({'ARRL VEC': one, 'SANDARC VEC': two}, NOW)
        self.assertEqual(output.count('<li data-session-start='), 2)
        self.assertLess(output.index('SANDARC VEC · Free exam'), output.index('ARRL VEC · $15'))
        self.assertIn('data-session-expires-at=', output)
        self.assertIn('https://hamstudy.org/sessions/bbbbbbbbbbbbbbbbbbbbbbbb/1', output)
        self.assertIn('https://hamstudy.org/sessions/aaaaaaaaaaaaaaaaaaaaaaaa/1', output)
        same = cache('W2EF', BASE + 10_000, url_id='cccccccccccccccccccccccc')
        together = render_combined_schedule({'ARRL VEC': one, 'SANDARC VEC': same}, NOW)
        self.assertEqual(together.count('<li data-session-start='), 2)

    def test_duplicate_appointment_url_is_only_displayed_once(self):
        single = cache()
        output = render_combined_schedule({'ARRL VEC': single, 'SANDARC VEC': {
            **single, 'source': SANDARC_SOURCE}}, NOW)
        self.assertEqual(output.count('<li data-session-start='), 1)

    def test_independent_fetch_failures_do_not_hide_other_teams(self):
        arrl = cache()
        only_arrl = render_combined_schedule({'ARRL VEC': arrl, 'SANDARC VEC': None}, NOW)
        self.assertIn('ARRL VEC · $15', only_arrl)
        self.assertNotIn('SANDARC VEC · Free exam', only_arrl)
        self.assertIn('sessions/W2EF/remote', only_arrl)
        only_w2ef = render_combined_schedule({'ARRL VEC': None, 'SANDARC VEC':
            cache('W2EF', BASE, url_id='dddddddddddddddddddddddd')}, NOW)
        self.assertIn('SANDARC VEC · Free exam', only_w2ef)
        self.assertNotIn('ARRL VEC · $15', only_w2ef)
        self.assertIn('sessions/WEARC/remote', only_w2ef)

    def test_cache_storage_and_fallback_independent(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            arrl_cache = path / 'arrl.json'
            w2ef_cache = path / 'w2ef.json'
            a = path / 'arrl.html'
            w = path / 'w2ef.html'
            a.write_text(markup('WEARC'))
            w.write_text(markup('W2EF', BASE + 1000, 'cccccccccccccccccccccccc'))
            arrl = load_snapshot(arrl_cache, NOW, a)
            other = load_snapshot(w2ef_cache, NOW, w, source=SANDARC_SOURCE, team_id='W2EF')
            self.assertEqual(arrl['source'], SOURCE)
            self.assertEqual(other['source'], SANDARC_SOURCE)
            with patch('hamstudy_sessions.fetch_listing', side_effect=URLError('offline')):
                self.assertEqual(load_snapshot(w2ef_cache, NOW + timedelta(hours=10),
                    source=SANDARC_SOURCE, team_id='W2EF'), other)
            self.assertEqual(json.loads(arrl_cache.read_text()), arrl)
            self.assertEqual(json.loads(w2ef_cache.read_text()), other)
            with self.assertRaises(ValueError):
                validate_snapshot(other, NOW, SOURCE)

    def test_expired_one_source_retains_other_and_limits_rows(self):
        old = cache(checked=NOW - timedelta(hours=49))
        fresh = cache('W2EF', BASE + 1000, 'cccccccccccccccccccccccc')
        output = render_combined_schedule({'ARRL VEC': old, 'SANDARC VEC': fresh}, NOW)
        self.assertEqual(output.count('<li data-session-start='), 1)
        self.assertIn('SANDARC VEC · Free exam', output)
        expired = render_combined_schedule({'ARRL VEC': old, 'SANDARC VEC': None}, NOW)
        self.assertEqual(expired.count('<li data-session-start='), 0)
        self.assertIn('data-session-fallback>', expired)
        self.assertNotIn('No sessions available', expired)
        multiple = cache()
        multiple['sessions'] *= 6
        self.assertLessEqual(render_combined_schedule({'ARRL VEC': multiple}, NOW, 3).count('<li data-session-start='), 3)

    def test_healthy_feed_is_rendered_beyond_initial_display_limit(self):
        old = cache(checked=NOW - timedelta(hours=40))
        fresh = cache('W2EF', checked=NOW)
        old['sessions'] = [
            cache(start=BASE + i * 60_000, url_id=f'{i + 100:024x}')['sessions'][0]
            for i in range(6)
        ]
        fresh['sessions'] = [
            cache('W2EF', BASE + (i + 6) * 60_000, f'{i + 200:024x}')['sessions'][0]
            for i in range(6)
        ]
        html = render_combined_schedule({'ARRL VEC': old, 'SANDARC VEC': fresh}, NOW, 6)
        self.assertIn('data-session-limit="6"', html)
        self.assertEqual(html.count('<li data-session-start='), 12)
        self.assertEqual(html.count('ARRL VEC · $15'), 6)
        self.assertEqual(html.count('SANDARC VEC · Free exam'), 6)
        self.assertEqual(html.count('<li data-session-start=') - html.count(' hidden><div><time'), 6)
        # The reserve entries follow the six earlier ARRL rows but retain
        # the later expiration of the healthy W2EF cache.
        self.assertLess(html.index('ARRL VEC · $15'), html.index('SANDARC VEC · Free exam'))
        expiry = int((NOW + timedelta(hours=48)).timestamp() * 1000)
        self.assertIn(f'data-session-expires-at="{expiry}" hidden>', html)

    def test_feed_specific_cap_also_applies_to_registration_page(self):
        old = cache()
        newer = cache('W2EF', BASE + 1, 'bbbbbbbbbbbbbbbbbbbbbbbb')
        old['sessions'] = [
            cache(start=BASE + i * 60_000, url_id=f'{i + 50:024x}')['sessions'][0]
            for i in range(5)
        ]
        html = render_combined_schedule({'ARRL VEC': old, 'SANDARC VEC': newer}, NOW, 3)
        self.assertEqual(html.count('<li data-session-start='), 4)
        self.assertIn('data-session-limit="3"', html)
        self.assertEqual(html.count(' hidden><div><time'), 1)
        self.assertIn('SANDARC VEC · Free exam', html)

    def test_invalid_urls_and_source_tags_rejected(self):
        bad = cache('W2EF')
        bad['sessions'][0]['url'] = 'javascript:alert(1)'
        with self.assertRaises(ValueError):
            validate_snapshot(bad, NOW, SANDARC_SOURCE)
        fail = render_combined_schedule({'SANDARC VEC': bad}, NOW)
        self.assertNotIn('<li data-session-start=', fail)


if __name__ == '__main__':
    unittest.main()
