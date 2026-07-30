# /// script
# requires-python = ">=3.12,<3.13"
# ///

"""
Checks whether the active Zola executable matches the project's pinned version.

Usage:
    uv run ./scripts/check_zola.py
    uv run ./scripts/check_zola.py /path/to/zola

This check is optional: Zola can serve or build the site without running this
script first. Run it before checking or rebuilding the site when Zola has been
installed or updated, when working in a different shell or environment, or when
investigating unexpected generated-output changes. The script does not modify
files; it reports an error if Zola cannot be run or its version differs from
the version recorded in `.zola-version`.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED = (PROJECT_ROOT / ".zola-version").read_text(encoding="utf-8").strip()


def main() -> None:
    executable = sys.argv[1] if len(sys.argv) > 1 else "zola"
    try:
        result = subprocess.run(
            [executable, "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"Could not run the configured Zola executable: {error}")

    match = re.search(r"\bzola\s+(\d+\.\d+\.\d+)\b", result.stdout)
    found = match.group(1) if match else "unknown"
    if found != EXPECTED:
        raise SystemExit(f"Zola {EXPECTED} is required; configured executable is {found}")
    print(f"Zola {found} is ready")


if __name__ == "__main__":
    main()
