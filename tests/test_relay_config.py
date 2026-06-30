# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Tests for Akuvox relay config helpers."""

from __future__ import annotations

from custom_components.local_akuvox.relay_config import _parse_config_int


def test_parse_config_int_uses_default_for_missing_value() -> None:
    """Test missing device config values fall back to defaults."""
    assert _parse_config_int(None, default=5, key="HoldDelayA") == 5
