#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0
"""Render Reno release notes as Markdown for the GitHub release body.

Reno's report command emits reStructuredText, so this script uses its
Python API to find notes for a release and render them as Markdown.

By default it renders unreleased notes: every note added since the most
recent release tag, plus staged or modified notes in the working copy.
``--version`` renders notes for an existing release tag instead.

With ``--release-drafter-config`` it writes a copy of that configuration
with the rendered notes appended to ``header``.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import textwrap
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import yaml

RELNOTES_DIR = "releasenotes"


class NoteLoader(Protocol):
    """The subset of ``reno.loader.Loader`` used by this script."""

    @property
    def versions(self) -> list[str]:
        """Return versions with notes, newest first."""

    def __getitem__(self, version: str) -> list[tuple[str, str | None]]:
        """Return ``(filename, sha)`` pairs for a version's notes."""

    def parse_note_file(self, filename: str, sha: str | None) -> dict[str, Any]:
        """Return parsed sections from one note file."""


@dataclass
class RenderedNotes:
    """Prelude paragraphs and section items gathered from note files."""

    prelude: list[str] = field(default_factory=list)
    sections: dict[str, list[str]] = field(default_factory=dict)


def select_versions(
    versions: Sequence[str], tags: set[str], version: str | None
) -> list[str]:
    """Select Reno versions whose notes belong in the output.

    Without ``version``, select leading entries that are not release tags:
    the working copy and Reno's ``<latest-tag>-<N>`` development version.
    With ``version``, select only that version, if it has notes.
    """
    if version is not None:
        return [version] if version in versions else []
    selected = []
    for candidate in versions:
        if candidate in tags:
            break
        selected.append(candidate)
    return selected


def collect_notes(
    loader: NoteLoader,
    versions: Sequence[str],
    section_names: Sequence[str],
    prelude_name: str,
) -> RenderedNotes:
    """Gather the prelude and section items from selected versions."""
    notes = RenderedNotes()
    for version in versions:
        for filename, sha in loader[version]:
            content = loader.parse_note_file(filename, sha)
            prelude = content.get(prelude_name)
            if prelude is not None and not isinstance(prelude, str):
                raise ValueError(
                    f"{filename}: section {prelude_name!r} must be a string"
                )
            if isinstance(prelude, str) and prelude.strip():
                notes.prelude.append(prelude)
            for name in section_names:
                items = content.get(name)
                if items is None:
                    continue
                if isinstance(items, str):
                    items = [items]
                elif not isinstance(items, list):
                    raise ValueError(
                        f"{filename}: section {name!r} must be a list or string"
                    )
                if any(not isinstance(item, str) for item in items):
                    raise ValueError(
                        f"{filename}: section {name!r} items must be strings"
                    )
                notes.sections.setdefault(name, []).extend(
                    item for item in items if item.strip()
                )
    return notes


def format_item(text: str) -> str:
    """Render a note item as a Markdown bullet.

    Continuation lines are indented by two spaces so paragraphs, nested
    lists, and fenced code blocks remain within the bullet.
    """
    lines = textwrap.dedent(text).strip().splitlines()
    rest = [f"  {line}" if line.strip() else "" for line in lines[1:]]
    return "\n".join([f"- {lines[0]}", *rest])


def render_markdown(
    notes: RenderedNotes, sections: Sequence[tuple[str, str, int]]
) -> str:
    """Render notes as Markdown, or return an empty string.

    ``sections`` contains ``(name, title, level)`` in output order;
    level 1 sections become ``###`` headings.
    """
    blocks = [textwrap.dedent(text).strip() for text in notes.prelude]
    for name, title, level in sections:
        items = notes.sections.get(name)
        if not items:
            continue
        blocks.append(f"{'#' * (2 + level)} {title}")
        blocks.append("\n".join(format_item(item) for item in items))
    return "\n\n".join(blocks)


def _literal_str(dumper: yaml.SafeDumper, data: str) -> yaml.ScalarNode:
    """Dump multiline strings as readable YAML literal blocks."""
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


class _ConfigDumper(yaml.SafeDumper):
    """YAML dumper that keeps multiline strings readable."""


_ConfigDumper.add_representer(str, _literal_str)


def build_drafter_config(base_config: str, notes_markdown: str) -> str:
    """Append notes to the Release Drafter config's ``header`` key."""
    if not notes_markdown:
        return base_config
    config = yaml.safe_load(base_config)
    header = config.get("header") or ""
    if header and not header.endswith("\n\n"):
        header = header.rstrip("\n") + "\n\n"
    config["header"] = f"{header}{notes_markdown.rstrip()}\n\n"
    dumped: str = yaml.dump(
        config,
        Dumper=_ConfigDumper,
        sort_keys=False,
        allow_unicode=True,
        width=1_000_000,
    )
    return (
        "---\n# Generated by scripts/render_release_notes.py; do not edit.\n" + dumped
    )


def git_tags(repo_root: Path) -> set[str]:
    """Return all tag names in the repository."""
    git_path = shutil.which("git")
    if git_path is None:
        raise FileNotFoundError("git executable not found")
    # Executable is resolved from PATH; all arguments are fixed.
    result = subprocess.run(  # noqa: S603
        [git_path, "tag", "--list"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return set(result.stdout.split())


def load_release_notes(repo_root: Path, version: str | None) -> str:
    """Scan repository notes with Reno and render them as Markdown."""
    from reno import config as reno_config
    from reno import loader as reno_loader

    conf = reno_config.Config(str(repo_root), RELNOTES_DIR)
    sections = [(s.name, s.title, s.section_level) for s in conf.sections]
    tags = git_tags(repo_root)
    with reno_loader.Loader(conf) as loader:
        versions = select_versions(loader.versions, tags, version)
        notes = collect_notes(
            loader,
            versions,
            [section[0] for section in sections],
            conf.prelude_section_name,
        )
    return render_markdown(notes, sections)


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="repository to scan (default: current directory)",
    )
    parser.add_argument(
        "--version",
        help="render notes of this release tag instead of unreleased notes",
    )
    parser.add_argument(
        "--release-drafter-config",
        type=Path,
        help="write this Release Drafter config with notes in its header",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="file to write instead of standard output",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the renderer and return its process exit status."""
    args = parse_args(argv)
    if args.version is not None and args.version not in git_tags(args.repo_root):
        sys.stderr.write(f"error: {args.version!r} is not a git tag\n")
        return 2
    try:
        output = load_release_notes(args.repo_root, args.version)
    except ValueError as err:
        sys.stderr.write(f"error: {err}\n")
        return 1
    if args.release_drafter_config is not None:
        output = build_drafter_config(
            args.release_drafter_config.read_text(encoding="utf-8"), output
        )
    elif output:
        output += "\n"
    if args.output is not None:
        args.output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
