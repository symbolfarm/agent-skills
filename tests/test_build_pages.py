from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_pages", ROOT / "tools" / "build_pages.py")
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)
FIXTURE = ROOT / "tests" / "fixtures" / "page-substrate"
# The builder no longer lives in a site repository, so its one end-to-end test
# against real committed output needs that site checked out beside this one.
# Skipped rather than failed when it is absent: agent-skills is public and
# clonable on its own.
ADUS = ROOT.parent / "adus-intelligence"


class BuilderTests(unittest.TestCase):
    def fixture_config(self, directory: Path, source: Path = FIXTURE) -> Path:
        meta = {
            "layer": "synthesis",
            "audience": "project contributor",
            "as_of": "2026-09-09",
            "status": "current version",
            "provenance": "committed page-substrate fixture",
            "not_human_reviewed": True,
        }
        config = {
            "description": "Explainer fixture",
            "brand": "Fixture",
            "output": str(directory / "output"),
            "stylesheet": "assets/styles.css",
            "pages": [
                {"source": str(source / "index.md"), "output": "index.html", "title": "Fixture", "explainer": meta},
                {"source": str(source / "second.md"), "output": "nested/second.html", "title": "Second", "explainer": meta},
            ],
            "navigation": [
                {"page": "index.html", "label": "Fixture"},
                {"page": "nested/second.html", "label": "Second"},
            ],
            "assets": [
                {"source": str(source / "diagram.svg"), "output": "assets/diagram.svg"},
                {"source": str(source / "styles.css"), "output": "assets/styles.css"},
            ],
        }
        path = directory / "site.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    @unittest.skipUnless((ADUS / "site" / "site.json").is_file(), "adus-intelligence not checked out beside this repository")
    def test_default_adus_build_is_byte_identical(self) -> None:
        site = builder.load_site(ADUS / "site" / "site.json")
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp)
            builder.build(site, candidate)
            self.assertEqual(builder.file_map(candidate), builder.file_map(ADUS / "docs"))

    def test_default_config_is_found_under_the_working_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with self.assertRaises(ValueError):
                builder.default_config(directory)
            nested = directory / "site"
            nested.mkdir()
            (nested / "site.json").write_text("{}", encoding="utf-8")
            self.assertEqual(builder.default_config(directory), nested / "site.json")
            (directory / "site.json").write_text("{}", encoding="utf-8")
            self.assertEqual(builder.default_config(directory), directory / "site.json")

    def test_portfolio_fixture_svg_assets_routes_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            site = builder.load_site(self.fixture_config(directory))
            builder.build(site, site.output)
            index = (site.output / "index.html").read_text(encoding="utf-8")
            second = (site.output / "nested" / "second.html").read_text(encoding="utf-8")
            self.assertIn('<svg id="inline-mark"', index)
            self.assertNotIn("&lt;svg", index)
            self.assertIn('href="nested/second.html"', index)
            self.assertIn('src="assets/diagram.svg"', index)
            self.assertIn("Not human-reviewed", index)
            self.assertIn("committed page-substrate fixture", index)
            self.assertIn('href="../index.html"', second)
            self.assertIn('href="../assets/styles.css"', second)
            self.assertEqual((site.output / "assets" / "diagram.svg").read_bytes(), (FIXTURE / "diagram.svg").read_bytes())

    def test_explainer_metadata_is_required_as_a_complete_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            config_path = self.fixture_config(directory)
            raw = json.loads(config_path.read_text(encoding="utf-8"))
            del raw["pages"][0]["explainer"]["provenance"]
            config_path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "explainer missing: provenance"):
                builder.load_site(config_path)

    def test_svg_passthrough_rejects_script_event_and_external_fetch(self) -> None:
        unsafe = [
            '<svg viewBox="0 0 1 1" role="img" aria-label="x"><script>alert(1)</script></svg>',
            '<svg viewBox="0 0 1 1" role="img" aria-label="x" onclick="alert(1)"></svg>',
            '<svg viewBox="0 0 1 1" role="img" aria-label="x"><image href="https://example.com/x.png"/></svg>',
        ]
        for raw_svg in unsafe:
            with self.subTest(raw_svg=raw_svg):
                with self.assertRaises(ValueError):
                    builder.audit_svg(raw_svg, Path("unsafe.md"))

    def test_svg_passthrough_requires_complete_accessible_svg(self) -> None:
        with self.assertRaisesRegex(ValueError, "viewBox"):
            builder.audit_svg('<svg role="img" aria-label="x"></svg>', Path("bad.md"))
        with self.assertRaisesRegex(ValueError, "aria-label"):
            builder.audit_svg('<svg viewBox="0 0 1 1"></svg>', Path("bad.md"))
        with self.assertRaisesRegex(ValueError, "incomplete"):
            builder.take_svg(["<svg viewBox=\"0 0 1 1\">"], 0, Path("bad.md"))


if __name__ == "__main__":
    unittest.main()
