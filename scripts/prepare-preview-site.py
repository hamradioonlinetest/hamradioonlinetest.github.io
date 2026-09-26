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

            # Legacy alias pages also redirect with meta refresh and JavaScript.
            # Keep those redirects on the preview host too.
            lowered = line.lower()
            is_meta_refresh = (
                'http-equiv="refresh"' in lowered
                or "http-equiv='refresh'" in lowered
            )
            is_script_redirect = any(
                marker in lowered
                for marker in (
                    "location.replace(",
                    "location.assign(",
                    "location.href",
                )
            )
            if is_meta_refresh or is_script_redirect:
                line = line.replace(PRODUCTION_ORIGIN + "/", "/")
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

    # Verify ordinary HTML assets/navigation can no longer escape to production.
    escaped = []
    for path in site.rglob("*.html"):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if 'rel="canonical"' in line or "rel='canonical'" in line:
                continue
            lowered = line.lower()
            ordinary_escape = any(
                marker in line
                for marker in (
                    'href="' + PRODUCTION_ORIGIN + '/',
                    "href='" + PRODUCTION_ORIGIN + "/",
                    'src="' + PRODUCTION_ORIGIN + '/',
                    "src='" + PRODUCTION_ORIGIN + "/",
                    'action="' + PRODUCTION_ORIGIN + '/',
                    "action='" + PRODUCTION_ORIGIN + "/",
                )
            )
            redirect_escape = (
                PRODUCTION_ORIGIN + "/" in line
                and (
                    'http-equiv="refresh"' in lowered
                    or "http-equiv='refresh'" in lowered
                    or "location.replace(" in lowered
                    or "location.assign(" in lowered
                    or "location.href" in lowered
                )
            )
            if ordinary_escape or redirect_escape:
                escaped.append(f"{path.relative_to(site)}:{line_number}")

    if escaped:
        print("Preview preparation left production-host asset/navigation references:", file=sys.stderr)
        for location in escaped[:20]:
            print(f"  {location}", file=sys.stderr)
        return 1

    # Defense in depth. Netlify also sends an X-Robots-Tag noindex header.
    (site / "robots.txt").write_text(
        "User-agent: *\nDisallow: /\n",
        encoding="utf-8",
    )

    print(f"Preview preparation complete: rewrote {changed} files; indexing disabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
