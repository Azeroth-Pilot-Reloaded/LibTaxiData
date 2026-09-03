#!/usr/bin/env python3
"""Tests for the Discord release notification formatter."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "post_discord.py"
SPEC = importlib.util.spec_from_file_location("post_discord", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to import {SCRIPT}")
post_discord = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(post_discord)


class ReleaseFromJsonTests(unittest.TestCase):
    def test_reads_gh_release_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "release.json"
            path.write_text(
                json.dumps(
                    {
                        "tagName": "v2.4.0",
                        "body": "# LibTaxiData\n\nChanges",
                        "url": "https://example.test/v2.4.0",
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                post_discord.release_from_json(path),
                (
                    "v2.4.0",
                    "# LibTaxiData\n\nChanges",
                    "https://example.test/v2.4.0",
                ),
            )

    def test_reads_release_event_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "event.json"
            path.write_text(
                json.dumps(
                    {
                        "release": {
                            "tag_name": "v3.0.0-beta",
                            "body": "Beta changes",
                            "html_url": "https://example.test/v3.0.0-beta",
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                post_discord.release_from_json(path),
                (
                    "v3.0.0-beta",
                    "Beta changes",
                    "https://example.test/v3.0.0-beta",
                ),
            )


class MessageTests(unittest.TestCase):
    def test_formats_release_and_removes_only_redundant_title(self) -> None:
        message = post_discord.format_release(
            "v2.4.0",
            "# LibTaxiData\n\n## v2.4.0\n\n- Updated data",
            "https://example.test/release",
        )

        self.assertEqual(
            message,
            "## Patch Note - LibTaxiData v2.4.0\n\n"
            "## v2.4.0\n\n- Updated data\n\n"
            "[View release on GitHub](https://example.test/release)",
        )

    def test_keeps_a_meaningful_first_heading(self) -> None:
        message = post_discord.format_release("v3.0.0", "# Breaking changes")

        self.assertIn("# Breaking changes", message)

    def test_splits_long_messages_within_discord_limit(self) -> None:
        message = "A" * 1500 + "\n" + "B" * 1500

        chunks = post_discord.split_message(message)

        self.assertEqual("".join(chunks), "A" * 1500 + "B" * 1500)
        self.assertTrue(all(len(chunk) <= 2000 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
