#!/usr/bin/env python3
"""Promote the validated staging build into tracked public output."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGING = PROJECT_ROOT / ".work" / "build"
PUBLIC = PROJECT_ROOT / "public"
BACKUP = PROJECT_ROOT / ".work" / "public.previous"
NEXT = PROJECT_ROOT / ".work" / "public.next"


def ensure_clean_public() -> None:
    repository = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if repository.returncode != 0:
        return
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", "public"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    if result.stdout.strip():
        raise SystemExit(
            "public/ has uncommitted changes; review or commit them before promotion"
        )


def validate_target() -> None:
    if not (PROJECT_ROOT / "zola.toml").is_file():
        raise SystemExit("Run promotion from a valid AMB site repository")
    if PUBLIC.is_symlink():
        raise SystemExit("Refusing to replace a symbolic-link public directory")
    for sentinel in (
        STAGING / "index.html",
        STAGING / "search" / "index.html",
        STAGING / "collection" / "ab-1" / "index.html",
    ):
        if not sentinel.is_file():
            raise SystemExit(f"Staging build is incomplete: {sentinel}")


def main() -> None:
    validate_target()
    ensure_clean_public()
    subprocess.run(
        ["python3", "scripts/validate.py", "build", ".work/build"],
        cwd=PROJECT_ROOT,
        check=True,
    )
    subprocess.run(
        ["python3", "scripts/build_manifest.py", "verify", ".work/build"],
        cwd=PROJECT_ROOT,
        check=True,
    )

    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    if BACKUP.exists():
        shutil.rmtree(BACKUP)
    if NEXT.exists():
        shutil.rmtree(NEXT)
    shutil.copytree(STAGING, NEXT)

    try:
        if PUBLIC.exists():
            PUBLIC.rename(BACKUP)
        NEXT.rename(PUBLIC)
    except Exception:
        if BACKUP.exists() and not PUBLIC.exists():
            BACKUP.rename(PUBLIC)
        raise
    print("Promoted the validated staging build into public/")


if __name__ == "__main__":
    main()
