#!/usr/bin/env python3
"""Check VEC separation and preserve all classic ARRL routes and referrals."""
from collections import Counter
from hashlib import sha1
from html import unescape
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]

def get(path):
    return (root / path).read_text(encoding="utf-8")

def git_blob_sha(path):
    content = (root / path).read_bytes()
    return sha1(b"blob " + str(len(content)).encode() + bytes([0]) + content).hexdigest()

# These are the unchanged source files from main before the SANDARC work.
# They include old aliases /checklist/ and /faq/ used by external referrals.
# Changes to existing ARRL instructions require an explicit baseline review.
ORIGINAL_ARRL_SOURCES = {
    "online-ham-radio-exam/index.html": "038f0581a192b369506100de81fea5c3b8725783",
    "online-ham-radio-exam-checklist/index.html": "61c0435ff48257dd614dca00eeb0bc4d474b4d82",
    "online-ham-radio-exam-id-requirements/index.html": "a08ac2d87fabceca726e1a95f6020ba31f83e909",
    "what-to-bring-online-ham-radio-exam/index.html": "acfeff1e55700b7e21c081785b078aca8fcbf086",
    "online-ham-radio-exam-faq/index.html": "471021daec82e2b15a81a7aac771d507b176c332",
    "online-ham-radio-exam-troubleshooting/index.html": "cce08d29189c3106b176e174da1d8966067dde38",
    "payment/index.html": "bac512ac31411a188659323749270c857aef0c08",
    "youth-ham-radio-exam/index.html": "7d5e955cb238b9c94c564172795f0c4422b7125e",
    "after-you-pass-ham-radio-exam/index.html": "e56a05b970a18c9fd7aa301826137b9843b45acd",
    "how-to-get-fcc-frn-ham-radio/index.html": "3ffd7301c86113ff0885c4a7aa048a0ffe27ed7d",
    "checklist/index.html": "77591cb7674ab7c03fce27d88678343f4ec8e453",
    "faq/index.html": "c3c4de2ee4a7406a759e57672c566d31bde9f4c2",
    "templates/header.html": "a26bd1ab962028a3c2f1c5cfe22b06e319f0a525",
    "templates/footer.html": "aaf49d2ea3e29ceefc04f9631d8b03cba8fcde79"
}

for path, original_sha in ORIGINAL_ARRL_SOURCES.items():
    assert (root / path).is_file(), f"Legacy ARRL path was removed: {path}"
    assert git_blob_sha(path) == original_sha, f"Existing ARRL page/navigation changed: {path}"
    if path.endswith(".html"):
        assert "SANDARC" not in get(path), f"Cross-VEC reference in ARRL page: {path}"

homepage = get("index.html")
selector = get("exam-instructions/index.html")
sandarc = get("sandarc-online-exam/index.html")
vec_header = get("templates/header-vec.html")
vec_footer = get("templates/footer-vec.html")
renderer = get("scripts/render-site.py")
sitemap = get("sitemap.xml")

# Original homepage outbound and internal URLs must all remain present with
# at least their former occurrence counts. Adding gateway links is allowed.
ORIGINAL_HOMEPAGE_HREFS = {
    "#main": 1,
    "https://hamstudy.org/sessions/WEARC/all": 4,
    "mailto:hamradiotest@osi3.net": 3,
    "https://hamradioonlinetest.com/in-person-sessions/": 1,
    "/payment/": 2,
    "https://hamradioonlinetest.com/online-ham-radio-exam-checklist/": 2,
    "/online-ham-radio-exam-faq/": 1,
    "https://hamstudy.org/sessions/WEARC/remote": 1,
    "/online-ham-radio-exam/": 1,
    "https://hamradioonlinetest.com/online-ham-radio-exam-id-requirements/": 2,
    "https://hamradioonlinetest.com/what-to-bring-online-ham-radio-exam/": 1,
    "https://hamradioonlinetest.com/how-to-get-fcc-frn-ham-radio/": 2,
    "https://hamradioonlinetest.com/youth-ham-radio-exam/": 1,
    "https://hamradioonlinetest.com/after-you-pass-ham-radio-exam/": 1,
    "https://hamradioonlinetest.com/frn/": 1,
    "https://hamradioonlinetest.com/online-ham-radio-exam-troubleshooting/": 1,
    "https://hamradioonlinetest.com/new-ham-radio-operator-starter-kit/": 1,
    "https://hamradioonlinetest.com/ham-radio-mentoring-community/": 1,
    "https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-97/subpart-A/section-97.5": 1,
    "https://www.arrl.org/foreign-licenses-operating-in-u-s": 1,
    "https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-97/subpart-A/section-97.23": 1,
    "https://www.arrl.org/605-instructions": 1,
    "https://www.arrl.org/ncvec-form-605": 1,
    "https://hamradioonlinetest.com/online-ham-radio-exam-faq/": 1,
    "tel:+1-917-502-2203": 1,
    "/youth-ham-radio-exam/": 1
}
current_hrefs = Counter(re.findall(r'<a[^>]+href="([^"]+)"', homepage))
for href, expected_count in ORIGINAL_HOMEPAGE_HREFS.items():
    assert current_hrefs[href] >= expected_count, f"Original homepage referral link removed or changed: {href}"

# Only the neutral selection page can compare or mention both VECs.
assert "ARRL VEC" in selector and "SANDARC VEC" in selector
assert "/online-ham-radio-exam-checklist/" in selector and "/payment/" in selector
assert "/sandarc-online-exam/" in selector
assert "/exam-instructions/" in homepage and "/sandarc-online-exam/" in homepage
# Equal candidate choices on the homepage and comparison page.
assert re.search(
    r'href="/online-ham-radio-exam-checklist/">ARRL VEC</a>\\s*'
    r'<a class="cta vec-choice-button" href="/sandarc-online-exam/">SANDARC VEC</a>',
    homepage
), "Home page must offer equivalent alphabetical VEC buttons"
assert re.search(
    r'href="/online-ham-radio-exam-checklist/">ARRL VEC</a>',
    selector
) and re.search(
    r'href="/sandarc-online-exam/">SANDARC VEC</a>',
    selector
)
assert homepage.count('class="vec-faq-pane"') == 2
faq_fragment = homepage.split('class="vec-faq-panes"', 1)[1]
assert faq_fragment.index('<summary>ARRL VEC</summary>') < faq_fragment.index('<summary>SANDARC VEC</summary>')
arrl_panel = faq_fragment.split('<summary>ARRL VEC</summary>', 1)[1].split('class="vec-faq-pane"', 1)[0]
sandarc_panel = faq_fragment.split('<summary>SANDARC VEC</summary>', 1)[1]
assert "SANDARC" not in arrl_panel, "ARRL homepage FAQ must not reference SANDARC"
assert "ARRL" not in sandarc_panel, "SANDARC homepage FAQ must not reference ARRL"
assert arrl_panel.count('<details>') == sandarc_panel.count('<details>') == 8
import json
ld = re.search(r'<script type="application/ld\\+json">([\\s\\S]*?)</script>', homepage)
assert ld, "FAQ structured data is missing"
faq_schema = next(item for item in json.loads(ld.group(1))['@graph'] if item['@type'] == 'FAQPage')
assert len(faq_schema['mainEntity']) == 16, "Structured FAQs must represent both VECs equally"
assert "special = page in {'index.html', 'exam-instructions/index.html', 'sandarc-online-exam/index.html'}" in renderer

# SANDARC candidate-facing page *and its rendered shared chrome* must not
# mention ARRL or link directly to legacy ARRL-only instructions/checkout.
for path, content in [("SANDARC page", sandarc), ("VEC header", vec_header), ("VEC footer", vec_footer)]:
    assert re.search(r"\\bARRL\\b", content, re.IGNORECASE) is None, f"ARRL reference in {path}"
    assert 'href="/payment/"' not in content
    assert 'href="https://hamradioonlinetest.com/payment/"' not in content
    assert "/online-ham-radio-exam-checklist/" not in content
    assert "/online-ham-radio-exam-faq/" not in content
assert "selected_header = vec_header if special else header" in renderer
assert "selected_footer = vec_footer if special else footer" in renderer
assert "page != 'sandarc-online-exam/index.html'" in renderer

# Retain candidate-approved SANDARC instructions.
assert "One camera" in sandarc and "only when necessary" in sandarc
assert "one active monitor or screen" in sandarc.lower()
assert "360-degree room scan" in sandarc
assert "one sheet of scratch paper" not in sandarc
assert "On your desk, keep only the <strong>computer, keyboard, and mouse</strong>" in sandarc
assert "No physical calculator" in sandarc and "No headphones or earbuds" in sandarc
assert "<strong>no ID is photographed, recorded, or copied</strong>" not in sandarc
assert "no ID is photographed, recorded, or copied" in sandarc
assert "<strong>No recording:</strong>" not in sandarc
assert "WEARC will disable Zoom recording" not in sandarc
assert "coppa@examtools.org" in sandarc and "before registration" in sandarc.lower()
assert "SANDARC exam fee: $0" in sandarc
assert "10 calendar days" in sandarc and "attach605@fcc.gov" in sandarc

felony = re.search(r"<p><strong>Felony question:</strong>.*?</p>", sandarc)
assert felony, "SANDARC felony question paragraph missing"
plain = unescape(re.sub(r"<[^>]*>", "", felony.group(0)))
assert plain == "Felony question: SANDARC VEs will not ask about the circumstances. If you answer “Yes” to the FCC Basic Qualification question, SANDARC directs you to submit an explanation with your FCC application number to attach605@fcc.gov within 14 days after the application is submitted.", "Felony question must match approved wording"
assert "SANDARC VEs must not ask about the circumstances." not in sandarc
assert "/exam-instructions/" in sitemap and "/sandarc-online-exam/" in sitemap
print("VEC isolation, SANDARC instructions, and all original ARRL route/link regression checks passed.")
