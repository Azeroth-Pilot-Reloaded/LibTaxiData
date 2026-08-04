#!/usr/bin/env python3
"""Tests for automatic semantic release planning."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.release_version import (  # noqa: E402
    SemanticVersion,
    is_build_with_node_update,
    plan_release,
    version_ids,
)


def taxi_nodes(build: str, node_id: int = 1) -> str:
    return f'''-- Source: test (build {build})
local data = {{
    build = "{build}",
    nodes = {{ [{node_id}] = true }},
}}
'''


class ReleaseVersionTests(unittest.TestCase):
    def test_initial_release_is_v1(self) -> None:
        plan = plan_release(None)
        self.assertEqual("major", plan.level)
        self.assertEqual("v1.0.0", plan.version.tag())

    def test_api_change_increments_major(self) -> None:
        plan = plan_release("v2.7.3", api_changed=True)
        self.assertEqual("major", plan.level)
        self.assertEqual("v3.0.0", plan.version.tag())

    def test_new_wow_version_increments_major(self) -> None:
        plan = plan_release("v2.7.3", added_versions=("midnight",))
        self.assertEqual("major", plan.level)
        self.assertEqual("v3.0.0", plan.version.tag())

    def test_node_update_increments_minor_and_resets_hotfix(self) -> None:
        plan = plan_release("v2.7.3", node_updates=("retail",))
        self.assertEqual("minor", plan.level)
        self.assertEqual("v2.8.0", plan.version.tag())

    def test_development_change_does_not_create_automatic_hotfix(self) -> None:
        plan = plan_release("v2.7.3")
        self.assertFalse(plan.changed)
        self.assertIsNone(plan.level)
        self.assertIsNone(plan.version)

    def test_minor_requires_both_build_and_node_changes(self) -> None:
        original = taxi_nodes("12.0.1.100", 1)
        build_only = taxi_nodes("12.0.1.101", 1)
        nodes_only = taxi_nodes("12.0.1.100", 2)
        build_and_nodes = taxi_nodes("12.0.1.101", 2)
        self.assertFalse(is_build_with_node_update(original, build_only))
        self.assertFalse(is_build_with_node_update(original, nodes_only))
        self.assertTrue(is_build_with_node_update(original, build_and_nodes))

    def test_added_version_ids_are_detectable(self) -> None:
        previous = json.dumps([{"id": "retail"}])
        current = json.dumps([{"id": "retail"}, {"id": "mists"}])
        self.assertEqual({"mists"}, version_ids(current) - version_ids(previous))

    def test_semantic_tags_are_strict(self) -> None:
        self.assertEqual(SemanticVersion(1, 2, 3), SemanticVersion.from_tag("v1.2.3"))
        with self.assertRaises(ValueError):
            SemanticVersion.from_tag("v1.2")


if __name__ == "__main__":
    unittest.main()
