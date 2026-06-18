<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Research: Service Registration Split

**Feature**: 010-service-registration-split **Date**: 2026-06-18
**Status**: Complete

## Research Topics

### 1. Registration Grouping Boundary

**Context**: `async_register_services` currently performs 18 direct calls to
`service.async_register_platform_entity_service(...)` in
`custom_components/local_akuvox/services.py`. The calls all use `DOMAIN`,
`entity_domain=Platform.LOCK`, a service-specific schema constant, and a matching
`func` name. The four `list_*` registrations additionally use
`supports_response=SupportsResponse.ONLY`.

**Decision**: Split the registrations into four private helpers by service
domain:

- `_register_schedule_services(hass)` registers:
  - `SERVICE_LIST_SCHEDULES` with `SERVICE_LIST_SCHEDULES_SCHEMA` and
    `SupportsResponse.ONLY`
  - `SERVICE_ADD_SCHEDULE` with `SERVICE_ADD_SCHEDULE_SCHEMA`
  - `SERVICE_MODIFY_SCHEDULE` with `SERVICE_MODIFY_SCHEDULE_SCHEMA`
  - `SERVICE_DELETE_SCHEDULE` with `SERVICE_DELETE_SCHEDULE_SCHEMA`
- `_register_user_services(hass)` registers:
  - `SERVICE_LIST_USERS` with `SERVICE_LIST_USERS_SCHEMA` and
    `SupportsResponse.ONLY`
  - `SERVICE_ADD_USER` with `SERVICE_ADD_USER_SCHEMA`
  - `SERVICE_MODIFY_USER` with `SERVICE_MODIFY_USER_SCHEMA`
  - `SERVICE_DELETE_USER` with `SERVICE_DELETE_USER_SCHEMA`
  - `SERVICE_ADD_USER_SCHEDULE_RELAY` with
    `SERVICE_ADD_USER_SCHEDULE_RELAY_SCHEMA`
  - `SERVICE_REMOVE_USER_SCHEDULE_RELAY` with
    `SERVICE_REMOVE_USER_SCHEDULE_RELAY_SCHEMA`
- `_register_contact_services(hass)` registers:
  - `SERVICE_LIST_CONTACTS` with `SERVICE_LIST_CONTACTS_SCHEMA` and
    `SupportsResponse.ONLY`
  - `SERVICE_ADD_CONTACT` with `SERVICE_ADD_CONTACT_SCHEMA`
  - `SERVICE_MODIFY_CONTACT` with `SERVICE_MODIFY_CONTACT_SCHEMA`
  - `SERVICE_DELETE_CONTACT` with `SERVICE_DELETE_CONTACT_SCHEMA`
- `_register_group_services(hass)` registers:
  - `SERVICE_LIST_GROUPS` with `SERVICE_LIST_GROUPS_SCHEMA` and
    `SupportsResponse.ONLY`
  - `SERVICE_ADD_GROUP` with `SERVICE_ADD_GROUP_SCHEMA`
  - `SERVICE_MODIFY_GROUP` with `SERVICE_MODIFY_GROUP_SCHEMA`
  - `SERVICE_DELETE_GROUP` with `SERVICE_DELETE_GROUP_SCHEMA`

**Rationale**: Domain grouping matches the Stage 1 specification, reduces the
public orchestrator to four helper calls, and keeps each helper cohesive enough
to inspect a related service set without scanning the full 18-call sequence.

**Alternatives considered**:

- Split by current source order chunks — rejected because it would reduce length
  but not improve maintainability by domain.
- One helper per registration — rejected because it creates 18 tiny functions and
  spreads related details too far apart.
- A data-driven registration table plus a loop — rejected for this stage because
  it increases indirection, makes `supports_response` exceptions less explicit,
  and goes beyond the issue/spec preference for four named domain helpers.

### 2. Helper Sync vs. Async Shape

**Context**: The live function calls
`service.async_register_platform_entity_service(...)` directly and does not await
those calls. `custom_components/local_akuvox/__init__.py` awaits only
`async_register_services(hass)` from `async_setup`.

**Decision**: Implement the private helpers as synchronous functions with this
shape:

```python
def _register_schedule_services(hass: HomeAssistant) -> None: ...
def _register_user_services(hass: HomeAssistant) -> None: ...
def _register_contact_services(hass: HomeAssistant) -> None: ...
def _register_group_services(hass: HomeAssistant) -> None: ...
```

Keep the public orchestrator as:

```python
async def async_register_services(hass: HomeAssistant) -> None: ...
```

**Rationale**: The Home Assistant registration helper is synchronous in the live
code path, so synchronous private helpers accurately model the side effect and
avoid unnecessary async functions. The public function remains async to preserve
the awaited setup signature and avoid any caller change.

**Alternatives considered**:

- Make all helpers `async def` — rejected because there is nothing to await, and
  it would add misleading coroutine machinery.
- Make `async_register_services` synchronous — rejected because `__init__.py`
  awaits it and the spec requires preserving that public contract.

### 3. Caller and Test Impact

**Context**: `custom_components/local_akuvox/__init__.py` imports
`async_register_services` and awaits it in `async_setup`. No other production
caller was found. `tests/test_services.py` contains
`test_services_registered_on_setup`, which loads the integration and asserts
that the 18 service names exist through `hass.services.has_service`. The service
behavior tests call registered services through Home Assistant. No test patches
or asserts on `service.async_register_platform_entity_service`, the internal
structure of `async_register_services`, helper existence, or registration call
order.

**Decision**: No caller or test changes are needed for the helper split. The
implementation should keep existing tests untouched unless a later discovery
contradicts this source review.

**Rationale**: Tests exercise observable registration and service behavior rather
than the private implementation structure. A mechanical helper split that keeps
all 18 calls and their arguments identical should be transparent to the test
suite and to automations.

**Alternatives considered**:

- Add tests that assert helper names — rejected because private helper structure
  is an implementation detail already specified by the feature docs.
- Mock `async_register_platform_entity_service` to assert call order — rejected
  because existing behavior-level setup tests already verify the public outcome,
  and call order is not a user-visible contract.

### 4. Behavior Preservation Strategy

**Context**: Every moved registration must keep the same `hass`, `DOMAIN`,
service constant, `entity_domain=Platform.LOCK`, schema constant, `func`, and
`supports_response` value from the live `services.py` source.

**Decision**: Move each registration block mechanically into its domain helper.
Do not alter schemas, constants, handler names, validation fields, event names,
response formatting, or Home Assistant service dispatch behavior.

**Rationale**: The only intended value is clearing the aislop function-length
finding and making registration maintenance easier. Any functional change would
violate the pure-refactor scope.

**Alternatives considered**:

- Rename helper-visible constants or schemas while moving — rejected as scope
  creep and behavior risk.
- Create a new service registration module — rejected because the spec requires
  all helpers and the orchestrator to stay inside `services.py`.

## Summary of Decisions

| Item | Decision |
| ---- | -------- |
| Helper count | Four private helpers |
| Helper signatures | `_register_<group>_services(hass: HomeAssistant) -> None` |
| Helper implementation | Synchronous `def`; registration calls are not awaited |
| Public orchestrator | Keep `async_register_services(hass: HomeAssistant) -> None` |
| Caller impact | `__init__.py` unchanged |
| Test impact | Existing `tests/test_services.py` stays untouched |
| Response support | Only the four `SERVICE_LIST_*` registrations use `SupportsResponse.ONLY` |
| New module | None; helpers remain in `services.py` |

<!-- markdownlint-enable MD013 -->
