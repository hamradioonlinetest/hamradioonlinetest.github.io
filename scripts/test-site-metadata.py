#!/usr/bin/env python3
"""Regressions for truthful dates and visible/schema breadcrumb agreement."""
from datetime import date, datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from site_metadata import (ORIGIN, NS, SCHEMA, breadcrumbs, content_digest,
                           modification_date, render_metadata, source_date)

HTML = '''<html><head><title>Exam guide</title><script type="application/ld+json">
{"@graph":[{"@type":"WebPage","url":"https://hamradioonlinetest.com/guide/"}]}
</script></head><body><main><h1>Exam guide &amp; FAQ</h1><p>Study and register.</p>
<div data-session-schedule data-expires-at="123"><a href="https://hamstudy.org/sessions/one">Exam</a>
<p data-session-checked>Schedule checked today.</p></div></main>
<footer>© <span data-year>2026</span><a href="/guide/">Guide</a></footer></body></html>'''


class MetadataTests(unittest.TestCase):
    def test_fetch_timestamp_and_copyright_do_not_change_digest(self):
        newer = HTML.replace('123', '456').replace('today.', 'tomorrow.').replace('2026</span>', '2027</span>')
        self.assertEqual(content_digest(HTML), content_digest(newer))

    def test_words_destinations_and_metadata_do_change_digest(self):
        for old, new in [('Study and register.', 'Prepare at home.'), ('sessions/one', 'sessions/two'),
                         ('<title>Exam guide', '<title>Online exam guide')]:
            with self.subTest(old=old):
                self.assertNotEqual(content_digest(HTML), content_digest(HTML.replace(old, new)))

    def test_description_formatting_preserves_digest_and_date(self):
        for marker, attribute in [('description', 'name'), ('og:description', 'property'),
                                  ('twitter:description', 'name')]:
            original = f'<meta {attribute}="{marker}" content="Study &amp; register.">'
            variants = [
                f"<meta content='Study &amp; register.' {attribute}='{marker}'>",
                f'<meta\n content = "Study &amp; register."\n {attribute} = "{marker}" />',
                f'<META CONTENT="Study &#38; register." {attribute.upper()}="{marker}">',
                f'<meta content="  Study   &amp; register.  " {attribute}="{marker}" class="unused">',
            ]
            digest = content_digest(HTML.replace('</head>', original + '</head>'))
            previous = {'digest': digest, 'lastmod': '2026-09-01'}
            for variant in variants:
                with self.subTest(marker=marker, variant=variant):
                    newer = content_digest(HTML.replace('</head>', variant + '</head>'))
                    self.assertEqual(digest, newer)
                    self.assertEqual(modification_date(newer, previous, '2026-09-01', date(2026,10,3)),
                                     '2026-09-01')

    def test_description_value_edits_advance_date_with_either_quote_style(self):
        for marker, attribute in [('description', 'name'), ('og:description', 'property'),
                                  ('twitter:description', 'name')]:
            for quote in ('"', "'"):
                with self.subTest(marker=marker, quote=quote):
                    tag = f'<meta content={quote}Study and register.{quote} {attribute}={quote}{marker}{quote}>'
                    old = content_digest(HTML.replace('</head>', tag + '</head>'))
                    new = content_digest(HTML.replace('</head>', tag.replace('Study and register.', 'Take your exam from home.') + '</head>'))
                    self.assertNotEqual(old, new)
                    self.assertEqual(modification_date(new, {'digest': old, 'lastmod': '2026-09-01'},
                                                       '2026-09-01', date(2026,10,3)), '2026-10-03')

    def test_description_tag_order_is_not_a_content_change(self):
        tags = ['<meta name="description" content="Study.">',
                '<meta property="og:description" content="Practice.">',
                '<meta name="twitter:description" content="Register.">']
        self.assertEqual(content_digest(HTML.replace('</head>', ''.join(tags) + '</head>')),
                         content_digest(HTML.replace('</head>', ''.join(reversed(tags)) + '</head>')))

    def test_unchanged_build_preserves_date(self):
        previous = {'digest': 'abc', 'lastmod': '2026-09-01'}
        self.assertEqual(modification_date('abc', previous, '2026-10-02', date(2026,10,3)), '2026-09-01')
        self.assertEqual(modification_date('changed', previous, '2026-09-01', date(2026,10,3)), '2026-10-03')

    def test_unknown_dates_are_omitted_and_invalid_cache_is_not_trusted(self):
        self.assertIsNone(modification_date('abc', None, None, date(2026,10,3)))
        self.assertEqual(modification_date('abc', {'digest':'abc','lastmod':'2099-01-01'},
                                          '2026-09-01', date(2026,10,3)), '2026-09-01')
        with patch('site_metadata.subprocess.check_output', return_value='true\n'):
            self.assertIsNone(source_date(Path('.'), 'index.html'))

    def test_breadcrumbs_match_the_visible_heading_and_webpage(self):
        url = ORIGIN + '/guide/'
        result = breadcrumbs(HTML, url)
        self.assertIn('aria-current="page">Exam guide &amp; FAQ', result)
        schemas = [json.loads(m[2]) for m in SCHEMA.finditer(result)]
        webpage = schemas[0]['@graph'][0]
        breadcrumb = schemas[1]
        self.assertEqual(webpage['breadcrumb']['@id'], breadcrumb['@id'])
        self.assertEqual(breadcrumb['itemListElement'], [
            {'@type':'ListItem','position':1,'name':'Home','item':ORIGIN+'/'},
            {'@type':'ListItem','position':2,'name':'Exam guide & FAQ','item':url}])
        self.assertEqual(breadcrumbs(HTML, ORIGIN+'/'), HTML)

    def test_persisted_state_tracks_schedule_changes_across_builds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); site = root/'_site'; (site/'guide').mkdir(parents=True)
            (site/'sitemap.xml').write_text(f'<urlset xmlns="{NS}"><url><loc>{ORIGIN}/guide/</loc></url></urlset>')
            def build(html, day):
                (site/'guide/index.html').write_text(html)
                with patch('site_metadata.source_date', return_value='2026-09-01'):
                    render_metadata(root, site, datetime(2026,10,day,tzinfo=timezone.utc))
                return ET.parse(site/'sitemap.xml').find(f'.//{{{NS}}}lastmod').text
            self.assertEqual(build(HTML, 1), '2026-09-01')
            self.assertEqual(build(HTML.replace('today.', 'tomorrow.'), 2), '2026-09-01')
            self.assertEqual(build(HTML.replace('sessions/one', 'sessions/two'), 3), '2026-10-03')
            self.assertEqual(build(HTML.replace('sessions/one', 'sessions/two'), 4), '2026-10-03')

    def test_lastmod_follows_loc_before_optional_sitemap_fields(self):
        for optional in ('', '<changefreq>weekly</changefreq>', '<priority>0.7</priority>',
                         '<changefreq>weekly</changefreq><priority>0.7</priority>'):
            with self.subTest(optional=optional), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); site = root/'_site'; (site/'guide').mkdir(parents=True)
                (site/'guide/index.html').write_text(HTML)
                (site/'sitemap.xml').write_text(
                    f'<urlset xmlns="{NS}"><url><loc>{ORIGIN}/guide/</loc>'
                    f'<lastmod>2020-01-01</lastmod>{optional}</url></urlset>')
                with patch('site_metadata.source_date', return_value='2026-09-01'):
                    render_metadata(root, site, datetime(2026,10,3,tzinfo=timezone.utc))
                node = ET.parse(site/'sitemap.xml').find(f'{{{NS}}}url')
                tags = [child.tag.rsplit('}', 1)[-1] for child in node]
                expected = ['loc', 'lastmod']
                if '<changefreq>' in optional:
                    expected.append('changefreq')
                if '<priority>' in optional:
                    expected.append('priority')
                self.assertEqual(tags, expected)
                self.assertEqual(node.find(f'{{{NS}}}lastmod').text, '2026-09-01')


if __name__ == '__main__':
    unittest.main()
