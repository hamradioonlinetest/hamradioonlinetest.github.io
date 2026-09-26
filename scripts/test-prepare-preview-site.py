#!/usr/bin/env python3
"""Regression tests for preview-only URL rewriting."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("prepare-preview-site.py")


class PreviewRedirectTests(unittest.TestCase):
    def prepare(self, html: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            page = site / "index.html"
            page.write_text(html, encoding="utf-8")
            subprocess.run(
                [sys.executable, str(SCRIPT), str(site)],
                check=True,
                capture_output=True,
                text=True,
            )
            return page.read_text(encoding="utf-8")

    def test_multiline_same_site_location_replace_is_rewritten(self) -> None:
        html = """<script>
window.location.replace(
  "https://hamradioonlinetest.com/online-ham-radio-exam-faq/",
);
</script>
"""
        output = self.prepare(html)
        self.assertIn('"/online-ham-radio-exam-faq/"', output)
        self.assertNotIn("https://hamradioonlinetest.com/online-ham-radio-exam-faq/", output)

    def test_multiline_external_location_replace_is_preserved(self) -> None:
        target = "https://docs.google.com/document/d/example/preview"
        html = f"""<script>
window.location.replace(
  "{target}",
);
</script>
"""
        output = self.prepare(html)
        self.assertIn(target, output)

    def test_multiline_same_site_meta_refresh_is_rewritten(self) -> None:
        html = """<meta
  http-equiv="refresh"
  content="0; url=https://hamradioonlinetest.com/online-ham-radio-exam-checklist/"
>
"""
        output = self.prepare(html)
        self.assertIn("content=\"0; url=/online-ham-radio-exam-checklist/\"", output)
        self.assertNotIn(
            "https://hamradioonlinetest.com/online-ham-radio-exam-checklist/",
            output,
        )

    def test_production_canonical_is_preserved(self) -> None:
        canonical = "https://hamradioonlinetest.com/online-ham-radio-exam-faq/"
        html = f'<link rel="canonical" href="{canonical}">\n'
        output = self.prepare(html)
        self.assertIn(canonical, output)


if __name__ == "__main__":
    unittest.main()
