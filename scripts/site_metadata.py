"""Visible breadcrumbs and sitemap dates based on substantive published content."""
from datetime import date
from hashlib import sha256
from html import escape, unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ORIGIN = 'https://hamradioonlinetest.com'
NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
SCHEMA = re.compile(r'(<script type="application/ld\+json">)\s*(.*?)\s*(</script>)', re.S)


def breadcrumbs(text, url):
    if url == ORIGIN + '/':
        return text
    heading = re.search(r'<h1\b[^>]*>(.*?)</h1>', text, re.S)
    label = unescape(re.sub(r'<[^>]+>', '', heading[1])).strip()
    identifier = url + '#breadcrumb'
    nav = ('\n    <nav class="breadcrumbs container" aria-label="Breadcrumb" data-pagefind-ignore>'
           '<ol><li><a href="/">Home</a></li>'
           f'<li aria-current="page">{escape(label)}</li></ol></nav>')
    text = re.sub(r'(<main\b[^>]*>)', lambda m: m[1] + nav, text, count=1)

    def connect(match):
        data = json.loads(match[2])
        for node in data.get('@graph', []):
            if node.get('@type') == 'WebPage':
                node['breadcrumb'] = {'@id': identifier}
        return match[1] + '\n' + json.dumps(data, indent=2) + '\n  ' + match[3]

    text = SCHEMA.sub(connect, text)
    data = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', '@id': identifier,
            'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': ORIGIN + '/'},
                {'@type': 'ListItem', 'position': 2, 'name': label, 'item': url}]}
    script = '\n  <script type="application/ld+json">\n' + json.dumps(data, indent=2) + '\n  </script>\n'
    return text.replace('</head>', script + '</head>')


class MeaningfulContent(HTMLParser):
    """Ignore cosmetic markup; keep visible words, destinations, and media."""
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, value):
        value = ' '.join(value.split())
        if value:
            self.parts.append(value)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ('href', 'src', 'alt', 'datetime'):
            if key in attrs:
                self.parts.append(key + '=' + attrs[key])


def content_digest(text):
    # Fetch/check timestamps and copyright years are not content changes.
    text = re.sub(r'<p\b[^>]*\bdata-session-checked\b[^>]*>.*?</p>', '', text, flags=re.S)
    text = re.sub(r'<span\b[^>]*\bdata-year\b[^>]*>.*?</span>', '', text, flags=re.S)
    parser = MeaningfulContent()
    for pattern in (r'<title\b[^>]*>(.*?)</title>', r'<main\b[^>]*>(.*?)</main>',
                    r'<header\b[^>]*>(.*?)</header>', r'<footer\b[^>]*>(.*?)</footer>'):
        match = re.search(pattern, text, re.S)
        if match:
            parser.feed(match[1])
    descriptions = re.findall(r'<meta\b[^>]*(?:name|property)="(?:description|og:description|twitter:description)"[^>]*>', text)
    schemas = [json.loads(m[2]) for m in SCHEMA.finditer(text)]
    return sha256(json.dumps([parser.parts, descriptions, schemas], sort_keys=True).encode()).hexdigest()


def source_date(root, relative):
    # A shallow checkout cannot establish the last actual change of a file.
    try:
        if subprocess.check_output(['git', 'rev-parse', '--is-shallow-repository'], cwd=root, text=True).strip() != 'false':
            return None
        result = subprocess.check_output(
            ['git', 'log', '-1', '--format=%cs', '--', relative, 'templates/header.html', 'templates/footer.html'],
            cwd=root, text=True).strip()
        return date.fromisoformat(result).isoformat() if result else None
    except (subprocess.CalledProcessError, ValueError):
        return None


def modification_date(digest, previous, baseline, today):
    if isinstance(previous, dict):
        try:
            prior_date = date.fromisoformat(previous['lastmod']) if previous.get('lastmod') else None
            if prior_date and prior_date > today:
                raise ValueError('Future date')
            if previous.get('digest') == digest:
                return previous.get('lastmod') or baseline
            return today.isoformat()
        except (KeyError, TypeError, ValueError):
            pass
    return baseline


def render_metadata(root, site, now):
    cache = root / '.cache/sitemap-state.json'
    try:
        state = json.loads(cache.read_text())
        previous = state['pages'] if state.get('version') == 1 else {}
        if not isinstance(previous, dict):
            previous = {}
    except (OSError, ValueError, KeyError, TypeError):
        previous = {}
    tree = ET.parse(site / 'sitemap.xml')
    pages = {}
    for node in tree.getroot().findall(f'{{{NS}}}url'):
        url = node.find(f'{{{NS}}}loc').text
        relative = urlsplit(url).path.strip('/')
        relative = (relative + '/' if relative else '') + 'index.html'
        path = site / relative
        text = breadcrumbs(path.read_text(), url)
        path.write_text(text)
        digest = content_digest(text)
        lastmod = modification_date(digest, previous.get(url), source_date(root, relative), now.date())
        pages[url] = {'digest': digest, 'lastmod': lastmod}
        for old in node.findall(f'{{{NS}}}lastmod'):
            node.remove(old)
        if lastmod:
            ET.SubElement(node, f'{{{NS}}}lastmod').text = lastmod
    ET.register_namespace('', NS)
    ET.indent(tree, space='  ')
    tree.write(site / 'sitemap.xml', encoding='UTF-8', xml_declaration=True)
    cache.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache.with_suffix('.tmp')
    temporary.write_text(json.dumps({'version': 1, 'pages': pages}, indent=2))
    temporary.replace(cache)
