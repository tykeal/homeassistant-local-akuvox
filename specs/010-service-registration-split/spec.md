<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Feature Specification: Service Registration Split

**Feature Branch**: `010-service-registration-split` **Created**: 2026-06-18
**Status**: Draft **Input**: User description: "GitHub issue #147 requests
splitting `custom_components/local_akuvox/services.py:async_register_services`
because aislop reports `complexity/function-too-long` at 168 lines with an
80-line maximum."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registration Function Clears Gate (Priority: P1)

As a maintainer, I need `async_register_services` to be a thin orchestrator
under the 80-line aislop function-length limit, so the current
`complexity/function-too-long` finding no longer blocks quality checks.

**Why this priority**: Issue #147 is specifically about the length of
`async_register_services`. Clearing that gate is the smallest valuable outcome
of this internal refactor.

**Independent Test**: Can be verified by measuring the function after the
refactor and running the aislop rule that currently reports it as too long.

**Acceptance Scenarios**:

1. **Given** `async_register_services` currently registers all services inline,
   **When** service registration is split into domain helpers, **Then**
   `async_register_services` contains 80 lines or fewer
1. **Given** aislop scans `services.py`, **When** the refactor is complete,
   **Then** `complexity/function-too-long` no longer reports
   `async_register_services`
1. **Given** a developer opens `async_register_services`, **When** they inspect
   the function, **Then** it reads as a short sequence of calls to cohesive
   helper functions rather than a long list of registration details

______________________________________________________________________

### User Story 2 - Services Remain Identical (Priority: P1)

As a maintainer guarding against regressions, I can verify that all 18 Local
Akuvox entity services are still registered with the same service names,
schemas, entity domain, handler function names, and response semantics.

**Why this priority**: This feature is a pure internal refactor. Any changed
service behavior, schema validation, response support, or public API would
violate the agreed scope.

**Independent Test**: Can be verified by running the existing service
registration tests and checking that the same 18 platform entity service
registrations are produced before and after the split.

**Acceptance Scenarios**:

1. **Given** the integration is loaded after the refactor, **When** Home
   Assistant registers Local Akuvox services, **Then** all 18 existing services
   are registered under `local_akuvox` exactly as before
1. **Given** a `list_*` service registration, **When** it is inspected after the
   refactor, **Then** it still uses `SupportsResponse.ONLY`
1. **Given** any non-list service registration, **When** it is inspected after
   the refactor, **Then** its response-support behavior is unchanged
1. **Given** an automation or script that calls an existing Local Akuvox
   service, **When** the integration version containing this refactor loads,
   **Then** no service name, field name, schema, response, or automation change
   is required

______________________________________________________________________

### User Story 3 - Registrations Are Cohesive (Priority: P2)

As a developer maintaining service registrations, I can find related schedule,
user, contact, and group registrations in focused private helpers within
`services.py`, so future changes can be made in the correct service group.

**Why this priority**: The length reduction should improve maintainability, not
just move lines around. Grouping registrations by domain provides a clear
structure for future service updates.

**Independent Test**: Can be verified by inspecting `services.py` and confirming
that each private helper owns the registrations for exactly one service group.

**Acceptance Scenarios**:

1. **Given** the refactor is complete, **When** a developer opens `services.py`,
   **Then** `_register_schedule_services`, `_register_user_services`,
   `_register_contact_services`, and `_register_group_services` are defined in
   that file
1. **Given** `_register_schedule_services`, **When** its registrations are
   inspected, **Then** it registers only list, add, modify, and delete schedule
   services
1. **Given** `_register_user_services`, **When** its registrations are inspected,
   **Then** it registers only list, add, modify, delete, add schedule relay, and
   remove schedule relay user services
1. **Given** `_register_contact_services` and `_register_group_services`,
   **When** their registrations are inspected, **Then** each helper registers
   only its corresponding list, add, modify, and delete services

______________________________________________________________________

### User Story 4 - Existing Gates Stay Green (Priority: P2)

As a maintainer, I need the refactor to keep the existing test and quality gates
passing, so reducing one aislop violation does not introduce new failures.

**Why this priority**: The project constitution requires passing tests,
linting, type checks, docstrings, and pre-commit hooks before merge.

**Independent Test**: Can be verified by running the existing repository test
suite and quality commands after the implementation stage.

**Acceptance Scenarios**:

1. **Given** the existing test suite, **When** it is run after the refactor,
   **Then** every existing test passes
1. **Given** interrogate checks docstring coverage, **When** the helper functions
   are added, **Then** docstring coverage remains 100%
1. **Given** ruff, mypy, reuse, markdownlint, gitlint, and other configured
   hooks run, **When** the refactor is committed, **Then** they complete without
   errors

### Edge Cases

- The refactor may group registrations by service domain, but it must not omit
  any registration or change observable Home Assistant behavior.
- Each `list_*` service must retain `SupportsResponse.ONLY`; accidentally
  removing response support would be a behavior change.
- Service schema objects must not be recreated or altered as part of this split;
  the helpers should reuse the existing schema constants.
- The public `async_register_services(hass)` name, signature, and awaitable
  contract must remain because `custom_components/local_akuvox/__init__.py`
  awaits it during integration setup.
- The helpers must remain in `services.py`; creating a new module is outside the
  settled scope for this issue.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `async_register_services(hass)` MUST keep its public name,
  signature, async contract, and role as the integration setup entry point for
  service registration.
- **FR-002**: `async_register_services(hass)` MUST delegate registration to the
  four private helpers `_register_schedule_services(hass)`,
  `_register_user_services(hass)`, `_register_contact_services(hass)`, and
  `_register_group_services(hass)`.
- **FR-003**: The four private helpers MUST be defined in
  `custom_components/local_akuvox/services.py`; the implementation MUST NOT add
  a new service-registration module for this refactor.
- **FR-004**: `_register_schedule_services(hass)` MUST register exactly
  `SERVICE_LIST_SCHEDULES`, `SERVICE_ADD_SCHEDULE`, `SERVICE_MODIFY_SCHEDULE`,
  and `SERVICE_DELETE_SCHEDULE`.
- **FR-005**: `_register_user_services(hass)` MUST register exactly
  `SERVICE_LIST_USERS`, `SERVICE_ADD_USER`, `SERVICE_MODIFY_USER`,
  `SERVICE_DELETE_USER`, `SERVICE_ADD_USER_SCHEDULE_RELAY`, and
  `SERVICE_REMOVE_USER_SCHEDULE_RELAY`.
- **FR-006**: `_register_contact_services(hass)` MUST register exactly
  `SERVICE_LIST_CONTACTS`, `SERVICE_ADD_CONTACT`, `SERVICE_MODIFY_CONTACT`, and
  `SERVICE_DELETE_CONTACT`.
- **FR-007**: `_register_group_services(hass)` MUST register exactly
  `SERVICE_LIST_GROUPS`, `SERVICE_ADD_GROUP`, `SERVICE_MODIFY_GROUP`, and
  `SERVICE_DELETE_GROUP`.
- **FR-008**: Every moved registration MUST keep the same `hass`, `DOMAIN`,
  service constant, `entity_domain=Platform.LOCK`, schema constant, `func`
  value, and `supports_response` value it has before the refactor.
- **FR-009**: `SERVICE_LIST_SCHEDULES`, `SERVICE_LIST_USERS`,
  `SERVICE_LIST_CONTACTS`, and `SERVICE_LIST_GROUPS` MUST continue to register
  with `supports_response=SupportsResponse.ONLY`.
- **FR-010**: The refactor MUST NOT change service names, schemas, field
  validation, handler dispatch names, response formats, errors, entity domain,
  Home Assistant setup behavior, or any other public/user-visible behavior.
- **FR-011**: The implementation MUST keep all existing tests passing.
- **FR-012**: The implementation MUST make aislop stop reporting the
  `complexity/function-too-long` finding for `async_register_services`.
- **FR-013**: The implementation MUST preserve project standards, including
  type annotations, ruff compliance, mypy compliance, reuse compliance,
  pre-commit compliance, and 100% interrogate docstring coverage. New private
  helpers therefore need docstrings.

### Key Entities

- **Schedule Service Group**: Registrations for `list_schedules`,
  `add_schedule`, `modify_schedule`, and `delete_schedule`. The list service
  returns response data and must retain `SupportsResponse.ONLY`.
- **User Service Group**: Registrations for `list_users`, `add_user`,
  `modify_user`, `delete_user`, `add_user_schedule_relay`, and
  `remove_user_schedule_relay`. The list service returns response data and must
  retain `SupportsResponse.ONLY`.
- **Contact Service Group**: Registrations for `list_contacts`, `add_contact`,
  `modify_contact`, and `delete_contact`. The list service returns response data
  and must retain `SupportsResponse.ONLY`.
- **Group Service Group**: Registrations for `list_groups`, `add_group`,
  `modify_group`, and `delete_group`. The list service returns response data and
  must retain `SupportsResponse.ONLY`.
- **Registration Orchestrator**: `async_register_services(hass)`, the public
  integration entry point awaited by setup code. It coordinates the four helper
  calls without owning individual registration details.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `async_register_services` contains 80 lines or fewer after the
  implementation stage.
- **SC-002**: The aislop `complexity/function-too-long` rule no longer reports
  `custom_components/local_akuvox/services.py:async_register_services` after the
  implementation stage.
- **SC-003**: 100% of existing tests pass after the implementation stage.
- **SC-004**: All 18 existing platform entity services remain registered with
  identical schemas, handler function names, entity domain, and response
  semantics.
- **SC-005**: Interrogate docstring coverage remains 100% after the
  implementation stage.
- **SC-006**: The refactor introduces zero public API changes and zero
  user-visible behavior changes.

## Assumptions

- This stage produces only the specification. Planning, task generation,
  implementation, tests, and code changes are deferred to later stages.
- Issue #147 remains open after this spec stage. A later implementation stage
  will close it when code, tests, and quality gates prove the refactor is done.
- The helpers may group registrations by service domain even if the textual
  order changes. Any implementation must still prove Home Assistant behavior and
  tests are unchanged.
- `async_register_platform_entity_service(...)` registration calls are
  synchronous and are not awaited in the current code. Later stages may therefore
  implement the private helpers as plain `def` functions while keeping
  `async_register_services` as `async def` for compatibility with its awaited
  caller.

## Dependencies

- **GitHub Issue #147**: This specification captures the agreed refactor for the
  `services.py` aislop `complexity/function-too-long` finding.
- **Existing Service Module**: The current `services.py` schema constants and
  platform entity service registration calls are the source of truth for the
  exact schemas, functions, entity domain, and response semantics to preserve.
