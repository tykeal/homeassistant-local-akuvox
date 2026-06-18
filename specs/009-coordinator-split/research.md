<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Research: Coordinator Relay Config Split

**Feature**: 009-coordinator-split **Date**: 2026-06-18 **Status**: Complete

## Research Topics

### 1. Extraction Boundary

**Context**: `coordinator.py` currently defines `RelayConfig`,
`_parse_config_int`, and `_build_relay_config` before the coordinator data class.
These definitions are class-independent and account for enough lines to bring the
470-line coordinator below the 400-line aislop limit once moved.

**Decision**: Extract exactly these three symbols to
`custom_components/local_akuvox/relay_config.py`:

- `RelayConfig`
- `_parse_config_int`
- `_build_relay_config`

**Rationale**: The three symbols are a cohesive unit: the dataclass represents
one relay's parsed configuration, `_parse_config_int` provides shared integer
validation rules, and `_build_relay_config` combines the relay-specific device
config keys into a `RelayConfig`. None of them use `self`, coordinator caches,
Home Assistant APIs, or device network access.

**Alternatives considered**:

- Extract only `_parse_config_int` — rejected because it leaves the relay model
  and builder in the oversized coordinator and does not create a clear module
  responsibility.
- Extract all config-fetching methods — rejected because
  `_async_fetch_device_config`, `_fetch_config_from_device_config`, and
  `_apply_default_config` manage coordinator cache and device error behavior.
- Move `AkuvoxCoordinatorData` too — rejected because it includes coordinator
  update results (`device_info`, `relay_status`, `users`) beyond relay-config
  parsing and should stay with the coordinator.

### 2. Import Surface for relay_config.py

**Context**: The live helpers in `coordinator.py` import constants from
`.const`, use module logging for warnings, and otherwise depend only on standard
library types.

**Decision**: `relay_config.py` imports these names from `.const`:

- `CONFIG_KEY_RELAY_HOLD_DELAY`
- `CONFIG_KEY_RELAY_MODE_SUFFIX`
- `CONFIG_KEY_RELAY_NAME`
- `CONFIG_KEY_RELAY_PREFIX`
- `CONFIG_KEY_RELAY_TYPE_SUFFIX`
- `DEFAULT_HOLD_DELAY_SECONDS`
- `DEFAULT_RELAY_MODE`
- `DEFAULT_RELAY_TYPE`

It defines its own `_LOGGER = logging.getLogger(__name__)` for the existing
warning messages. It does not import `_LOGGER` from `coordinator.py` and does not
import `RELAY_KEY_RE`.

**Rationale**: Importing from `coordinator.py` would create a circular dependency
and would couple pure parsing to coordinator state. `RELAY_KEY_RE` is used by
`coordinator.py` to discover relay letters from status keys; it is not used by
`RelayConfig`, `_parse_config_int`, or `_build_relay_config`.

**Alternatives considered**:

- Import `_LOGGER` from `coordinator.py` — rejected because it creates a reverse
  dependency on the module being slimmed.
- Move `RELAY_KEY_RE` to `relay_config.py` — rejected because relay-key discovery
  stays in coordinator fetch/cache logic and is not part of config parsing.

### 3. Helper Naming and Module Privacy

**Context**: The spec calls out `_parse_config_int` and `_build_relay_config` by
name. They are internal helpers but will be imported across integration modules
after extraction.

**Decision**: Keep the leading-underscore names for `_parse_config_int` and
`_build_relay_config` in `relay_config.py`. Export `RelayConfig` without an
underscore.

**Rationale**: The move is an internal refactor, not a public API expansion.
Keeping the names preserves the current intent and minimizes implementation
churn. `coordinator.py` may import `_build_relay_config` from the new module even
though it remains private to the package. Tests that exercise parser behavior can
also import private helpers from `relay_config.py` because they are white-box
unit tests.

**Alternatives considered**:

- Rename to `parse_config_int` and `build_relay_config` — rejected because it
  would imply a new stable module API and create unnecessary call-site churn.
- Keep aliases in `coordinator.py` — rejected because compatibility for private
  helper imports is not required and aliases would leave confusing surface area in
  the file being reduced.

### 4. Test Import Impact

**Context**: `tests/test_coordinator.py` currently imports `RelayConfig`,
`_build_relay_config`, and `_parse_config_int` directly from
`custom_components.local_akuvox.coordinator` and contains direct tests for all
three symbols. `tests/test_lock.py` also imports `RelayConfig` from
`coordinator.py` inside `test_relay_defaults_when_no_config_entry` to construct
a coordinator data fixture.

**Decision**: Update those test imports to
`custom_components.local_akuvox.relay_config` during implementation. Do not keep
coordinator-level compatibility aliases solely for private helper imports.

**Rationale**: The direct imports are white-box tests of internal parser symbols.
They are not a Home Assistant public API, and the Stage 1 spec explicitly allows
test imports to move to the new module path. Avoiding compatibility aliases keeps
the coordinator focused and ensures the file-size reduction is real.

**Alternatives considered**:

- Re-export moved symbols from `coordinator.py` — rejected because it preserves an
  unnecessary private import path and undermines the cleanup.
- Delete direct helper tests — rejected because they provide useful regression
  coverage for parsing edge cases and should keep their assertions.

### 5. Behavior Preservation Strategy

**Context**: The extracted code handles default names, default hold delays,
allowed relay type/mode values, empty strings, invalid integers, and warning log
messages.

**Decision**: Move code mechanically with no logic changes. Preserve defaults,
function signatures, warning message text, and key construction exactly.
`coordinator.py` should only replace inline definitions with imports and keep its
cache/fallback methods semantically unchanged.

**Rationale**: The value of this feature is clearing the file-size gate with zero
runtime behavior change. Mechanical movement plus existing tests is the lowest
risk approach.

**Alternatives considered**:

- Normalize values or improve validation while moving — rejected as scope creep.
- Add new public configuration behavior — rejected because the spec forbids
  user-visible API changes.

## Summary of Decisions

| Item | Decision |
| ---- | -------- |
| New module | `custom_components/local_akuvox/relay_config.py` |
| Symbols moved | `RelayConfig`, `_parse_config_int`, `_build_relay_config` |
| Helper names | Keep leading underscores |
| Coordinator re-export | No re-export for moved private helpers |
| Test impact | Update `test_coordinator.py` and `test_lock.py` imports |
| `RELAY_KEY_RE` | Remains imported/used by `coordinator.py` only |
| Logging | New module-local `_LOGGER = logging.getLogger(__name__)` |

<!-- markdownlint-enable MD013 -->
