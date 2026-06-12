<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Research: Service Layer Extraction

**Feature**: 008-service-layer-extraction **Date**: 2026-06-12 **Status**:
Complete

## Research Topics

### 1. Home Assistant Platform Entity Service Registration Pattern

**Context**: The current `__init__.py` uses
`service.async_register_platform_entity_service()` to register 18 services in
`async_setup()`. Need to confirm this can be called from a delegated module.

**Decision**: Service registration stays in `__init__.py`'s `async_setup()` but
the schema definitions and the registration call list are defined in
`services.py` and imported as a single function
(`async_register_services(hass)`).

**Rationale**: The `async_setup()` function is the canonical Home Assistant
integration entry point for service registration. Moving the call entirely to
another module would obscure the integration's lifecycle. However, extracting
the *definitions* (schemas + service metadata tuples) into a separate module is
clean and follows the pattern used by HA core integrations like `zwave_js`.

**Alternatives considered**:

- Moving `async_setup` entirely into `services.py` — rejected because it breaks
  HA conventions (init must define the function)
- Keeping schemas in `__init__.py` and only extracting handlers — rejected
  because it doesn't reduce `__init__.py` size enough

### 2. Import Direction and Circular Import Prevention

**Context**: After extraction, `lock.py` will import from `validation.py` for
helper functions. `services.py` will import from `const.py` for service name
constants. Need to verify no circular paths.

**Decision**: Strict unidirectional dependency graph:

```text
const.py (leaf - no local imports)
    ↑
validation.py (imports only const.py)
    ↑
services.py (imports const.py, validation.py for _csv_to_list)
    ↑
lock.py (imports validation.py, const.py)
    ↑
__init__.py (imports services.py, const.py, coordinator.py, webhook.py)
```

**Rationale**: This graph has no cycles. `validation.py` is a pure utility
module with no dependencies on entity or platform code. `services.py` only needs
`_csv_to_list` from validation (used in schema definitions) and constants.
`lock.py` entity methods call validation helpers directly.

**Alternatives considered**:

- Having `services.py` import from `lock.py` — rejected because it creates a
  cycle (lock imports services for typing, services imports lock for handlers)
- Merging validation into services — rejected because it conflates schema
  definitions with runtime validation logic and would push services over 500
  lines

### 3. Service Handler Method Location (Entity-Bound vs Module-Level)

**Context**: HA services registered with
`async_register_platform_entity_service` bind to entity methods by name (the
`func` parameter is a string matching a method name on the entity). Need to
confirm handlers must stay on the entity class.

**Decision**: Service handler methods (e.g., `add_user`, `modify_schedule`)
remain as methods on `AkuvoxLockEntity`. They delegate to extracted
validation/utility helpers in `validation.py`.

**Rationale**: The `func` parameter in `async_register_platform_entity_service`
is the method name string on the target entity. HA's dispatcher calls
`getattr(entity, func)(**kwargs)`. The handlers *must* live on the entity class.
However, their inline logic (PIN validation, cloud checks, schedule_relay
building, date conversions) can be extracted to standalone functions in
`validation.py`.

**Alternatives considered**:

- Module-level handler functions with entity passed as parameter — rejected
  because HA's service dispatch mechanism requires entity methods
- Thin proxy methods that delegate to a separate handler class — over-engineered
  for this refactor scope

### 4. What Moves to validation.py

**Context**: Need to decide precisely which functions/methods move from
`lock.py` to `validation.py`.

**Decision**: The following move to `validation.py`:

- `_validate_pin(pin)` — PIN format validation (4-8 digits)
- `_is_cloud_provisioned_user(user)` — cloud-provisioning check for users
- `_is_cloud_provisioned_schedule(schedule)` — cloud-provisioning check for
  schedules
- `_check_required_schedule_fields(schedule_type, **kwargs)` — schedule type
  field requirements
- `_convert_week(days)` — day-name list to digit string
- `_convert_date(value)` — date to YYYYMMDD
- `_convert_time(value)` — time to HH:MM
- `_parse_schedule_relay_pairs(raw, *, allow_empty)` — schedule_relay string
  parsing
- `_build_schedule_relay(display_ids, relay_number)` — schedule_relay string
  builder
- `_csv_to_list(value)` — CSV string to list (currently in `__init__.py`)

These become module-level functions (no longer `@staticmethod` or instance
methods). Those that currently use `self` (e.g., `_build_schedule_relay` which
uses `self._relay_number`) will take the relay_number as a parameter instead.

**Rationale**: All of these are pure logic with no entity state dependency (or
trivial state that can be passed as a parameter). Extracting them makes
`lock.py` focused on entity lifecycle and device communication.

**Alternatives considered**:

- Extracting only static methods — rejected because instance methods like
  `_validate_pin` and `_check_required_schedule_fields` also have no real `self`
  dependency (they just use `self` for convention)
- Creating a separate `utils.py` for date/CSV helpers — rejected because the
  spec explicitly puts these in `validation.py` and the total is well under 500
  lines

### 5. What Moves to services.py

**Context**: Need to decide what from `__init__.py` moves to `services.py`.

**Decision**: The following move to `services.py`:

- All 18 `service.async_register_platform_entity_service(...)` calls (lines
  101-357 of `__init__.py`)
- The voluptuous schema definitions embedded in those calls
- A single public function:
  `async_register_services(hass: HomeAssistant) -> None`

`__init__.py` retains:

- `CONFIG_SCHEMA`
- `async_setup()` — becomes a 2-line function calling
  `async_register_services(hass)`
- `_get_config_value()`, `_create_device()`
- `async_setup_entry()`, `_async_update_listener()`, `async_unload_entry()`,
  `async_remove_entry()`

**Rationale**: This achieves the spec target of ~100-150 lines for `__init__.py`
(currently 549 → estimated ~120 after removing 257 lines of service
registrations plus 20 lines of imports no longer needed).

**Alternatives considered**:

- Moving `_create_device` to a separate module — rejected because it's part of
  entry lifecycle and small (30 lines)
- Keeping schemas as module-level constants in `services.py` and composing
  registration calls — adds indirection for no benefit; keeping them inline in
  the registration function is clearest

### 6. lock.py Estimated Size After Extraction

**Context**: Need to verify the realistic post-extraction size of `lock.py`
given that Home Assistant binds entity services to methods on
`AkuvoxLockEntity`.

**Decision**: Post-extraction `lock.py` will remain approximately 1,540-1,550
lines. The refactor removes the validation/utility helpers (~190 lines), but the
service handler methods themselves stay on the entity class.

**Rationale**: Current `lock.py` = 1734 lines. Code to extract:

- Validation helpers and associated constants (~130 lines): `_validate_pin`,
  `_is_cloud_provisioned_user`, `_is_cloud_provisioned_schedule`,
  `_check_required_schedule_fields`, `_REQUIRED_FIELDS`, `_FACTORY_SCHEDULE_IDS`
- Conversion utilities (~25 lines): `_convert_week`, `_convert_date`,
  `_convert_time`
- Schedule relay helpers (~35 lines): `_build_schedule_relay`,
  `_parse_schedule_relay_pairs`
- Total realistic extraction: ~190 lines from `lock.py`

Code that must remain in `lock.py`:

- Module-level relay functions and platform setup helpers
- `AkuvoxLockEntity` lifecycle, properties, lock/unlock, timers
- All HA-dispatch-bound service handler methods (`add_user`, `modify_user`,
  `add_schedule`, etc.), because
  `async_register_platform_entity_service(..., func=...)` resolves methods on
  the entity instance

This makes `lock.py` materially smaller and better focused, but not a
sub-500-line file.

**Alternatives considered**:

- Moving service handlers to module-level functions — rejected because Home
  Assistant service dispatch requires entity methods
- Aggressive follow-up split via mixins or thin delegates — deferred to a future
  refactor outside this spec

### 7. Test Impact Assessment

**Context**: Need to understand which tests reference moved code and what
changes are needed.

**Decision**: Tests should need only import/symbol-reference updates for moved
helpers. No behavioral test changes are expected.

**Rationale**:

- `tests/test_services.py` (3249 lines): Imports `AkuvoxLockEntity` from `lock`
  and directly calls `_is_cloud_provisioned_user(...)` /
  `_is_cloud_provisioned_schedule(...)` as class helpers in several assertions.
  Those call sites must be updated to import `is_cloud_provisioned_user` and
  `is_cloud_provisioned_schedule` from `validation.py` instead.
- `tests/test_lock.py` (3762 lines): Imports `_RELAY_REFRESH_BUFFER_SECONDS`
  from `lock` — no change (stays in lock.py). No direct references to moved
  validation helpers identified.
- `tests/test_init.py` (539 lines): Tests `async_setup`, `async_setup_entry`,
  etc. — functions stay in `__init__.py`. May need to verify service
  registration still works.
- `tests/test_contact_group_services.py` (834 lines): Imports from `const` — no
  change.
- No test file directly imports `_csv_to_list` or `_validate_pin`; the known
  direct references are the cloud-provisioning helper assertions in
  `tests/test_services.py`.

Mock target paths that may need updating: None identified — current mocking
primarily targets `coordinator.device.*` methods, not the moved validation
helpers.

**Alternatives considered**: N/A — analysis confirms minimal but non-zero test
touch points.

### 8. `_csv_to_list` Usage in Schema Definitions

**Context**: `_csv_to_list` is currently defined in `__init__.py` and used
directly in schema definitions (as a voluptuous coercion function). After moving
it to `validation.py`, `services.py` needs to import it.

**Decision**: `_csv_to_list` moves to `validation.py`. `services.py` imports it
as `from .validation import csv_to_list` (dropping the underscore prefix since
it becomes a public module-level function).

**Rationale**: The function is used as a voluptuous coercion in schema
definitions (`vol.All(_csv_to_list, ...)`). It needs to be importable by
`services.py`. Making it a public function (no underscore) is appropriate since
it's now part of the module's public API.

**Alternatives considered**:

- Keeping `_csv_to_list` in `services.py` — rejected because it's a
  parsing/validation utility that logically belongs with other validation
  helpers
- Keeping underscore prefix — rejected because it's now exported across module
  boundaries

<!-- markdownlint-disable MD013 -->

## Summary of Decisions

| Item                               | Location        | Public API                                                                                           |
| ---------------------------------- | --------------- | ---------------------------------------------------------------------------------------------------- |
| Service schemas + registration     | `services.py`   | `async_register_services(hass)`                                                                      |
| `csv_to_list` (née `_csv_to_list`) | `validation.py` | `csv_to_list(value)`                                                                                 |
| PIN validation                     | `validation.py` | `validate_pin(pin)`                                                                                  |
| Cloud-provisioned checks           | `validation.py` | `is_cloud_provisioned_user(user)`, `is_cloud_provisioned_schedule(schedule)`                         |
| Schedule field validation          | `validation.py` | `check_required_schedule_fields(schedule_type, **kwargs)`                                            |
| Date/time conversions              | `validation.py` | `convert_week(days)`, `convert_date(value)`, `convert_time(value)`                                   |
| Schedule relay helpers             | `validation.py` | `build_schedule_relay(display_ids, relay_number)`, `parse_schedule_relay_pairs(raw, *, allow_empty)` |
| Lock entity class                  | `lock.py`       | `AkuvoxLockEntity` (unchanged public interface)                                                      |
| Integration lifecycle              | `__init__.py`   | `async_setup`, `async_setup_entry`, `async_unload_entry`, `async_remove_entry`                       |
| `FACTORY_SCHEDULE_IDS`             | `validation.py` | Module-level constant                                                                                |
| `_REQUIRED_FIELDS`                 | `validation.py` | Module-level constant (renamed `REQUIRED_SCHEDULE_FIELDS`)                                           |

<!-- markdownlint-enable MD013 -->
