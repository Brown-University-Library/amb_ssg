#!/usr/bin/env python3
"""Bind a staged site build to the exact source state that produced it."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / ".work" / "build-manifest.json"
EXCLUDED_SOURCE_PARTS = {
    ".git",
    ".work",
    "public",
    "private-input",
    "__pycache__",
}
EXCLUDED_SOURCE_NAMES = {".DS_Store"}


def tree_digest(root: Path, excluded_parts: set[str] | None = None) -> str:
    digest = hashlib.sha256()
    excluded_parts = excluded_parts or set()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in excluded_parts for part in relative.parts):
            continue
        if path.name in EXCLUDED_SOURCE_NAMES or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError(f"Symbolic links are not allowed in build inputs: {relative}")
        if not path.is_file():
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def current_manifest(build_dir: Path) -> dict[str, object]:
    version = (PROJECT_ROOT / ".zola-version").read_text(encoding="utf-8").strip()
    return {
        "schema_version": 1,
        "zola_version": version,
        "source_sha256": tree_digest(PROJECT_ROOT, EXCLUDED_SOURCE_PARTS),
        "build_sha256": tree_digest(build_dir),
    }


def write_manifest(build_dir: Path) -> None:
    if not (build_dir / "index.html").is_file():
        raise SystemExit("Cannot record an incomplete staged build")
    payload = current_manifest(build_dir)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("Recorded the staged build's source and output digests")


def verify_manifest(build_dir: Path) -> None:
    if not MANIFEST_PATH.is_file():
        raise SystemExit("The staged build has no source-state manifest; run make build")
    expected = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    actual = current_manifest(build_dir)
    if expected != actual:
        raise SystemExit("The staged build is stale or changed; run make build again")
    print("The staged build matches the current source")


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in {"write", "verify"}:
        raise SystemExit("Usage: build_manifest.py write|verify [build-directory]")
    build_dir = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else PROJECT_ROOT / ".work" / "build"
    ).resolve()
    if sys.argv[1] == "write":
        write_manifest(build_dir)
    else:
        verify_manifest(build_dir)


if __name__ == "__main__":
    main()
