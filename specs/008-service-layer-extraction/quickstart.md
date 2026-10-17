<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Quickstart: Service Layer Extraction

**Feature**: 008-service-layer-extraction **Date**: 2026-06-12

## Overview

This refactor extracts the service layer from two oversized files (`__init__.py`
at ~550 lines, `lock.py` at ~1,735 lines) into focused modules while maintaining
100% behavioral compatibility.

## Architecture After Refactor

```text
__init__.py (120 lines)     → Lifecycle orchestration only
services.py (290 lines)     → Schema definitions + registration
validation.py (200 lines)   → Pure validation/conversion helpers
lock.py (~1,545 lines; validation extracted, service handlers remain entity-bound)
```

## Development Workflow

### Prerequisites

- Feature branch `008-service-layer-extraction` checked out
- `uv sync` for dependency installation
- All tests passing on `main` (baseline)

### Phase Execution Order

1. **Create `validation.py`** — Copy helpers from `lock.py` and `_csv_to_list`
   from `__init__.py` into the new module; leave originals unchanged for now
1. **Create `services.py`** — Move service registration from `__init__.py`
1. **Update `__init__.py`** — Replace inline service registration with
   `services.async_register_services(hass)` call
1. **Update `lock.py`** — Update callers to use `validation.py` imports, then
   remove the original helper implementations
1. **Update test imports/references** — Fix any import paths or direct helper
   references that point to moved code
1. **Verify** — Run full test suite, lint, type check

### Key Constraints

- **No test logic changes** — Only import paths or symbol references to moved
  helpers may change in test files
- **No mock target changes** — Service tests mock `coordinator.device.*` which
  is unchanged
- **No behavior changes** — Every service call produces identical results
- **No new features** — Refactor only

## How to Verify

```bash
# Run full test suite
uv run pytest tests/ -v

# Lint check
uv run ruff check custom_components/local_akuvox/

# Type check
uv run mypy custom_components/local_akuvox/

# REUSE compliance (SPDX headers)
uv run reuse lint

# Line count check (~500 target; lock.py exempt)
wc -l custom_components/local_akuvox/*.py | sort -n

# Verify service count (should show 18 registrations)
grep -c "async_register_platform_entity_service" custom_components/local_akuvox/services.py
```

Note: `lock.py` is exempt from the ~500-line target because Home Assistant
platform entity service handlers must stay on the entity class for dispatch.

## Import Guide (Post-Refactor)

### For lock.py service handlers

```python
# Before (inline in lock.py methods):
# self._validate_pin(pin)
# self._is_cloud_provisioned_user(user)
# schedule_relay = self._build_schedule_relay(schedules)

# After:
from .validation import (
    build_schedule_relay,
    check_required_schedule_fields,
    convert_date,
    convert_time,
    convert_week,
    is_cloud_provisioned_schedule,
    is_cloud_provisioned_user,
    parse_schedule_relay_pairs,
    validate_pin,
)
```

### For **init**.py

```python
# Before: 257 lines of inline service registration
# After:
from .services import async_register_services


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register platform entity services for Akuvox."""
    await async_register_services(hass)
    return True
```

### For services.py

```python
from .validation import csv_to_list
from .const import DOMAIN, SERVICE_ADD_USER, ...  # all 18 service constants
```

## Common Pitfalls

1. **Don't move `_fetch_local_user` / `_fetch_local_schedule` /
   `_check_cloud_schedules`** — These need `self.coordinator.device` access and
   stay on the entity class.

1. **`build_schedule_relay` signature change** — It was
   `self._build_schedule_relay(display_ids)` using `self._relay_number`. Now
   it's `build_schedule_relay(display_ids, self._relay_number)` — the
   relay_number becomes an explicit parameter.

1. **`_csv_to_list` → `csv_to_list`** — Dropping the underscore prefix since
   it's now a public module-level function exported across module boundaries.

1. **`async_register_services` stays async despite no current I/O** — Keep it as
   `async def` to match Home Assistant service registration conventions and to
   allow future async schema loading. Even though it currently only performs
   synchronous registration calls, callers should still
   `await async_register_services(hass)`.

1. **`_REQUIRED_FIELDS` → `REQUIRED_SCHEDULE_FIELDS`** — Renamed for clarity
   since it's no longer a private class-adjacent constant.

1. **`_FACTORY_SCHEDULE_IDS` → `FACTORY_SCHEDULE_IDS`** — Same reasoning; moves
   from class variable to module constant.
