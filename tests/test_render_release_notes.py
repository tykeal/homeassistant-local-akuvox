# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0
"""Tests for rendering Reno snippets as Markdown release notes."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_renderer() -> Any:
    """Import the renderer by path because ``scripts`` is not a package."""
    path = REPO_ROOT / "scripts" / "render_release_notes.py"
    spec = importlib.util.spec_from_file_location("render_release_notes", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rrn = _load_renderer()

SECTIONS = [
    ("upgrade", "Upgrade Notes", 1),
    ("features", "New Features", 1),
    ("fixes", "Bug Fixes", 1),
]
SECTION_NAMES = [name for name, _, _ in SECTIONS]


class FakeLoader:
    """In-memory stand-in for ``reno.loader.Loader``."""

    def __init__(self, notes: dict[str, dict[str, dict[str, Any]]]) -> None:
        """Store ``{version: {filename: parsed content}}``."""
        self._notes = notes

    def __enter__(self) -> FakeLoader:
        """Return the loader from a context manager."""
        return self

    def __exit__(self, *_args: object) -> None:
        """Support the Reno loader context-manager interface."""

    @property
    def versions(self) -> list[str]:
        """Return versions newest first, as Reno does."""
        return list(self._notes)

    def __getitem__(self, version: str) -> list[tuple[str, str | None]]:
        """Return the note files belonging to one version."""
        return [(name, "sha") for name in self._notes[version]]

    def parse_note_file(self, filename: str, sha: str | None) -> dict[str, Any]:
        """Return parsed content for a note file."""
        for files in self._notes.values():
            if filename in files:
                return files[filename]
        raise KeyError(filename)


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        (None, ["*working-copy*", "v3.9.0-2"]),
        ("v3.9.0", ["v3.9.0"]),
        ("v3.7.0", []),
    ],
)
def test_select_versions(version: str | None, expected: list[str]) -> None:
    """Unreleased notes stop at the newest tag; a named tag stands alone."""
    versions = ["*working-copy*", "v3.9.0-2", "v3.9.0", "v3.8.0"]
    tags = {"v3.9.0", "v3.8.0", "v3.7.0"}

    assert rrn.select_versions(versions, tags, version) == expected


def test_select_versions_head_on_tag_has_no_unreleased_notes() -> None:
    """Right after a release, there are no unreleased notes."""
    assert rrn.select_versions(["v3.9.0", "v3.8.0"], {"v3.9.0", "v3.8.0"}, None) == []


def test_load_release_notes_scans_explicit_tag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Explicit versions scan that tag without collapsing prereleases."""
    from reno import config as reno_config
    from reno import loader as reno_loader

    scan_options: dict[str, Any] = {}

    class FakeConfig:
        sections = [
            SimpleNamespace(name="upgrade", title="Upgrade Notes", section_level=1)
        ]
        prelude_section_name = "prelude"

        def __init__(self, *_args: object) -> None:
            """Set up Reno config substitute."""

        def override(self, **options: Any) -> None:
            """Record scanner configuration."""
            scan_options.update(options)

    monkeypatch.setattr(reno_config, "Config", FakeConfig)
    monkeypatch.setattr(
        reno_loader,
        "Loader",
        lambda _conf: FakeLoader(
            {"v3.9.0rc1": {"note.yaml": {"upgrade": ["Pre-release change."]}}}
        ),
    )
    monkeypatch.setattr(rrn, "git_tags", lambda _root: {"v3.9.0rc1"})

    assert rrn.load_release_notes(tmp_path, "v3.9.0rc1") == (
        "### Upgrade Notes\n\n- Pre-release change."
    )
    assert scan_options == {
        "branch": "v3.9.0rc1",
        "collapse_pre_releases": False,
    }


def test_render_orders_sections_and_formats_multiline_items() -> None:
    """Sections follow config order and continuation lines stay in bullets."""
    loader = FakeLoader(
        {
            "v3.9.0-1": {
                "a.yaml": {
                    "fixes": ["Fixed a thing.\n"],
                    "upgrade": [
                        "First line\nsecond line.\n\n```yaml\nkey: value\n```\n"
                    ],
                },
                "b.yaml": {
                    "prelude": "A summary\nparagraph.\n",
                    "fixes": "A single string item.\n",
                },
            }
        }
    )

    notes = rrn.collect_notes(loader, ["v3.9.0-1"], SECTION_NAMES, "prelude")

    assert rrn.render_markdown(notes, SECTIONS) == (
        "A summary\nparagraph.\n\n"
        "### Upgrade Notes\n\n"
        "- First line\n  second line.\n\n  ```yaml\n  key: value\n  ```\n\n"
        "### Bug Fixes\n\n"
        "- Fixed a thing.\n- A single string item."
    )


@pytest.mark.parametrize("section_content", [[], ["  \n"]])
def test_collect_notes_rejects_empty_sections(
    section_content: list[str],
) -> None:
    """A note with no nonblank configured section is rejected."""
    loader = FakeLoader(
        {"v3.9.0-1": {"a.yaml": {"fixes": section_content, "upgrade": []}}}
    )

    with pytest.raises(ValueError, match=r"a\.yaml: release note must contain"):
        rrn.collect_notes(loader, ["v3.9.0-1"], SECTION_NAMES, "prelude")


def test_render_without_notes_is_empty() -> None:
    """An empty collection of notes produces no output."""
    notes = rrn.RenderedNotes()

    assert rrn.render_markdown(notes, SECTIONS) == ""


def test_collect_notes_rejects_invalid_section_types() -> None:
    """Malformed section values fail with the note filename and section."""
    loader = FakeLoader({"*working-copy*": {"bad.yaml": {"fixes": True}}})

    with pytest.raises(ValueError, match=r"bad\.yaml: section 'fixes'"):
        rrn.collect_notes(loader, ["*working-copy*"], SECTION_NAMES, "prelude")


def test_drafter_config_unchanged_without_notes() -> None:
    """With no notes, use the committed config unchanged."""
    base = "---\nheader: |+\n  badge\n\ntemplate: |\n  $CHANGES\n"

    assert rrn.build_drafter_config(base, "") == base


def test_drafter_config_places_notes_between_badge_and_changes() -> None:
    """Notes follow the badge in the header; all other config is preserved."""
    base_text = (REPO_ROOT / ".github" / "release-drafter.yml").read_text()
    base = yaml.safe_load(base_text)

    generated = yaml.safe_load(
        rrn.build_drafter_config(base_text, "### Bug Fixes\n\n- Fixed.")
    )

    body = generated["header"] + generated["template"]
    assert body.startswith(base["header"] + "### Bug Fixes\n\n- Fixed.\n\n$CHANGES")
    assert {key: value for key, value in generated.items() if key != "header"} == {
        key: value for key, value in base.items() if key != "header"
    }


def test_main_rejects_unknown_version(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An explicit version must be an existing tag."""
    monkeypatch.setattr(rrn, "git_tags", lambda _root: {"v3.9.0"})

    assert rrn.main(["--version", "v9.9.9"]) == 2
    assert "not a git tag" in capsys.readouterr().err


def test_main_writes_drafter_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The CLI merges rendered notes into the supplied config."""
    monkeypatch.setattr(rrn, "load_release_notes", lambda _root, _version: "- Note.")
    base = tmp_path / "base.yml"
    base.write_text("header: |\n  badge\ntemplate: $CHANGES\n")
    output = tmp_path / "out.yml"

    assert (
        rrn.main(["--release-drafter-config", str(base), "--output", str(output)]) == 0
    )
    assert yaml.safe_load(output.read_text())["header"] == "badge\n\n- Note.\n\n"
