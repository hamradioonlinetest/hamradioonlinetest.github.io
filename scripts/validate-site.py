#!/usr/bin/env python3
"""Validate SEO, structured data, internal links, and basic form accessibility.

The validator intentionally relies only on Python's standard library so it can run
in GitHub Actions without adding a project dependency.
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

BASE_URL = "https://hamradioonlinetest.com/"
BASE_HOST = "hamradioonlinetest.com"
ORG_ID = BASE_URL + "#org"
WEBSITE_ID = BASE_URL + "#website"

EXPECTED_ORG = {
    "name": "West Essex Amateur Radio Club (WEARC)",
    "alternateName": "WEARC",
    "url": BASE_URL,
    "logo": BASE_URL + "assets/img/wearc-logo.png",
    "email": "hamradiotest@osi3.net",
    "telephone": "+1-917-502-2203",
}
EXPECTED_WEBSITE = {
    "name": "Ham Radio Online Test",
    "url": BASE_URL,
}


def normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def attr_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    return {name.lower(): (value or "") for name, value in attrs}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title_count = 0
        self.title_parts: list[str] = []
        self.h1_count = 0
        self.pagefind_body = False
        self.meta_names: dict[str, list[str]] = {}
        self.meta_properties: dict[str, list[str]] = {}
        self.canonicals: list[str] = []
        self.anchors: list[str] = []
        self.inputs: list[dict[str, str]] = []
        self.site_header_mounts = 0
        self.site_footer_mounts = 0
        self.scripts: list[dict[str, str]] = []

        self.in_label = False
        self.current_label_for: str | None = None
        self.current_label_parts: list[str] = []
        self.current_label_inputs: list[dict[str, str]] = []
        self.labels: dict[str, str] = {}

        self.in_jsonld = False
        self.current_jsonld_parts: list[str] = []
        self.jsonld_blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = attr_dict(attrs)

        if tag == "title":
            self.title_count += 1
            self.in_title = True
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "meta":
            name = a.get("name", "").lower()
            prop = a.get("property", "").lower()
            content = a.get("content", "")
            if name:
                self.meta_names.setdefault(name, []).append(content)
            if prop:
                self.meta_properties.setdefault(prop, []).append(content)
        elif tag == "link":
            rel = {token.lower() for token in a.get("rel", "").split()}
            if "canonical" in rel and a.get("href"):
                self.canonicals.append(a["href"])
        elif tag == "a" and a.get("href"):
            self.anchors.append(a["href"])
        elif tag == "label":
            self.in_label = True
            self.current_label_for = a.get("for") or None
            self.current_label_parts = []
            self.current_label_inputs = []
        elif tag == "input":
            self.inputs.append(a)
            if self.in_label:
                self.current_label_inputs.append(a)
        elif tag == "script":
            self.scripts.append(a)
            if a.get("type", "").lower() == "application/ld+json":
                self.in_jsonld = True
                self.current_jsonld_parts = []

        if "data-site-header" in a:
            self.site_header_mounts += 1
        if "data-site-footer" in a:
            self.site_footer_mounts += 1
        if "data-pagefind-body" in a:
            self.pagefind_body = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        elif tag == "label" and self.in_label:
            text = " ".join("".join(self.current_label_parts).split())
            if self.current_label_for:
                self.labels[self.current_label_for] = text
            for input_attrs in self.current_label_inputs:
                input_attrs["_implicit_label"] = text
            self.in_label = False
            self.current_label_for = None
            self.current_label_parts = []
            self.current_label_inputs = []
        elif tag == "script" and self.in_jsonld:
            self.jsonld_blocks.append("".join(self.current_jsonld_parts).strip())
            self.in_jsonld = False
            self.current_jsonld_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.in_label:
            self.current_label_parts.append(data)
        if self.in_jsonld:
            self.current_jsonld_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join("".join(self.title_parts).split())


def find_typed_nodes(data: Any, expected_type: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return

        node_type = node.get("@type")
        types = node_type if isinstance(node_type, list) else [node_type]
        if expected_type in types:
            found.append(node)

        for value in node.values():
            walk(value)

    walk(data)
    return found


def url_to_file(site_root: Path, url: str) -> Path:
    parsed = urlparse(url)
    path = unquote(parsed.path)
    if path == "/" or not path:
        return site_root / "index.html"
    if path.endswith("/"):
        return site_root / path.lstrip("/") / "index.html"

    candidate = site_root / path.lstrip("/")
    if candidate.exists():
        return candidate
    if candidate.suffix:
        return candidate
    return candidate / "index.html"


def validate_jsonld(
    parser: PageParser,
    canonical: str,
    page_label: str,
    errors: list[str],
) -> None:
    if not parser.jsonld_blocks:
        errors.append(f"{page_label}: missing JSON-LD")
        return

    documents: list[Any] = []
    for index, block in enumerate(parser.jsonld_blocks, start=1):
        try:
            documents.append(json.loads(block))
        except json.JSONDecodeError as exc:
            errors.append(f"{page_label}: invalid JSON-LD block {index}: {exc}")

    if not documents:
        return

    org_nodes: list[dict[str, Any]] = []
    site_nodes: list[dict[str, Any]] = []
    webpage_nodes: list[dict[str, Any]] = []
    for document in documents:
        org_nodes.extend(find_typed_nodes(document, "Organization"))
        site_nodes.extend(find_typed_nodes(document, "WebSite"))
        webpage_nodes.extend(find_typed_nodes(document, "WebPage"))

    org_nodes = [node for node in org_nodes if node.get("@id") == ORG_ID]
    site_nodes = [node for node in site_nodes if node.get("@id") == WEBSITE_ID]

    if len(org_nodes) != 1:
        errors.append(
            f"{page_label}: expected exactly one Organization definition with @id {ORG_ID}, "
            f"found {len(org_nodes)}"
        )
    else:
        org = org_nodes[0]
        for key, expected in EXPECTED_ORG.items():
            if org.get(key) != expected:
                errors.append(
                    f"{page_label}: Organization {key} must be {expected!r}, "
                    f"found {org.get(key)!r}"
                )
        same_as = org.get("sameAs")
        if not isinstance(same_as, list) or "https://www.wearc.org/" not in same_as:
            errors.append(f"{page_label}: Organization sameAs must include https://www.wearc.org/")

    if len(site_nodes) != 1:
        errors.append(
            f"{page_label}: expected exactly one WebSite definition with @id {WEBSITE_ID}, "
            f"found {len(site_nodes)}"
        )
    else:
        website = site_nodes[0]
        for key, expected in EXPECTED_WEBSITE.items():
            if website.get(key) != expected:
                errors.append(
                    f"{page_label}: WebSite {key} must be {expected!r}, "
                    f"found {website.get(key)!r}"
                )
        publisher = website.get("publisher")
        if not isinstance(publisher, dict) or publisher.get("@id") != ORG_ID:
            errors.append(f"{page_label}: WebSite publisher must reference {ORG_ID}")

    matching_webpages = [node for node in webpage_nodes if node.get("url") == canonical]
    if len(matching_webpages) != 1:
        errors.append(
            f"{page_label}: expected exactly one WebPage whose url matches canonical "
            f"{canonical}, found {len(matching_webpages)}"
        )


def validate_title(parser: PageParser, page_label: str, errors: list[str]) -> None:
    if parser.title_count != 1 or not parser.title:
        errors.append(
            f"{page_label}: expected exactly one non-empty <title>, "
            f"found {parser.title_count}"
        )


def validate_inputs(parser: PageParser, page_label: str, errors: list[str]) -> None:
    excluded_types = {"hidden", "button", "submit", "reset", "image"}

    for input_attrs in parser.inputs:
        input_type = input_attrs.get("type", "text").lower()
        if input_type in excluded_types:
            continue

        input_id = input_attrs.get("id", "")
        visible_label = parser.labels.get(input_id, "") if input_id else ""
        if not visible_label:
            visible_label = input_attrs.get("_implicit_label", "")
        aria_label = input_attrs.get("aria-label", "").strip()
        aria_labelledby = input_attrs.get("aria-labelledby", "").strip()

        if not visible_label and not aria_label and not aria_labelledby:
            descriptor = input_id or input_attrs.get("name") or "(unnamed input)"
            errors.append(f"{page_label}: input {descriptor!r} has no accessible name")

        if visible_label and aria_label:
            visible_norm = normalize_text(visible_label)
            aria_norm = normalize_text(aria_label)
            if visible_norm and visible_norm not in aria_norm:
                descriptor = input_id or input_attrs.get("name") or "(unnamed input)"
                errors.append(
                    f"{page_label}: input {descriptor!r} has visible label {visible_label!r} "
                    f"but aria-label {aria_label!r}; visible label text must be included "
                    "in the accessible name"
                )


def validate_shared_chrome(
    parser: PageParser,
    canonical: str,
    page_label: str,
    errors: list[str],
) -> None:
    if parser.site_header_mounts != 1:
        errors.append(
            f"{page_label}: expected exactly one data-site-header mount, "
            f"found {parser.site_header_mounts}"
        )

    if parser.site_footer_mounts != 1:
        errors.append(
            f"{page_label}: expected exactly one data-site-footer mount, "
            f"found {parser.site_footer_mounts}"
        )

    main_js_url = BASE_URL + "assets/js/main.js"
    matching_scripts = [
        attrs
        for attrs in parser.scripts
        if attrs.get("src")
        and urljoin(canonical, attrs["src"]) == main_js_url
    ]

    if len(matching_scripts) != 1:
        errors.append(
            f"{page_label}: expected exactly one shared main.js include, "
            f"found {len(matching_scripts)}"
        )
    elif "defer" not in matching_scripts[0]:
        errors.append(f"{page_label}: shared main.js include must use defer")


def validate_internal_links(
    parser: PageParser,
    canonical: str,
    site_root: Path,
    page_label: str,
    errors: list[str],
) -> None:
    checked: set[str] = set()

    for href in parser.anchors:
        href = href.strip()
        if not href or href.startswith("#"):
            continue

        parsed_href = urlparse(href)
        if parsed_href.scheme in {"mailto", "tel", "sms", "javascript", "data"}:
            continue

        absolute = urljoin(canonical, href)
        parsed = urlparse(absolute)
        if parsed.hostname != BASE_HOST:
            continue

        if parsed.scheme != "https":
            errors.append(f"{page_label}: internal link must use HTTPS: {href}")
            continue

        clean_url = parsed._replace(query="", fragment="").geturl()
        if clean_url in checked:
            continue
        checked.add(clean_url)

        target = url_to_file(site_root, clean_url)
        if not target.exists():
            errors.append(f"{page_label}: broken internal link {href} -> {target.relative_to(site_root)}")


def parse_page(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def validate_canonical_page(
    site_root: Path,
    url: str,
    errors: list[str],
) -> None:
    path = url_to_file(site_root, url)
    page_label = str(path.relative_to(site_root))

    if not path.is_file():
        errors.append(f"{url}: sitemap target is missing: {page_label}")
        return

    parser = parse_page(path)

    validate_title(parser, page_label, errors)

    descriptions = parser.meta_names.get("description", [])
    if len(descriptions) != 1 or not descriptions[0].strip():
        errors.append(f"{page_label}: expected exactly one non-empty meta description")

    if parser.canonicals != [url]:
        errors.append(
            f"{page_label}: canonical must exactly match sitemap URL {url}; "
            f"found {parser.canonicals!r}"
        )

    robots_values = parser.meta_names.get("robots", [])
    if len(robots_values) != 1:
        errors.append(f"{page_label}: expected exactly one robots meta tag")
    elif "noindex" in robots_values[0].lower():
        errors.append(f"{page_label}: canonical sitemap page must not be noindex")

    if parser.h1_count != 1:
        errors.append(f"{page_label}: expected exactly one H1, found {parser.h1_count}")

    if not parser.pagefind_body:
        errors.append(f"{page_label}: missing data-pagefind-body")

    site_names = parser.meta_properties.get("og:site_name", [])
    if site_names != ["Ham Radio Online Test"]:
        errors.append(
            f"{page_label}: og:site_name must be 'Ham Radio Online Test'; "
            f"found {site_names!r}"
        )

    validate_jsonld(parser, url, page_label, errors)
    validate_inputs(parser, page_label, errors)
    validate_shared_chrome(parser, url, page_label, errors)
    validate_internal_links(parser, url, site_root, page_label, errors)


def validate_404(site_root: Path, errors: list[str]) -> None:
    path = site_root / "404.html"
    if not path.is_file():
        errors.append("404.html: missing custom 404 page")
        return

    parser = parse_page(path)
    robots_values = parser.meta_names.get("robots", [])
    if len(robots_values) != 1 or "noindex" not in robots_values[0].lower():
        errors.append("404.html: robots meta must contain noindex")
    if parser.pagefind_body:
        errors.append("404.html: error page must not use data-pagefind-body")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate-site.py <site-root>", file=sys.stderr)
        return 2

    site_root = Path(sys.argv[1]).resolve()
    sitemap_path = site_root / "sitemap.xml"
    errors: list[str] = []

    if not sitemap_path.is_file():
        print(f"ERROR: missing sitemap: {sitemap_path}", file=sys.stderr)
        return 1

    try:
        tree = ET.parse(sitemap_path)
    except ET.ParseError as exc:
        print(f"ERROR: invalid sitemap.xml: {exc}", file=sys.stderr)
        return 1

    urls = [
        (element.text or "").strip()
        for element in tree.iter()
        if element.tag.rsplit("}", 1)[-1] == "loc"
    ]
    urls = [url for url in urls if url]

    if not urls:
        errors.append("sitemap.xml: contains no <loc> URLs")

    duplicates = sorted({url for url in urls if urls.count(url) > 1})
    for url in duplicates:
        errors.append(f"sitemap.xml: duplicate URL {url}")

    for url in urls:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != BASE_HOST:
            errors.append(f"sitemap.xml: URL must use {BASE_URL}: {url}")
            continue
        validate_canonical_page(site_root, url, errors)

    validate_404(site_root, errors)

    if errors:
        print(f"Site validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        f"Site validation passed: {len(urls)} canonical sitemap pages, "
        "structured data, shared site chrome, internal links, and basic accessibility checks verified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
