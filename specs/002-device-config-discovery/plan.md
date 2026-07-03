<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Implementation Plan: Device Config Discovery

**Branch**: `002-device-config-discovery` | **Date**: 2026-02-25
**Spec**: [spec.md](spec.md)

## Summary

Update the Akuvox integration to read device configuration from the device on
every connection event (onboarding, reload, reconnect) and use those values to:
(1) name the device and relay entities from device-configured labels, (2) use
per-relay hold-delay instead of a hardcoded 5s constant, and (3) interpret
relay state correctly for NO/NC wiring types. The `pylocal-akuvox` v0.2.3
library already provides `get_device_config()` returning a `DeviceConfig`
dict-like object with all relevant keys.

## Technical Context

**Language/Version**: Python ≥3.14.2 (HA 2026.7.0 requirement)
**Primary Dependencies**: homeassistant, pylocal-akuvox ≥0.2.3, voluptuous
**Storage**: N/A (all config read from device, cached in coordinator)
**Testing**: pytest with homeassistant test helpers, AsyncMock
**Target Platform**: Home Assistant custom integration (HACS)
**Project Type**: HA custom component (custom_components/akuvox/)
**Performance Goals**: Config fetch adds one HTTP request per connection event;
must not block event loop
**Constraints**: All async, no blocking calls; config fetch runs
inside `_async_update_data` on connection events only (not every poll)
**Scale/Scope**: Single device integration; 2 relays per device typical

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
| --- | --- | --- |
| I. Code Quality | ✅ PASS | ruff/mypy/interrogate via pre-commit |
| II. TDD | ✅ PASS | Failing test first for all changes |
| III. UX Consistency | ✅ PASS | Fallback to defaults when unavailable |
| IV. Performance | ✅ PASS | One extra HTTP call per connection |
| V. Atomic Commits | ✅ PASS | Phased with atomic commits |
| VI. Phased Dev | ✅ PASS | Three user stories = three phases |

No violations. No complexity tracking needed.

## Project Structure

### Documentation (this feature)

```text
specs/002-device-config-discovery/
├── spec.md
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
custom_components/akuvox/
├── __init__.py          # async_setup_entry — device creation
├── config_flow.py       # Config/options flow
├── const.py             # Constants, config keys, defaults
├── coordinator.py       # AkuvoxDataUpdateCoordinator — config fetch
├── entity.py            # AkuvoxEntity — device_info property
├── lock.py              # AkuvoxLockEntity — relay control, state parsing
├── manifest.json
├── strings.json
└── translations/

tests/
├── conftest.py          # Shared fixtures (add DeviceConfig mock)
├── test_config_flow.py
├── test_coordinator.py
├── test_init.py
└── test_lock.py
```

**Structure Decision**: Existing HACS custom component layout. No new modules
needed — all changes fit within existing files. A helper module for config
key extraction may be added if complexity warrants it.
