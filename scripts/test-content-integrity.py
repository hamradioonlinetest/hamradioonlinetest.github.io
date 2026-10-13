#!/usr/bin/env python3
"""Guard FAQ schema accuracy and obsolete asset cleanup in checked-in sources."""
from collections import Counter
from html import unescape
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent.parent


def normalize(text):
    return " ".join(unescape(re.sub(r"<[^>]*>", "", text)).split())


def schema_questions(page):
    found = re.search(r'<script\s+type="application/ld\+json"\s*>(.*?)</script>',
                      page, re.DOTALL)
    assert found, "Missing JSON-LD"
    graph = json.loads(found.group(1)).get("@graph", [])
    nodes = [node for node in graph if node.get("@type") == "FAQPage"]
    assert len(nodes) == 1, "Expected exactly one FAQPage schema"
    entities = nodes[0].get("mainEntity", [])
    assert entities, "Missing FAQPage questions"
    for entry in entities:
        assert entry.get("@type") == "Question"
        assert entry.get("acceptedAnswer", {}).get("text", "").strip()
    return [normalize(entry["name"]) for entry in entities]


def visible_questions(page, homepage):
    if homepage:
        summaries = re.findall(r"<summary\b[^>]*>(.*?)</summary>", page, re.DOTALL)
        return [q for raw in summaries if (q := normalize(raw)).endswith("?")]
    return [normalize(raw) for raw in
            re.findall(r"<h4\b[^>]*>(.*?)</h4>", page, re.DOTALL)]


for name, homepage in (("index.html", True),
                       ("online-ham-radio-exam-faq/index.html", False)):
    page = (ROOT / name).read_text(encoding="utf-8")
    schema = schema_questions(page)
    visible = visible_questions(page, homepage)
    if homepage:
        # Matching ARRL/SANDARC panels intentionally repeat the same eight
        # questions. Duplicates are valid across panels, never within a panel.
        faq = page.split('<div class="vec-faq-panes">', 1)[1]
        arrl = faq.split('<summary>ARRL VEC</summary>', 1)[1].split(
            '<details class="vec-faq-pane">', 1
        )[0]
        sandarc = faq.split('<summary>SANDARC VEC</summary>', 1)[1]
        titles = []
        for panel in (arrl, sandarc):
            questions = [normalize(x) for x in re.findall(
                r'<details>\s*<summary>(.*?)</summary>', panel, re.DOTALL
            )]
            assert len(questions) == len(set(questions)) == 8, (
                f"Duplicate or missing questions within a VEC panel: {name}"
            )
            titles.append(questions)
        assert titles[0] == titles[1], "ARRL/SANDARC FAQ question order differs"
    else:
        assert len(visible) == len(set(visible)), f"Duplicate visible questions: {name}"
    assert Counter(schema) == Counter(visible), (
        f"FAQPage schema mismatches visible questions in {name}: "
        f"schema-only={list((Counter(schema)-Counter(visible)).elements())}; "
        f"visible-only={list((Counter(visible)-Counter(schema)).elements())}"
    )
    if homepage:
        # FAQPage JSON-LD text must accurately represent each visible answer.
        pairs = []
        for panel in (arrl, sandarc):
            for question, answer_markup in re.findall(
                r'<details>\s*<summary>(.*?)</summary>(.*?)</details>',
                panel, re.DOTALL
            ):
                answer = normalize(
                    answer_markup.replace("</p>", " </p>").replace(
                        "</li>", " </li>"
                    )
                )
                pairs.append((normalize(question), answer))
        schema_markup = re.search(
            r'<script\s+type="application/ld\\+json"\s*>(.*?)</script>',
            page, re.DOTALL
        )
        graph = json.loads(schema_markup.group(1))["@graph"]
        entries = next(node for node in graph if node["@type"] == "FAQPage")["mainEntity"]
        assert len(pairs) == len(entries) == 16
        for (question, answer), entry in zip(pairs, entries):
            assert question == normalize(entry["name"]), f"FAQ question schema drift: {question}"
            assert answer == normalize(entry["acceptedAnswer"]["text"]), (
                f"FAQ answer schema drift: {question}"
            )


assert (ROOT / "assets/img/online-ve-exam-example.webp").is_file()
assert "online-ve-exam-example.webp" in (
    ROOT / "online-ham-radio-exam-checklist/index.html"
).read_text(encoding="utf-8")
for obsolete in ("assets/img/online-ve-exam-example.png",
                 "assets/img/online-ve-exam-example-rev2.png",
                 "site.config.json"):
    assert not (ROOT / obsolete).exists(), f"Obsolete file: {obsolete}"

css = (ROOT / "assets/css/styles.css").read_text(encoding="utf-8")
assert ".email-address" not in css and ".zelle-instructions" not in css
print("Content integrity passed: FAQ schema matches visible questions; obsolete assets absent")
