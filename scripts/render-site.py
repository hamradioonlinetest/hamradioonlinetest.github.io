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
# Only the two new VEC pages receive neutral navigation; every existing page
# retains its original shared header/footer links and labels.
vec_header = (root / 'templates/header-vec.html').read_text()
vec_footer = (root / 'templates/footer-vec.html').read_text().replace('{{YEAR}}', str(now.year))
search = (root / 'templates/search.html').read_text()
css_version = sha256((site / 'assets/css/styles.css').read_bytes()).hexdigest()[:12]
for path in site.rglob('*.html'):
    text = path.read_text()
    if 'assets/css/styles.css' not in text:
        # Redirect fallback links should use the same visual system too.
        text = text.replace('</head>', '  <meta name="viewport" content="width=device-width,initial-scale=1">\n  <link rel="stylesheet" href="https://hamradioonlinetest.com/assets/css/styles.css">\n</head>')
        text = text.replace('<body>', '<body class="redirect-page">')
    page = path.relative_to(site).as_posix()
    excluded = page in {'404.html', 'sessions/index.html', 'counts/index.html', 'vescript/index.html'}
    special = page in {'index.html', 'exam-instructions/index.html', 'sandarc-online-exam/index.html'}
    selected_header = vec_header if special else header
    selected_footer = vec_footer if special else footer
    # The SANDARC guide should not surface unrelated VEC results through
    # the site's global search component. The neutral selector retains search.
    show_search = not excluded and page != 'sandarc-online-exam/index.html'
    text = text.replace('<div data-site-header></div>', selected_header.replace('{{SEARCH}}', search if show_search else ''))
    text = text.replace('<div data-site-footer></div>', selected_footer)
    if page == 'sandarc-online-exam/index.html' and 'ARRL' in text:
        raise ValueError('Cross-VEC reference on SANDARC instructions page')
    text = text.replace('<!-- UPCOMING_SESSIONS -->', render_schedule(snapshot, now))
    text = text.replace('assets/css/styles.css"', f'assets/css/styles.css?v={css_version}"')
    path.write_text(text)
render_metadata(root, site, now)
print('Rendered shared navigation, footer, sessions, breadcrumbs, and sitemap dates')
