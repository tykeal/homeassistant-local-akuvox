<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Quickstart: Schedule & User Management Services

**Feature**: 003-schedule-user-services
**Date**: 2026-02-27

## Prerequisites

- Existing local-akuvox integration (specs 001 + 002 implemented)
- Python ≥3.14.2
- uv package manager
- pylocal-akuvox ≥0.2.3

## New Files

```text
custom_components/akuvox/
├── services.yaml        # Service definitions with entity targets

tests/
├── test_services.py     # Service handler tests
```

## Modified Files

- `__init__.py` — Add `async_setup()` with
  `service.async_register_platform_entity_service()` calls
- `const.py` — Add service name and event name constants
- `lock.py` — Add entity service methods (list/add/modify/delete
  for schedules and users, plus add/remove schedule_relay pair)
- `strings.json` — Add services + exceptions sections
- `translations/en.json` — Add services + exceptions sections
- `tests/conftest.py` — Add schedule/user fixtures

## No Changes Required

- `coordinator.py` — No changes; entity methods call device directly
- `entity.py` — No changes; base entity unchanged
- `config_flow.py` — No changes; no new config options
- `manifest.json` — No changes; no new dependencies

## Running Tests

```bash
# All tests
uv run pytest tests/ -x -q

# Only service tests
uv run pytest tests/test_services.py -x -q
```

## Running Linters

```bash
uv run ruff check custom_components/ tests/
uv run ruff format --check custom_components/ tests/
uv run mypy custom_components/
```

## Key Implementation Order

1. `const.py` — Add service name and event name constants
2. `services.yaml` — Define all 10 services with entity target
   selectors (domain: lock, integration: akuvox)
3. `lock.py` — Add entity service methods matching the `func`
   string parameter names (e.g., `list_schedules`, `add_schedule`,
   `add_user_schedule_relay`, `remove_user_schedule_relay`)
4. `__init__.py` — Add `async_setup()` to register all services
   via `service.async_register_platform_entity_service()`
5. `strings.json` + `translations/en.json` — Add service + exception
   strings
6. `tests/conftest.py` — Add schedule/user mock fixtures
7. `tests/test_services.py` — Test all services

## Service Call Examples (Developer Tools)

### List Schedules

```yaml
service: akuvox.list_schedules
target:
  entity_id: lock.akuvox_front_door
```

### Add Schedule

```yaml
service: akuvox.add_schedule
target:
  entity_id: lock.akuvox_front_door
data:
  schedule_type: "0"
  name: "Weekday Access"
  week: "12345"
  time_start: "08:00"
  time_end: "18:00"
```

### Add User

```yaml
service: akuvox.add_user
target:
  entity_id: lock.akuvox_front_door
data:
  name: "John Doe"
  schedules:
    - "10"
  lift_floor_num: "3"
  private_pin: "1234"
```

### Modify User

```yaml
service: akuvox.modify_user
target:
  entity_id: lock.akuvox_front_door
data:
  id: "42"
  private_pin: "5678"
```

### Delete Schedule

```yaml
service: akuvox.delete_schedule
target:
  entity_id: lock.akuvox_front_door
data:
  id: "7"
```

### Add Schedule-Relay Pair to User

```yaml
service: akuvox.add_user_schedule_relay
target:
  entity_id: lock.akuvox_front_door
data:
  id: "42"
  schedule_id: "2"
  relay_id: "3"
```

### Remove Schedule-Relay Pair from User

```yaml
service: akuvox.remove_user_schedule_relay
target:
  entity_id: lock.akuvox_front_door
data:
  id: "42"
  schedule_id: "1"
  relay_id: "1"
```
