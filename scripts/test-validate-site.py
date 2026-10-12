#!/usr/bin/env python3
"""Regression tests for the static-site validator."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

VALIDATOR_PATH = Path(__file__).with_name("validate-site.py")
SPEC = importlib.util.spec_from_file_location("validate_site", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load validator from {VALIDATOR_PATH}")

validate_site = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate_site)


class ValidatorTests(unittest.TestCase):
    def parse(self, html: str):
        parser = validate_site.PageParser()
        parser.feed(html)
        parser.close()
        return parser

    def test_sitemap_requires_every_indexable_self_canonical_page(self) -> None:
        with TemporaryDirectory() as folder:
            site = Path(folder)
            (site / "index.html").write_text(
                '<link rel="canonical" href="https://hamradioonlinetest.com/">'
                '<meta name="robots" content="index,follow">'
            )
            (site / "free-online-ham-radio-exam").mkdir()
            (site / "free-online-ham-radio-exam/index.html").write_text(
                '<link rel="canonical" href="https://hamradioonlinetest.com/free-online-ham-radio-exam/">'
                '<meta name="robots" content="index,follow">'
            )
            errors: list[str] = []
            validate_site.validate_sitemap_completeness(
                site, ["https://hamradioonlinetest.com/"], errors
            )
            self.assertEqual(len(errors), 1)
            self.assertIn("/free-online-ham-radio-exam/", errors[0])

    def test_sitemap_rejects_indexable_page_without_canonical(self) -> None:
        with TemporaryDirectory() as folder:
            site = Path(folder)
            (site / "new-guide").mkdir()
            (site / "new-guide/index.html").write_text(
                '<title>New public guide</title>'
                '<meta name="robots" content="index,follow">'
            )
            errors: list[str] = []
            validate_site.validate_sitemap_completeness(site, [], errors)
            self.assertEqual(len(errors), 1)
            self.assertIn("new-guide/index.html", errors[0])
            self.assertIn("missing canonical", errors[0])

    def test_sitemap_excludes_redirects_and_noindex(self) -> None:
        with TemporaryDirectory() as folder:
            site = Path(folder)
            destination = "https://hamradioonlinetest.com/destination/"
            (site / "redirect").mkdir()
            (site / "redirect/index.html").write_text(
                f'<link rel="canonical" href="{destination}">'
                f'<meta http-equiv="refresh" content="0; url={destination}">'
            )
            (site / "destination").mkdir()
            (site / "destination/index.html").write_text(
                f'<link rel="canonical" href="{destination}">'
            )
            (site / "internal").mkdir()
            (site / "internal/index.html").write_text(
                '<link rel="canonical" href="https://hamradioonlinetest.com/internal/">'
                '<meta name="robots" content="noindex,follow">'
            )
            errors: list[str] = []
            validate_site.validate_sitemap_completeness(site, [destination], errors)
            self.assertEqual(errors, [])

    def test_sitemap_catches_wrong_or_duplicate_canonicals_without_redirect(self) -> None:
        canonical = "https://hamradioonlinetest.com/another-page/"
        page_cases = {
            "wrong_canonical_without_redirect":
                f'<link rel="canonical" href="{canonical}">',
            "duplicate_canonicals_even_with_redirect":
                f'<link rel="canonical" href="{canonical}">'
                f'<link rel="canonical" href="{canonical}">'
                f'<meta http-equiv="refresh" content="0; url={canonical}">',
            "wrong_refresh_target":
                f'<link rel="canonical" href="{canonical}">'
                '<meta http-equiv="refresh" content="0; url=https://hamradioonlinetest.com/other/">',
            "non_immediate_refresh":
                f'<link rel="canonical" href="{canonical}">'
                f'<meta http-equiv="refresh" content="5; url={canonical}">',
        }
        for case, html in page_cases.items():
            with self.subTest(case=case), TemporaryDirectory() as folder:
                site = Path(folder)
                (site / "new-guide").mkdir()
                (site / "new-guide/index.html").write_text(html)
                errors: list[str] = []
                validate_site.validate_sitemap_completeness(site, [], errors)
                self.assertEqual(len(errors), 1)
                self.assertIn("canonical must match", errors[0])

    def test_sitemap_allows_explicit_matching_immediate_redirect(self) -> None:
        with TemporaryDirectory() as folder:
            site = Path(folder)
            destination = "https://hamradioonlinetest.com/new-guide/"
            (site / "old-guide").mkdir()
            (site / "old-guide/index.html").write_text(
                f'<link rel="canonical" href="{destination}">'
                f'<meta http-equiv="refresh" content="0; url={destination}">'
            )
            (site / "new-guide").mkdir()
            (site / "new-guide/index.html").write_text(
                f'<link rel="canonical" href="{destination}">'
            )
            errors: list[str] = []
            validate_site.validate_sitemap_completeness(site, [destination], errors)
            self.assertEqual(errors, [])

    def test_sitemap_rejects_redirect_to_missing_or_unlisted_target(self) -> None:
        target = "https://hamradioonlinetest.com/new-guide/"
        for case in ("missing_and_unlisted", "exists_but_unlisted", "listed_but_missing"):
            with self.subTest(case=case), TemporaryDirectory() as folder:
                site = Path(folder)
                (site / "old-guide").mkdir()
                (site / "old-guide/index.html").write_text(
                    f'<link rel="canonical" href="{target}">'
                    f'<meta http-equiv="refresh" content="0; url={target}">'
                )
                if case == "exists_but_unlisted":
                    (site / "new-guide").mkdir()
                    (site / "new-guide/index.html").write_text(
                        f'<link rel="canonical" href="{target}">'
                    )
                listed = [target] if case == "listed_but_missing" else []
                errors: list[str] = []
                validate_site.validate_sitemap_completeness(site, listed, errors)
                if case == "exists_but_unlisted":
                    self.assertEqual(len(errors), 2)
                    self.assertTrue(any("missing indexable canonical" in e for e in errors))
                else:
                    self.assertEqual(len(errors), 1)
                self.assertTrue(any(
                    "redirect destination is missing" in e
                    if case == "listed_but_missing"
                    else "redirect destination is not in sitemap.xml" in e
                    for e in errors
                ))

    def test_sitemap_rejects_conflicting_or_malformed_refresh_tags(self) -> None:
        target = "https://hamradioonlinetest.com/new-guide/"
        for extra in (
            f'<meta http-equiv="refresh" content="5; url={target}">',
            '<meta http-equiv="refresh" content="malformed">',
            f'<meta http-equiv="refresh" content="0; url={target}">',
            '<meta http-equiv="refresh">',
        ):
            with self.subTest(extra=extra), TemporaryDirectory() as folder:
                site = Path(folder)
                (site / "old-guide").mkdir()
                (site / "old-guide/index.html").write_text(
                    f'<link rel="canonical" href="{target}">'
                    f'<meta http-equiv="refresh" content="0; url={target}">'
                    + extra
                )
                (site / "new-guide").mkdir()
                (site / "new-guide/index.html").write_text(
                    f'<link rel="canonical" href="{target}">'
                )
                errors: list[str] = []
                validate_site.validate_sitemap_completeness(site, [target], errors)
                self.assertEqual(len(errors), 1)
                self.assertIn("refresh tags 2", errors[0])

    def test_sitemap_rejects_empty_second_canonical(self) -> None:
        target = "https://hamradioonlinetest.com/new-guide/"
        with TemporaryDirectory() as folder:
            site = Path(folder)
            (site / "old-guide").mkdir()
            (site / "old-guide/index.html").write_text(
                f'<link rel="canonical" href="{target}">'
                '<link rel="canonical">'
                f'<meta http-equiv="refresh" content="0; url={target}">'
            )
            (site / "new-guide").mkdir()
            (site / "new-guide/index.html").write_text(
                f'<link rel="canonical" href="{target}">'
            )
            errors: list[str] = []
            validate_site.validate_sitemap_completeness(site, [target], errors)
            self.assertEqual(len(errors), 1)
            self.assertIn("canonical must match", errors[0])

    def test_noindex_redirect_requires_valid_destination_and_refresh(self) -> None:
        target = "https://hamradioonlinetest.com/new-guide/"
        for case in ("valid", "unlisted", "missing", "duplicate_refresh", "wrong_canonical"):
            with self.subTest(case=case), TemporaryDirectory() as folder:
                site = Path(folder)
                (site / "old-guide").mkdir()
                extra = (
                    f'<meta http-equiv="refresh" content="2; url={target}">'
                    if case == "duplicate_refresh" else ""
                )
                canonical = (
                    "https://hamradioonlinetest.com/wrong/"
                    if case == "wrong_canonical" else target
                )
                (site / "old-guide/index.html").write_text(
                    '<meta name="robots" content="noindex,follow">'
                    f'<link rel="canonical" href="{canonical}">'
                    f'<meta http-equiv="refresh" content="0; url={target}">'
                    + extra
                )
                if case != "missing":
                    (site / "new-guide").mkdir()
                    (site / "new-guide/index.html").write_text(
                        f'<link rel="canonical" href="{target}">'
                    )
                urls = [] if case == "unlisted" else [target]
                errors: list[str] = []
                validate_site.validate_sitemap_completeness(site, urls, errors)
                if case == "valid":
                    self.assertEqual(errors, [])
                else:
                    self.assertTrue(
                        any(
                            "redirect destination" in error
                            or "canonical must match" in error
                            for error in errors
                        ),
                        errors,
                    )

    def test_operational_noindex_without_redirect_remains_exempt(self) -> None:
        with TemporaryDirectory() as folder:
            site = Path(folder)
            (site / "private").mkdir()
            (site / "private/index.html").write_text(
                '<meta name="robots" content="noindex,follow">'
            )
            errors: list[str] = []
            validate_site.validate_sitemap_completeness(site, [], errors)
            self.assertEqual(errors, [])

    def test_private_ve_script_external_redirect_is_explicitly_allowed(self) -> None:
        target = validate_site.EXTERNAL_NOINDEX_REDIRECTS["vescript/index.html"]
        for case in ("valid", "duplicate", "wrong_destination", "late",
                     "javascript_redirect", "external_script"):
            with self.subTest(case=case), TemporaryDirectory() as folder:
                site = Path(folder)
                (site / "vescript").mkdir()
                refresh = (
                    f'<meta http-equiv="refresh" content="0; url={target}">'
                )
                if case == "duplicate":
                    refresh += refresh
                elif case == "wrong_destination":
                    refresh = (
                        '<meta http-equiv="refresh" content="0; url=https://example.org/">'
                    )
                elif case == "late":
                    refresh = f'<meta http-equiv="refresh" content="5; url={target}">'
                script = ""
                if case == "javascript_redirect":
                    script = '<script>window.location.replace("https://example.org/")</script>'
                elif case == "external_script":
                    script = '<script src="https://example.org/redirect.js"></script>'
                (site / "vescript/index.html").write_text(
                    '<meta name="robots" content="noindex,nofollow">' + refresh + script
                )
                errors: list[str] = []
                validate_site.validate_sitemap_completeness(site, [], errors)
                if case == "valid":
                    self.assertEqual(errors, [])
                else:
                    self.assertEqual(len(errors), 1)
                    self.assertIn("invalid private external redirect", errors[0])

    def test_implicit_label_gives_input_an_accessible_name(self) -> None:
        parser = self.parse(
            '<label>FCC FRN <input id="frn" name="frn" type="text"></label>'
        )
        errors: list[str] = []
        validate_site.validate_inputs(parser, "fixture.html", errors)
        self.assertEqual(errors, [])

    def test_implicit_label_still_enforces_label_in_name(self) -> None:
        parser = self.parse(
            '<label>FCC FRN '
            '<input id="frn" name="frn" type="text" aria-label="FRN">'
            '</label>'
        )
        errors: list[str] = []
        validate_site.validate_inputs(parser, "fixture.html", errors)
        self.assertEqual(len(errors), 1)
        self.assertIn("visible label 'FCC FRN'", errors[0])

    def test_duplicate_titles_are_rejected(self) -> None:
        parser = self.parse("<title>First</title><title>Second</title>")
        errors: list[str] = []
        validate_site.validate_title(parser, "fixture.html", errors)
        self.assertEqual(len(errors), 1)
        self.assertIn("expected exactly one non-empty <title>", errors[0])

    def test_single_nonempty_title_is_accepted(self) -> None:
        parser = self.parse("<title>Ham Radio Online Test</title>")
        errors: list[str] = []
        validate_site.validate_title(parser, "fixture.html", errors)
        self.assertEqual(errors, [])

    def test_shared_site_chrome_is_accepted(self) -> None:
        parser = self.parse(
            '<header data-site-header><nav><a href="/">Home</a></nav></header>'
            '<footer data-site-footer>Contact</footer>'
            '<script src="https://hamradioonlinetest.com/assets/js/main.js" defer></script>'
        )
        errors: list[str] = []
        validate_site.validate_shared_chrome(
            parser,
            "https://hamradioonlinetest.com/example/",
            "fixture.html",
            errors,
        )
        self.assertEqual(errors, [])

    def test_shared_site_chrome_requires_footer_and_defer(self) -> None:
        parser = self.parse(
            '<header data-site-header><nav><a href="/">Home</a></nav></header>'
            '<script src="/assets/js/main.js"></script>'
        )
        errors: list[str] = []
        validate_site.validate_shared_chrome(
            parser,
            "https://hamradioonlinetest.com/example/",
            "fixture.html",
            errors,
        )
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("data-site-footer" in error for error in errors))
        self.assertTrue(any("must use defer" in error for error in errors))

    def test_shared_site_chrome_rejects_async_with_defer(self) -> None:
        parser = self.parse(
            '<header data-site-header><nav><a href="/">Home</a></nav></header>'
            '<footer data-site-footer>Contact</footer>'
            '<script src="/assets/js/main.js" async defer></script>'
        )
        errors: list[str] = []
        validate_site.validate_shared_chrome(
            parser,
            "https://hamradioonlinetest.com/example/",
            "fixture.html",
            errors,
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("must not use async with defer", errors[0])


if __name__ == "__main__":
    unittest.main()
