#!/usr/bin/env python3
"""Regression tests for the static-site validator."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
