#!/usr/bin/env python3
"""Render Zola artwork pages and compact browser-search data."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "collection_records.json"
CONTENT_DIR = PROJECT_ROOT / "content" / "collection"
SEARCH_PATH = PROJECT_ROOT / "static" / "search" / "collection-records.json"

EXPECTED_KEYS = {
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


def toml_string(value: object) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def validate(payload: dict[str, object]) -> list[dict[str, object]]:
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported collection data schema")
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != 151:
        raise ValueError("Expected exactly 151 normalized records")

    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Each collection record must be an object")
        keys = set(record)
        if keys != EXPECTED_KEYS:
            unknown = sorted(keys - EXPECTED_KEYS)
            missing = sorted(EXPECTED_KEYS - keys)
            raise ValueError(f"Record schema mismatch; extra={unknown}, missing={missing}")
        slug = str(record["slug"])
        if not re.fullmatch(r"ab-\d{1,3}", slug) or slug in seen:
            raise ValueError(f"Invalid or duplicate slug: {slug}")
        seen.add(slug)
    return records


def page_text(record: dict[str, object]) -> str:
    description_parts = [str(record["artist"])]
    if record["nationality"]:
        description_parts.append(str(record["nationality"]))
    description = " — ".join(description_parts)

    lines = [
        "+++",
        f"title = {toml_string(record['title'])}",
        f"description = {toml_string(description)}",
        'template = "collection-item.html"',
        "in_search_index = false",
        "",
        "[extra]",
    ]
    for key in (
        "item_id",
        "inventory_id",
        "artist",
        "artist_dates",
        "nationality",
        "time_period",
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
        "image_alt",
    ):
        lines.append(f"{key} = {toml_string(record[key])}")

    image_path = (
        f"images/collection/{record['slug']}.webp"
        if record["has_image"]
        else ""
    )
    lines.extend(
        [
            f"number = {int(record['number'])}",
            f"has_image = {str(bool(record['has_image'])).lower()}",
            f"image = {toml_string(image_path)}",
            "+++",
            "",
        ]
    )
    return "\n".join(lines)


def render_pages(records: list[dict[str, object]]) -> None:
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    expected = {str(record["slug"]) for record in records}

    for path in CONTENT_DIR.iterdir():
        if path.is_dir() and re.fullmatch(r"ab-\d{1,3}", path.name):
            if path.name not in expected:
                shutil.rmtree(path)

    for record in records:
        page_dir = CONTENT_DIR / str(record["slug"])
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.md").write_text(page_text(record), encoding="utf-8")


def render_search(records: list[dict[str, object]]) -> None:
    compact = []
    for record in records:
        compact.append(
            {
                "item_id": record["item_id"],
                "slug": record["slug"],
                "artist": record["artist"],
                "artist_dates": record["artist_dates"],
                "nationality": record["nationality"],
                "title": record["title"],
                "image": (
                    f"images/collection/{record['slug']}.webp"
                    if record["has_image"]
                    else None
                ),
            }
        )
    SEARCH_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEARCH_PATH.write_text(
        json.dumps(
            {"schema_version": 1, "record_count": len(compact), "records": compact},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    records = validate(payload)
    render_pages(records)
    render_search(records)
    print(f"Rendered {len(records)} collection pages and browser-search records")


if __name__ == "__main__":
    main()
