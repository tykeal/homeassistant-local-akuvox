<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Data Model: Service Registration Split

**Feature**: 010-service-registration-split **Date**: 2026-06-18

This feature introduces no data entity, persistence model, or runtime state.
Instead, the design artifact is a function inventory for the service
registration contracts that a later implementation stage will implement
inside `custom_components/local_akuvox/services.py`.

## Function Inventory

### async_register_services

```python
async def async_register_services(hass: HomeAssistant) -> None:
    ...
```

**Responsibility**: Public integration setup entry point for registering all
Local Akuvox lock entity services.

**Inputs**:

- `hass`: Home Assistant instance passed by `async_setup`.

**Side effects**:

- Delegates to four private helpers.
- Results in all 18 existing `local_akuvox` platform entity services being
  registered for `Platform.LOCK`.

**Returns**: `None`.

**Invariants**:

- Function name, async signature, and awaited caller contract remain unchanged.
- Contains no individual registration argument details after the split.
- Stays at or below 80 lines after implementation.

### _register_schedule_services

```python
def _register_schedule_services(hass: HomeAssistant) -> None:
    ...
```

**Responsibility**: Register schedule service operations.

**Side effects**:

- Registers four services:
  - `SERVICE_LIST_SCHEDULES` (`SupportsResponse.ONLY`)
  - `SERVICE_ADD_SCHEDULE`
  - `SERVICE_MODIFY_SCHEDULE`
  - `SERVICE_DELETE_SCHEDULE`

**Returns**: `None`.

**Invariants**:

- Every call uses `DOMAIN` and `entity_domain=Platform.LOCK`.
- Schema and `func` arguments remain identical to the live source.

### _register_user_services

```python
def _register_user_services(hass: HomeAssistant) -> None:
    ...
```

**Responsibility**: Register user and user schedule-relay service operations.

**Side effects**:

- Registers six services:
  - `SERVICE_LIST_USERS` (`SupportsResponse.ONLY`)
  - `SERVICE_ADD_USER`
  - `SERVICE_MODIFY_USER`
  - `SERVICE_DELETE_USER`
  - `SERVICE_ADD_USER_SCHEDULE_RELAY`
  - `SERVICE_REMOVE_USER_SCHEDULE_RELAY`

**Returns**: `None`.

**Invariants**:

- Every call uses `DOMAIN` and `entity_domain=Platform.LOCK`.
- Schema and `func` arguments remain identical to the live source.

### _register_contact_services

```python
def _register_contact_services(hass: HomeAssistant) -> None:
    ...
```

**Responsibility**: Register contact service operations.

**Side effects**:

- Registers four services:
  - `SERVICE_LIST_CONTACTS` (`SupportsResponse.ONLY`)
  - `SERVICE_ADD_CONTACT`
  - `SERVICE_MODIFY_CONTACT`
  - `SERVICE_DELETE_CONTACT`

**Returns**: `None`.

**Invariants**:

- Every call uses `DOMAIN` and `entity_domain=Platform.LOCK`.
- Schema and `func` arguments remain identical to the live source.

### _register_group_services

```python
def _register_group_services(hass: HomeAssistant) -> None:
    ...
```

**Responsibility**: Register group service operations.

**Side effects**:

- Registers four services:
  - `SERVICE_LIST_GROUPS` (`SupportsResponse.ONLY`)
  - `SERVICE_ADD_GROUP`
  - `SERVICE_MODIFY_GROUP`
  - `SERVICE_DELETE_GROUP`

**Returns**: `None`.

**Invariants**:

- Every call uses `DOMAIN` and `entity_domain=Platform.LOCK`.
- Schema and `func` arguments remain identical to the live source.

## State Transitions

N/A — this refactor adds no state machine. Home Assistant's service registry is
mutated in the same way as before; only the source organization of the
registration calls changes.

<!-- markdownlint-enable MD013 -->
