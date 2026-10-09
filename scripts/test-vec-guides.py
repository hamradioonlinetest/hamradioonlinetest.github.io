#!/usr/bin/env python3
"""Ensure VEC candidate routing and critical SANDARC policies do not regress."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]

def get(path):
    return (root / path).read_text(encoding="utf-8")

homepage = get("index.html")
selector = get("exam-instructions/index.html")
sandarc = get("sandarc-online-exam/index.html")
header = get("templates/header.html")
sitemap = get("sitemap.xml")

assert "/exam-instructions/" in homepage and "/sandarc-online-exam/" in homepage
assert "/exam-instructions/" in header
assert "ARRL VEC" in selector and "SANDARC VEC" in selector
assert "/online-ham-radio-exam-checklist/" in selector and "/payment/" in selector
assert "/sandarc-online-exam/" in selector
assert "One camera" in sandarc and "only when necessary" in sandarc
assert "one active monitor or screen" in sandarc.lower()
assert "360-degree room scan" in sandarc
assert "one sheet of scratch paper" not in sandarc
assert "On your desk, keep only the <strong>computer, keyboard, and mouse</strong>" in sandarc
assert "No physical calculator" in sandarc
assert "No headphones or earbuds" in sandarc
assert "<strong>no ID is photographed, recorded, or copied</strong>" not in sandarc
assert "no ID is photographed, recorded, or copied" in sandarc
assert "<strong>No recording:</strong>" not in sandarc
assert "WEARC will disable Zoom recording" not in sandarc
assert "coppa@examtools.org" in sandarc and "before registration" in sandarc.lower()
assert "SANDARC exam fee: $0" in sandarc
assert "10 calendar days" in sandarc and "attach605@fcc.gov" in sandarc
from html import unescape
import re
paragraph = re.search(r"<p><strong>Felony question:</strong>.*?</p>", sandarc)
assert paragraph, "SANDARC felony question paragraph missing"
plain_text = unescape(re.sub(r"<[^>]*>", "", paragraph.group(0)))
assert plain_text == "Felony question: SANDARC VEs will not ask about the circumstances. If you answer “Yes” to the FCC Basic Qualification question, SANDARC directs you to submit an explanation with your FCC application number to attach605@fcc.gov within 14 days after the application is submitted.", "SANDARC felony question must match approved wording"
assert "SANDARC VEs must not ask about the circumstances." not in sandarc
assert "/payment/" not in sandarc, "SANDARC must never link to ARRL payment"
assert "/online-ham-radio-exam-checklist/" not in sandarc
assert "/exam-instructions/" in sitemap and "/sandarc-online-exam/" in sitemap
print("VEC candidate routing and SANDARC policy regression checks passed.")
