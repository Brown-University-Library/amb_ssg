# /// script
# requires-python = ">=3.12,<3.13"
# ///

"""
Rebuilds the compact browser-search JSON from collection Markdown.

Usage:
    uv run ./scripts/rebuild_index_json.py

The script reads the maintained front matter under `content/collection/`,
validates the fields used by collection search and result cards, orders records
by item number, and writes `static/search/collection-records.json`.
"""

import json
import tomllib
from operator import itemgetter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COLLECTION_DIR = PROJECT_ROOT / "content" / "collection"
OUTPUT_PATH = PROJECT_ROOT / "static" / "search" / "collection-records.json"
EXPECTED_RECORD_COUNT = 151
STRING_EXTRA_FIELDS = (
    "item_id",
    "artist",
    "artist_dates",
    "nationality",
    "image",
)

type SearchRecord = dict[str, str | None]


def parse_front_matter(page_path: Path) -> dict[str, object]:
    """
    Parses a collection page's TOML front matter.

    Called by: build_record()
    """
    text = page_path.read_text(encoding="utf-8")
    parts = text.split("+++", maxsplit=2)
    if len(parts) != 3 or parts[0]:
        raise ValueError(f"Invalid TOML front matter: {page_path}")
    try:
        front_matter = tomllib.loads(parts[1])
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"Invalid TOML front matter in {page_path}: {error}") from error
    return front_matter


def build_record(page_path: Path) -> tuple[int, SearchRecord]:
    """
    Builds one approved browser-search record from collection front matter.

    Called by: load_records()
    """
    front_matter = parse_front_matter(page_path)
    slug = page_path.parent.name
    title = front_matter.get("title")
    extra = front_matter.get("extra")

    if not isinstance(title, str) or not title:
        raise ValueError(f"Missing or invalid title for {slug}")
    if not isinstance(extra, dict):
        raise ValueError(f"Missing [extra] data for {slug}")

    values: dict[str, str] = {}
    for field in STRING_EXTRA_FIELDS:
        value = extra.get(field)
        if not isinstance(value, str):
            raise ValueError(f"Missing or invalid {field} for {slug}")
        values[field] = value

    number = extra.get("number")
    has_image = extra.get("has_image")
    if type(number) is not int:
        raise ValueError(f"Missing or invalid number for {slug}")
    if not isinstance(has_image, bool):
        raise ValueError(f"Missing or invalid has_image for {slug}")
    if not values["artist"]:
        raise ValueError(f"Missing artist for {slug}")

    expected_slug = f"ab-{number}"
    expected_item_id = f"AB {number}"
    expected_image = f"images/collection/{slug}.webp" if has_image else ""
    if slug != expected_slug or values["item_id"] != expected_item_id:
        raise ValueError(f"Slug, number, and item identifier differ for {slug}")
    if values["image"] != expected_image:
        raise ValueError(f"Invalid image path for {values['item_id']}")

    record: SearchRecord = {
        "item_id": values["item_id"],
        "slug": slug,
        "artist": values["artist"],
        "artist_dates": values["artist_dates"],
        "nationality": values["nationality"],
        "title": title,
        "image": values["image"] if has_image else None,
    }
    return number, record


def load_records(collection_dir: Path) -> list[SearchRecord]:
    """
    Loads, validates, and numerically orders all collection search records.

    Called by: main()
    """
    page_paths = list(collection_dir.glob("ab-*/index.md"))
    if len(page_paths) != EXPECTED_RECORD_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_RECORD_COUNT} collection pages, found {len(page_paths)}"
        )

    numbered_records = [build_record(page_path) for page_path in page_paths]
    numbers = {number for number, record in numbered_records}
    item_ids = {record["item_id"] for number, record in numbered_records}
    if len(numbers) != EXPECTED_RECORD_COUNT or len(item_ids) != EXPECTED_RECORD_COUNT:
        raise ValueError("Collection numbers and item identifiers must be unique")

    numbered_records.sort(key=itemgetter(0))
    records = [record for number, record in numbered_records]
    return records


def serialize_records(records: list[SearchRecord]) -> str:
    """
    Serializes records in the compact browser-search data format.

    Called by: main()
    """
    payload: dict[str, object] = {
        "schema_version": 1,
        "record_count": len(records),
        "records": records,
    }
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    return text


def write_index_json(output_path: Path, text: str) -> bool:
    """
    Writes the browser-search data only when its serialized content changed.

    Called by: main()
    """
    existing = output_path.read_text(encoding="utf-8") if output_path.exists() else None
    changed = existing != text
    if changed:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    return changed


def main() -> None:
    """
    Rebuilds the tracked browser-search data from maintained collection pages.

    Called by: command line entry point
    """
    try:
        records = load_records(COLLECTION_DIR)
        text = serialize_records(records)
        changed = write_index_json(OUTPUT_PATH, text)
    except (OSError, ValueError) as error:
        raise SystemExit(f"Could not rebuild browser-search data: {error}") from error

    relative_output = OUTPUT_PATH.relative_to(PROJECT_ROOT)
    action = "Wrote" if changed else "Already current"
    print(f"{action}: {relative_output} ({len(records)} records)")


if __name__ == "__main__":
    main()
