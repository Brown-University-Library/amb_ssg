#!/usr/bin/env python3
"""Create stable, web-ready images from the repository source assets."""

from __future__ import annotations

import json
import hashlib
import shutil
import struct
import subprocess
from functools import cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "collection_records.json"
COLLECTION_SOURCE = PROJECT_ROOT / "assets" / "collection"
COLLECTION_OUTPUT = PROJECT_ROOT / "static" / "images" / "collection"
NARRATIVE_SOURCE = PROJECT_ROOT / "assets" / "narrative"
NARRATIVE_OUTPUT = PROJECT_ROOT / "static" / "images" / "narrative"
MANIFEST_PATH = PROJECT_ROOT / "assets" / "image-derivatives.json"
WEBP_VERSION_PATH = PROJECT_ROOT / ".webp-version"
MAX_COLLECTION_EDGE = 1200
MAX_NARRATIVE_EDGE = 1600
QUALITY = 82


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


@cache
def recipe_digest() -> str:
    digest = hashlib.sha256()
    digest.update(Path(__file__).read_bytes())
    digest.update(WEBP_VERSION_PATH.read_bytes())
    return digest.hexdigest()


def derivative_signature(source: Path, target: Path, max_edge: int) -> str:
    digest = hashlib.sha256()
    digest.update(file_digest(source).encode("ascii"))
    digest.update(recipe_digest().encode("ascii"))
    digest.update(str(max_edge).encode("ascii"))
    digest.update(target.name.encode("utf-8"))
    return digest.hexdigest()


def image_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(32)
        if header[:3] == b"\xff\xd8\xff":
            handle.seek(2)
            while True:
                byte = handle.read(1)
                if not byte:
                    break
                if byte != b"\xff":
                    continue
                marker = handle.read(1)
                while marker == b"\xff":
                    marker = handle.read(1)
                if marker in {bytes([value]) for value in range(0xC0, 0xC4)} | {
                    bytes([value]) for value in range(0xC5, 0xC8)
                } | {bytes([value]) for value in range(0xC9, 0xCC)} | {
                    bytes([value]) for value in range(0xCD, 0xD0)
                }:
                    length = struct.unpack(">H", handle.read(2))[0]
                    data = handle.read(length - 2)
                    return struct.unpack(">HH", data[1:5])[::-1]
                length_bytes = handle.read(2)
                if len(length_bytes) != 2:
                    break
                length = struct.unpack(">H", length_bytes)[0]
                handle.seek(length - 2, 1)
        elif header[:6] in (b"GIF87a", b"GIF89a"):
            return struct.unpack("<HH", header[6:10])
        elif header[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", header[16:24])
    raise ValueError(f"Unsupported image format: {path}")


def target_size(path: Path, max_edge: int) -> tuple[int, int] | None:
    width, height = image_size(path)
    largest = max(width, height)
    if largest <= max_edge:
        return None
    scale = max_edge / largest
    return max(1, round(width * scale)), max(1, round(height * scale))


@cache
def ensure_tools() -> tuple[str, str]:
    cwebp = shutil.which("cwebp")
    gif2webp = shutil.which("gif2webp")
    if not cwebp or not gif2webp:
        raise SystemExit("WebP tools are required to regenerate web-ready images")
    expected = WEBP_VERSION_PATH.read_text(encoding="utf-8").strip()
    for executable in (cwebp, gif2webp):
        result = subprocess.run(
            [executable, "-version"],
            check=True,
            capture_output=True,
            text=True,
        )
        reported = result.stdout + result.stderr
        if expected not in reported:
            raise SystemExit(
                f"WebP tools {expected} are required to regenerate images"
            )
    return cwebp, gif2webp


def convert(
    source: Path,
    target: Path,
    max_edge: int,
    previous: dict[str, str] | None,
) -> dict[str, str]:
    signature = derivative_signature(source, target, max_edge)
    if (
        target.is_file()
        and previous
        and previous.get("input_sha256") == signature
        and previous.get("output_sha256") == file_digest(target)
    ):
        return previous

    target.parent.mkdir(parents=True, exist_ok=True)
    cwebp, gif2webp = ensure_tools()
    if source.suffix.casefold() == ".gif":
        command = [
            gif2webp,
            "-quiet",
            "-q",
            str(QUALITY),
            str(source),
            "-o",
            str(target),
        ]
    else:
        command = [cwebp, "-quiet", "-mt", "-q", str(QUALITY)]
        if size := target_size(source, max_edge):
            command.extend(["-resize", str(size[0]), str(size[1])])
        command.extend([str(source), "-o", str(target)])
    subprocess.run(command, check=True)
    return {
        "input_sha256": signature,
        "output_sha256": file_digest(target),
    }


def render_collection(
    previous: dict[str, dict[str, str]],
) -> dict[str, dict[str, str]]:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    expected: set[str] = set()
    rendered: dict[str, dict[str, str]] = {}
    for record in payload["records"]:
        if not record["has_image"]:
            continue
        source = COLLECTION_SOURCE / record["image"]
        target = COLLECTION_OUTPUT / f"{record['slug']}.webp"
        manifest_key = target.relative_to(PROJECT_ROOT).as_posix()
        expected.add(target.name)
        rendered[manifest_key] = convert(
            source,
            target,
            MAX_COLLECTION_EDGE,
            previous.get(manifest_key),
        )

    COLLECTION_OUTPUT.mkdir(parents=True, exist_ok=True)
    for target in COLLECTION_OUTPUT.glob("*.webp"):
        if target.name not in expected:
            target.unlink()
    return rendered


def render_narrative(
    previous: dict[str, dict[str, str]],
) -> dict[str, dict[str, str]]:
    if not NARRATIVE_SOURCE.exists():
        return {}
    expected: set[str] = set()
    rendered: dict[str, dict[str, str]] = {}
    for source in sorted(NARRATIVE_SOURCE.iterdir()):
        if source.suffix.casefold() not in {".jpg", ".jpeg", ".png", ".gif"}:
            continue
        target_name = f"{source.stem}.webp"
        if source.name.casefold() == "album2.jpg":
            target_name = "album2-photo.webp"
        target = NARRATIVE_OUTPUT / target_name
        manifest_key = target.relative_to(PROJECT_ROOT).as_posix()
        expected.add(target.name)
        rendered[manifest_key] = convert(
            source,
            target,
            MAX_NARRATIVE_EDGE,
            previous.get(manifest_key),
        )

    NARRATIVE_OUTPUT.mkdir(parents=True, exist_ok=True)
    for target in NARRATIVE_OUTPUT.glob("*.webp"):
        if target.name not in expected:
            target.unlink()
    return rendered


def load_manifest() -> dict[str, dict[str, str]]:
    if not MANIFEST_PATH.is_file():
        return {}
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported image derivative manifest")
    entries = payload.get("derivatives")
    if not isinstance(entries, dict):
        raise ValueError("Invalid image derivative manifest")
    return entries


def write_manifest(entries: dict[str, dict[str, str]]) -> None:
    payload = {
        "schema_version": 1,
        "webp_version": WEBP_VERSION_PATH.read_text(encoding="utf-8").strip(),
        "derivative_count": len(entries),
        "derivatives": dict(sorted(entries.items())),
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if not MANIFEST_PATH.is_file() or MANIFEST_PATH.read_text(encoding="utf-8") != text:
        MANIFEST_PATH.write_text(text, encoding="utf-8")


def main() -> None:
    previous = load_manifest()
    rendered = render_collection(previous)
    rendered.update(render_narrative(previous))
    write_manifest(rendered)
    print("Web-ready collection and narrative images are current")


if __name__ == "__main__":
    main()
