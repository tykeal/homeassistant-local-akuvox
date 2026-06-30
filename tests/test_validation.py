# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Tests for Akuvox validation helpers."""

from __future__ import annotations

from custom_components.local_akuvox.validation import csv_to_list


def test_csv_to_list_coerces_non_string_list_items() -> None:
    """Test list inputs keep strings split and coerce non-strings."""
    assert csv_to_list(["one, two", 3]) == ["one", "two", "3"]


def test_csv_to_list_delegates_other_iterables() -> None:
    """Test non-string, non-list values use Home Assistant coercion."""
    assert csv_to_list(None) == []
