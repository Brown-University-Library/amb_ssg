#!/usr/bin/env python3
"""Validate the portable Zola source or a generated AMB site."""

from __future__ import annotations

import json
import re
import sys
import tomllib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "collection_records.json"
ABSOLUTE_PATH_PATTERNS = (
    re.compile(r"/(?:Users|home|root)/"),
    re.compile(r"/private/(?:tmp|var)/"),
    re.compile(r"\b[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/]"),
    re.compile(r"file://", re.IGNORECASE),
)
LOCAL_URL_PATTERNS = (
    re.compile(r"localhost", re.IGNORECASE),
    re.compile(r"127\.0\.0\.1"),
)
COLLECTION_RECORD_KEYS = {
    "item_id",
    "inventory_id",
    "artist",
    "artist_dates",
    "nationality",
    "time_period",
    "title",
    "artwork_date",
    "medium",
    "dimensions",
    "acquisition_date",
    "provenance",
    "library",
    "room",
    "catalog_entry",
    "catalog_artist",
    "catalog_dates",
    "catalog_school",
    "catalog_note",
    "catalog_title",
    "description",
    "references",
    "formats",
    "location",
    "image",
    "number",
    "slug",
    "artist_sort",
    "title_sort",
    "artist_initial",
    "title_initial",
    "has_image",
    "image_alt",
}
SEARCH_RECORD_KEYS = {
    "item_id",
    "slug",
    "artist",
    "artist_dates",
    "nationality",
    "title",
    "image",
}
NARRATIVE_PATHS = (
    "about",
    "about-the-database",
    "catalog-introduction",
    "hawkins-writings",
    "early-memorial",
    "early-memorial-rooms",
    "browns-of-rhode-island",
)


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attribute = "href" if tag in {"a", "link"} else "src"
        if tag not in {"a", "link", "img", "script", "source"}:
            return
        values = dict(attrs)
        if values.get(attribute):
            self.urls.append(str(values[attribute]))


def text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        relative_parts = path.relative_to(root).parts
        if any(
            part in {".git", ".work", "themes", "assets"}
            for part in relative_parts
        ):
            continue
        if path.suffix.casefold() in {
            ".md",
            ".toml",
            ".html",
            ".css",
            ".js",
            ".json",
            ".py",
            ".txt",
            ".xml",
        } or path.name in {"Makefile", ".gitignore", ".gitattributes"}:
            yield path


def find_patterns(root: Path, patterns: tuple[re.Pattern[str], ...]) -> list[str]:
    failures: list[str] = []
    for path in text_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in patterns:
            if pattern.search(text):
                failures.append(f"{path.relative_to(root)} matches {pattern.pattern}")
    return failures


def validate_internal_links(build_dir: Path) -> list[str]:
    failures: list[str] = []
    config = tomllib.loads(
        (PROJECT_ROOT / "zola.toml").read_text(encoding="utf-8")
    )
    base = urlparse(config["base_url"])
    base_path = base.path.rstrip("/")
    missing: set[tuple[str, str]] = set()

    for page_path in build_dir.rglob("*.html"):
        parser = LinkCollector()
        parser.feed(page_path.read_text(encoding="utf-8", errors="replace"))
        relative_page = page_path.relative_to(build_dir)
        public_page = (
            base_path + "/"
            if relative_page.as_posix() == "index.html"
            else base_path + "/" + relative_page.parent.as_posix().strip("/") + "/"
        )

        for url in parser.urls:
            parsed = urlparse(url)
            if parsed.scheme in {"mailto", "tel", "data"} or url.startswith("//"):
                continue
            if parsed.scheme in {"http", "https"}:
                if parsed.netloc != base.netloc:
                    continue
                public_path = parsed.path
                if not (
                    public_path == base_path
                    or public_path.startswith(base_path + "/")
                ):
                    continue
            elif parsed.scheme:
                continue
            elif url.startswith("#"):
                continue
            else:
                public_path = urlparse(urljoin(public_page, url)).path

            relative_url = unquote(public_path[len(base_path) :]).lstrip("/")
            target = build_dir / relative_url
            if public_path.endswith("/") or target.is_dir():
                target = target / "index.html"
            if not target.is_file():
                missing.add((relative_page.as_posix(), url))

    for source, url in sorted(missing):
        failures.append(f"Broken internal link in {source}: {url}")
    return failures


def validate_source() -> list[str]:
    failures: list[str] = []
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    if payload.get("record_count") != 151 or len(records) != 151:
        failures.append("Normalized collection must contain 151 records")

    ids = {record.get("item_id") for record in records}
    if len(ids) != 151:
        failures.append("Normalized collection identifiers must be unique")
    for record in records:
        if set(record) != COLLECTION_RECORD_KEYS:
            failures.append(f"Unexpected normalized fields for {record.get('item_id')}")

    pages = list((PROJECT_ROOT / "content" / "collection").glob("ab-*/index.md"))
    if len(pages) != 151:
        failures.append(f"Expected 151 artwork Markdown pages, found {len(pages)}")

    search_path = PROJECT_ROOT / "static" / "search" / "collection-records.json"
    search_payload = json.loads(search_path.read_text(encoding="utf-8"))
    search_records = search_payload.get("records", [])
    if search_payload.get("record_count") != 151 or len(search_records) != 151:
        failures.append("Browser-search data must contain 151 records")
    if {record.get("item_id") for record in search_records} != ids:
        failures.append("Browser-search identifiers must match normalized collection")
    normalized_by_id = {record["item_id"]: record for record in records}
    for record in search_records:
        if set(record) != SEARCH_RECORD_KEYS:
            failures.append(
                f"Unexpected browser-search fields for {record.get('item_id')}"
            )
            continue
        normalized = normalized_by_id.get(record["item_id"])
        if normalized is None:
            continue
        expected_search = {
            "item_id": normalized["item_id"],
            "slug": normalized["slug"],
            "artist": normalized["artist"],
            "artist_dates": normalized["artist_dates"],
            "nationality": normalized["nationality"],
            "title": normalized["title"],
            "image": (
                f"images/collection/{normalized['slug']}.webp"
                if normalized["has_image"]
                else None
            ),
        }
        if record != expected_search:
            failures.append(
                f"Browser-search record differs from normalized source: "
                f"{record.get('item_id')}"
            )

    for record in records:
        if record.get("has_image"):
            image = (
                PROJECT_ROOT
                / "static"
                / "images"
                / "collection"
                / f"{record['slug']}.webp"
            )
            if not image.is_file():
                failures.append(f"Missing web image for {record['item_id']}")

    failures.extend(find_patterns(PROJECT_ROOT, ABSOLUTE_PATH_PATTERNS))
    return failures


def validate_build(build_dir: Path) -> list[str]:
    failures: list[str] = []
    if not (build_dir / "index.html").is_file():
        failures.append("Built home page is missing")
    search_page = build_dir / "search" / "index.html"
    if not search_page.is_file():
        failures.append("Built search page is missing")
    else:
        search_html = search_page.read_text(encoding="utf-8", errors="replace")
        expected_search_ids = {
            "collection-search-form",
            "collection-search-query",
            "collection-search-submit",
            "collection-search-status",
            "collection-search-results",
        }

        class SearchElementCollector(HTMLParser):
            def __init__(self) -> None:
                super().__init__()
                self.ids: set[str] = set()

            def handle_starttag(
                self, tag: str, attrs: list[tuple[str, str | None]]
            ) -> None:
                element_id = dict(attrs).get("id")
                if element_id:
                    self.ids.add(element_id)

        search_elements = SearchElementCollector()
        search_elements.feed(search_html)
        missing_search_ids = sorted(expected_search_ids - search_elements.ids)
        if missing_search_ids:
            failures.append(
                "Built search page is missing required elements: "
                + ", ".join(missing_search_ids)
            )

    pages = list((build_dir / "collection").glob("ab-*/index.html"))
    if len(pages) != 151:
        failures.append(f"Expected 151 built artwork pages, found {len(pages)}")

    search_data = build_dir / "search" / "collection-records.json"
    if not search_data.is_file():
        failures.append("Built browser-search data is missing")
    else:
        payload = json.loads(search_data.read_text(encoding="utf-8"))
        source_search_data = (
            PROJECT_ROOT / "static" / "search" / "collection-records.json"
        )
        if search_data.read_bytes() != source_search_data.read_bytes():
            failures.append("Built browser-search data differs from source")
        search_records = payload.get("records", [])
        if payload.get("record_count") != 151 or len(search_records) != 151:
            failures.append("Built browser-search data must contain 151 records")
        identifiers = [record.get("item_id") for record in search_records]
        if len(set(identifiers)) != 151:
            failures.append("Built browser-search identifiers must be unique")
        for record in search_records:
            if set(record) != SEARCH_RECORD_KEYS:
                failures.append(
                    f"Unexpected built browser-search fields for "
                    f"{record.get('item_id')}"
                )
                continue
            target = build_dir / "collection" / record["slug"] / "index.html"
            if not target.is_file():
                failures.append(f"Search record has no page: {record.get('item_id')}")

    for narrative_path in NARRATIVE_PATHS:
        if not (build_dir / narrative_path / "index.html").is_file():
            failures.append(f"Built narrative page is missing: {narrative_path}")

    failures.extend(find_patterns(build_dir, ABSOLUTE_PATH_PATTERNS))
    failures.extend(find_patterns(build_dir, LOCAL_URL_PATTERNS))
    failures.extend(validate_internal_links(build_dir))

    forbidden_extensions = {".php", ".sql", ".tif", ".tiff"}
    for path in build_dir.rglob("*"):
        if path.is_file() and path.suffix.casefold() in forbidden_extensions:
            failures.append(f"Unexpected deployable file: {path.relative_to(build_dir)}")
    return failures


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "source"
    if mode == "source":
        failures = validate_source()
    elif mode == "build":
        build_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else PROJECT_ROOT / ".work" / "build"
        failures = validate_build(build_dir.resolve())
    else:
        raise SystemExit("Usage: validate.py source | validate.py build [directory]")

    if failures:
        raise SystemExit("Validation failed:\n- " + "\n- ".join(failures))
    print(f"{mode.capitalize()} validation passed")


if __name__ == "__main__":
    main()
