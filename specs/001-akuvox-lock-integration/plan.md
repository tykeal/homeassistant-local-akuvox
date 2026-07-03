<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Implementation Plan: Akuvox Lock Integration

**Branch**: `001-akuvox-lock-integration` | **Date**: 2026-02-23
**Spec**: [spec.md](spec.md)
**Input**: Feature specification from
`/specs/001-akuvox-lock-integration/spec.md`

## Summary

Home Assistant custom integration that exposes Akuvox intercom device
relays as lock entities via the local HTTP/HTTPS API. Uses the
`pylocal-akuvox` library for device communication. Supports three
authentication modes (None/AllowList, Basic Auth, Digest Auth),
explicit SSL selection with optional certificate verification, and
multiple relays per device. Follows standard HA patterns with
DataUpdateCoordinator for polling-based state updates. The repository
MUST be HACS-compatible for installation.

## Technical Context

**Language/Version**: Python ≥3.14.2
**Primary Dependencies**: pylocal-akuvox (device communication),
homeassistant (HA core framework)
**Storage**: Home Assistant config entries (no external database)
**Testing**: pytest, pytest-homeassistant-custom-component,
pytest-asyncio, pytest-cov
**Target Platform**: Home Assistant (any platform running HA Core)
**Project Type**: Home Assistant custom integration (HACS)
**Performance Goals**: Unlock commands delivered within 5 seconds;
state polling every 30 seconds
**Constraints**: MUST NOT block the HA event loop; all device I/O
MUST be async; repository MUST follow HACS integration structure
**Scale/Scope**: Single integration supporting multiple Akuvox
devices, each with multiple relays

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1
design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| I. Code Quality | ✅ PASS | ruff/mypy/interrogate; SPDX headers |
| II. TDD | ✅ PASS | pytest + HA custom component tests |
| III. UX Consistency | ✅ PASS | Standard HA config flow patterns |
| IV. Performance | ✅ PASS | Async I/O via aiohttp; no blocking |
| V. Atomic Commits | ✅ PASS | Pre-commit hooks; DCO sign-off |
| VI. Phased Dev | ✅ PASS | Four phases match user stories |

## Project Structure

### Documentation (this feature)

```text
specs/001-akuvox-lock-integration/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

HACS requires the integration to be at
`custom_components/DOMAIN_NAME/` at the repository root.
No `src/` prefix is used.

```text
custom_components/akuvox/
├── __init__.py          # Integration setup, coordinator
├── manifest.json        # HA integration metadata
├── const.py             # Constants, config keys, defaults
├── config_flow.py       # Multi-step config flow + options
├── coordinator.py       # DataUpdateCoordinator
├── entity.py            # Base CoordinatorEntity for Akuvox
├── lock.py              # Lock platform entities
├── strings.json         # UI strings for config flow
└── translations/
    └── en.json          # English translations

hacs.json                # HACS repository metadata (repo root)

tests/
├── conftest.py          # Shared fixtures, mock device
├── test_config_flow.py  # Config flow tests
├── test_init.py         # Integration setup/teardown tests
├── test_lock.py         # Lock entity behavior tests
└── test_coordinator.py  # Coordinator polling/error tests
```

**Structure Decision**: Standard HACS custom integration layout
with `custom_components/akuvox/` at the repository root. Tests
at repository root in `tests/`. This follows the HACS requirement
that integration files live under
`ROOT_OF_REPO/custom_components/INTEGRATION_NAME/`.

## Complexity Tracking

> No constitution violations to justify.
