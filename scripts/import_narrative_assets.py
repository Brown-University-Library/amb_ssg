#!/usr/bin/env python3
"""Copy the selected legacy narrative images into the Zola source tree."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEGACY_ROOT = PROJECT_ROOT.parent / "amb"
OUTPUT_DIR = PROJECT_ROOT / "assets" / "narrative"

ABOUT_IMAGES = (
    "rhawkins.jpg",
    "ab64_color.jpg",
    "ab65_color.jpg",
    "flowers3.jpg",
    "ambline.jpg",
    "ab41_color.jpg",
    "ab91_color.jpg",
    "expo.jpg",
    "ab49.jpg",
)
ALBUM_IMAGES = tuple(f"album{number}.jpg" for number in range(1, 32) if number != 7)
SELECTED_IMAGES = ABOUT_IMAGES + ALBUM_IMAGES + ("album2.gif",)
ROOT_IMAGES = ("browns3.jpg",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", type=Path, default=DEFAULT_LEGACY_ROOT)
    return parser.parse_args()


def copy_selected(legacy_root: Path) -> None:
    sources = {
        name: legacy_root / "images" / name
        for name in SELECTED_IMAGES
    }
    sources.update({name: legacy_root / name for name in ROOT_IMAGES})

    missing = sorted(name for name, path in sources.items() if not path.is_file())
    if missing:
        raise ValueError(f"Missing selected narrative images: {', '.join(missing)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    expected = set(sources)
    for existing in OUTPUT_DIR.iterdir():
        if existing.is_file() and existing.name not in expected:
            existing.unlink()

    for name, source in sorted(sources.items()):
        target = OUTPUT_DIR / name
        if not target.exists() or source.stat().st_mtime_ns != target.stat().st_mtime_ns:
            shutil.copy2(source, target)


def main() -> None:
    args = parse_args()
    copy_selected(args.legacy_root)
    print(f"Imported {len(SELECTED_IMAGES) + len(ROOT_IMAGES)} narrative images")


if __name__ == "__main__":
    main()
