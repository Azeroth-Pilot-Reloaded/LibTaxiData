#!/usr/bin/env python3
"""Post the contents of a GitHub release to a Discord webhook."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DISCORD_MESSAGE_LIMIT = 2000
PROJECT_NAME = "LibTaxiData"


def release_from_json(path: Path) -> tuple[str, str, str]:
    """Read either a GitHub API release or a release event payload."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("The release JSON must be an object")

    release: Any = document.get("release", document)
    if not isinstance(release, dict):
        raise ValueError("The release payload does not contain a release object")

    tag = release.get("tag_name", release.get("tagName"))
    body = release.get("body") or ""
    url = release.get("html_url", release.get("url")) or ""
    if not isinstance(tag, str) or not tag.strip():
        raise ValueError("The release payload does not contain a tag name")
    if not isinstance(body, str) or not isinstance(url, str):
        raise ValueError("The release body and URL must be strings")
    return tag.strip(), body, url.strip()


def strip_redundant_project_heading(body: str) -> str:
    """Remove the generated '# LibTaxiData' heading while keeping all notes."""
    lines = body.strip().splitlines()
    if lines and lines[0].lstrip("#").strip().casefold() == PROJECT_NAME.casefold():
        lines.pop(0)
        while lines and not lines[0].strip():
            lines.pop(0)
    return "\n".join(lines).strip()


def format_release(tag: str, body: str, url: str = "") -> str:
    sections = [f"## Patch Note - {PROJECT_NAME} {tag}"]
    notes = strip_redundant_project_heading(body)
    if notes:
        sections.append(notes)
    if url:
        sections.append(f"[View release on GitHub]({url})")
    return "\n\n".join(sections)


def split_message(message: str, limit: int = DISCORD_MESSAGE_LIMIT) -> list[str]:
    """Split long release notes at natural boundaries accepted by Discord."""
    if limit <= 0:
        raise ValueError("The Discord message limit must be positive")

    chunks: list[str] = []
    remaining = message.strip()
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit + 1)
        if split_at < limit // 2:
            split_at = remaining.rfind(" ", 0, limit + 1)
        if split_at <= 0:
            split_at = limit

        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()

    if remaining:
        chunks.append(remaining)
    return chunks


def post_message(webhook_url: str, message: str) -> None:
    payload = json.dumps(
        {
            "content": message,
            "flags": 4,
            "allowed_mentions": {"parse": []},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "LibTaxiData-Release-Notifier/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(
            f"Discord returned HTTP {error.code}: {detail or error.reason}"
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Unable to reach Discord: {error.reason}") from error

    if status not in (200, 204):
        raise RuntimeError(f"Discord returned unexpected HTTP status {status}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Post GitHub release notes to Discord"
    )
    parser.add_argument(
        "--release-json",
        type=Path,
        help="GitHub release JSON returned by gh or received as an event payload",
    )
    parser.add_argument("--tag", help="Release tag (or set RELEASE_TAG)")
    parser.add_argument("--body", help="Release body (or set RELEASE_BODY)")
    parser.add_argument("--url", help="Release URL (or set RELEASE_URL)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the Discord payload without sending it",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.release_json:
            tag, body, url = release_from_json(args.release_json)
        else:
            tag = args.tag or os.getenv("RELEASE_TAG", "")
            body = args.body if args.body is not None else os.getenv("RELEASE_BODY", "")
            url = args.url or os.getenv("RELEASE_URL", "")
            if not tag.strip():
                raise ValueError("RELEASE_TAG or --tag is required")

        messages = split_message(format_release(tag, body, url))
        if args.dry_run:
            print("\n\n--- Discord message boundary ---\n\n".join(messages))
            return 0

        webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
        if not webhook_url:
            raise ValueError("The DISCORD_WEBHOOK_URL repository secret is not set")

        for message in messages:
            post_message(webhook_url, message)
        print(f"Discord notification sent for {tag} ({len(messages)} message(s)).")
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
