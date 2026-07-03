<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->
<!-- markdownlint-disable MD013 -->

# Implementation Plan: Contact & Group Management Services

**Branch**: `006-contact-group-services` | **Date**: 2026-04-24
**Spec**: [spec.md](spec.md)
**Input**: Feature specification from
`/specs/006-contact-group-services/spec.md`

> Archived design artifact: this feature has already been implemented
> and merged. Version references in this plan are historical; see
> `pyproject.toml` and
> `custom_components/local_akuvox/manifest.json` for current
> dependency requirements.

## Summary

Add eight custom Home Assistant services to the Akuvox integration
for CRUD operations on device contacts and groups, leveraging
pylocal-akuvox v0.3.0 contact and group API support. Services are
registered as platform entity services using
`service.async_register_platform_entity_service()` in
`async_setup()`, following the identical pattern established by the
schedule and user management services (feature 003). Service calls
target lock entities via HA's standard entity targeting. Handler
methods live on the `AkuvoxLockEntity` class and delegate to
`pylocal-akuvox` library methods, with input validation and event
firing for automations. Contacts support batch deletion (list of
IDs). The integration acts as a pass-through — no local caching.

## Technical Context

**Language/Version**: Python ≥3.14.2
**Primary Dependencies**: pylocal-akuvox ≥0.3.0 (contact/group
APIs), homeassistant ≥2026.7.0 (service framework)
**Storage**: None; integration is a pass-through to device local API
**Testing**: pytest, pytest-homeassistant-custom-component,
pytest-asyncio, pytest-cov
**Target Platform**: Home Assistant (any platform running HA Core)
**Project Type**: Home Assistant custom integration (HACS)
**Performance Goals**: Service calls complete within 5 seconds;
errors returned within 10 seconds (SC-001, SC-006)
**Constraints**: MUST NOT block HA event loop; all device I/O async;
no local caching of contacts or groups
**Scale/Scope**: 8 new services across existing Akuvox device
entries; no new entities, config flows, or platforms

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1
design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| I. Code Quality | ✅ PASS | ruff/mypy/interrogate; SPDX on new files |
| II. TDD | ✅ PASS | pytest with TDD red-green-refactor; test_contact_group_services.py |
| III. UX Consistency | ✅ PASS | Consistent schemas, actionable errors, follows 003 patterns |
| IV. Performance | ✅ PASS | Async I/O; 5s target from spec SC-001 |
| V. Atomic Commits | ✅ PASS | Pre-commit hooks; DCO; one change/commit |
| VI. Phased Dev | ✅ PASS | Three phases matching priority tiers (P1 read, P2 write, P3 delete) |

**Post-Phase 1 re-check**: ✅ All gates still pass. pylocal-akuvox
version bump is the only dependency change (0.2.3 → 0.3.0). No
complexity violations. Contact and group services follow the exact
same error handling, event bus, and entity targeting patterns as the
existing schedule/user services.

## Project Structure

### Documentation (this feature)

```text
specs/006-contact-group-services/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── contact-services.md
│   └── group-services.md
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

Extends the existing HACS integration layout. No new platforms or
entity types.

```text
custom_components/local_akuvox/
├── __init__.py          # Updated: register 8 new services in async_setup()
├── const.py             # Updated: service/event name constants
├── lock.py              # Updated: add 8 entity service methods
├── services.yaml        # Updated: 8 new service definitions
├── strings.json         # Updated: service + exception strings
└── translations/
    └── en.json          # Updated: service + exception translations

pyproject.toml           # Updated: pylocal-akuvox >=0.3.0
custom_components/local_akuvox/manifest.json  # Updated: pylocal-akuvox >=0.3.0

tests/
├── conftest.py                      # Updated: contact/group mock fixtures
└── test_contact_group_services.py   # New: contact/group service tests
```

**Structure Decision**: Service handler methods live on the
`AkuvoxLockEntity` class in `lock.py`, following the identical
pattern used by schedule and user services. HA routes
entity-targeted service calls directly to the matched entity
instance, which has direct access to the coordinator and device via
`self.coordinator.device`. No standalone `services.py` module is
needed.

**Service Registration**: All 8 new services are registered in
`async_setup()` using
`service.async_register_platform_entity_service()` from
`homeassistant.helpers.service`, consistent with the existing 10
services. Each service maps to a named async method on the entity
class (the `func` parameter is a string matching the method name).

**Dependency Bump**: Both `pyproject.toml` (project dependencies)
and `manifest.json` (HA requirements) must be updated from
`>=0.2.3` to `>=0.3.0` to access the contact and group API surface.

## Complexity Tracking

> No constitution violations to justify.
