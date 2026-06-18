# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Relay configuration parsing helpers for the Akuvox integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .const import (
    CONFIG_KEY_RELAY_HOLD_DELAY,
    CONFIG_KEY_RELAY_MODE_SUFFIX,
    CONFIG_KEY_RELAY_NAME,
    CONFIG_KEY_RELAY_PREFIX,
    CONFIG_KEY_RELAY_TYPE_SUFFIX,
    DEFAULT_HOLD_DELAY_SECONDS,
    DEFAULT_RELAY_MODE,
    DEFAULT_RELAY_TYPE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RelayConfig:
    """Per-relay configuration extracted from device config.

    Attributes:
        name: Display name from config (empty triggers fallback).
        hold_delay: Unlock duration in seconds.
        relay_type: 0=NO (normally-open), 1=NC (normally-closed).
        relay_mode: 0=Auto-close, 1=Manual.

    """

    name: str = ""
    hold_delay: int = DEFAULT_HOLD_DELAY_SECONDS
    relay_type: int = DEFAULT_RELAY_TYPE
    relay_mode: int = DEFAULT_RELAY_MODE


def _parse_config_int(
    value: str | None,
    *,
    default: int,
    min_val: int | None = None,
    max_val: int | None = None,
    allowed: set[int] | None = None,
    key: str = "",
) -> int:
    """Parse a string config value to an integer with validation.

    Args:
        value: The string value to parse (None returns default).
        default: Default to return on parse/validation failure.
        min_val: Minimum acceptable value (inclusive).
        max_val: Maximum acceptable value (inclusive).
        allowed: Set of explicitly allowed values.
        key: Config key name for log messages.

    Returns:
        Parsed integer or default on failure.

    """
    if value is None:
        return default
    try:
        result = int(value)
    except (ValueError, TypeError):
        if value != "":
            _LOGGER.warning(
                "Invalid integer value '%s' for config key '%s', using default %d",
                value,
                key,
                default,
            )
        return default

    if min_val is not None and result < min_val:
        _LOGGER.warning(
            "Value %d for '%s' below minimum %d, using default %d",
            result,
            key,
            min_val,
            default,
        )
        return default

    if max_val is not None and result > max_val:
        _LOGGER.warning(
            "Value %d for '%s' above maximum %d, using default %d",
            result,
            key,
            max_val,
            default,
        )
        return default

    if allowed is not None and result not in allowed:
        _LOGGER.warning(
            "Value %d for '%s' not in allowed set %s, using default %d",
            result,
            key,
            allowed,
            default,
        )
        return default

    return result


def _build_relay_config(config: Any, letter: str) -> RelayConfig:
    """Build a RelayConfig from a DeviceConfig for a given relay letter.

    Args:
        config: DeviceConfig instance with dict-like access.
        letter: Relay letter suffix (e.g., "A", "B").

    Returns:
        RelayConfig with parsed values or defaults for missing keys.

    """
    name = config.get(f"{CONFIG_KEY_RELAY_NAME}{letter}", "")
    hold_delay = _parse_config_int(
        config.get(
            f"{CONFIG_KEY_RELAY_HOLD_DELAY}{letter}",
            str(DEFAULT_HOLD_DELAY_SECONDS),
        ),
        default=DEFAULT_HOLD_DELAY_SECONDS,
        min_val=1,
        key=f"HoldDelay{letter}",
    )
    relay_type = _parse_config_int(
        config.get(
            f"{CONFIG_KEY_RELAY_PREFIX}{letter}{CONFIG_KEY_RELAY_TYPE_SUFFIX}",
            str(DEFAULT_RELAY_TYPE),
        ),
        default=DEFAULT_RELAY_TYPE,
        allowed={0, 1},
        key=f"Relay{letter}Type",
    )
    relay_mode = _parse_config_int(
        config.get(
            f"{CONFIG_KEY_RELAY_PREFIX}{letter}{CONFIG_KEY_RELAY_MODE_SUFFIX}",
            str(DEFAULT_RELAY_MODE),
        ),
        default=DEFAULT_RELAY_MODE,
        allowed={0, 1},
        key=f"Relay{letter}Mode",
    )
    return RelayConfig(
        name=name,
        hold_delay=hold_delay,
        relay_type=relay_type,
        relay_mode=relay_mode,
    )
