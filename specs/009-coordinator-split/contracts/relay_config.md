<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Contract: relay_config.py Module Interface

**Module**: `custom_components/local_akuvox/relay_config.py` **Type**: Internal
module API (not user-facing) **Consumers**: `coordinator.py`, white-box tests

## Public Surface

### RelayConfig

```python
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
```

**Contract**:

- Frozen dataclass; field assignment after construction raises `AttributeError`.
- Defaults match the current coordinator implementation.
- No Home Assistant runtime dependency.
- Used by `AkuvoxCoordinatorData.relay_configs` and lock entities exactly as
  before.

______________________________________________________________________

### _parse_config_int

```python
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
```

**Contract**:

- `None` returns `default`.
- Valid integer strings return the parsed value.
- Non-numeric non-empty values log a warning and return `default`.
- Empty string returns `default` without the invalid-integer warning.
- `min_val`, `max_val`, and `allowed` validation each preserve current fallback
  and warning behavior.

______________________________________________________________________

### _build_relay_config

```python
def _build_relay_config(config: Any, letter: str) -> RelayConfig:
    """Build a RelayConfig from a DeviceConfig for a given relay letter.

    Args:
        config: DeviceConfig instance with dict-like access.
        letter: Relay letter suffix (e.g., "A", "B").

    Returns:
        RelayConfig with parsed values or defaults for missing keys.

    """
```

**Contract**:

- Reads relay name from `CONFIG_KEY_RELAY_NAME + letter`, defaulting to `""`.
- Reads hold delay from `CONFIG_KEY_RELAY_HOLD_DELAY + letter`, defaulting to
  `str(DEFAULT_HOLD_DELAY_SECONDS)` and requiring `min_val=1`.
- Reads relay type from
  `CONFIG_KEY_RELAY_PREFIX + letter + CONFIG_KEY_RELAY_TYPE_SUFFIX`, defaulting
  to `str(DEFAULT_RELAY_TYPE)` and requiring `allowed={0, 1}`.
- Reads relay mode from
  `CONFIG_KEY_RELAY_PREFIX + letter + CONFIG_KEY_RELAY_MODE_SUFFIX`, defaulting
  to `str(DEFAULT_RELAY_MODE)` and requiring `allowed={0, 1}`.
- Returns a `RelayConfig` with parsed/defaulted values.

## Dependencies

```python
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
```

`RELAY_KEY_RE` remains a `coordinator.py` dependency for discovering relay
letters and is not part of this module contract.

## Compatibility

`RelayConfig`, `_parse_config_int`, and `_build_relay_config` are internal
integration helpers. Existing tests that import these symbols from `coordinator.py` should move to
`relay_config.py`; `coordinator.py` should not keep compatibility aliases solely
for private helper imports.

<!-- markdownlint-enable MD013 -->
