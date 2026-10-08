#!/usr/bin/env python3
"""Build committed explainer/static pages with the Python standard library.

The builder is intentionally one self-contained file with no runtime
dependencies. Site-specific source, navigation, asset, shell and output choices
live in a JSON config, and every path in that config resolves relative to the
config file — so one builder serves any number of sites from their own
checkouts.

Run it from the site's repository, which supplies the config::

    python3 ../agent-skills/tools/build_pages.py --check
    python3 ../agent-skills/tools/build_pages.py --config site/site.json

With no ``--config``, the candidates below are tried in order against the
working directory. The builder itself ships no site config; it lived beside one
in ``adus-intelligence`` until 2026-09-12 (HMT-C1 R3).

Markdown source may use a closed set of three block components, written as
fenced directives. Their rendered classes come from the hand-authored digest and
altitude pages of 2026-09-16, so existing stylesheets keep working::

    ```:reading                     ```:option                  ```:status
    @best                           @option                     @built
    label: The decision             verdict: recommended         Charters exist and work.
    title: A, B, C or D             title: B. Graduate           @designed
                                                                 The entry-point skill.
    You suspected a change.         Run it on a real model.      @open
    @alternative                    @option                      Where priority lives.
    label: Going deeper             verdict: strong second
    title: The layer below          title: C. Redirect
    The arc is in the digest.       A router picks the block.
    ```                             ```                         ```

An entry's ``field: value`` header must come first; everything after the first
blank line is body prose, split into paragraphs. Any other directive name, or a
malformed one, fails the build naming the source file and line -- nothing falls
through to raw passthrough, which is what keeps the audited inline-SVG block the
only unescaped markup in output.

A site config may also set ``inline_stylesheet`` to one stylesheet path, which
is embedded in every output document so a single file renders standalone. The
``stylesheet`` link behaviour is unchanged when it is absent.

A site may declare a glossary, which is one of its own pages::

    "glossary": {"page": "glossary.html",
                 "common_knowledge": "terms-known.md",
                 "lint_ignore": ["Short answer"]}

Each heading at ``entry_level`` (default 3) on that page is an entry; its first
paragraph is the definition, and an optional ``- **Also written:** a, b`` line
lists other surface forms (a trailing parenthetical on the heading is not part
of the term). On every other page the first use of each term in prose is
linked: a checkbox and label reveal the definition in place on tap, click or
keyboard, with no script, and the definition links to the full entry. Glossary
entries and pages gain "Mentioned in" backlinks. ``--lint`` reports bold terms
of one to three words that match no entry, no line of the common-knowledge file
(``- term; other term — reason``), no ``lint_ignore`` phrase and no
``lint_ignore_patterns`` regular expression. An explicit
link to a glossary entry also opens in place on its first use. A site with no
glossary renders exactly as before.

``source_links`` maps local links that leave the site to a hosted copy of the
source, so a page can cite files the site does not render::

    "source_links": [{"root": "..", "url": "https://example.org/repo/blob/main/"}]

A link whose target lies under ``root`` (relative to the config) and is not a
site page or asset becomes ``url`` plus its path below ``root``.
"""

from __future__ import annotations

import argparse
import html
import json
import posixpath
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn
from urllib.parse import urlsplit

SCRIPT = Path(__file__).resolve()
CONFIG_CANDIDATES = (Path("site.json"), Path("site") / "site.json")
EXPLAINER_FIELDS = ("layer", "audience", "as_of", "status", "provenance")
FORBIDDEN_SVG_ELEMENTS = {"script", "foreignObject", "style"}

# The closed component vocabulary. A fence whose info string starts with ":" is
# a block directive, so ordinary ```sh / ```text fences keep rendering as code.
# The set is closed on purpose: an unrecognised or malformed directive is a
# build failure, never raw passthrough, which is what keeps the narrow audited
# SVG block the only markup that reaches output unescaped.
DIGEST_STYLESHEET = SCRIPT.parent / "digest.css"
DIGEST_REQUIRED = ("title", "reader", "date", "status")
DIGEST_OPTIONAL = ("charter", "summary", "supersedes")
DIRECTIVES = ("reading", "option", "status")
PILL_VARIANTS = ("built", "designed", "open")
DIRECTIVE_FIELDS: dict[str, tuple[str, ...]] = {
    "reading": ("label", "title"),
    "option": ("verdict", "title"),
    "status": (),
}
REQUIRED_DIRECTIVE_FIELDS: dict[str, tuple[str, ...]] = {
    "reading": ("title",),
    "option": ("verdict", "title"),
    "status": (),
}


@dataclass(frozen=True)
class Page:
    source: Path
    output: str
    title: str
    explainer: dict[str, Any] | None = None
    text: str | None = None

    def read(self) -> str:
        return self.text if self.text is not None else self.source.read_text(encoding="utf-8")


@dataclass(frozen=True)
class Site:
    config_path: Path
    output: Path
    description: str
    brand: str
    brand_suffix: str
    footer_html: str
    stylesheet: str
    inline_stylesheet: Path | None
    write_nojekyll: bool
    pages: tuple[Page, ...]
    navigation: tuple[tuple[str, str], ...]
    assets: tuple[tuple[Path, str], ...]
    aliases: dict[str, str]
    section_reference_page: str | None
    glossary: Glossary | None = None
    source_links: tuple[tuple[Path, str], ...] = ()

    @property
    def source_routes(self) -> dict[Path, str]:
        return {page.source.resolve(): page.output for page in self.pages}

    @property
    def page_by_output(self) -> dict[str, Page]:
        return {page.output: page for page in self.pages}


@dataclass(frozen=True)
class Term:
    anchor: str
    title: str
    surfaces: tuple[str, ...]
    definition: str


@dataclass(frozen=True)
class Glossary:
    page: str
    entry_level: int
    terms: tuple[Term, ...]
    common: frozenset[str]
    ignore: frozenset[str]
    ignore_patterns: tuple[re.Pattern[str], ...] = ()

    @property
    def pattern(self) -> re.Pattern[str] | None:
        return surface_pattern(surface for term in self.terms for surface in term.surfaces)

    def term_for(self, text: str) -> Term | None:
        key = normal_term(text)
        for term in self.terms:
            if any(key in plural_forms(surface) for surface in term.surfaces):
                return term
        return None


class Linker:
    """Per-page state for glossary linking: first use only, and what was used."""

    def __init__(self, glossary: Glossary, page: Page) -> None:
        self.glossary = glossary
        self.page = page
        self.pattern = glossary.pattern
        self.used: dict[str, Term] = {}
        self.count = 0


def fail(message: str) -> NoReturn:
    raise ValueError(message)


def default_config(cwd: Path | None = None) -> Path:
    """The site config to build when the caller named none.

    Searched under the working directory rather than beside the builder: the
    builder is shared and the config belongs to the site.
    """
    base = (cwd or Path.cwd()).resolve()
    for candidate in CONFIG_CANDIDATES:
        path = base / candidate
        if path.is_file():
            return path
    tried = ", ".join(str(candidate) for candidate in CONFIG_CANDIDATES)
    fail(f"no site config under {base} (tried {tried}); pass --config")


def resolve_from(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def load_site(config_path: Path) -> Site:
    config_path = config_path.resolve()
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"missing config: {config_path}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON config {config_path}: {exc}")
    if not isinstance(raw, dict):
        fail("site config must be an object")
    base = config_path.parent

    pages: list[Page] = []
    outputs: set[str] = set()
    sources: set[Path] = set()
    for index, item in enumerate(raw.get("pages", [])):
        if not isinstance(item, dict):
            fail(f"pages[{index}] must be an object")
        missing = [key for key in ("source", "output", "title") if not item.get(key)]
        if missing:
            fail(f"pages[{index}] missing: {', '.join(missing)}")
        source = resolve_from(base, str(item["source"]))
        output = clean_output(str(item["output"]), f"pages[{index}].output")
        if source in sources:
            fail(f"duplicate page source: {source}")
        if output in outputs:
            fail(f"duplicate page output: {output}")
        if not source.is_file():
            fail(f"missing page source: {source}")
        explainer = item.get("explainer")
        if explainer is not None:
            if not isinstance(explainer, dict):
                fail(f"pages[{index}].explainer must be an object")
            absent = [key for key in EXPLAINER_FIELDS if not str(explainer.get(key, "")).strip()]
            if absent:
                fail(f"pages[{index}].explainer missing: {', '.join(absent)}")
            if "not_human_reviewed" in explainer and not isinstance(explainer["not_human_reviewed"], bool):
                fail(f"pages[{index}].explainer.not_human_reviewed must be boolean")
        pages.append(Page(source, output, str(item["title"]), explainer))
        outputs.add(output)
        sources.add(source)
    if not pages:
        fail("site config needs at least one page")

    navigation: list[tuple[str, str]] = []
    for index, item in enumerate(raw.get("navigation", [])):
        if not isinstance(item, dict) or not item.get("page") or not item.get("label"):
            fail(f"navigation[{index}] needs page and label")
        page = clean_output(str(item["page"]), f"navigation[{index}].page")
        if page not in outputs:
            fail(f"navigation[{index}] references undeclared page: {page}")
        navigation.append((page, str(item["label"])))

    assets: list[tuple[Path, str]] = []
    asset_outputs: set[str] = set()
    for index, item in enumerate(raw.get("assets", [])):
        if not isinstance(item, dict) or not item.get("source") or not item.get("output"):
            fail(f"assets[{index}] needs source and output")
        source = resolve_from(base, str(item["source"]))
        output = clean_output(str(item["output"]), f"assets[{index}].output")
        if not source.exists():
            fail(f"missing declared asset: {source}")
        if output in outputs or output in asset_outputs:
            fail(f"duplicate page/asset output: {output}")
        assets.append((source, output))
        asset_outputs.add(output)

    section_page = raw.get("section_reference_page")
    if section_page is not None:
        section_page = clean_output(str(section_page), "section_reference_page")
        if section_page not in outputs:
            fail(f"section_reference_page is undeclared: {section_page}")

    inline_stylesheet: Path | None = None
    if "inline_stylesheet" in raw and raw["inline_stylesheet"] is not None:
        value = raw["inline_stylesheet"]
        if not isinstance(value, str) or not value.strip():
            fail("inline_stylesheet must be a path to one stylesheet, relative to the config")
        inline_stylesheet = resolve_from(base, value)
        if not inline_stylesheet.is_file():
            fail(f"missing inline_stylesheet: {inline_stylesheet}")

    aliases = raw.get("aliases", {})
    if not isinstance(aliases, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in aliases.items()):
        fail("aliases must be a string-to-string object")

    glossary = load_glossary(raw.get("glossary"), base, pages, outputs)

    source_links: list[tuple[Path, str]] = []
    for index, item in enumerate(raw.get("source_links", [])):
        if not isinstance(item, dict) or not item.get("root") or not item.get("url"):
            fail(f"source_links[{index}] needs root and url")
        url = str(item["url"])
        if not re.match(r"https?://", url) or not url.endswith("/"):
            fail(f"source_links[{index}].url must be an http(s) URL ending in '/'")
        source_links.append((resolve_from(base, str(item["root"])), url))

    output = resolve_from(base, str(raw.get("output", "docs")))
    return Site(
        config_path=config_path,
        output=output,
        description=str(raw.get("description", "Explainer pages")),
        brand=str(raw.get("brand", "Explainers")),
        brand_suffix=str(raw.get("brand_suffix", "")),
        footer_html=str(raw.get("footer_html", "")),
        stylesheet=str(raw.get("stylesheet", "styles.css")),
        inline_stylesheet=inline_stylesheet,
        write_nojekyll=bool(raw.get("write_nojekyll", True)),
        pages=tuple(pages),
        navigation=tuple(navigation),
        assets=tuple(assets),
        aliases=dict(aliases),
        section_reference_page=section_page,
        glossary=glossary,
        source_links=tuple(source_links),
    )


GLOSSARY_FIELDS = ("page", "entry_level", "common_knowledge", "lint_ignore", "lint_ignore_patterns")


def normal_term(text: str) -> str:
    return re.sub(r"\s+", " ", plain(text).strip(" .:;,'\"")).lower()


def plural_forms(surface: str) -> set[str]:
    key = normal_term(surface)
    return {key, key + "s", key + "es"}


def surface_pattern(surfaces: Any) -> re.Pattern[str] | None:
    """One case-insensitive alternation, longest first, on whole words."""
    forms = sorted({normal_term(surface) for surface in surfaces if normal_term(surface)}, key=len, reverse=True)
    if not forms:
        return None
    body = "|".join(re.escape(html.escape(form, quote=False)).replace(r"\ ", r"\s+") for form in forms)
    return re.compile(rf"(?<![\w\x00-])(?:{body})(?:s|es)?(?![\w\x00-])", re.IGNORECASE)


def load_glossary(raw: Any, base: Path, pages: list[Page], outputs: set[str]) -> Glossary | None:
    if raw is None:
        return None
    if not isinstance(raw, dict) or not raw.get("page"):
        fail("glossary must be an object naming its page")
    unknown = sorted(set(raw) - set(GLOSSARY_FIELDS))
    if unknown:
        fail(f"glossary has unknown field(s): {', '.join(unknown)}")
    page_output = clean_output(str(raw["page"]), "glossary.page")
    if page_output not in outputs:
        fail(f"glossary.page is undeclared: {page_output}")
    level = raw.get("entry_level", 3)
    if not isinstance(level, int) or not 1 <= level <= 6:
        fail("glossary.entry_level must be an integer from 1 to 6")
    ignore = raw.get("lint_ignore", [])
    if not isinstance(ignore, list) or not all(isinstance(item, str) for item in ignore):
        fail("glossary.lint_ignore must be a list of strings")
    patterns = raw.get("lint_ignore_patterns", [])
    if not isinstance(patterns, list) or not all(isinstance(item, str) for item in patterns):
        fail("glossary.lint_ignore_patterns must be a list of regular expressions")
    try:
        compiled = tuple(re.compile(item) for item in patterns)
    except re.error as exc:
        fail(f"glossary.lint_ignore_patterns: {exc}")
    common: set[str] = set()
    if raw.get("common_knowledge"):
        path = resolve_from(base, str(raw["common_knowledge"]))
        if not path.is_file():
            fail(f"missing glossary.common_knowledge: {path}")
        common = common_knowledge(path)
    page = next(page for page in pages if page.output == page_output)
    return Glossary(page_output, level, glossary_terms(page.source, level), frozenset(common), frozenset(normal_term(item) for item in ignore), compiled)


def common_knowledge(path: Path) -> set[str]:
    """Terms from ``- term; other term — reason`` lines; other lines are prose."""
    terms: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*-\s+(.+?)\s+[—–]\s+\S", line)
        if match:
            terms.update(normal_term(part) for part in match.group(1).split(";") if part.strip())
    return terms


def glossary_terms(source: Path, level: int) -> tuple[Term, ...]:
    text = source.read_text(encoding="utf-8")
    _, headings = heading_data(source, text)
    anchors = iter(headings)
    terms: list[Term] = []
    current: dict[str, Any] | None = None

    def close() -> None:
        if current is not None:
            surfaces = [current["title"], *current["aliases"]]
            terms.append(Term(current["anchor"], current["title"], tuple(dict.fromkeys(s for s in surfaces if s)), " ".join(current["definition"])))

    in_code = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            depth, title, anchor = next(anchors)
            if depth <= level:
                close()
                current = None
            if depth == level:
                title = re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()
                current = {"anchor": anchor, "title": title, "aliases": [], "definition": [], "open": True}
            continue
        if current is None:
            continue
        also = re.match(r"^\s*[-*]\s+\*\*Also written:?\*\*:?\s*(.+)$", line)
        if also:
            current["aliases"].extend(part.strip() for part in plain(also.group(1)).split(",") if part.strip())
            current["open"] = False
            continue
        if not line.strip():
            if current["definition"]:
                current["open"] = False
            continue
        if current["open"] and not re.match(r"^\s*([*-]|\d+\.)\s+", line):
            current["definition"].append(plain(line.strip()))
        else:
            current["open"] = False
    close()
    if not terms:
        fail(f"{source}: glossary declares no level-{level} entries")
    return tuple(terms)


def clean_output(value: str, context: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value.endswith("/"):
        fail(f"{context} must be a relative file path without '..': {value}")
    return str(path)


def plain(text: str) -> str:
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    return re.sub(r"[*_`]+", "", text).strip()


def slug(text: str) -> str:
    value = plain(text).lower().replace("§", "section-")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "section"


def section_number(text: str) -> str | None:
    match = re.match(r"(\d+(?:\.\d+)*)\b", plain(text))
    return match.group(1) if match else None


def heading_data(source: Path, text: str | None = None) -> tuple[dict[str, str], list[tuple[int, str, str]]]:
    sections: dict[str, str] = {}
    headings: list[tuple[int, str, str]] = []
    used: dict[str, int] = {}
    in_code = False
    for line in (text if text is not None else source.read_text(encoding="utf-8")).splitlines():
        if line.startswith("```"):
            in_code = not in_code
            continue
        match = None if in_code else re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if not match:
            continue
        level, text = len(match.group(1)), plain(match.group(2))
        base = slug(text)
        count = used.get(base, 0)
        used[base] = count + 1
        anchor = base if count == 0 else f"{base}-{count + 1}"
        headings.append((level, text, anchor))
        number = section_number(text)
        if number:
            sections[number] = anchor
    return sections, headings


def relative_route(source_output: str, target_output: str) -> str:
    source_parent = PurePosixPath(source_output).parent
    source_parts = source_parent.parts if str(source_parent) != "." else ()
    target_parts = PurePosixPath(target_output).parts
    shared = 0
    while shared < min(len(source_parts), len(target_parts)) and source_parts[shared] == target_parts[shared]:
        shared += 1
    parts = ("..",) * (len(source_parts) - shared) + target_parts[shared:]
    return "/".join(parts) or PurePosixPath(target_output).name


def link_target(site: Site, page: Page, target: str) -> str:
    parsed = urlsplit(target)
    if parsed.scheme or target.startswith(("mailto:", "#", "//")):
        return target
    if target in site.aliases:
        route = relative_route(page.output, site.aliases[target])
        return route + (f"#{parsed.fragment}" if parsed.fragment else "")
    source_target = (page.source.parent / parsed.path).resolve() if parsed.path else page.source
    output = site.source_routes.get(source_target)
    if output is None:
        for asset_source, asset_output in site.assets:
            if asset_source.is_file() and source_target == asset_source.resolve():
                output = asset_output
                break
            if asset_source.is_dir():
                try:
                    remainder = source_target.relative_to(asset_source.resolve())
                except ValueError:
                    continue
                output = str(PurePosixPath(asset_output) / PurePosixPath(remainder.as_posix()))
                break
    if output:
        route = relative_route(page.output, output)
        return route + (f"#{parsed.fragment}" if parsed.fragment else "")
    for root, url in site.source_links:
        try:
            remainder = source_target.relative_to(root)
        except ValueError:
            continue
        return url + remainder.as_posix() + (f"#{parsed.fragment}" if parsed.fragment else "")
    return target


def inline(text: str, site: Site, page: Page, report_sections: dict[str, str], linker: Linker | None = None) -> str:
    tokens: list[str] = []

    def hold(value: str) -> str:
        tokens.append(value)
        return f"\x00{len(tokens) - 1}\x00"

    def markdown_image(match: re.Match[str]) -> str:
        alt, target = match.group(1), link_target(site, page, match.group(2))
        return hold(f'<img src="{html.escape(target, quote=True)}" alt="{html.escape(alt, quote=True)}">')

    def markdown_link(match: re.Match[str]) -> str:
        label, target = match.group(1), link_target(site, page, match.group(2))
        term = glossary_link(site, page, target, linker)
        if term is not None and linker is not None:
            linker.used[term.anchor] = term
            return hold(term_html(page, linker, term, html.escape(label)))
        return hold(f'<a href="{html.escape(target, quote=True)}">{html.escape(label)}</a>')

    text = re.sub(r"!\[([^]]*)\]\(([^)]+)\)", markdown_image, text)
    text = re.sub(r"\[([^]]+)\]\(([^)]+)\)", markdown_link, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", lambda m: hold(f"<code>{m.group(1)}</code>"), text)
    if linker is not None and linker.pattern is not None:
        text = link_terms(text, site, page, linker, hold)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)

    if site.section_reference_page:
        report_prefix = "" if page.output == site.section_reference_page else relative_route(page.output, site.section_reference_page)

        def section_link(match: re.Match[str]) -> str:
            number = match.group(1)
            anchor = report_sections.get(number)
            if not anchor:
                return match.group(0)
            return f'<a class="section-ref" href="{report_prefix}#{anchor}">§{number}</a>'

        text = re.sub(r"§(\d+(?:\.\d+)*)", section_link, text)

    text = re.sub(
        r"(?<![\"'=])(https?://[^\s<]+)",
        lambda m: f'<a href="{m.group(1).rstrip(".,;")}">{m.group(1).rstrip(".,;")}</a>{m.group(1)[len(m.group(1).rstrip(".,;")):]}',
        text,
    )
    for index, value in enumerate(tokens):
        text = text.replace(f"\x00{index}\x00", value)
    return text


def glossary_link(site: Site, page: Page, target: str, linker: Linker | None) -> Term | None:
    """The term an explicit link to a glossary entry names, on its first use here."""
    if linker is None:
        return None
    path, _, fragment = target.partition("#")
    if not fragment or relative_route(page.output, linker.glossary.page) != path:
        return None
    term = next((term for term in linker.glossary.terms if term.anchor == fragment), None)
    return None if term is None or term.anchor in linker.used else term


def term_html(page: Page, linker: Linker, term: Term, label: str) -> str:
    """A term whose definition opens in place: checkbox state, so no script."""
    linker.count += 1
    ident = f"term-{linker.count}"
    entry = relative_route(page.output, linker.glossary.page) + f"#{term.anchor}"
    return (
        f'<span class="term"><input type="checkbox" class="term-toggle" id="{ident}" '
        f'aria-label="Definition of {html.escape(term.title, quote=True)}">'
        f'<label class="term-label" for="{ident}">{label}</label>'
        f'<span class="term-def" role="note">{html.escape(term.definition)} '
        f'<a href="{html.escape(entry, quote=True)}">Full entry</a></span></span>'
    )


def link_terms(text: str, site: Site, page: Page, linker: Linker, hold: Any) -> str:
    """Wrap the first use on this page of each glossary term, in escaped prose."""

    def wrap(match: re.Match[str]) -> str:
        term = linker.glossary.term_for(html.unescape(match.group(0)))
        if term is None or term.anchor in linker.used:
            return match.group(0)
        linker.used[term.anchor] = term
        return hold(term_html(page, linker, term, match.group(0)))

    return linker.pattern.sub(wrap, text)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def audit_svg(raw: str, source: Path) -> None:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        fail(f"{source}: invalid complete SVG block: {exc}")
    if local_name(root.tag) != "svg":
        fail(f"{source}: raw block must have one svg root")
    if "viewBox" not in root.attrib:
        fail(f"{source}: inline SVG requires viewBox")
    names = {local_name(child.tag) for child in root.iter()}
    role_named = root.attrib.get("role") == "img" and bool(root.attrib.get("aria-label", "").strip())
    element_named = "title" in names or "desc" in names
    if not (role_named or element_named):
        fail(f"{source}: inline SVG requires role=img plus aria-label, or title/desc")
    for element in root.iter():
        name = local_name(element.tag)
        if name in FORBIDDEN_SVG_ELEMENTS:
            fail(f"{source}: inline SVG forbids <{name}>")
        for raw_attr, value in element.attrib.items():
            attr = local_name(raw_attr)
            if attr.lower().startswith("on"):
                fail(f"{source}: inline SVG forbids event attribute {attr}")
            if attr in {"href", "src"} and value and not value.startswith("#"):
                fail(f"{source}: inline SVG forbids non-local {attr}={value!r}")
            if "url(" in value and not re.fullmatch(r".*url\(\s*#[^)]+\).*", value):
                fail(f"{source}: inline SVG forbids external CSS URL")


def take_svg(lines: list[str], start: int, source: Path) -> tuple[str, int] | None:
    if not lines[start].lstrip().startswith("<svg"):
        return None
    block: list[str] = []
    index = start
    while index < len(lines):
        block.append(lines[index])
        if "</svg>" in lines[index]:
            if lines[index].split("</svg>", 1)[1].strip():
                fail(f"{source}:{index + 1}: content after closing </svg> is not audited passthrough")
            raw = "\n".join(block)
            audit_svg(raw, source)
            return raw, index + 1
        index += 1
    fail(f"{source}:{start + 1}: incomplete inline SVG block")


def directive_block(lines: list[str], start: int, source: Path) -> tuple[str, list[tuple[int, str]], int]:
    """Split one `````:name`` fence into its name and numbered body lines."""
    header = lines[start].strip()
    known = ", ".join(f":{name}" for name in DIRECTIVES)
    match = re.fullmatch(r"```:([A-Za-z][\w-]*)", header)
    if not match:
        fail(f"{source}:{start + 1}: malformed block directive {header!r}; expected a bare ```:<name> fence ({known})")
    name = match.group(1)
    if name not in DIRECTIVES:
        fail(f"{source}:{start + 1}: unknown block directive ':{name}'; the vocabulary is closed ({known})")
    body: list[tuple[int, str]] = []
    index = start + 1
    while index < len(lines):
        if lines[index].strip() == "```":
            return name, body, index + 1
        body.append((index + 1, lines[index]))
        index += 1
    fail(f"{source}:{start + 1}: unterminated ':{name}' block directive")


def directive_entries(name: str, body: list[tuple[int, str]], source: Path, fence_line: int) -> list[dict[str, Any]]:
    """Cut a directive body at its ``@kind`` markers."""
    entries: list[dict[str, Any]] = []
    for line_number, raw in body:
        marker = re.fullmatch(r"@([A-Za-z][\w-]*)", raw.strip())
        if marker:
            entries.append({"line": line_number, "kind": marker.group(1), "lines": []})
        elif entries:
            entries[-1]["lines"].append((line_number, raw))
        elif raw.strip():
            fail(f"{source}:{line_number}: ':{name}' content before the first @entry marker")
    if not entries:
        fail(f"{source}:{fence_line}: ':{name}' block declares no @entry")
    return entries


def entry_parts(name: str, entry: dict[str, Any], source: Path) -> tuple[dict[str, str], list[str]]:
    """The leading ``field: value`` header and the blank-line-separated body."""
    allowed = DIRECTIVE_FIELDS[name]
    lines: list[tuple[int, str]] = entry["lines"]
    where = f"':{name}' @{entry['kind']}"
    fields: dict[str, str] = {}
    index = 0
    while allowed and index < len(lines) and lines[index][1].strip():
        line_number, raw = lines[index]
        match = re.fullmatch(r"([a-z][a-z_]*):\s*(.+)", raw.strip())
        if not match:
            break
        field = match.group(1)
        if field not in allowed:
            fail(f"{source}:{line_number}: {where} has unknown field {field!r}; allowed: {', '.join(allowed)}")
        if field in fields:
            fail(f"{source}:{line_number}: {where} repeats field {field!r}")
        fields[field] = match.group(2).strip()
        index += 1
    for field in REQUIRED_DIRECTIVE_FIELDS[name]:
        if field not in fields:
            fail(f"{source}:{entry['line']}: {where} needs a {field!r} field")
    paragraphs: list[str] = []
    buffer: list[str] = []
    for _, raw in lines[index:]:
        if raw.strip():
            buffer.append(raw.strip())
        elif buffer:
            paragraphs.append(" ".join(buffer))
            buffer = []
    if buffer:
        paragraphs.append(" ".join(buffer))
    if not paragraphs:
        fail(f"{source}:{entry['line']}: {where} has no body text")
    return fields, paragraphs


def render_directive(lines: list[str], start: int, site: Site, page: Page, report_sections: dict[str, str], linker: Linker | None = None) -> tuple[str, int]:
    """Render one block component. Class names follow the hand-authored pages."""
    source = page.source
    name, body, next_index = directive_block(lines, start, source)
    entries = directive_entries(name, body, source, start + 1)

    def ink(text: str) -> str:
        return inline(text, site, page, report_sections, linker)

    def prose(paragraphs: list[str]) -> str:
        return "".join(f"<p>{ink(paragraph)}</p>" for paragraph in paragraphs)

    if name == "reading":
        kinds = [entry["kind"] for entry in entries]
        if kinds != ["best", "alternative"]:
            got = ", ".join(f"@{kind}" for kind in kinds) or "nothing"
            fail(f"{source}:{start + 1}: ':reading' needs exactly @best then @alternative; got {got}")
        cells: list[str] = []
        for entry in entries:
            fields, paragraphs = entry_parts(name, entry, source)
            label = f'<span class="label">{ink(fields["label"])}</span>' if fields.get("label") else ""
            cells.append(f'<div class="{entry["kind"]}">{label}<h3>{ink(fields["title"])}</h3>{prose(paragraphs)}</div>')
        return f'<div class="reading">{"".join(cells)}</div>', next_index

    if name == "option":
        cards: list[str] = []
        for entry in entries:
            if entry["kind"] != "option":
                fail(f"{source}:{entry['line']}: ':option' allows only @option entries; got @{entry['kind']}")
            fields, paragraphs = entry_parts(name, entry, source)
            cards.append(
                f'<article class="opt"><span class="verdict">{ink(fields["verdict"])}</span>'
                f'<h3>{ink(fields["title"])}</h3>{prose(paragraphs)}</article>'
            )
        return f'<div class="four">{"".join(cards)}</div>', next_index

    rows: list[str] = []
    for entry in entries:
        if entry["kind"] not in PILL_VARIANTS:
            allowed = ", ".join(f"@{variant}" for variant in PILL_VARIANTS)
            fail(f"{source}:{entry['line']}: ':status' pill must be one of {allowed}; got @{entry['kind']}")
        _, paragraphs = entry_parts(name, entry, source)
        cell = ink(paragraphs[0]) if len(paragraphs) == 1 else prose(paragraphs)
        rows.append(f'<span class="pill {entry["kind"]}">{entry["kind"]}</span><div>{cell}</div>')
    return f'<div class="state">{"".join(rows)}</div>', next_index


def site_front_matter(text: str, source: Path) -> tuple[dict[str, str], str]:
    """Front matter on a site page, if the page opens with a valid block.

    A page that opens with a rule rather than ``key: value`` lines keeps it, so
    sites written before pages carried front matter render as they did.
    """
    try:
        return front_matter(text, source)
    except ValueError:
        return {}, text


def render_markdown(site: Site, page: Page, report_sections: dict[str, str], linker: Linker | None = None) -> tuple[str, list[tuple[int, str, str]]]:
    meta, text = site_front_matter(page.read(), page.source)
    lines = text.splitlines()
    _, headings = heading_data(page.source, text)
    heading_iter = iter(headings)
    output: list[str] = []
    paragraph: list[str] = []
    list_kind: str | None = None
    in_code = False
    code_lines: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{inline(' '.join(part.strip() for part in paragraph), site, page, report_sections, linker)}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_kind
        if list_kind:
            output.append(f"</{list_kind}>")
            list_kind = None

    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            if not in_code and line.strip().startswith("```:"):
                flush_paragraph(); close_list()
                rendered, index = render_directive(lines, index, site, page, report_sections, linker)
                output.append(rendered)
                continue
            flush_paragraph(); close_list()
            if in_code:
                output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines.clear()
            in_code = not in_code
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue
        svg = take_svg(lines, index, page.source)
        if svg:
            flush_paragraph(); close_list()
            raw, index = svg
            output.append(f'<div class="inline-svg">{raw}</div>')
            continue
        if index + 1 < len(lines) and line.startswith("|") and re.match(r"^\|?\s*:?-+", lines[index + 1]):
            flush_paragraph(); close_list()
            rows: list[list[str]] = []
            while index < len(lines) and lines[index].startswith("|"):
                rows.append([cell.strip() for cell in lines[index].strip().strip("|").split("|")])
                index += 1
            output.append('<div class="table-wrap"><table><thead><tr>' + "".join(f"<th>{inline(cell, site, page, report_sections, linker)}</th>" for cell in rows[0]) + "</tr></thead><tbody>")
            for row in rows[2:]:
                output.append("<tr>" + "".join(f"<td>{inline(cell, site, page, report_sections, linker)}</td>" for cell in row) + "</tr>")
            output.append("</tbody></table></div>")
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if heading:
            flush_paragraph(); close_list()
            level, text, anchor = next(heading_iter)
            output.append(f'<h{level} id="{anchor}">{inline(text, site, page, report_sections)}<a class="permalink" href="#{anchor}" aria-label="Link to this section">#</a></h{level}>')
            index += 1
            continue
        item = re.match(r"^\s*([*-]|\d+\.)\s+(.+)$", line)
        if item:
            flush_paragraph()
            kind = "ol" if item.group(1)[0].isdigit() else "ul"
            if list_kind != kind:
                close_list(); output.append(f"<{kind}>"); list_kind = kind
            parts = [item.group(2)]
            index += 1
            while index < len(lines) and lines[index].strip():
                continuation = lines[index]
                if (re.match(r"^\s*([*-]|\d+\.)\s+", continuation)
                        or re.match(r"^#{1,6}\s+", continuation)
                        or re.match(r"^\s*---+\s*$", continuation)
                        or continuation.startswith(("```", "> ", "|", "<svg"))):
                    break
                parts.append(continuation.strip())
                index += 1
            output.append(f"<li>{inline(' '.join(parts), site, page, report_sections, linker)}</li>")
            continue
        if re.match(r"^\s*---+\s*$", line):
            flush_paragraph(); close_list(); output.append("<hr>"); index += 1; continue
        if line.startswith("> "):
            flush_paragraph(); close_list(); output.append(f"<blockquote>{inline(line[2:], site, page, report_sections, linker)}</blockquote>"); index += 1; continue
        if not line.strip():
            flush_paragraph(); close_list(); index += 1; continue
        paragraph.append(line)
        index += 1
    flush_paragraph(); close_list()
    if in_code:
        fail(f"Unclosed code fence in {page.source}")
    body = "\n".join(output)
    if meta and all(meta.get(key) for key in DIGEST_REQUIRED) and "</h1>" in body:
        end = body.index("</h1>") + len("</h1>")
        body = body[:end] + digest_declaration(digest_meta(meta, page.source)) + body[end:]
    return body, headings


def toc(headings: list[tuple[int, str, str]]) -> str:
    items = [f'<li class="toc-level-{level}"><a href="#{anchor}">{html.escape(text)}</a></li>' for level, text, anchor in headings if 2 <= level <= 3]
    return '<nav class="toc" aria-label="On this page"><h2>On this page</h2><ol>' + "".join(items) + "</ol></nav>" if items else ""


def explainer_declaration(meta: dict[str, Any] | None) -> str:
    if meta is None:
        return ""
    labels = (("Layer", "layer"), ("Audience", "audience"), ("As of", "as_of"), ("Status", "status"), ("Provenance", "provenance"))
    rows = "".join(f'<div><dt>{label}</dt><dd>{html.escape(str(meta[key]))}</dd></div>' for label, key in labels)
    if meta.get("not_human_reviewed"):
        rows += '<div><dt>Review</dt><dd><strong>Not human-reviewed</strong></dd></div>'
    return f'<aside class="explainer-meta" aria-label="Explainer declaration"><dl>{rows}</dl></aside>'


def inline_stylesheet_css(path: Path) -> str:
    """The stylesheet text to embed, audited for standalone self-containment.

    Inlining exists so one output file renders with no external request, so the
    embedded text may not reach back out for anything.
    """
    text = path.read_text(encoding="utf-8")
    if "</style" in text.lower():
        fail(f"{path}: inlined stylesheet may not contain a closing </style> tag")
    if "@import" in text:
        fail(f"{path}: inlined stylesheet may not @import; a standalone page makes no request")
    for value in re.findall(r"url\(([^)]*)\)", text):
        target = value.strip().strip("\"'")
        if not target.startswith(("data:", "#")):
            fail(f"{path}: inlined stylesheet may not reference {target!r}; only data: and #fragment URLs are self-contained")
    return text.strip("\n")


# Injected only for sites that declare a glossary, so other sites' output is
# unchanged. The term rules need no script: the checkbox state shows the
# definition. The rest keeps a 360-414 px page from scrolling sideways: wide
# tables, code and diagrams scroll inside their own boxes.
GLOSSARY_CSS = """
.term{position:relative}
.term-toggle{position:absolute;left:0;top:0;opacity:0;width:1px;height:1px;margin:0;pointer-events:none}
.term-label{border-bottom:1px dotted currentColor;cursor:pointer}
.term-toggle:focus-visible+.term-label{outline:2px solid currentColor;outline-offset:2px}
.term-def{display:none}
.term-toggle:checked~.term-def{display:block;margin:.4rem 0 .6rem;padding:.55rem .75rem;border:1px solid rgba(127,127,127,.45);border-left:4px solid currentColor;font-size:.92em;font-weight:normal;font-style:normal;text-transform:none;letter-spacing:normal;white-space:normal;overflow-wrap:anywhere}
.backlinks,.term-backlinks{font-size:.9em}
.backlinks{margin-top:2.5rem;border-top:1px solid rgba(127,127,127,.45);padding-top:.8rem}
html{-webkit-text-size-adjust:100%}
main{min-width:0;max-width:100%}
p,li,dd,blockquote{overflow-wrap:anywhere}
img,svg,video{max-width:100%;height:auto}
pre,.table-wrap,.inline-svg{max-width:100%;overflow-x:auto}
"""


def head_styles(site: Site, page: Page) -> str:
    extra = f"\n  <style>{GLOSSARY_CSS}</style>" if site.glossary is not None else ""
    if site.inline_stylesheet is not None:
        return f"<style>\n{inline_stylesheet_css(site.inline_stylesheet)}\n  </style>{extra}"
    stylesheet = relative_route(page.output, site.stylesheet)
    return f'<link rel="stylesheet" href="{html.escape(stylesheet, quote=True)}">{extra}'


def shell(site: Site, page: Page, body: str, headings: list[tuple[int, str, str]]) -> str:
    nav = "".join(f'<a href="{relative_route(page.output, href)}"{(" aria-current=\"page\"" if href == page.output else "")}>{label}</a>' for href, label in site.navigation)
    suffix = f" <span>{html.escape(site.brand_suffix)}</span>" if site.brand_suffix else ""
    home = relative_route(page.output, site.navigation[0][0]) if site.navigation else PurePosixPath(page.output).name
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{html.escape(site.description, quote=True)}">
  <title>{html.escape(page.title)}</title>
  {head_styles(site, page)}
</head>
<body>
  <a class="skip-link" href="#content">Skip to content</a>
  <header class="site-header"><a class="brand" href="{home}">{html.escape(site.brand)}{suffix}</a><nav aria-label="Primary">{nav}</nav></header>
  <div class="layout">{toc(headings)}<main id="content">{explainer_declaration(page.explainer)}{body}</main></div>
  <footer>{site.footer_html}</footer>
</body>
</html>
'''


def copy_asset(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        shutil.copyfile(source, target)


def build(site: Site, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    report_sections: dict[str, str] = {}
    if site.section_reference_page:
        report_sections, _ = heading_data(site.page_by_output[site.section_reference_page].source)
    rendered: dict[str, tuple[str, list[tuple[int, str, str]]]] = {}
    mentions: dict[str, list[str]] = {}
    for page in site.pages:
        linker = Linker(site.glossary, page) if site.glossary is not None and page.output != site.glossary.page else None
        rendered[page.output] = render_markdown(site, page, report_sections, linker)
        if linker is not None:
            for anchor in linker.used:
                mentions.setdefault(anchor, []).append(page.output)
    if site.glossary is not None:
        rendered = add_backlinks(site, rendered, mentions)
    for page in site.pages:
        body, headings = rendered[page.output]
        target = destination / page.output
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(shell(site, page, body, headings), encoding="utf-8", newline="\n")
    for source, output in site.assets:
        copy_asset(source, destination / output)
    if site.write_nojekyll:
        (destination / ".nojekyll").write_text("", encoding="utf-8")
    validate(site, destination)


def page_links(site: Site, page: Page, body: str) -> set[str]:
    """Other site pages this rendered body links to, as outputs."""
    found: set[str] = set()
    for target in re.findall(r'<a href="([^"#]+)(?:#[^"]*)?"', body):
        parsed = urlsplit(target)
        if parsed.scheme or target.startswith(("mailto:", "//")):
            continue
        output = str(PurePosixPath(PurePosixPath(page.output).parent / target))
        parts: list[str] = []
        for part in PurePosixPath(output).parts:
            if part == "..":
                if parts:
                    parts.pop()
            elif part != ".":
                parts.append(part)
        resolved = "/".join(parts)
        if resolved in site.page_by_output and resolved != page.output:
            found.add(resolved)
    return found


def backlink_list(site: Site, here: str, sources: list[str]) -> str:
    links = [f'<a href="{html.escape(relative_route(here, source), quote=True)}">{html.escape(site.page_by_output[source].title)}</a>' for source in sorted(set(sources), key=lambda name: site.page_by_output[name].title.lower())]
    return ", ".join(links)


def add_backlinks(site: Site, rendered: dict[str, tuple[str, list[tuple[int, str, str]]]], mentions: dict[str, list[str]]) -> dict[str, tuple[str, list[tuple[int, str, str]]]]:
    """Add "Mentioned in" lists: per glossary entry, and per page linked from others."""
    assert site.glossary is not None
    glossary = site.glossary
    incoming: dict[str, list[str]] = {}
    for page in site.pages:
        for target in page_links(site, page, rendered[page.output][0]):
            if page.output != glossary.page:
                incoming.setdefault(target, []).append(page.output)
    result = dict(rendered)
    body, headings = result[glossary.page]
    starts = [(match.start(), int(match.group(1)), match.group(2)) for match in re.finditer(r'<h([1-6]) id="([^"]+)"', body)]
    inserts: list[tuple[int, str]] = []
    for index, (_, level, anchor) in enumerate(starts):
        if level != glossary.entry_level or anchor not in mentions:
            continue
        end = next((start for start, other, _ in starts[index + 1:] if other <= glossary.entry_level), None)
        if end is None:
            closing = re.search(r"<hr>|$", body[starts[index][0]:])
            end = starts[index][0] + (closing.start() if closing else len(body) - starts[index][0])
        inserts.append((end, f'<p class="term-backlinks">Mentioned in: {backlink_list(site, glossary.page, mentions[anchor])}</p>\n'))
    for position, text in sorted(inserts, reverse=True):
        body = body[:position] + text + body[position:]
    result[glossary.page] = (body, headings)
    for output, sources in incoming.items():
        body, headings = result[output]
        result[output] = (body + f'\n<aside class="backlinks" aria-label="Mentioned in"><p>Mentioned in: {backlink_list(site, output, sources)}</p></aside>', headings)
    return result


def lint(site: Site) -> list[str]:
    """Bold terms of one to three words that the glossary does not explain.

    A single all-lowercase word with no digit or hyphen is read as emphasis
    ("**not**"), not as a coined term. A candidate that contains a glossary
    term ("a **trained holder**") counts as explained by it.
    """
    if site.glossary is None:
        fail("lint needs a site with a glossary")
    glossary = site.glossary
    pattern = glossary.pattern
    known = glossary.common | glossary.ignore
    findings: list[str] = []
    for page in site.pages:
        if page.output == glossary.page:
            continue
        in_code = False
        seen: set[str] = set()
        for number, line in enumerate(page.read().splitlines(), start=1):
            if line.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            for raw in re.findall(r"\*\*([^*\n]+)\*\*", re.sub(r"`[^`]*`", "", line)):
                candidate = plain(raw)
                if not re.fullmatch(r"[A-Za-z][\w'’\- /]*", candidate) or len(candidate.split()) > 3:
                    continue
                if re.fullmatch(r"[a-z]+", candidate) or any(pattern.fullmatch(candidate) for pattern in glossary.ignore_patterns):
                    continue
                key = normal_term(candidate)
                if key in seen or key in known or glossary.term_for(candidate):
                    continue
                if pattern is not None and pattern.search(html.escape(candidate, quote=False)):
                    continue
                seen.add(key)
                findings.append(f"{page.source}:{number}: {candidate!r} has no glossary entry and is not common knowledge")
    return findings


def validate(site: Site, destination: Path) -> None:
    pages = {page.output: (destination / page.output).read_text(encoding="utf-8") for page in site.pages}
    ids = {name: set(re.findall(r'\bid="([^"]+)"', text)) for name, text in pages.items()}
    errors: list[str] = []
    for page in site.pages:
        name, text = page.output, pages[page.output]
        if 'name="viewport"' not in text:
            errors.append(f"{name}: missing viewport")
        if page.explainer:
            declaration = re.search(r'<aside class="explainer-meta".*?</aside>', text, re.DOTALL)
            if not declaration:
                errors.append(f"{name}: missing visible explainer declaration")
            else:
                block = declaration.group(0)
                for field in EXPLAINER_FIELDS:
                    if html.escape(str(page.explainer[field])) not in block:
                        errors.append(f"{name}: missing explainer metadata {field}")
                if page.explainer.get("not_human_reviewed") and "Not human-reviewed" not in block:
                    errors.append(f"{name}: missing not-human-reviewed caveat")
        for attr, target_value in re.findall(r'(href|src)="([^"]+)"', text):
            parsed = urlsplit(target_value)
            if parsed.scheme or target_value.startswith(("mailto:", "//")):
                continue
            target_name = posixpath.normpath(str(PurePosixPath(name).parent / (parsed.path or PurePosixPath(name).name)))
            target = destination / target_name
            if not target.exists():
                errors.append(f"{name}: missing target {attr}={target_value}")
            elif parsed.fragment and parsed.fragment not in ids.get(target_name, set()):
                errors.append(f"{name}: missing fragment {target_value}")
    if errors:
        raise SystemExit("Link/metadata validation failed:\n" + "\n".join(errors))


def file_map(root: Path) -> dict[Path, bytes]:
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def check(site: Site) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        candidate = Path(tmp)
        build(site, candidate)
        expected = file_map(candidate)
        actual = file_map(site.output) if site.output.exists() else {}
        if expected != actual:
            missing = sorted(str(path) for path in expected.keys() - actual.keys())
            extra = sorted(str(path) for path in actual.keys() - expected.keys())
            changed = sorted(str(path) for path in expected.keys() & actual.keys() if expected[path] != actual[path])
            raise SystemExit(f"output is stale (missing={missing}, extra={extra}, changed={changed})")
        print(f"{site.output} is byte-reproducible and all local links/metadata resolve")


def front_matter(text: str, source: Path) -> tuple[dict[str, str], str]:
    """Split a leading ``---`` block of ``key: value`` lines from the body.

    Only flat string values are allowed; that is all a digest header needs and
    it keeps the format readable without a YAML parser.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    meta: dict[str, str] = {}
    for number, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            return meta, "\n".join(lines[number:]) + "\n"
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep or not re.fullmatch(r"[a-z_]+", key.strip()):
            fail(f"{source}:{number}: front matter lines are 'key: value'; got {line!r}")
        meta[key.strip()] = value.strip().strip('"')
    fail(f"{source}: front matter opened with --- is never closed")


def digest_meta(meta: dict[str, str], source: Path) -> dict[str, str]:
    missing = [key for key in DIGEST_REQUIRED if not meta.get(key)]
    if missing:
        fail(f"{source}: digest front matter missing: {', '.join(missing)}")
    unknown = sorted(set(meta) - set(DIGEST_REQUIRED) - set(DIGEST_OPTIONAL))
    if unknown:
        fail(f"{source}: unknown digest front matter: {', '.join(unknown)}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", meta["date"]):
        fail(f"{source}: digest date must be YYYY-MM-DD; got {meta['date']!r}")
    return meta


def digest_declaration(meta: dict[str, str]) -> str:
    labels = (("Reader", "reader"), ("Date", "date"), ("Charter", "charter"), ("Status", "status"), ("Supersedes", "supersedes"))
    rows = "".join(f"<div><dt>{label}</dt><dd>{html.escape(meta[key])}</dd></div>" for label, key in labels if meta.get(key))
    return f'<aside class="digest-meta" aria-label="Digest declaration"><dl>{rows}</dl></aside>'


def render_document(source: Path, *, digest: bool = True, stylesheet: Path = DIGEST_STYLESHEET) -> str:
    """Render one markdown file as a standalone page, with no site config.

    With ``digest`` the file must open with digest front matter, which becomes
    the page title and a visible declaration. Without it (older digests written
    before the format), the first heading is the title. Relative links are left
    as written, so they resolve beside the source file.
    """
    source = source.resolve()
    meta, body = front_matter(source.read_text(encoding="utf-8"), source)
    if digest:
        meta = digest_meta(meta, source)
        title = meta["title"]
        body = f"# {title}\n\n{body}"
    else:
        headings = heading_data(source, body)[1]
        title = meta.get("title") or (headings[0][1] if headings else source.stem)
    page = Page(source, source.name, title, None, body)
    site = Site(
        config_path=source, output=source.parent, description=meta.get("summary", title),
        brand="Digest" if digest else "Document", brand_suffix="", footer_html="",
        stylesheet="", inline_stylesheet=stylesheet, write_nojekyll=False, pages=(page,),
        navigation=(), assets=(), aliases={}, section_reference_page=None,
    )
    rendered, headings = render_markdown(site, page, {})
    if digest:
        first_heading_end = rendered.index("</h1>") + len("</h1>")
        rendered = rendered[:first_heading_end] + digest_declaration(meta) + rendered[first_heading_end:]
    contents = headings if sum(2 <= level <= 3 for level, _, _ in headings) >= 3 else []
    return shell(site, page, rendered, contents)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=None, help="JSON site config (default: site.json or site/site.json under the working directory)")
    parser.add_argument("--check", action="store_true", help="fail if committed output is stale")
    parser.add_argument("--digest", type=Path, help="render one digest markdown file as a standalone page instead of a site")
    parser.add_argument("--out", type=Path, help="with --digest: write here instead of standard output")
    parser.add_argument("--lint", action="store_true", help="report bold terms the site glossary does not explain; exit 1 if any")
    args = parser.parse_args()
    if args.digest:
        try:
            page = render_document(args.digest)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        if args.out:
            args.out.write_text(page, encoding="utf-8", newline="\n")
        else:
            print(page, end="")
        return
    try:
        site = load_site(args.config if args.config is not None else default_config())
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    try:
        if args.lint:
            findings = lint(site)
            for finding in findings:
                print(finding)
            print(f"lint: {len(findings)} unexplained term(s)")
            raise SystemExit(1 if findings else 0)
        if args.check:
            check(site)
        else:
            build(site, site.output)
            print(f"Built {len(site.pages)} pages in {site.output}")
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
