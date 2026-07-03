<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Implementation Plan: Schedule & User Management Services

**Branch**: `003-schedule-user-services` | **Date**: 2026-02-27
**Spec**: [spec.md](spec.md)
**Input**: Feature specification from
`/specs/003-schedule-user-services/spec.md`

## Summary

Add ten custom Home Assistant services to the Akuvox integration
for CRUD operations on device schedules and users, plus two
convenience services for adding/removing individual
schedule+relay pairs on existing users (best-effort updates;
concurrent calls may race). Services are registered as
platform entity services using
`service.async_register_platform_entity_service()` in
`async_setup()`, following the Schlage integration pattern
(reference: `homeassistant/components/schlage`). Service calls
target lock entities via HA's standard entity targeting. Handler
methods live on the `AkuvoxLockEntity` class and delegate to
`pylocal-akuvox` library methods, with input validation,
cloud-entity protection (read-only for cloud-provisioned
entities), and event firing for automations. Cloud-provisioned
schedules cannot be used when creating local user codes. PINs and
card codes are returned in plain text for automation consumption
but masked in logs.

## Technical Context

**Language/Version**: Python ≥3.14.2
**Primary Dependencies**: pylocal-akuvox ≥0.2.3 (schedule/user
APIs), homeassistant ≥2026.7.0 (service framework)
**Storage**: None; integration is a pass-through to device local API
**Testing**: pytest, pytest-homeassistant-custom-component,
pytest-asyncio, pytest-cov
**Target Platform**: Home Assistant (any platform running HA Core)
**Project Type**: Home Assistant custom integration (HACS)
**Performance Goals**: Service calls complete within 5 seconds;
errors returned within 10 seconds
**Constraints**: MUST NOT block HA event loop; all device I/O async;
PINs/card codes plain text in responses, masked in logs
**Scale/Scope**: 10 services across existing Akuvox device entries;
no new entities, config flows, or platforms

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1
design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| I. Code Quality | ✅ PASS | ruff/mypy/interrogate; SPDX on new files |
| II. TDD | ✅ PASS | pytest with TDD red-green-refactor; test_services.py |
| III. UX Consistency | ✅ PASS | Consistent schemas, actionable errors |
| IV. Performance | ✅ PASS | Async I/O; 5s target from spec SC-001 |
| V. Atomic Commits | ✅ PASS | Pre-commit hooks; DCO; one change/commit |
| VI. Phased Dev | ✅ PASS | Three phases matching priority tiers |

**Post-Phase 1 re-check**: ✅ All gates still pass. No new
dependencies, no complexity violations.

## Project Structure

### Documentation (this feature)

```text
specs/003-schedule-user-services/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── schedule-services.md
│   └── user-services.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

Extends the existing HACS integration layout. No new platforms or
entity types.

```text
custom_components/akuvox/
├── __init__.py          # Updated: add async_setup() for service registration
├── const.py             # Updated: service/event name constants
├── lock.py              # Updated: add entity service methods
├── services.yaml        # New: service definitions with entity targets
├── strings.json         # Updated: service + exception strings
└── translations/
    └── en.json          # Updated: service + exception translations

tests/
├── conftest.py          # Updated: schedule/user mock fixtures
└── test_services.py     # New: entity service method tests
```

**Structure Decision**: Service handler methods live on the
`AkuvoxLockEntity` class in `lock.py`, following the Schlage
integration pattern. HA routes entity-targeted service calls
directly to the matched entity instance, which has direct access
to the coordinator and device via `self.coordinator.device`. No
standalone `services.py` module is needed.

**Service Registration**: Per HA core developer guidance, all
services are registered in `async_setup()` (not
`async_setup_entry()`) using
`service.async_register_platform_entity_service()` from
`homeassistant.helpers.service`. This ensures services are always
discoverable by the automation UI even when no config entries are
loaded. Each service maps to a named async method on the entity
class (the `func` parameter is a string matching the method name).
HA automatically routes calls to the targeted entity via standard
entity/device/area targeting.

**Reference implementation**: The Schlage integration
(`homeassistant/components/schlage`) uses exactly this pattern
for its `add_code`, `delete_code`, and `get_codes` services.

**Schedule-Relay Pair Services**: The pylocal-akuvox library has
no atomic add/remove for individual schedule+relay pairs — the
`schedule_relay` field is a single string (e.g. `"1-1,2-3"`).
Two convenience services (`add_user_schedule_relay` and
`remove_user_schedule_relay`) are implemented at the entity level
by fetching the current user, parsing the string, performing the
add/remove, and calling `modify_user` with the updated string.

## Complexity Tracking

> No constitution violations to justify.
