#!/usr/bin/env python3
"""Render shared chrome and public schedule into staged HTML before indexing."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import os
import sys
from hamstudy_sessions import load_snapshot, render_schedule
from site_metadata import render_metadata

root = Path(__file__).resolve().parent.parent
site = Path(sys.argv[1]).resolve()
now = datetime.now(timezone.utc)
fixture = os.environ.get('HAMSTUDY_HTML_FIXTURE')
snapshot = load_snapshot(root / '.cache/hamstudy-sessions.json', now, Path(fixture) if fixture else None)
header = (root / 'templates/header.html').read_text()
footer = (root / 'templates/footer.html').read_text().replace('{{YEAR}}', str(now.year))
search = (root / 'templates/search.html').read_text()
css_version = sha256((site / 'assets/css/styles.css').read_bytes()).hexdigest()[:12]
for path in site.rglob('*.html'):
    text = path.read_text()
    excluded = path.relative_to(site).as_posix() in {'404.html', 'sessions/index.html', 'counts/index.html', 'vescript/index.html'}
    text = text.replace('<div data-site-header></div>', header.replace('{{SEARCH}}', '' if excluded else search))
    text = text.replace('<div data-site-footer></div>', footer)
    text = text.replace('<!-- UPCOMING_SESSIONS -->', render_schedule(snapshot, now))
    text = text.replace('assets/css/styles.css"', f'assets/css/styles.css?v={css_version}"')
    path.write_text(text)
render_metadata(root, site, now)
print('Rendered shared navigation, footer, sessions, breadcrumbs, and sitemap dates')
