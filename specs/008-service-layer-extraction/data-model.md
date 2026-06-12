<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Data Model: Service Layer Extraction

**Feature**: 008-service-layer-extraction **Date**: 2026-06-12

## Module Dependency Graph

This refactor creates no new data entities. The "data model" for this feature is
the **module dependency graph** — the structural relationships between files
after extraction.

```text
                    ┌─────────────┐
                    │   const.py  │  (leaf module — no local imports)
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
     ┌──────────────┐  ┌──────────┐  ┌───────────────┐
     │ validation.py│  │webhook.py│  │coordinator.py │
     │              │  │          │  │               │
     │ • csv_to_list│  │          │  │               │
     │ • validate_  │  │          │  │               │
     │   pin        │  │          │  │               │
     │ • is_cloud_* │  │          │  │               │
     │ • convert_*  │  │          │  │               │
     │ • parse/build│  │          │  │               │
     │   schedule   │  │          │  │               │
     └──────┬───────┘  └────┬─────┘  └───────┬───────┘
            │               │                 │
            ▼               │                 │
     ┌──────────────┐       │                 │
     │  services.py │       │                 │
     │              │       │                 │
     │ • schemas    │       │                 │
     │ • async_     │       │                 │
     │   register_  │       │                 │
     │   services() │       │                 │
     └──────┬───────┘       │                 │
            │               │                 │
            ▼               ▼                 ▼
     ┌─────────────────────────────────────────────┐
     │                 __init__.py                   │
     │                                              │
     │ • CONFIG_SCHEMA                              │
     │ • async_setup() → calls register_services()  │
     │ • async_setup_entry()                        │
     │ • async_unload_entry()                       │
     │ • async_remove_entry()                       │
     └──────────────────────────────────────────────┘
                           │
                           ▼
     ┌─────────────────────────────────────────────┐
     │                   lock.py                    │
     │                                              │
     │ • Relay parsing functions                    │
     │ • async_setup_entry (platform)               │
     │ • AkuvoxLockEntity                           │
     │   - Entity lifecycle                         │
     │   - lock/unlock actions                      │
     │   - Service handler methods (thin delegates) │
     └─────────────────────────────────────────────┘
            │
            │ imports helpers from
            ▼
     ┌──────────────┐
     │ validation.py│
     └──────────────┘
```

## Module Specifications

### validation.py

**Responsibility**: Pure validation logic and format conversion utilities with
minimal Home Assistant dependencies (`ServiceValidationError` for raised
validation errors and `config_validation` helpers used by schema coercion).

**Constants**:

| Name                       | Type                         | Value                                                                | Description                                   |
| -------------------------- | ---------------------------- | -------------------------------------------------------------------- | --------------------------------------------- |
| `REQUIRED_SCHEDULE_FIELDS` | `dict[str, tuple[str, ...]]` | `{"0": ("week", "date_start", "date_end"), "1": ("week",), "2": ()}` | Required fields per schedule type             |
| `FACTORY_SCHEDULE_IDS`     | `frozenset[str]`             | `frozenset({"1001", "1002"})`                                        | Schedule IDs that are never cloud-provisioned |

**Functions**:

| Function                         | Signature                                               | Origin                                             |
| -------------------------------- | ------------------------------------------------------- | -------------------------------------------------- |
| `csv_to_list`                    | `(value: Any) -> list[str]`                             | `__init__._csv_to_list`                            |
| `validate_pin`                   | `(pin: str \| None) -> None`                            | `AkuvoxLockEntity._validate_pin`                   |
| `is_cloud_provisioned_user`      | `(user: User) -> bool`                                  | `AkuvoxLockEntity._is_cloud_provisioned_user`      |
| `is_cloud_provisioned_schedule`  | `(schedule: AccessSchedule) -> bool`                    | `AkuvoxLockEntity._is_cloud_provisioned_schedule`  |
| `check_required_schedule_fields` | `(schedule_type: str, **kwargs: Any) -> None`           | `AkuvoxLockEntity._check_required_schedule_fields` |
| `convert_week`                   | `(days: list[str]) -> str`                              | `AkuvoxLockEntity._convert_week`                   |
| `convert_date`                   | `(value: dt.date) -> str`                               | `AkuvoxLockEntity._convert_date`                   |
| `convert_time`                   | `(value: dt.time) -> str`                               | `AkuvoxLockEntity._convert_time`                   |
| `parse_schedule_relay_pairs`     | `(raw: str, *, allow_empty: bool = False) -> list[str]` | `AkuvoxLockEntity._parse_schedule_relay_pairs`     |
| `build_schedule_relay`           | `(display_ids: list[str], relay_number: int) -> str`    | `AkuvoxLockEntity._build_schedule_relay`           |

**Validation Rules**:

- PIN: Must be 4-8 decimal digits if provided (non-None)
- Cloud user: If `source` is non-None and not in `("Local", "")`, return `True`.
  Otherwise if `source_type` is non-None and not in `("1", "Local", "")`, return
  `True`. Otherwise return `False`.
- Cloud schedule: `source_type` not in `("1", "")` AND not in
  `FACTORY_SCHEDULE_IDS`
- Schedule fields: Type "0" requires week + date_start + date_end; Type "1"
  requires week; Type "2" has no extra requirements

### services.py

**Responsibility**: Service schema definitions (voluptuous) and registration
orchestration.

**Functions**:

| Function                  | Signature                       | Description                              |
| ------------------------- | ------------------------------- | ---------------------------------------- |
| `async_register_services` | `(hass: HomeAssistant) -> None` | Register all 18 platform entity services |

**Internal constants** (module-level, not exported):

- Schema definitions for each of the 18 services (inline in registration calls)

### **init**.py (post-refactor)

**Responsibility**: Integration lifecycle orchestration only.

**Public functions** (required by HA):

| Function             | Lines (est.) | Description                                                     |
| -------------------- | ------------ | --------------------------------------------------------------- |
| `async_setup`        | 5            | Delegates to `services.async_register_services(hass)`           |
| `async_setup_entry`  | 35           | Device creation, coordinator init, webhook, platform forwarding |
| `async_unload_entry` | 15           | Platform unload, webhook cleanup, device session close          |
| `async_remove_entry` | 20           | Best-effort webhook disable on device                           |

**Private helpers** (remain in `__init__.py`):

| Function                 | Lines (est.) | Description                            |
| ------------------------ | ------------ | -------------------------------------- |
| `_get_config_value`      | 5            | Config entry value accessor            |
| `_create_device`         | 30           | AkuvoxDevice factory from config entry |
| `_async_update_listener` | 3            | Reload on options change               |

### lock.py (post-refactor)

**Responsibility**: Lock entity platform setup, entity class lifecycle,
lock/unlock actions, and thin service handler methods.

**Retained from current lock.py**:

- Module-level relay helper functions (`_relay_key_to_number`,
  `_relay_key_to_label`, `_parse_relay_state`, `_parse_int_state`,
  `_parse_str_state`)
- `async_setup_entry` (platform setup)
- `AkuvoxLockEntity` class:
  - `__init__`, `is_locked` property
  - `async_lock`, `async_unlock`
  - Timer management (`_schedule_delayed_refresh`,
    `_async_finish_optimistic_unlock`, `_async_finish_optimistic_lock`)
  - `async_will_remove_from_hass`
  - All 18 service handler methods (simplified to delegate to `validation.py`
    helpers)
  - `_fetch_local_schedule`, `_fetch_local_user`, `_check_cloud_schedules`
    (these stay because they need `self.coordinator.device` access)

## State Transitions

N/A — No state machines are introduced or modified. This is a pure structural
refactor.

## Estimated Line Counts Post-Refactor

| Module          | Current | Post-Refactor | Change                                      |
| --------------- | ------- | ------------- | ------------------------------------------- |
| `__init__.py`   | ~550    | ~120          | -78%                                        |
| `lock.py`       | ~1,735  | ~1,545        | -11%                                        |
| `services.py`   | —       | ~290          | new                                         |
| `validation.py` | —       | ~200          | new                                         |
| **Total**       | ~2,285  | ~1060         | -54% (deduplication of imports/boilerplate) |

Note: Total LOC decreases slightly because extracted functions shed duplicate
imports and the `self` parameter overhead of unnecessary static methods. Actual
total will be close to original (code is moved, not deleted). `lock.py` remains
relatively large because Home Assistant platform entity service handlers are
entity-bound and stay on `AkuvoxLockEntity`.

<!-- markdownlint-enable MD013 -->
