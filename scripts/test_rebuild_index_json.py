# /// script
# requires-python = ">=3.12,<3.13"
# ///

"""
Tests rebuilding the compact browser-search JSON from collection Markdown.
"""

import tempfile
import unittest
from pathlib import Path

import rebuild_index_json


class RebuildIndexJsonTests(unittest.TestCase):
    def test_current_markdown_recreates_tracked_json(self) -> None:
        """
        Checks that the maintained collection reproduces the tracked search data.
        """
        records = rebuild_index_json.load_records(rebuild_index_json.COLLECTION_DIR)
        actual = rebuild_index_json.serialize_records(records)
        expected = rebuild_index_json.OUTPUT_PATH.read_text(encoding="utf-8")

        self.assertEqual(actual, expected)

    def test_missing_search_field_is_rejected(self) -> None:
        """
        Checks that an incomplete collection page cannot produce a search record.
        """
        with tempfile.TemporaryDirectory() as temporary_directory:
            page_path = Path(temporary_directory) / "ab-1" / "index.md"
            page_path.parent.mkdir()
            page_path.write_text(
                """+++
title = "Example"

[extra]
item_id = "AB 1"
artist = "Example Artist"
nationality = "Example"
number = 1
has_image = false
image = ""
+++
""",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "artist_dates"):
                rebuild_index_json.build_record(page_path)


if __name__ == "__main__":
    unittest.main()
