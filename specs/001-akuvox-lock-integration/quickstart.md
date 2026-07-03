<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Quickstart: Akuvox Lock Integration

**Feature**: 001-akuvox-lock-integration
**Date**: 2026-02-23

## Prerequisites

- Python ≥3.14.2
- uv package manager
- Home Assistant development environment (or
  pytest-homeassistant-custom-component for testing)

## Project Setup

```bash
# Clone and enter repo
cd /path/to/local-akuvox

# Initialize Python project with uv (--no-package avoids src/ layout)
uv init --no-package --name local-akuvox
uv add pylocal-akuvox
uv add --dev pytest pytest-asyncio pytest-cov
uv add --dev pytest-homeassistant-custom-component
uv add --dev ruff mypy interrogate
```

## Directory Structure

```text
custom_components/akuvox/
├── __init__.py          # async_setup_entry, coordinator
├── manifest.json        # Integration metadata
├── const.py             # DOMAIN, config keys, defaults
├── config_flow.py       # Multi-step config flow
├── coordinator.py       # DataUpdateCoordinator
├── entity.py            # Base entity class
├── lock.py              # Lock platform
├── strings.json         # UI strings
└── translations/
    └── en.json          # English translations

hacs.json                # HACS metadata (repo root)

tests/
├── conftest.py          # Fixtures, mock AkuvoxDevice
├── test_config_flow.py  # Config flow tests
├── test_init.py         # Setup/teardown tests
├── test_lock.py         # Lock entity tests
└── test_coordinator.py  # Polling/error tests
```

## Running Tests

```bash
uv run pytest tests/ -x -q
```

## Running Linters

```bash
uv run ruff check custom_components/ tests/
uv run ruff format --check custom_components/ tests/
uv run mypy custom_components/
```

## Key Implementation Order

1. `const.py` — Define DOMAIN, config keys, defaults
2. `manifest.json` — Integration metadata with pylocal-akuvox
   dependency
3. `__init__.py` — Coordinator + async_setup_entry
4. `entity.py` — Base entity with device_info
5. `lock.py` — Lock entity with unlock action
6. `config_flow.py` — Multi-step config flow
7. `strings.json` + `translations/en.json` — UI strings

## Config Flow User Experience

1. User adds "Akuvox" integration
2. Enter device IP, toggle "Use SSL"
3. If SSL → "Verify SSL" checkbox (defaults unchecked)
4. Select auth mode (None/AllowList/Basic/Digest)
5. If Basic or Digest → enter username/password
6. Integration tests connection → creates lock entities
