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

# Approved ARRL file baselines retain legacy routes and established procedures.
# On October 11, 2026, candidate-specific guides were updated to display
# consistent VEC labels near the title, and generic Find a Session links were
# routed to the common calendar. Explicit ARRL HamStudy registration links
# remain direct. Earlier NCVEC Form 605 terminology remains unchanged.
# On October 12, approved international-candidate guidance was synchronized
# across both VECs: U.S. mailing address, FRN and a welcoming invitation.
# These six baseline updates cover international guidance only; all other
# classic ARRL procedures and routes remain protected by their hashes.
# Further changes to ARRL procedures require explicit review.
ORIGINAL_ARRL_SOURCES = {
    "online-ham-radio-exam/index.html": "e38d098f1707a6e26c25f07730cea8bd1b0b2756",
    "online-ham-radio-exam-checklist/index.html": "8be0803fd4aac08e488215dbed543b0112194d6f",
    "online-ham-radio-exam-id-requirements/index.html": "5a8057c481d9f942248450a6463cbddfe82937a1",
    "what-to-bring-online-ham-radio-exam/index.html": "81f6b1b2669800a61002917527e8c43393b8fdf8",
    "online-ham-radio-exam-faq/index.html": "cad1d5521cb02bd7cb71d69e7ea9783e87193203",
    "online-ham-radio-exam-troubleshooting/index.html": "2d3b8a7686266ed0391b7ddeb956016969ec2e9b",
    "payment/index.html": "0938de3b1a9e5bd0272fc6aa6f0458618ef0fe39",
    "youth-ham-radio-exam/index.html": "41a9ac8fb1517788f172fc595baebfecb33549ca",
    "after-you-pass-ham-radio-exam/index.html": "d0aee484b40e5fe904f133bd035482d09fb1f446",
    "how-to-get-fcc-frn-ham-radio/index.html": "7b9532969eed24611f9c36b3efd7122d9ac6f03d",
    "checklist/index.html": "77591cb7674ab7c03fce27d88678343f4ec8e453",
    "faq/index.html": "c3c4de2ee4a7406a759e57672c566d31bde9f4c2",
    "templates/header.html": "548eeb45781b2b285419e8244ac21279b85939b6",
    "templates/footer.html": "4150d809bbb863b2e13468e71cc9d1b598f8e270"
}

for path, original_sha in ORIGINAL_ARRL_SOURCES.items():
    assert (root / path).is_file(), f"Legacy ARRL path was removed: {path}"
    assert git_blob_sha(path) == original_sha, f"Existing ARRL page/navigation changed: {path}"
    if path.endswith(".html"):
        assert "SANDARC" not in get(path), f"Cross-VEC reference in ARRL page: {path}"

# Keep the ARRL guide, identification and FAQ terminology accurate while
# retaining every established ARRL URL and registration procedure.
arrl_checklist = get("online-ham-radio-exam-checklist/index.html")
arrl_ids = get("online-ham-radio-exam-id-requirements/index.html")
arrl_faq = get("online-ham-radio-exam-faq/index.html")
assert "NCVEC Form 605 and VEC CSCE documents" in arrl_checklist
assert "FCC 605 form" not in arrl_checklist
assert "mailing address shown on the NCVEC Form 605" in arrl_ids
assert "mailing address shown on Form 605" not in arrl_ids
assert "Basic Qualification Question and NCVEC Form 605 certifications" in arrl_faq
assert "Basic Qualification Question and Form 605 certifications" not in arrl_faq


# P1 candidate-experience regressions: the established ARRL pages remain
# VEC-specific without introducing SANDARC wording or changing existing links.
ARRL_SCOPE_PAGES = (
    "online-ham-radio-exam/index.html",
    "online-ham-radio-exam-checklist/index.html",
    "online-ham-radio-exam-id-requirements/index.html",
    "online-ham-radio-exam-faq/index.html",
    "online-ham-radio-exam-troubleshooting/index.html",
    "what-to-bring-online-ham-radio-exam/index.html",
)
# All VEC-specific guides announce the coordinating VEC before the page title.
ARRL_ONLINE_PAGES = ARRL_SCOPE_PAGES + (
    "payment/index.html",
    "youth-ham-radio-exam/index.html",
    "after-you-pass-ham-radio-exam/index.html",
)
for guide in ARRL_ONLINE_PAGES:
    assert re.search(
        r'<div class="kicker">ARRL VEC • WEARC online examinations</div>\s*<h1\b',
        get(guide),
    ), f"ARRL-specific guide lacks the standard title label: {guide}"
    assert "SANDARC" not in get(guide), (
        f"Cross-VEC reference added to ARRL candidate instructions: {guide}"
    )
for guide in ARRL_SCOPE_PAGES:
    assert "<strong>ARRL VEC online sessions.</strong>" not in get(guide), (
        f"Redundant VEC statement remains in lead paragraph: {guide}"
    )
# The instructions retain the SANDARC label; the free-exam landing page
# uses a welcoming candidate-first kicker and identifies SANDARC in the fee copy.
assert re.search(
    r'<div class="kicker">SANDARC VEC • WEARC online examinations</div>\s*<h1\b',
    get("sandarc-online-exam/index.html"),
), "SANDARC instruction guide lacks its standard title label"


in_person = get("in-person-sessions/index.html")
assert re.search(r'<div class="kicker">ARRL VEC • WEARC in-person examinations</div>\s*<h1\b', in_person)
assert "<h3>FCC FRN (all candidates)</h3>" in in_person
assert "Every candidate, including those upgrading" in in_person
assert "<strong>$15</strong> for adults; <strong>$5</strong> for candidates under 18" in in_person
assert "<h3>$15 cash</h3>" not in in_person
assert "If you are taking the Technician exam" not in in_person

# Generic session discovery always uses the dual-VEC calendar; explicit
# ARRL/SANDARC registration links on the respective guide remain direct.
GENERIC_SESSION_LINK_TEXT = {
    "find a session",
    "find an upcoming online session",
    "view the wearc session calendar",
    "session schedule",
    "find wearc exam sessions",
    "view all wearc online sessions",
    "register for a session",
    "register for an exam",
    "wearc session calendar",
    "our combined session calendar",
}
canonical_urls = re.findall(r"<loc>https://hamradioonlinetest\.com(/[^<]*)</loc>",
                            get("sitemap.xml"))
assert len(canonical_urls) >= 19
canonical_pages = [
    "index.html" if url == "/" else url.strip("/") + "/index.html"
    for url in canonical_urls
]
generic_link_count = 0
for page in canonical_pages + [
    "404.html", "templates/header.html", "templates/header-vec.html",
    "templates/footer.html", "templates/footer-vec.html",
]:
    html = get(page)
    for match in re.finditer(r'<a\b([^>]*)>(.*?)</a>', html, re.S | re.I):
        attrs, body = match.groups()
        label = " ".join(unescape(re.sub(r"<[^>]*>", "", body)).split()).casefold()
        if label not in GENERIC_SESSION_LINK_TEXT:
            continue
        generic_link_count += 1
        url_match = re.search(r'\bhref="([^"]+)"', attrs)
        assert url_match, f"Session discovery anchor has no href on {page}"
        assert url_match.group(1) in {
            "/find-a-session/", "https://hamradioonlinetest.com/find-a-session/",
        }, f"Generic session link bypasses combined calendar on {page}: {label}"
        assert 'target="_blank"' not in attrs, (
            f"Internal session discovery must stay in the same tab: {page}"
        )
assert generic_link_count >= 20, "Site-wide discovery regression coverage too small"
for guide in (
    "online-ham-radio-exam-checklist/index.html",
    "youth-ham-radio-exam/index.html",
):
    assert 'href="https://hamstudy.org/sessions/WEARC/all"' in get(guide), (
        f"Keep direct ARRL HamStudy links for explicit registration on {guide}"
    )
assert 'https://hamstudy.org/sessions/WEARC/all' not in (
    get("templates/header.html") + get("templates/footer.html")
)

mobile_css = get("assets/css/styles.css")
assert re.search(
    r"@media \(max-width: 720px\) \{\s*/\* Allow the full navigation and search "
    r"to scroll away on small screens\. \*/\s*\.header \{\s*position: static;",
    mobile_css,
), "Mobile site header must not remain sticky above short phone viewports"
assert "min-height: 44px;\n    padding: 6px 0;" in mobile_css
assert "min-height: 48px;\n    margin-top: 5px;" in mobile_css

# P2 navigation, instruction clarity, and touch-target regressions.
not_found = get("404.html")
assert 'href="/find-a-session/">Find a session' in not_found
assert "https://hamstudy.org/sessions/WEARC/all" not in not_found
assert "'404.html', 'exam-instructions/index.html'" in get("scripts/render-site.py")
vec_header_link = re.search(
    r'<a class="cta" href="https://hamradioonlinetest.com/find-a-session/"([^>]*)>',
    get("templates/header-vec.html"),
)
assert vec_header_link and "target=" not in vec_header_link.group(1), (
    "Internal registration navigation must remain in the same browser tab"
)
selector_copy = get("exam-instructions/index.html")
assert "Which instructions apply?" in selector_copy
assert "Your session determines the VEC, not your personal preference" not in selector_copy
assert "Follow the instructions for your registered session" in selector_copy
assert "target=" not in re.search(r'<a href="/find-a-session/"([^>]*)>', selector_copy).group(1)

zoom_style = get("assets/css/styles.css")
assert re.search(r"\.zoom-audio-help__trigger\s*\{[^}]*width: 44px;[^}]*height: 44px;[^}]*flex: 0 0 44px;", zoom_style, re.S)
assert re.search(r"@media \(max-width: 720px\) \{\s*\.zoom-audio-help__panel\s*\{[^}]*position: fixed;[^}]*right: 16px;[^}]*bottom: 16px;", zoom_style, re.S)

homepage = get("index.html")
selector = get("exam-instructions/index.html")
sandarc = get("sandarc-online-exam/index.html")
vec_header = get("templates/header-vec.html")
vec_footer = get("templates/footer-vec.html")
renderer = get("scripts/render-site.py")
sitemap = get("sitemap.xml")

# Homepage referrals remain protected, except the three ARRL documentation
# links that were intentionally removed from the shared international FAQs.
# This keeps SANDARC guidance neutral while preserving WEARC and FCC links.
ORIGINAL_HOMEPAGE_HREFS = {
    "#main": 1,
    "mailto:hamradiotest@osi3.net": 3,
    "https://hamradioonlinetest.com/in-person-sessions/": 1,
    "/payment/": 2,
    "https://hamradioonlinetest.com/online-ham-radio-exam-checklist/": 1,  # Original resource-list link remains
    "/online-ham-radio-exam-faq/": 1,
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
    "https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-97/subpart-A/section-97.23": 1,
    "https://hamradioonlinetest.com/online-ham-radio-exam-faq/": 1,
    "tel:+1-917-502-2203": 1,
    "/youth-ham-radio-exam/": 1
}
current_hrefs = Counter(re.findall(r'<a[^>]+href="([^"]+)"', homepage))
for href, expected_count in ORIGINAL_HOMEPAGE_HREFS.items():
    assert current_hrefs[href] >= expected_count, f"Original homepage referral link removed or changed: {href}"
assert not any("www.arrl.org" in url for url in current_hrefs), "Shared homepage must not cite ARRL-only manuals"

# Candidate-first homepage hero: introductory copy should avoid VEC jargon,
# while retaining the site's established search-facing title and description.
hero = homepage.split('<div class="home-hero-primary">', 1)[1].split(
    '<div class="home-registration-panel">', 1)[0]
panel = homepage.split('<div class="home-registration-panel">', 1)[1].split(
    '<div class="btnrow">', 1)[0]
assert 'Friendly online ham radio exams' in hero
assert 'Thinking about getting your ham radio license?' in hero
assert 'U.S. amateur radio license exam online from home' in hero
assert all(level in hero for level in ('Technician', 'General', 'Amateur Extra'))
assert 'ARRL VEC' not in hero and 'SANDARC VEC' not in hero
assert panel.count('<li>') == 4, "Candidate onboarding must remain four simple steps"
assert 'check the VEC' not in panel and "session's VEC" not in panel
assert 'exam fees' in panel and 'href="/exam-instructions/"' in panel
assert '<title>Online Ham Radio Testing &amp; Exam Sessions | WEARC VE Team</title>' in homepage
assert '<h1 class="h1">Online Ham Radio Testing &amp; License Exam Sessions</h1>' in homepage
assert '<meta name="description" content="Take your ham radio license exam online with WEARC. Choose ARRL VEC sessions or free SANDARC VEC exams ($0 session fee). Technician, General, and Amateur Extra.">' in homepage
assert '<link rel="canonical" href="https://hamradioonlinetest.com/">' in homepage
# The redundant VEC fee comparison paragraph is intentionally absent.
# Individual fee links remain accessible through each VEC's resources and FAQ.
assert "WEARC offers both options:" not in homepage
assert "The FCC separately charges a $35 application fee for most new licenses." not in homepage
assert 'href="/payment/">Exam payment</a>' in homepage
assert 'href="/free-online-ham-radio-exam/"' in homepage

# Only the neutral selection page can compare or mention both VECs.
assert "ARRL VEC" in selector and "SANDARC VEC" in selector
assert "/online-ham-radio-exam-checklist/" in selector and "/payment/" in selector
assert "/sandarc-online-exam/" in selector
assert "/exam-instructions/" in homepage and "/sandarc-online-exam/" in homepage
assert "Before you join, review the" not in homepage, "Removed homepage ARRL-specific notice must stay absent"
assert current_hrefs["https://hamradioonlinetest.com/online-ham-radio-exam-checklist/"] == 1, "Keep resource link, not homepage notice"
free_page = get("free-online-ham-radio-exam/index.html")
assert "https://hamradioonlinetest.com/free-online-ham-radio-exam/" in sitemap
assert '<h1 class="h1" data-pagefind-weight="10">Free online ham radio license exams</h1>' in free_page
assert "<!-- FREE_SANDARC_SESSIONS -->" in free_page
assert 'href="https://hamstudy.org/sessions/W2EF/remote"' in free_page
assert "/sandarc-online-exam/" in free_page
assert "ARRL" not in free_page
free_intro = free_page.split('<section class="info-lead">', 1)[1].split('</section>', 1)[0]
assert '<div class="kicker">Friendly, free online ham radio exams</div>' in free_intro
assert "<strong>Thinking about getting your ham radio license?</strong>" in free_intro
assert "Take your U.S. amateur radio license exam online from home" in free_intro
assert "first Technician exam or upgrading to General or Amateur Extra" in free_intro
assert "friendly volunteer examiners" in free_intro
assert "Exams through SANDARC VEC are delivered <strong>free of charge ($0 exam session fee)</strong>" in free_intro, "Keep the SANDARC VEC name unbolded in the intro"
assert free_intro.index("Thinking about getting your ham radio license?") < free_intro.index("Exams through SANDARC VEC"), "First introduce the exam to a new candidate"
assert "ARRL" not in free_page, "SANDARC-only landing page must not mention ARRL"
assert "<strong>SANDARC VEC</strong>" not in free_page, "Free exam page must not visually emphasize the VEC name"
free_ld_match = re.search(r'<script type="application/ld\+json">([\s\S]*?)</script>', free_page)
assert free_ld_match, "Free exam page must publish JSON-LD"
import json
free_graph = json.loads(free_ld_match.group(1))["@graph"]
free_services = [node for node in free_graph if node.get("@type") == "Service"]
assert len(free_services) == 1, "Only one well-defined free examination service"
offer = free_services[0]["offers"]
assert str(offer["price"]) == "0" and offer["priceCurrency"] == "USD"
assert offer["url"] == "https://hamstudy.org/sessions/W2EF/remote"
assert "FCC application fees" in offer["description"]
assert "<strong>$35 application fee</strong>" in free_page
assert "a routine license-class upgrade" not in free_page or "upgrade does not have that FCC fee" in free_page
assert "free-online-ham-radio-exam/index.html" in renderer
assert "vec_only='SANDARC VEC'" in renderer
assert 'href="/free-online-ham-radio-exam/"' in homepage
assert 'href="/free-online-ham-radio-exam/"' in sandarc
assert homepage.count('class="vec-faq-pane"') == 2
assert homepage.count('class="cta vec-choice-button"') == 2
assert "SANDARC VEC resources" in homepage and "ARRL VEC resources" in homepage

registration = get("find-a-session/index.html")
# The session finder may be a candidate's first landing page; lead with plain,
# welcoming copy and explain free sessions without emphasizing VEC jargon.
session_intro = registration.split('<section class="info-lead">', 1)[1].split('</section>', 1)[0]
assert "<strong>Thinking about getting your ham radio license?</strong>" in session_intro
assert "Take your U.S. amateur radio license exam online from home" in session_intro
assert "first Technician exam or upgrading to General or Amateur Extra" in session_intro
assert "friendly volunteer examiners" in session_intro
assert "Exams through SANDARC VEC are delivered free of charge ($0 exam session fee)" in session_intro
assert "<strong>free of charge ($0 exam session fee)</strong>" not in session_intro, "Do not bold the free session fee on the combined session finder"
assert "<strong>SANDARC VEC</strong>" not in session_intro, "Emphasize the free fee, not the VEC"
assert '<div class="kicker">WEARC offers two options</div>' in registration
assert "Choose a VEC below to view available sessions and register on HamStudy." in registration
assert '<meta name="description" content="Find WEARC online ham radio exam dates. Choose ARRL VEC sessions or free SANDARC VEC exams ($0 session fee), then register through HamStudy.">' in registration
assert 'href="/payment/">view fees</a>' in registration
assert 'href="/free-online-ham-radio-exam/">$0 exam fee and dates</a>' in registration
assert "Two equal options" not in registration
assert "Prefer to browse directly on HamStudy?" not in registration
assert "If one VEC's published schedule cannot be retrieved" not in registration
assert "Always check HamStudy for the latest appointment availability." not in registration
assert "/find-a-session/" in sitemap
assert 'href="https://hamstudy.org/sessions/WEARC/remote"' in registration
assert 'href="https://hamstudy.org/sessions/W2EF/remote"' in registration
assert registration.index('>ARRL VEC</a>') < registration.index('>SANDARC VEC</a>')
assert "<!-- UPCOMING_SESSIONS_FULL -->" in registration
assert 'href="/find-a-session/"' in homepage
assert "https://hamstudy.org/sessions/WEARC/all" not in homepage
assert "https://hamstudy.org/sessions/WEARC/remote" not in homepage
assert "https://hamstudy.org/sessions/WEARC/all" not in vec_header + vec_footer
assert "/find-a-session/" in vec_header + vec_footer
assert "https://hamstudy.org/sessions/W2EF/remote" in sandarc
assert "https://hamstudy.org/sessions/WEARC/all" not in sandarc
assert "/find-a-session/" in get("ham-radio-mentoring-community/index.html")
assert "/find-a-session/" in get("new-ham-radio-operator-starter-kit/index.html")
# Equal candidate choices on the homepage and comparison page.
assert re.search(
    r'href="/online-ham-radio-exam-checklist/">ARRL VEC</a>\s*'
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
ld = re.search(r'<script type="application/ld\+json">([\s\S]*?)</script>', homepage)
assert ld, "FAQ structured data is missing"
faq_schema = next(item for item in json.loads(ld.group(1))['@graph'] if item['@type'] == 'FAQPage')
assert len(faq_schema['mainEntity']) == 16, "Structured FAQs must represent both VECs equally"
assert "special = page in neutral_pages" in renderer
for neutral_page in ("index.html", "frn/index.html", "ham-radio-mentoring-community/index.html", "new-ham-radio-operator-starter-kit/index.html"):
    assert f"'{neutral_page}'" in renderer

# Shared FCC and community pages must be VEC-neutral.
assert '/online-ham-radio-exam-checklist/' not in get("ham-radio-mentoring-community/index.html"), "Shared community page must not route exclusively to ARRL"
for shared in ("frn/index.html", "ham-radio-mentoring-community/index.html", "new-ham-radio-operator-starter-kit/index.html"):
    assert "ARRL" not in get(shared), f"ARRL-specific wording on neutral page: {shared}"
    assert "SANDARC" not in get(shared), f"SANDARC-specific wording on neutral page: {shared}"

assert homepage.count('class="home-extra-guides"') == 2
extra = homepage.split('class="vec-more-guides"', 1)[1]
assert extra.index('<summary>ARRL VEC resources</summary>') < extra.index('<summary>SANDARC VEC resources</summary>')
assert '/sandarc-online-exam/#equipment' in extra and '/online-ham-radio-exam/' in extra

# SANDARC candidate-facing page *and its rendered shared chrome* must not
# mention ARRL or link directly to legacy ARRL-only instructions/checkout.
for path, content in [("SANDARC page", sandarc), ("VEC header", vec_header), ("VEC footer", vec_footer)]:
    assert re.search(r"\bARRL\b", content, re.IGNORECASE) is None, f"ARRL reference in {path}"
    assert 'href="/payment/"' not in content
    assert 'href="https://hamradioonlinetest.com/payment/"' not in content
    assert "/online-ham-radio-exam-checklist/" not in content
    assert "/online-ham-radio-exam-faq/" not in content
assert "selected_header = vec_header if special else header" in renderer
assert "selected_footer = vec_footer if special else footer" in renderer
assert "page != 'sandarc-online-exam/index.html'" in renderer

# Candidate instructions use one predictable list system:
# numbers only for ordered actions, bullets for independent requirements.
# Shared .info-page .list styles provide identical spacing, indentation,
# marker color and row separators; no ARRL/global CSS changes are required.
expected_sandarc_lists = (
    ("register", "ol", 4),   # pre-exam actions, in order
    ("equipment", "ul", 7),  # independent checklist
    ("room", "ul", 4),       # independent checklist
    ("id", "ul", 4),         # four ID cases/rules, none hidden as paragraphs
    ("exam", "ol", 7),      # chronological exam day
    ("fees", "ul", 3),      # fees and operating privileges
    ("other", "ul", 3),     # accessibility and special cases
)
for section_id, marker, expected_count in expected_sandarc_lists:
    section = sandarc.split(f'<section class="section" id="{section_id}">', 1)[1].split(
        '</div></div></section>', 1
    )[0]
    assert section.count('<ol class="list">') == (marker == "ol"), section_id
    assert section.count('<ul class="list">') == (marker == "ul"), section_id
    assert section.count('<li>') == expected_count, section_id
    assert section.count('</li>') == expected_count, section_id
    assert section.count('</ol>') == (marker == "ol"), section_id
    assert section.count('</ul>') == (marker == "ul"), section_id
    if section_id in ("id", "fees", "other"):
        assert "<p>" not in section, f"Unmarked requirement paragraphs in {section_id}"

# Preserve styled exceptions outside requirement lists: an under-13 consent
# callout, an exam-day introduction, short notices, and the FCC status link.
assert '<strong>Under age 13?</strong>' in sandarc
exam_section = sandarc.split('<section class="section" id="exam">', 1)[1].split(
    '</div></div></section>', 1
)[0]
assert "We will verify your identity" in exam_section
assert exam_section.count('<p class="notice">') == 2
fees_section = sandarc.split('<section class="section" id="fees">', 1)[1].split(
    '</div></div></section>', 1
)[0]
assert "Check your FCC application status by FRN" in fees_section
assert '<p class="notice">' in fees_section
assert '<strong>FCC application fee:</strong>' in fees_section
assert '<strong>Operating privileges:</strong>' in fees_section

# Retain candidate-approved SANDARC instructions.
assert "One camera" in sandarc and "only when necessary" in sandarc
assert "one active monitor or screen" in sandarc.lower()
assert "360-degree room scan" in sandarc
assert "one sheet of scratch paper" not in sandarc
assert "On your desk, keep only the <strong>computer, keyboard, and mouse</strong>" in sandarc
assert "No physical calculator" in sandarc and "No headphones or earbuds" in sandarc
assert "A tablet or phone is also allowed" not in sandarc
assert '<li>A computer or laptop is recommended for <strong>Zoom screen sharing and ExamTools</strong>.</li>' in sandarc
# SANDARC VEC Manual, p.39: "Physical calculators are not authorized for remote exams."
assert "No physical calculator" in sandarc and "Put away books, notes and study materials" in sandarc
assert "Answer the FCC Basic Qualification (felony) question accurately." not in sandarc
assert "<strong>Join Zoom with one device only.</strong>" in sandarc
assert "latest version of the Zoom client" in sandarc
assert "HD video" in sandarc and "VPN software" in sandarc
assert "Windows taskbar notification area" in sandarc
assert "Only the candidate should be in the room during testing" in sandarc
assert "Remove hats, sunglasses and smartwatches" in sandarc
assert "<strong>on-screen calculator</strong>" in sandarc
assert "we will show you how to access it before the exam begins" in sandarc
assert "5–10 minutes early" in sandarc and "Zoom waiting room" in sandarc
assert "electronic signature for the NCVEC Quick-Form 605 and CSCE" in sandarc
assert "After the form is signed, there are some final instructions and often a friendly casual discussion that will follow." in sandarc
assert "The VEs will provide final instructions and can answer any remaining questions if time allows." not in sandarc
assert "electronic signature for the FCC Form 605" not in sandarc
assert "typically takes about 30 minutes" in sandarc
assert "If you want to take more than one exam element" in sandarc
assert "email WEARC" in sandarc
for excluded in ("Join Zoom with two devices", "small stand for the smartphone", "Don’t Connect To Audio", "WEARC online exam ID requirements", "pay the exam fee within one hour"):
    assert excluded.lower() not in sandarc.lower(), f"SANDARC page must not reuse ARRL-only instruction: {excluded}"
assert "<strong>no ID is photographed, recorded, or copied</strong>" not in sandarc
assert "no ID is photographed, recorded, or copied" in sandarc
assert "<strong>No recording:</strong>" not in sandarc
assert "WEARC will disable Zoom recording" not in sandarc
# SANDARC VEC Manual pp. 12, 28 and 31: minors without government-issued
# photo ID can have a parent/guardian show their own ID and verify identity.
# School/library cards are discretionary alternatives, not a second required ID.
# Candidates should contact WEARC before exam day: such documents aren't
# automatically sufficient without Team Lead approval.
identity_section = sandarc.split('<div class="kicker">Step 4 • Identity check</div>', 1)[1].split(
    '<div class="kicker">Step 5 • During your exam</div>', 1
)[0]
for required in (
    "<strong>Adults (18 and older):</strong>",
    "Your legal name should match your FCC registration and exam application",
    "<strong>Applicants under 18:</strong>",
    "a parent or guardian may present their own photo ID and confirm your identity",
    "A school ID, library card, or similar document may be accepted at the VE Team Lead's discretion",
    "If neither option is available",
    "contact WEARC before exam day",
    "not automatically sufficient on their own",
    "no ID is photographed, recorded, or copied",
    "no ID numbers are written down",
    "existing amateur radio license and any qualifying CSCE",
):
    assert required in identity_section, f"Missing manual-compliant SANDARC ID guidance: {required}"
for obsolete in (
    "Bring <strong>both</strong>",
    "A separate document bearing the candidate's name",
    "verbal confirmation alone are not sufficient",
    "match your FRN",
):
    assert obsolete not in identity_section, f"Obsolete SANDARC ID requirement remains: {obsolete}"

# Homepage visible FAQ and search-engine JSON-LD must agree with Step 4.
sandarc_id_faq = "Adults should have a government-issued photo ID. Candidates under 18 without government-issued photo ID may have a parent or guardian present their own photo ID and confirm the candidate's identity. If neither option is available, contact WEARC before exam day. The VE Team Lead may accept a school ID, library card, or similar document, but these documents are not automatically sufficient on their own. IDs are inspected visually over camera, are not photographed or recorded, and ID numbers are not written down."
assert homepage.count(sandarc_id_faq) == 2, "Visible SANDARC FAQ and JSON-LD must share current ID rules"
visible_sandarc_id_faq = sandarc_panel.split(
    '<summary>What identification do I need for an online ham radio exam?</summary>', 1
)[1].split('</details>', 1)[0]
assert sandarc_id_faq in visible_sandarc_id_faq
# Mirrored questions use the same wording and order in both VEC panes.
# International registration guidance is shared in both FAQ panes.
# Identification and exam fees remain VEC-specific answers.
arrl_faq_titles = re.findall(r'<details>\s*<summary>([^<]+)</summary>', arrl_panel)
sandarc_faq_titles = re.findall(r'<details>\s*<summary>([^<]+)</summary>', sandarc_panel)
assert len(arrl_faq_titles) == len(sandarc_faq_titles) == 8
assert arrl_faq_titles == sandarc_faq_titles, "VEC questions must match word for word"
assert len(set(arrl_faq_titles)) == 8, "No duplicate question within a VEC pane"
assert arrl_faq_titles[5] == "What identification do I need for an online ham radio exam?"
assert arrl_faq_titles[7] == "What is the ham radio exam fee?"
assert "What ID do I need" not in homepage
assert "Full requirements:" not in sandarc_panel, "Remove redundant SANDARC-only FAQ footer"
faq_entities = faq_schema["mainEntity"]
assert [entry["name"] for entry in faq_entities[:8]] == arrl_faq_titles
assert [entry["name"] for entry in faq_entities[8:]] == sandarc_faq_titles
assert faq_entities[13]["acceptedAnswer"]["text"] == sandarc_id_faq
for i in (0, 1, 2, 3, 4, 6):
    assert faq_entities[i]["acceptedAnswer"]["text"] == faq_entities[i+8]["acceptedAnswer"]["text"], (
        f"Non-policy FAQ answer mismatch at {i}"
    )
for i in (1, 9):
    answer = faq_entities[i]["acceptedAnswer"]["text"]
    assert "valid U.S. mailing address" in answer
    assert "U.S. citizenship and U.S. residence are not required" in answer
    assert "foreign/exempt" in answer
    assert "not a representative of a foreign government" in answer
    assert "ARRL" not in answer, "Shared international FAQ must be VEC-neutral"
assert "$15 per session" in faq_entities[7]["acceptedAnswer"]["text"]
assert "free for every candidate" in faq_entities[15]["acceptedAnswer"]["text"]
# Prevent a future edit from omitting the U.S. mailing address on other
# international candidate pages or reintroducing ARRL-only documentation.
long_faq = get("online-ham-radio-exam-faq/index.html")
long_international = long_faq.split(
    "<h4>Can international candidates take a U.S. Amateur Radio license exam with WEARC?</h4>", 1
)[1].split("<h4>", 1)[0]
for required in (
    "welcome and encourage international candidates",
    "valid U.S. mailing address",
    "You do not have to live in the United States",
    "foreign/exempt",
    "ExamTools",
    "government-issued passport",
    "not a representative of a foreign government",
):
    assert required in long_international, f"International long FAQ missing: {required}"
assert "arrl.org" not in long_international.lower()
assert "ARRL VEC" not in long_international
long_faq_graph = json.loads(
    long_faq.split('<script type="application/ld+json">', 1)[1].split('</script>', 1)[0]
)["@graph"]
long_faq_schema = next(node for node in long_faq_graph if node.get("@type") == "FAQPage")
long_faq_answer = next(
    entry["acceptedAnswer"]["text"] for entry in long_faq_schema["mainEntity"]
    if entry["name"] == "Can international candidates take a U.S. Amateur Radio license exam with WEARC?"
)
assert "valid U.S. mailing address" in long_faq_answer
assert "ARRL" not in long_faq_answer

for page in (
    "sandarc-online-exam/index.html",
    "how-to-get-fcc-frn-ham-radio/index.html",
    "online-ham-radio-exam-checklist/index.html",
    "online-ham-radio-exam/index.html",
    "what-to-bring-online-ham-radio-exam/index.html",
    "youth-ham-radio-exam/index.html",
):
    html = get(page)
    assert "valid U.S. mailing address" in html, f"Missing U.S. address requirement: {page}"
    assert "international" in html.lower() or "foreign applicants" in html.lower(), page
assert "ARRL VEC application" not in get("online-ham-radio-exam-checklist/index.html")
assert "ARRL VEC license application" not in get("how-to-get-fcc-frn-ham-radio/index.html")
assert "www.arrl.org" not in sandarc
assert "foreign/exempt" in sandarc
assert "U.S. citizenship and residence are not required" in sandarc

assert "must bring both a parent or guardian" not in homepage
assert "guardian’s ID and verbal verification alone are not sufficient" not in homepage
assert "coppa@examtools.org" in sandarc and "before registration" in sandarc.lower()
assert "Policy reference:" not in sandarc
assert "vec.sandarc.org/manual" not in sandarc
assert "SANDARC exam fee: $0" in sandarc
assert "10 calendar days" in sandarc and "attach605@fcc.gov" in sandarc

felony = re.search(r"<li><strong>Felony question:</strong>.*?</li>", sandarc)
assert felony, "SANDARC felony question paragraph missing"
plain = unescape(re.sub(r"<[^>]*>", "", felony.group(0)))
assert plain == "Felony question: SANDARC VEs will not ask about the circumstances. If you answer “Yes” to the FCC Basic Qualification question, SANDARC directs you to submit an explanation with your FCC application number to attach605@fcc.gov within 14 days after the application is submitted.", "Felony question must match approved wording"
assert "SANDARC VEs must not ask about the circumstances." not in sandarc
assert "/exam-instructions/" in sitemap and "/sandarc-online-exam/" in sitemap
print("VEC isolation, SANDARC instructions, and all original ARRL route/link regression checks passed.")
