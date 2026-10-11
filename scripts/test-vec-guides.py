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
# Further changes to ARRL procedures require explicit review.
ORIGINAL_ARRL_SOURCES = {
    "online-ham-radio-exam/index.html": "412b5983541fcedec106f414b23d669ba5857bcf",
    "online-ham-radio-exam-checklist/index.html": "8ae54efb8017b7928467a06091185990136a1a6a",
    "online-ham-radio-exam-id-requirements/index.html": "5a8057c481d9f942248450a6463cbddfe82937a1",
    "what-to-bring-online-ham-radio-exam/index.html": "900edf2ee836524c1fb546e660b640443ec18117",
    "online-ham-radio-exam-faq/index.html": "26da27f2d2c3c93ac096614b150e1fceabf647cf",
    "online-ham-radio-exam-troubleshooting/index.html": "2d3b8a7686266ed0391b7ddeb956016969ec2e9b",
    "payment/index.html": "0938de3b1a9e5bd0272fc6aa6f0458618ef0fe39",
    "youth-ham-radio-exam/index.html": "659e439ade14bcd2548e8b2b1391e63528a7c07d",
    "after-you-pass-ham-radio-exam/index.html": "e56a05b970a18c9fd7aa301826137b9843b45acd",
    "how-to-get-fcc-frn-ham-radio/index.html": "426469016dc6aaf9a20eab1b0dc4a7689b2fcb49",
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
for guide in (
    "sandarc-online-exam/index.html",
    "free-online-ham-radio-exam/index.html",
):
    assert re.search(
        r'<div class="kicker">SANDARC VEC • WEARC online examinations</div>\s*<h1\b',
        get(guide),
    ), f"SANDARC-specific guide lacks the standard title label: {guide}"


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

# Original homepage outbound and internal URLs must all remain present with
# at least their former occurrence counts. Adding gateway links is allowed.
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
assert "Before you join, review the" not in homepage, "Removed homepage ARRL-specific notice must stay absent"
assert current_hrefs["https://hamradioonlinetest.com/online-ham-radio-exam-checklist/"] == 1, "Keep resource link, not homepage notice"
free_page = get("free-online-ham-radio-exam/index.html")
assert "https://hamradioonlinetest.com/free-online-ham-radio-exam/" in sitemap
assert '<h1 class="h1" data-pagefind-weight="10">Free online ham radio license exams</h1>' in free_page
assert "<!-- FREE_SANDARC_SESSIONS -->" in free_page
assert 'href="https://hamstudy.org/sessions/W2EF/remote"' in free_page
assert "/sandarc-online-exam/" in free_page
assert "ARRL" not in free_page
assert "Take your Technician, General, or Amateur Extra license exam online with WEARC through SANDARC VEC. <strong>The exam session fee is $0.</strong>" in free_page, "Candidate-facing fee, not VEC name, must be emphasized"
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
assert '<div class="kicker">WEARC offers two options</div>' in registration
assert "Choose a VEC below to view available sessions and register on HamStudy." in registration
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
# SANDARC preflight requires a parent/guardian photo ID PLUS a document
# showing the minor's name; the manual (p.28) lists school/library ID.
minor_guidance = sandarc.split('<strong>Under 18 without your own photo ID:</strong>', 1)[1].split('<section class="section" id="exam">', 1)[0]
assert "Bring <strong>both</strong>" in minor_guidance
assert "A parent or guardian must attend, show their own photo ID" in minor_guidance
assert "A separate document bearing the candidate's name" in minor_guidance
assert "<strong>school ID</strong>" in minor_guidance and "<strong>library card</strong>" in minor_guidance
assert "another similar name-bearing document at their discretion" in minor_guidance
assert "verbal confirmation alone are not sufficient" in minor_guidance
assert "a parent or guardian may show their own photo ID and verify" not in sandarc
assert homepage.count("Candidates under 18 without their own photo ID must bring both a parent or guardian with photo ID and a separate document") == 2
assert "The guardian’s ID and verbal verification alone are not sufficient." in homepage
assert "coppa@examtools.org" in sandarc and "before registration" in sandarc.lower()
assert "Policy reference:" not in sandarc
assert "vec.sandarc.org/manual" not in sandarc
assert "SANDARC exam fee: $0" in sandarc
assert "10 calendar days" in sandarc and "attach605@fcc.gov" in sandarc

felony = re.search(r"<p><strong>Felony question:</strong>.*?</p>", sandarc)
assert felony, "SANDARC felony question paragraph missing"
plain = unescape(re.sub(r"<[^>]*>", "", felony.group(0)))
assert plain == "Felony question: SANDARC VEs will not ask about the circumstances. If you answer “Yes” to the FCC Basic Qualification question, SANDARC directs you to submit an explanation with your FCC application number to attach605@fcc.gov within 14 days after the application is submitted.", "Felony question must match approved wording"
assert "SANDARC VEs must not ask about the circumstances." not in sandarc
assert "/exam-instructions/" in sitemap and "/sandarc-online-exam/" in sitemap
print("VEC isolation, SANDARC instructions, and all original ARRL route/link regression checks passed.")
