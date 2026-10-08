from __future__ import annotations

import importlib.util
import json
import re
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
COMPONENTS = ROOT / "tests" / "fixtures" / "altitude-page"
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

class ComponentTests(unittest.TestCase):
    """The closed three-component vocabulary and stylesheet inlining."""

    def render(self, markdown: str, directory: Path) -> str:
        source = directory / "page.md"
        source.write_text(markdown, encoding="utf-8")
        config = {
            "output": str(directory / "output"),
            "pages": [{"source": str(source), "output": "index.html", "title": "Components"}],
        }
        path = directory / "site.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        site = builder.load_site(path)
        body, _ = builder.render_markdown(site, site.pages[0], {})
        return body

    def render_in_tmp(self, markdown: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            return self.render(markdown, Path(tmp))

    def test_reading_component_renders_the_best_alternative_pair(self) -> None:
        body = self.render_in_tmp(
            "```:reading\n"
            "@best\n"
            "label: The decision\n"
            "title: A, B, C or D\n"
            "\n"
            "The timeline in `s3` supports it.\n"
            "\n"
            "@alternative\n"
            "label: Going deeper\n"
            "title: The layer below\n"
            "\n"
            "The detail is in the digest.\n"
            "```\n"
        )
        self.assertIn('<div class="reading"><div class="best">', body)
        self.assertIn('<span class="label">The decision</span><h3>A, B, C or D</h3>', body)
        self.assertIn("<p>The timeline in <code>s3</code> supports it.</p></div>", body)
        self.assertIn('<div class="alternative"><span class="label">Going deeper</span>', body)
        self.assertTrue(body.strip().endswith("</div></div>"))
        # An unpaired reading is malformed: the pair is the component.
        with self.assertRaisesRegex(ValueError, "exactly @best then @alternative"):
            self.render_in_tmp("```:reading\n@best\ntitle: Alone\n\nBody.\n```\n")

    def test_option_component_carries_a_verdict_label(self) -> None:
        body = self.render_in_tmp(
            "```:option\n"
            "@option\n"
            "verdict: recommended\n"
            "title: B. Graduate the substrate\n"
            "\n"
            "Run it on a model **not** built for it.\n"
            "\n"
            "@option\n"
            "verdict: strong second\n"
            "title: C. Redirect to routing\n"
            "\n"
            "A router picks the block.\n"
            "```\n"
        )
        self.assertIn('<div class="four"><article class="opt">', body)
        self.assertIn('<span class="verdict">recommended</span><h3>B. Graduate the substrate</h3>', body)
        self.assertIn("<p>Run it on a model <strong>not</strong> built for it.</p></article>", body)
        self.assertEqual(body.count('<article class="opt">'), 2)
        with self.assertRaisesRegex(ValueError, "needs a 'verdict' field"):
            self.render_in_tmp("```:option\n@option\ntitle: No verdict\n\nBody.\n```\n")

    def test_status_component_renders_pill_rows_in_three_variants(self) -> None:
        body = self.render_in_tmp(
            "```:status\n"
            "@built\n"
            "**Charters exist and work.**\n"
            "\n"
            "@designed\n"
            "The entry-point skill. *Not written.*\n"
            "\n"
            "@open\n"
            "Where priority lives.\n"
            "```\n"
        )
        self.assertIn('<div class="state"><span class="pill built">built</span>', body)
        self.assertIn("<div><strong>Charters exist and work.</strong></div>", body)
        self.assertIn('<span class="pill designed">designed</span>', body)
        self.assertIn('<span class="pill open">open</span><div>Where priority lives.</div></div>', body)
        with self.assertRaisesRegex(ValueError, "pill must be one of"):
            self.render_in_tmp("```:status\n@shipped\nBody.\n```\n")

    def test_unknown_or_malformed_directive_fails_the_build_with_file_and_line(self) -> None:
        cases = (
            ("```:timeline\n@row\nBody.\n```\n", r"page\.md:1: unknown block directive ':timeline'"),
            ("Prose.\n\n```:reading extra\n@best\n```\n", r"page\.md:3: malformed block directive"),
            ("```:reading\n@best\ntitle: T\n\nBody.\n", r"page\.md:1: unterminated"),
            ("```:status\nOrphan prose.\n@built\nBody.\n```\n", r"page\.md:2: ':status' content before the first @entry"),
            ("```:option\n@option\nverdict: v\nweight: 3\ntitle: T\n\nBody.\n```\n", r"page\.md:4: ':option' @option has unknown field 'weight'"),
            ("```:reading\n@best\ntitle: T\n\nBody.\n\n@alternative\ntitle: T2\n```\n", r"page\.md:7: ':reading' @alternative has no body text"),
        )
        for markdown, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(ValueError, expected):
                    self.render_in_tmp(markdown)

    def test_an_ordinary_code_fence_is_still_a_code_block(self) -> None:
        body = self.render_in_tmp("```sh\npython3 build_pages.py --check\n```\n")
        self.assertIn("<pre><code>python3 build_pages.py --check</code></pre>", body)

    def test_inline_stylesheet_embeds_the_css_and_makes_no_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = directory / "page.md"
            source.write_text("# Page\n\nBody.\n", encoding="utf-8")
            css = directory / "theme.css"
            css.write_text(":root{--ink:#111}\nbody{color:var(--ink)}\n", encoding="utf-8")
            config = {
                "output": str(directory / "output"),
                "stylesheet": "theme.css",
                "inline_stylesheet": "theme.css",
                "pages": [{"source": str(source), "output": "index.html", "title": "Page"}],
            }
            path = directory / "site.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            site = builder.load_site(path)
            builder.build(site, site.output)
            page = (site.output / "index.html").read_text(encoding="utf-8")
            self.assertIn("<style>\n:root{--ink:#111}\nbody{color:var(--ink)}\n  </style>", page)
            self.assertNotIn("<link rel=\"stylesheet\"", page)
            self.assertFalse((site.output / "theme.css").exists())

            # Linking, not inlining, stays the default for sites that omit it.
            del config["inline_stylesheet"]
            config["assets"] = [{"source": "theme.css", "output": "theme.css"}]
            path.write_text(json.dumps(config), encoding="utf-8")
            linked = builder.load_site(path)
            builder.build(linked, linked.output)
            page = (linked.output / "index.html").read_text(encoding="utf-8")
            self.assertIn('<link rel="stylesheet" href="theme.css">', page)
            self.assertNotIn("<style>", page)

    def test_inlined_stylesheet_must_be_self_contained(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            css = Path(tmp) / "theme.css"
            css.write_text("@import url('other.css');\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "@import"):
                builder.inline_stylesheet_css(css)
            css.write_text("body{background:url(https://example.com/x.png)}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "may not reference"):
                builder.inline_stylesheet_css(css)


class AltitudeFixtureTests(unittest.TestCase):
    """The proof obligation: an altitude page's shape from Markdown source.

    The page this reproduces is a private hand-authored page of 2026-09-16; it
    stays hand-authored and is not converted. The fixture asserts component
    structure, not byte identity -- whitespace, attribute order and the
    generated page shell all differ from the published page.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        directory = Path(cls._tmp.name)
        config = {
            "description": "An altitude page reproduced from Markdown as a fixture",
            "brand": "Altitude fixture",
            "output": str(directory / "output"),
            "stylesheet": "styles.css",
            "inline_stylesheet": str(COMPONENTS / "styles.css"),
            "pages": [
                {
                    "source": str(COMPONENTS / "altitude.md"),
                    "output": "altitude.html",
                    "title": "What this lane is for — 2026-09-16",
                    "explainer": {
                        "layer": "altitude",
                        "audience": "portfolio owner, deciding direction",
                        "as_of": "2026-09-16",
                        "status": "current version",
                        "provenance": "reproduced from a hand-authored 2026-09-16 altitude page",
                        "not_human_reviewed": True,
                    },
                },
                {"source": str(COMPONENTS / "status.md"), "output": "status.html", "title": "The chain as it stands"},
            ],
            "navigation": [{"page": "altitude.html", "label": "Altitude"}],
        }
        path = directory / "site.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        cls.site = builder.load_site(path)
        builder.build(cls.site, cls.site.output)
        cls.page = (cls.site.output / "altitude.html").read_text(encoding="utf-8")
        cls.status = (cls.site.output / "status.html").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_the_reading_pair_is_present_and_nested_as_the_published_page_nests_it(self) -> None:
        self.assertIn('<div class="reading"><div class="best">', self.page)
        self.assertIn('<span class="label">The decision</span>', self.page)
        self.assertIn('<div class="alternative"><span class="label">If you want to go deeper</span>', self.page)
        self.assertEqual(self.page.count('<div class="reading">'), 1)

    def test_every_option_card_carries_its_verdict(self) -> None:
        self.assertEqual(self.page.count('<article class="opt">'), 4)
        for verdict in ("not recommended", "recommended", "strong second", "viable, and no failure"):
            self.assertIn(f'<span class="verdict">{verdict}</span>', self.page)

    def test_the_status_pill_row_carries_all_three_variants(self) -> None:
        # The altitude page carries no pill row; the sibling fixture page does.
        self.assertNotIn('class="pill', self.page)
        self.assertIn('<div class="state"><span class="pill built">built</span>', self.status)
        for variant in ("built", "designed", "open"):
            self.assertIn(f'<span class="pill {variant}">{variant}</span>', self.status)

    def test_both_diagrams_survive_as_svg_elements(self) -> None:
        self.assertEqual(self.page.count("<svg viewBox="), 2)
        self.assertNotIn("&lt;svg", self.page)
        self.assertIn('aria-labelledby="cw-t cw-d"', self.page)
        self.assertIn('fill="var(--accent)"', self.page)

    def test_the_page_stands_alone_with_no_script_or_external_reference(self) -> None:
        self.assertIn("<style>", self.page)
        self.assertNotIn("<link rel=\"stylesheet\"", self.page)
        self.assertNotIn("<script", self.page)
        for attribute, target in re.findall(r'(href|src)="([^"]+)"', self.page):
            with self.subTest(target=target):
                self.assertFalse(target.startswith(("http://", "https://", "//")), f"{attribute} reaches out to {target}")


DIGEST = """---
title: A foundation the next lesson builds on
reader: project owner, oriented on the programme
date: 2026-09-30
charter: EX-C4
status: agent-authored; not human-reviewed
summary: Holding A lets B be learned from its own lesson.
---

## What changed

Oracle text reaches the ceiling. See [the record](../notebook/r3.md).

```:status
@built
A calibrated curriculum.
@open
Construction's case.
```
"""


class DigestTests(unittest.TestCase):
    def render(self, text: str, **kw) -> str:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "digest.md"
            source.write_text(text, encoding="utf-8")
            return builder.render_document(source, **kw)

    def test_digest_renders_title_declaration_and_components_standalone(self) -> None:
        page = self.render(DIGEST)
        self.assertIn("<title>A foundation the next lesson builds on</title>", page)
        declaration = re.search(r'<aside class="digest-meta".*?</aside>', page, re.DOTALL).group(0)
        for value in ("project owner, oriented on the programme", "2026-09-30", "EX-C4", "not human-reviewed"):
            self.assertIn(value, declaration)
        self.assertLess(page.index("</h1>"), page.index("<aside class=\"digest-meta\""))
        self.assertIn('class="pill open"', page)
        self.assertIn('href="../notebook/r3.md"', page)
        self.assertNotIn("<link", page)
        self.assertNotIn("reader:", page)

    def test_digest_front_matter_is_required_and_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing: reader"):
            self.render(DIGEST.replace("reader: project owner, oriented on the programme\n", ""))
        with self.assertRaisesRegex(ValueError, "YYYY-MM-DD"):
            self.render(DIGEST.replace("2026-09-30", "30 Sep"))
        with self.assertRaisesRegex(ValueError, "unknown digest front matter: verdict"):
            self.render(DIGEST.replace("summary:", "verdict: yes\nsummary:"))
        with self.assertRaisesRegex(ValueError, "never closed"):
            self.render("---\ntitle: x\n")

    def test_older_markdown_renders_without_front_matter(self) -> None:
        page = self.render("# ADUS-C1 close digest\n\nBody.\n", digest=False)
        self.assertIn("<title>ADUS-C1 close digest</title>", page)
        self.assertNotIn("<aside class=\"digest-meta\"", page)


if __name__ == "__main__":
    unittest.main()


GLOSSARY = ROOT / "tests" / "fixtures" / "glossary-site"


class GlossaryTests(unittest.TestCase):
    def build_site(self, directory: Path, **glossary: object) -> tuple[object, dict[str, str]]:
        config = {
            "output": str(directory / "out"),
            "stylesheet": "styles.css",
            "assets": [{"source": str(GLOSSARY / "styles.css"), "output": "styles.css"}],
            "pages": [
                {"source": str(GLOSSARY / "start.md"), "output": "index.html", "title": "Start"},
                {"source": str(GLOSSARY / "concept.md"), "output": "notes/concept.html", "title": "Concept"},
                {"source": str(GLOSSARY / "glossary.md"), "output": "glossary.html", "title": "Glossary"},
            ],
            "glossary": {"page": "glossary.html", "common_knowledge": str(GLOSSARY / "known.md"),
                         "lint_ignore": ["emphasis phrase"], **glossary},
        }
        path = directory / "site.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        site = builder.load_site(path)
        builder.build(site, directory / "out")
        pages = {name: (directory / "out" / name).read_text(encoding="utf-8")
                 for name in ("index.html", "notes/concept.html", "glossary.html")}
        return site, pages

    def test_entries_aliases_and_definitions_are_read_from_the_glossary_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, _ = self.build_site(Path(tmp))
        terms = {term.title: term for term in site.glossary.terms}
        self.assertEqual(set(terms), {"Flonk", "Wibble gate", "Zarp cache"})
        self.assertEqual(terms["Wibble gate"].anchor, "wibble-gate-invented")
        self.assertIn("wibble", terms["Wibble gate"].surfaces)
        self.assertEqual(terms["Flonk"].definition,
                         "A flonk is a small invented widget that hums when touched. It exists only in this fixture.")

    def test_first_use_of_each_term_links_once_and_opens_without_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, pages = self.build_site(Path(tmp))
        start = pages["index.html"]
        self.assertEqual(start.count('class="term-label"'), 3)
        self.assertEqual(start.count(">flonk</label>"), 1)
        self.assertIn('for="term-2">wibble gate</label>', start)
        self.assertIn('>zarp</label>', start)
        self.assertIn('<input type="checkbox" class="term-toggle" id="term-1"', start)
        self.assertIn('hums when touched. It exists only in this fixture. <a href="glossary.html#flonk">Full entry</a>', start)
        self.assertNotIn("<script", start)
        self.assertIn(".term-toggle:checked~.term-def{display:block", start)
        concept = pages["notes/concept.html"]
        self.assertIn('<a href="../glossary.html#wibble-gate-invented">Full entry</a>', concept)
        self.assertNotIn('term-label', re.search(r"<h2.*?</h2>", concept).group(0))

    def test_code_links_headings_and_the_glossary_itself_are_not_linked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, pages = self.build_site(Path(tmp))
        start = pages["index.html"]
        self.assertIn("<code>flonk</code>", start)
        self.assertIn('<a href="glossary.html#wibble-gate-invented">wibble gate</a>', start)
        self.assertNotIn('class="term-label"', pages["glossary.html"])

    def test_backlinks_on_entries_and_on_pages_linked_from_others(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, pages = self.build_site(Path(tmp))
        glossary = pages["glossary.html"]
        flonk = glossary[glossary.index('id="flonk"'):glossary.index('id="w"')]
        self.assertIn('Mentioned in: <a href="index.html">Start</a></p>', flonk)
        wibble = glossary[glossary.index('id="wibble-gate-invented"'):glossary.index('id="zarp-cache"')]
        self.assertIn('Mentioned in: <a href="notes/concept.html">Concept</a>, <a href="index.html">Start</a>', wibble)
        zarp = glossary[glossary.index('id="zarp-cache"'):]
        self.assertIn('Mentioned in: <a href="index.html">Start</a>', zarp)
        self.assertIn('<aside class="backlinks" aria-label="Mentioned in"><p>Mentioned in: <a href="../index.html">Start</a></p></aside>',
                      pages["notes/concept.html"])

    def test_lint_reports_only_unexplained_bold_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            site, _ = self.build_site(Path(tmp))
            findings = builder.lint(site)
        self.assertEqual(len(findings), 1, findings)
        self.assertIn("'mystery term' has no glossary entry", findings[0])

    def test_wide_content_scrolls_in_its_own_box(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, pages = self.build_site(Path(tmp))
        start = pages["index.html"]
        self.assertIn('<div class="table-wrap"><table>', start)
        self.assertIn("pre,.table-wrap,.inline-svg{max-width:100%;overflow-x:auto}", start)
        self.assertIn("<td>zarps</td>", start)

    def test_glossary_config_is_validated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "unknown field"):
                self.build_site(Path(tmp), colour="red")
            with self.assertRaisesRegex(ValueError, "entry_level"):
                self.build_site(Path(tmp), entry_level=9)

    def test_sites_without_a_glossary_get_no_glossary_styles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = BuilderTests().fixture_config(directory)
            site = builder.load_site(path)
            builder.build(site, directory / "output")
            text = (directory / "output" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("term-toggle", text)
