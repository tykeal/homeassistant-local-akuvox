<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Data Model: Coordinator Relay Config Split

**Feature**: 009-coordinator-split **Date**: 2026-06-18

## Entity: RelayConfig

`RelayConfig` is a frozen dataclass representing the parsed configuration for one
Akuvox relay.

| Field | Type | Default | Description |
| ----- | ---- | ------- | ----------- |
| `name` | `str` | `""` | Display name from device config. An empty value triggers existing entity fallback naming. |
| `hold_delay` | `int` | `DEFAULT_HOLD_DELAY_SECONDS` (`5`) | Unlock duration in seconds. Values below `1` fall back to the default. |
| `relay_type` | `int` | `DEFAULT_RELAY_TYPE` (`0`) | Relay wiring type. `0` means normally open; `1` means normally closed. |
| `relay_mode` | `int` | `DEFAULT_RELAY_MODE` (`0`) | Relay mode. `0` means auto-close; `1` means manual. |

**Invariants**:

- The dataclass remains `frozen=True`.
- Defaults are imported from `custom_components.local_akuvox.const`.
- Construction with no arguments produces the same default relay config currently
  produced by `coordinator.py`.
- The class contains no Home Assistant or device API dependencies.

## Helper Function Contracts

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
) -> int: ...
```

**Responsibility**: Convert a string-like device config value to an integer and
apply optional range or allowed-set validation.

**Rules**:

- `None` returns `default` without logging.
- Valid integer strings return the parsed integer when validation passes.
- Invalid non-empty strings return `default` and log a warning containing `key`.
- Empty strings return `default` without the invalid-integer warning.
- Values below `min_val` return `default` and log the existing below-minimum
  warning.
- Values above `max_val` return `default` and log the existing above-maximum
  warning.
- Values outside `allowed` return `default` and log the existing allowed-set
  warning.

### _build_relay_config

```python
def _build_relay_config(config: Any, letter: str) -> RelayConfig: ...
```

**Responsibility**: Build one `RelayConfig` from a dict-like `DeviceConfig` and a
relay letter such as `"A"` or `"B"`.

**Inputs**:

- `config`: object supporting `.get(key, default)` as provided by
  `pylocal_akuvox.DeviceConfig`.
- `letter`: uppercase relay suffix discovered by `coordinator.py` from relay
  status keys.

**Config keys used**:

- `f"{CONFIG_KEY_RELAY_NAME}{letter}"`
- `f"{CONFIG_KEY_RELAY_HOLD_DELAY}{letter}"`
- `f"{CONFIG_KEY_RELAY_PREFIX}{letter}{CONFIG_KEY_RELAY_TYPE_SUFFIX}"`
- `f"{CONFIG_KEY_RELAY_PREFIX}{letter}{CONFIG_KEY_RELAY_MODE_SUFFIX}"`

**Output**:

- `RelayConfig(name=name, hold_delay=hold_delay, relay_type=relay_type, relay_mode=relay_mode)`

**Rules**:

- Missing relay name defaults to `""`.
- Missing hold delay defaults to `str(DEFAULT_HOLD_DELAY_SECONDS)` before integer
  parsing.
- Hold delay uses `_parse_config_int(..., min_val=1, key=f"HoldDelay{letter}")`.
- Relay type uses `_parse_config_int(..., allowed={0, 1}, key=f"Relay{letter}Type")`.
- Relay mode uses `_parse_config_int(..., allowed={0, 1}, key=f"Relay{letter}Mode")`.

## Module Dependency Model

```text
const.py
  ↑
relay_config.py
  ↑
coordinator.py
```

`relay_config.py` imports constants from `const.py` and has no dependency on
`coordinator.py`. `coordinator.py` imports `RelayConfig` and
`_build_relay_config` from `relay_config.py`, while retaining `RELAY_KEY_RE` for
relay-letter discovery.

## State Transitions

N/A — this refactor introduces no new state machine. Coordinator cache fields and
update flow remain in `coordinator.py`.

<!-- markdownlint-enable MD013 -->
