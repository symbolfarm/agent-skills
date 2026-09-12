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
"""

from __future__ import annotations

import argparse
import html
import json
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


@dataclass(frozen=True)
class Page:
    source: Path
    output: str
    title: str
    explainer: dict[str, Any] | None = None


@dataclass(frozen=True)
class Site:
    config_path: Path
    output: Path
    description: str
    brand: str
    brand_suffix: str
    footer_html: str
    stylesheet: str
    write_nojekyll: bool
    pages: tuple[Page, ...]
    navigation: tuple[tuple[str, str], ...]
    assets: tuple[tuple[Path, str], ...]
    aliases: dict[str, str]
    section_reference_page: str | None

    @property
    def source_routes(self) -> dict[Path, str]:
        return {page.source.resolve(): page.output for page in self.pages}

    @property
    def page_by_output(self) -> dict[str, Page]:
        return {page.output: page for page in self.pages}


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

    aliases = raw.get("aliases", {})
    if not isinstance(aliases, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in aliases.items()):
        fail("aliases must be a string-to-string object")

    output = resolve_from(base, str(raw.get("output", "docs")))
    return Site(
        config_path=config_path,
        output=output,
        description=str(raw.get("description", "Explainer pages")),
        brand=str(raw.get("brand", "Explainers")),
        brand_suffix=str(raw.get("brand_suffix", "")),
        footer_html=str(raw.get("footer_html", "")),
        stylesheet=str(raw.get("stylesheet", "styles.css")),
        write_nojekyll=bool(raw.get("write_nojekyll", True)),
        pages=tuple(pages),
        navigation=tuple(navigation),
        assets=tuple(assets),
        aliases=dict(aliases),
        section_reference_page=section_page,
    )


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


def heading_data(source: Path) -> tuple[dict[str, str], list[tuple[int, str, str]]]:
    sections: dict[str, str] = {}
    headings: list[tuple[int, str, str]] = []
    used: dict[str, int] = {}
    for line in source.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
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
    return target


def inline(text: str, site: Site, page: Page, report_sections: dict[str, str]) -> str:
    tokens: list[str] = []

    def hold(value: str) -> str:
        tokens.append(value)
        return f"\x00{len(tokens) - 1}\x00"

    def markdown_image(match: re.Match[str]) -> str:
        alt, target = match.group(1), link_target(site, page, match.group(2))
        return hold(f'<img src="{html.escape(target, quote=True)}" alt="{html.escape(alt, quote=True)}">')

    def markdown_link(match: re.Match[str]) -> str:
        label, target = match.group(1), link_target(site, page, match.group(2))
        return hold(f'<a href="{html.escape(target, quote=True)}">{html.escape(label)}</a>')

    text = re.sub(r"!\[([^]]*)\]\(([^)]+)\)", markdown_image, text)
    text = re.sub(r"\[([^]]+)\]\(([^)]+)\)", markdown_link, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", lambda m: hold(f"<code>{m.group(1)}</code>"), text)
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


def render_markdown(site: Site, page: Page, report_sections: dict[str, str]) -> tuple[str, list[tuple[int, str, str]]]:
    lines = page.source.read_text(encoding="utf-8").splitlines()
    _, headings = heading_data(page.source)
    heading_iter = iter(headings)
    output: list[str] = []
    paragraph: list[str] = []
    list_kind: str | None = None
    in_code = False
    code_lines: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{inline(' '.join(part.strip() for part in paragraph), site, page, report_sections)}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_kind
        if list_kind:
            output.append(f"</{list_kind}>")
            list_kind = None

    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
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
            output.append('<div class="table-wrap"><table><thead><tr>' + "".join(f"<th>{inline(cell, site, page, report_sections)}</th>" for cell in rows[0]) + "</tr></thead><tbody>")
            for row in rows[2:]:
                output.append("<tr>" + "".join(f"<td>{inline(cell, site, page, report_sections)}</td>" for cell in row) + "</tr>")
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
            output.append(f"<li>{inline(' '.join(parts), site, page, report_sections)}</li>")
            continue
        if re.match(r"^\s*---+\s*$", line):
            flush_paragraph(); close_list(); output.append("<hr>"); index += 1; continue
        if line.startswith("> "):
            flush_paragraph(); close_list(); output.append(f"<blockquote>{inline(line[2:], site, page, report_sections)}</blockquote>"); index += 1; continue
        if not line.strip():
            flush_paragraph(); close_list(); index += 1; continue
        paragraph.append(line)
        index += 1
    flush_paragraph(); close_list()
    if in_code:
        fail(f"Unclosed code fence in {page.source}")
    return "\n".join(output), headings


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


def shell(site: Site, page: Page, body: str, headings: list[tuple[int, str, str]]) -> str:
    nav = "".join(f'<a href="{relative_route(page.output, href)}"{(" aria-current=\"page\"" if href == page.output else "")}>{label}</a>' for href, label in site.navigation)
    suffix = f" <span>{html.escape(site.brand_suffix)}</span>" if site.brand_suffix else ""
    home = relative_route(page.output, site.navigation[0][0]) if site.navigation else PurePosixPath(page.output).name
    stylesheet = relative_route(page.output, site.stylesheet)
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{html.escape(site.description, quote=True)}">
  <title>{html.escape(page.title)}</title>
  <link rel="stylesheet" href="{html.escape(stylesheet, quote=True)}">
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
    for page in site.pages:
        body, headings = render_markdown(site, page, report_sections)
        target = destination / page.output
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(shell(site, page, body, headings), encoding="utf-8", newline="\n")
    for source, output in site.assets:
        copy_asset(source, destination / output)
    if site.write_nojekyll:
        (destination / ".nojekyll").write_text("", encoding="utf-8")
    validate(site, destination)


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
            target_name = str((PurePosixPath(name).parent / (parsed.path or PurePosixPath(name).name)))
            target_name = str(PurePosixPath(target_name))
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=None, help="JSON site config (default: site.json or site/site.json under the working directory)")
    parser.add_argument("--check", action="store_true", help="fail if committed output is stale")
    args = parser.parse_args()
    try:
        site = load_site(args.config if args.config is not None else default_config())
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if args.check:
        check(site)
    else:
        build(site, site.output)
        print(f"Built {len(site.pages)} pages in {site.output}")


if __name__ == "__main__":
    main()
