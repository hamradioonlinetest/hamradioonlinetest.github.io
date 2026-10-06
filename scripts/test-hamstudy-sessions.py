#!/usr/bin/env python3
"""Regression coverage for third-party markup, time zones, and stale data."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from http.client import IncompleteRead
import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError
from hamstudy_sessions import SOURCE, fetch_listing, load_snapshot, parse_listing, render_schedule, validate_snapshot

NOW = datetime(2026, 10, 3, 14, tzinfo=timezone.utc)

def entry(start=1791156600000, status='open', team='WEARC', id='6aa3131c37fea0678f8c5ce8'):
    return f'''<div class="schedule-team-entry" data-teamId="{team}"><div class="session-row"><a class="session-entry {status}" href="/sessions/{id}/1"><span class="session-time allowMove" data-time="{start}" data-duration="7200">7:30-9:30pm EDT</span><span class="badge">3</span></a></div></div>'''

def page(content):
    return '<h1>Upcoming online / remote sessions from WEARC</h1><div class="schedule">'+content+'</div>'

def snapshot(content=None):
    return {'version': 1, 'source': SOURCE, 'fetched_at': NOW.isoformat(), 'sessions': parse_listing(page(content or entry()))}

class ScheduleTests(unittest.TestCase):
    def test_real_markup_extracts_epoch_and_link(self):
        data = parse_listing(page(entry()))
        self.assertEqual(data[0]['start'], 1791156600000)
        self.assertEqual(data[0]['url'], 'https://hamstudy.org/sessions/6aa3131c37fea0678f8c5ce8/1')
        self.assertEqual(data[0]['duration'], 7200)

    def test_rejects_wrong_team_page_and_changed_markup(self):
        for html in ['<h1>Login</h1>', page(entry(team='OTHER')), page(entry().replace('data-time=', 'changed=')), page('')]:
            with self.assertRaises((ValueError, KeyError)):
                parse_listing(html)

    def test_full_past_and_duplicates_are_not_advertised(self):
        content = entry()+entry()+entry(status='full',id='aaaaaaaaaaaaaaaaaaaaaaaa')+entry(start=1700000000000,id='bbbbbbbbbbbbbbbbbbbbbbbb')
        rendered = render_schedule(snapshot(content), NOW)
        self.assertEqual(rendered.count('<li '), 1)
        self.assertIn('Sunday, October 4, 2026', rendered)
        self.assertIn('7:30 PM–9:30 PM EDT', rendered)

    def test_eastern_daylight_saving_transition(self):
        stamp=int(datetime(2026,11,2,0,30,tzinfo=timezone.utc).timestamp()*1000)
        rendered=render_schedule(snapshot(entry(start=stamp)), NOW)
        self.assertIn('Sunday, November 1, 2026',rendered)
        self.assertIn('7:30 PM–9:30 PM EST',rendered)

    def test_stale_future_and_unsafe_cache_rejected(self):
        for change in [dict(fetched_at=(NOW-timedelta(hours=48)).isoformat()),dict(fetched_at=(NOW+timedelta(hours=1)).isoformat()),dict(source='https://example.com')]:
            with self.assertRaises(ValueError):
                validate_snapshot(dict(snapshot(),**change),NOW)
        data=snapshot();data['sessions'][0]['url']='javascript:alert(1)'
        with self.assertRaises(ValueError):validate_snapshot(data,NOW)

    def test_fetch_failure_preserves_recent_cache_then_falls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            cache=Path(directory)/'schedule.json'
            cache.write_text(json.dumps(snapshot()))
            with patch('hamstudy_sessions.urlopen',side_effect=OSError('offline')):
                self.assertIsNotNone(load_snapshot(cache,NOW+timedelta(hours=1)))
                self.assertIsNotNone(load_snapshot(cache,NOW+timedelta(hours=7)))
                self.assertIsNone(load_snapshot(cache,NOW+timedelta(hours=48)))
            self.assertEqual(json.loads(cache.read_text())['fetched_at'],NOW.isoformat())
        self.assertIn('view the online session list on HamStudy',render_schedule(None,NOW))

    def test_refresh_replaces_removed_sessions_and_fallback_has_no_false_empty_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            cache=Path(directory)/'cache.json';fixture=Path(directory)/'fixture.html'
            cache.write_text(json.dumps(snapshot()))
            fixture.write_text(page(entry(id='cccccccccccccccccccccccc')))
            data=load_snapshot(cache,NOW,fixture)
            self.assertEqual(len(data['sessions']),1)
            self.assertIn('cccccccccccccccccccccccc',data['sessions'][0]['url'])
        rendered=render_schedule(snapshot(entry(status='full')),NOW)
        self.assertNotIn('<li ',rendered)
        self.assertNotIn('no sessions',rendered.lower())

    def test_delayed_build_keeps_future_dates_and_original_check_time(self):
        data=snapshot(entry(start=int((NOW+timedelta(days=3)).timestamp()*1000)))
        fresh=render_schedule(data,NOW+timedelta(hours=5))
        delayed=render_schedule(data,NOW+timedelta(hours=6))
        self.assertIn('data-session-stale-warning hidden',fresh)
        self.assertIn('data-session-stale-warning>',delayed)
        self.assertIn('<li ',delayed)
        self.assertIn('Oct 03, 2026 at 10:00 AM EDT',delayed)
        self.assertIn(f'data-expires-at="{int((NOW+timedelta(hours=48)).timestamp()*1000)}"',delayed)
        self.assertNotIn('<li ',render_schedule(data,NOW+timedelta(hours=48)))

    def test_delayed_snapshot_still_excludes_started_sessions(self):
        self.assertNotIn('<li ',render_schedule(snapshot(),NOW+timedelta(hours=36)))

    def test_retry_transient_fetch_then_refresh_cache(self):
        response=MagicMock()
        response.__enter__.return_value=response
        response.status=200
        response.headers={'Content-Type':'text/html'}
        response.read.return_value=page(entry()).encode()
        with tempfile.TemporaryDirectory() as directory:
            cache=Path(directory)/'cache.json'
            errors=[URLError('timeout'),HTTPError(SOURCE,503,'unavailable',{},None),response]
            with patch('hamstudy_sessions.urlopen',side_effect=errors) as fetch, patch('hamstudy_sessions.sleep') as pause:
                data=load_snapshot(cache,NOW)
                self.assertEqual(fetch.call_count,3)
                self.assertEqual(pause.call_count,2)
            self.assertEqual(data['fetched_at'],NOW.isoformat())
            self.assertEqual(json.loads(cache.read_text()),data)

    def test_retries_are_bounded_and_permanent_failures_not_retried(self):
        with patch('hamstudy_sessions.urlopen',side_effect=URLError('offline')) as fetch, patch('hamstudy_sessions.sleep'):
            with self.assertRaises(URLError):fetch_listing()
            self.assertEqual(fetch.call_count,3)
        with patch('hamstudy_sessions.urlopen',side_effect=HTTPError(SOURCE,404,'missing',{},None)) as fetch:
            with self.assertRaises(HTTPError):fetch_listing()
            self.assertEqual(fetch.call_count,1)

    def test_truncated_read_retries_and_creates_cache_from_complete_response(self):
        response=MagicMock()
        response.__enter__.return_value=response
        response.status=200
        response.headers={'Content-Type':'text/html'}
        complete=page(entry()).encode()
        response.read.side_effect=[IncompleteRead(complete[:30],len(complete)-30),complete]
        with tempfile.TemporaryDirectory() as directory:
            cache=Path(directory)/'cache.json'
            with patch('hamstudy_sessions.urlopen',return_value=response) as fetch, patch('hamstudy_sessions.sleep') as pause:
                data=load_snapshot(cache,NOW)
                self.assertEqual(fetch.call_count,2)
                self.assertEqual(response.read.call_count,2)
                pause.assert_called_once_with(1)
            self.assertEqual(data,snapshot())
            self.assertEqual(json.loads(cache.read_text()),data)

    def test_repeated_truncated_reads_use_cache_only_after_retry_limit(self):
        for cached in [False,True]:
            with self.subTest(cached=cached), tempfile.TemporaryDirectory() as directory:
                cache=Path(directory)/'cache.json'
                if cached:cache.write_text(json.dumps(snapshot()))
                response=MagicMock()
                response.__enter__.return_value=response
                response.status=200
                response.headers={'Content-Type':'text/html'}
                response.read.side_effect=IncompleteRead(b'<h1>Upcoming',100)
                with patch('hamstudy_sessions.urlopen',return_value=response) as fetch, patch('hamstudy_sessions.sleep') as pause:
                    data=load_snapshot(cache,NOW+timedelta(hours=9))
                    self.assertEqual(fetch.call_count,3)
                    self.assertEqual(response.read.call_count,3)
                    self.assertEqual(pause.call_count,2)
                if cached:
                    self.assertEqual(data,snapshot())
                    self.assertEqual(json.loads(cache.read_text()),snapshot())
                else:
                    self.assertIsNone(data)
                    self.assertFalse(cache.exists())

    def test_invalid_listing_preserves_usable_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cache=Path(directory)/'cache.json';fixture=Path(directory)/'fixture.html'
            cache.write_text(json.dumps(snapshot()))
            fixture.write_text('<h1>Login</h1>')
            self.assertEqual(load_snapshot(cache,NOW+timedelta(hours=9),fixture),snapshot())
            self.assertEqual(json.loads(cache.read_text()),snapshot())

if __name__=='__main__':unittest.main()
