"""Bounded logical HTML blocks with explicit ownership; no model or network calls.

Lists and tables are indivisible evidence blocks. Headings inside an infobox or
accordion panel do not change the scope of later siblings. This is a conservative
HTML adapter, not a claim to understand every site's layout.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from .concepts import (HTML_PAGE_SUFFIXES, TEXT_PAGE_SUFFIXES, NormalizedPage,
                       NormalizedSection, PageNormalizationError,
                       _normalize_language_tag, _normalize_plain_text)

VERSION = "swisstip.logical-blocks/v3"
_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_HIDDEN = {"script", "style", "noscript", "svg", "template", "head"}
_ATOMIC = {"p": "paragraph", "address": "address", "ul": "list", "ol": "list",
           "dl": "definition_list", "table": "table", "pre": "preformatted", "blockquote": "quotation"}
# Exact component tokens observed in SEM and Zurich snapshots. Do not match
# substrings: e.g. mdl-anchornav__wrapper contains the substantive page body,
# and mdl-page-header contains the article title and introductory prose.
_NAVIGATION_CLASSES = {
    "mod-mainnavigation", "nav-main", "navbar-nav", "nav-tabs", "mod-leftnavigation",
    "mod-breadcrumb", "breadcrumb", "mdl-skiplinks", "mdl-anchornav",
    "mdl-page-header__breadcrumb", "mdl-page-header__logo-container",
    "mdl-footer__menu", "mdl-footer__submenu", "mdl-footer__social-media",
    "site-map", "mod-socialshare", "mdl-scroll2top", "mdl-backtochat",
}
# These Zurich related-link components were previously emitted as ordinary
# lists. Classify their existing blocks without collapsing the subtree, so
# section IDs, ownership and evidence offsets remain comparable to v2.
_CONTENT_NAVIGATION_CLASSES = {
    "mdl-related-content", "mdl-content_nav", "mdl-content_nav__list",
}
_CONTENT_CONTAINERS = {"main", "article", "section", "aside", "details"}


@dataclass
class Node:
    tag: str
    attrs: dict[str, str | None] = field(default_factory=dict)
    children: list[Node | str] = field(default_factory=list)


class TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]
        self.nodes = 0
        self.issues: set[str] = set()

    def handle_starttag(self, tag, attrs):
        self.nodes += 1
        if self.nodes > 50_000 or len(self.stack) > 128:
            raise PageNormalizationError("HTML exceeds logical structure limits")
        # HTML permits omitted closing tags for common list/table elements.
        closable = {"li": {"li"}, "p": {"p"}, "tr": {"tr"}, "td": {"td", "th"}, "th": {"td", "th"}}
        if tag in closable and self.stack[-1].tag in closable[tag]:
            self.stack.pop()
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                dangling = self.stack[index + 1:]
                if any(n.tag not in {"p", "li", "dt", "dd", "td", "th", "tr", "tbody", "thead"} for n in dangling):
                    self.issues.add("malformed_html_nesting")
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _text(node: Node | str) -> str:
    if isinstance(node, str):
        return node
    if node.tag in _HIDDEN:
        return ""
    if node.tag == "br":
        return "\n"
    value = "".join(_text(child) for child in node.children)
    if node.tag == "a":
        target = node.attrs.get("href") or ""
        if target.lower().startswith(("mailto:", "tel:")) and target not in value:
            value += f" ({target})"
    if node.tag in {"td", "th"}:
        return " ".join(value.split()) + " | "
    if node.tag in {*_ATOMIC, "div", "section", "aside", "li", "dt", "dd", "tr", "caption", "h1", "h2", "h3", "h4", "h5", "h6"}:
        return "\n" + value + "\n"
    return value


def _clean(value):
    return re.sub(r"\n{3,}", "\n\n", "\n".join(" ".join(line.split()) for line in value.splitlines())).strip()


def _owned(node):
    classes = (node.attrs.get("class") or "").lower()
    return node.tag in {"section", "article", "aside", "details"} or node.attrs.get("role") == "tabpanel" or any(
        marker in classes for marker in ("infobox", "info-box", "accordion", "tab-panel"))


def _only_navigation_controls(node):
    """Recognize standalone SEM sidebar/top links, including inline wrappers.

    A paragraph with any substantive prose remains intact, as do ordinary
    application links and contact links. Labels/languages are not classifiers.
    """
    if isinstance(node, str):
        return not node.strip()
    if node.tag == "a":
        classes = set((node.attrs.get("class") or "").lower().split())
        target = node.attrs.get("href")
        return ((target == "#context-sidebar" and "icon--root" in classes)
                or (target == "#" and "icon--power" in classes))
    return node.tag in {"p", "small", "span", "strong", "em"} and all(
        _only_navigation_controls(child) for child in node.children)


def _navigation(node, in_content):
    role = (node.attrs.get("role") or "").lower()
    classes = set((node.attrs.get("class") or "").lower().split())
    if (node.tag == "nav" or role == "navigation" or classes & _NAVIGATION_CLASSES
            or _only_navigation_controls(node)):
        return True
    # Page-level banners own their menus/search/skip links. Article and section
    # headers can contain claims, so preserve them even when they have this ID.
    return (not in_content and node.tag == "header"
            and (role == "banner" or node.attrs.get("id") == "header"))


def _content_navigation(node):
    return bool(set((node.attrs.get("class") or "").lower().split()) & _CONTENT_NAVIGATION_CLASSES)


def normalize_blocks(path: Path, value: str, raw: bytes) -> NormalizedPage:
    sections = []
    title, language = path.stem, None
    serial = 0

    def scope():
        nonlocal serial
        serial += 1
        return f"scope-{serial:04d}"

    def emit(text, kind, headings, owner, issues=()):
        text = _clean(text)
        if text:
            sections.append(NormalizedSection(f"section-{len(sections)+1:04d}",
                            " > ".join(headings[k] for k in sorted(headings)), text,
                            block_kind=kind, scope_id=owner, structure_issues=tuple(issues)))

    if path.suffix.lower() in HTML_PAGE_SUFFIXES:
        parser = TreeParser()
        parser.feed(value)
        parser.close()
        if any(n.tag not in {"html", "body", "p", "li", "td", "th", "tr", "tbody"} for n in parser.stack[1:]):
            parser.issues.add("unclosed_html_structure")

        def walk(node, headings, owner, contextual=False, in_content=False, in_navigation=False):
            nonlocal title, language
            in_content = in_content or node.tag in _CONTENT_CONTAINERS or node.attrs.get("role") == "main"
            in_navigation = in_navigation or _content_navigation(node)
            pending = []

            def flush():
                emit("".join(pending), "navigation" if in_navigation else "text", headings, owner, parser.issues)
                pending.clear()

            for child in node.children:
                if isinstance(child, str):
                    pending.append(child)
                    continue
                if child.tag == "html":
                    language = _normalize_language_tag(child.attrs.get("lang"))
                if child.tag == "head":
                    for item in child.children:
                        if isinstance(item, Node) and item.tag == "title":
                            title = _clean(_text(item)) or title
                    continue
                if child.tag in _HIDDEN:
                    continue
                if _navigation(child, in_content):
                    flush()
                    # Retain the complete excluded subtree for the audit, but
                    # do not let its headings change ownership of later facts.
                    emit(_text(child), "navigation", headings, scope(), parser.issues)
                elif re.fullmatch(r"h[1-6]", child.tag):
                    flush()
                    level = int(child.tag[1])
                    headings = {k: v for k, v in headings.items() if k < level}
                    headings[level] = _clean(_text(child))
                    if not contextual:
                        owner = scope()
                    if level == 1 and title == path.stem:
                        title = headings[level]
                    emit(headings[level], "heading", headings, owner, parser.issues)
                elif child.tag in _ATOMIC:
                    flush()
                    issues = set(parser.issues)
                    # Complex table spans need an adapter/review, not flattened certainty.
                    def table_spans(n):
                        if isinstance(n, str):
                            return False
                        return any(n.attrs.get(a) not in (None, "1") for a in ("rowspan", "colspan")) or any(table_spans(c) for c in n.children)
                    if child.tag == "table" and table_spans(child):
                        issues.add("table_spans_require_review")
                    kind = "navigation" if in_navigation or _content_navigation(child) else _ATOMIC[child.tag]
                    emit(_text(child), kind, headings, owner, issues)
                elif _owned(child):
                    flush()
                    is_context = child.tag == "aside" or any(marker in (child.attrs.get("class") or "").lower()
                                                            for marker in ("infobox", "info-box"))
                    # A nested infobox supports its enclosing block group; its
                    # heading is local and must not relabel the continued list.
                    walk(child, dict(headings), owner if is_context else scope(), is_context, in_content, in_navigation)
                else:
                    flush()
                    headings, owner = walk(child, headings, owner, contextual, in_content, in_navigation)
            flush()
            return headings, owner

        walk(parser.root, {}, scope())
    elif path.suffix.lower() in TEXT_PAGE_SUFFIXES:
        title, source_sections = _normalize_plain_text(value, path.stem, preserve_structure=True)
        for heading, text in source_sections:
            # Keep the entire text section: do not guess list/table dependencies.
            emit(text or heading, "text_section", {1: heading} if heading else {}, scope())
    else:
        raise PageNormalizationError(f"unsupported page extension: {path.suffix}")
    if not sections:
        raise PageNormalizationError(f"page contains no extractable text: {path}")
    raw_hash = hashlib.sha256(raw).hexdigest()
    payload = {"version": VERSION, "source_sha256": raw_hash, "title": title,
               "language": language, "blocks": [s.content_dict() for s in sections]}
    content_hash = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return NormalizedPage(f"page-{content_hash[:16]}", str(path), title, language,
                          content_hash, tuple(sections), VERSION, raw_hash)
