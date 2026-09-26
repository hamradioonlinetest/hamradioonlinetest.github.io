#!/usr/bin/env python3
"""Prepare a validated production build for an isolated preview host.

Production pages intentionally use absolute hamradioonlinetest.com URLs in many
places. For a deploy preview, those asset/navigation URLs must stay on the
preview host so visual changes can actually be reviewed.

This script operates only on the already-built _site directory. It does not
modify source pages.
"""

from __future__ import annotations

import sys
from pathlib import Path

PRODUCTION_ORIGIN = "https://hamradioonlinetest.com"


def rewrite_html(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    original = text
    lines = []

    replacements = (
        ('href="' + PRODUCTION_ORIGIN + '/', 'href="/'),
        ("href='" + PRODUCTION_ORIGIN + "/", "href='/"),
        ('src="' + PRODUCTION_ORIGIN + '/', 'src="/'),
        ("src='" + PRODUCTION_ORIGIN + "/", "src='/"),
        ('action="' + PRODUCTION_ORIGIN + '/', 'action="/'),
        ("action='" + PRODUCTION_ORIGIN + "/", "action='/"),
    )

    for line in text.splitlines(keepends=True):
        # Keep the production canonical intact even on preview copies.
        if 'rel="canonical"' not in line and "rel='canonical'" not in line:
            for old, new in replacements:
                line = line.replace(old, new)
        lines.append(line)

    text = "".join(lines)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return 1
    return 0


def rewrite_text_asset(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    original = text

    # Shared JS creates the site header/footer from quoted absolute URLs.
    text = text.replace('"' + PRODUCTION_ORIGIN + '/', '"/')
    text = text.replace("'" + PRODUCTION_ORIGIN + "/", "'/")

    # CSS or manifests may use unquoted absolute asset references.
    text = text.replace(PRODUCTION_ORIGIN + "/", "/")

    if text != original:
        path.write_text(text, encoding="utf-8")
        return 1
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: prepare-preview-site.py <site-directory>", file=sys.stderr)
        return 2

    site = Path(sys.argv[1]).resolve()
    if not site.is_dir():
        print(f"Preview site directory not found: {site}", file=sys.stderr)
        return 2

    changed = 0

    for path in site.rglob("*.html"):
        changed += rewrite_html(path)

    for pattern in ("*.js", "*.css", "*.webmanifest"):
        for path in site.rglob(pattern):
            changed += rewrite_text_asset(path)

    # Defense in depth. Netlify also sends an X-Robots-Tag noindex header.
    (site / "robots.txt").write_text(
        "User-agent: *\nDisallow: /\n",
        encoding="utf-8",
    )

    print(f"Preview preparation complete: rewrote {changed} files; indexing disabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
