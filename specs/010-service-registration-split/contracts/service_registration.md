<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Contract: services.py Service Registration Functions

**Module**: `custom_components/local_akuvox/services.py` **Type**: Internal
function organization plus existing public setup entry point **Consumers**:
`custom_components/local_akuvox/__init__.py`, Home Assistant service registry,
behavior tests

## Public Surface

### async_register_services

```python
async def async_register_services(hass: HomeAssistant) -> None:
    """Register all Akuvox lock entity services."""
```

**Contract**:

- Keeps the existing public name, async signature, and return value.
- Is still awaited by `async_setup` in `custom_components/local_akuvox/__init__.py`.
- Calls the four private helpers in `services.py`.
- Registers the same 18 `local_akuvox` lock entity services after delegation.
- Does not expose the private helper names as a public Home Assistant API.

## Private Helper Contracts

### _register_schedule_services

```python
def _register_schedule_services(hass: HomeAssistant) -> None:
    """Register Akuvox schedule entity services."""
```

Registers these platform entity services with `DOMAIN` and
`entity_domain=Platform.LOCK`:

| Service constant | Service name | Schema | Func | Supports response |
| ---------------- | ------------ | ------ | ---- | ----------------- |
| `SERVICE_LIST_SCHEDULES` | `list_schedules` | `SERVICE_LIST_SCHEDULES_SCHEMA` | `SERVICE_LIST_SCHEDULES` | `SupportsResponse.ONLY` |
| `SERVICE_ADD_SCHEDULE` | `add_schedule` | `SERVICE_ADD_SCHEDULE_SCHEMA` | `SERVICE_ADD_SCHEDULE` | unchanged default |
| `SERVICE_MODIFY_SCHEDULE` | `modify_schedule` | `SERVICE_MODIFY_SCHEDULE_SCHEMA` | `SERVICE_MODIFY_SCHEDULE` | unchanged default |
| `SERVICE_DELETE_SCHEDULE` | `delete_schedule` | `SERVICE_DELETE_SCHEDULE_SCHEMA` | `SERVICE_DELETE_SCHEDULE` | unchanged default |

### _register_user_services

```python
def _register_user_services(hass: HomeAssistant) -> None:
    """Register Akuvox user entity services."""
```

Registers these platform entity services with `DOMAIN` and
`entity_domain=Platform.LOCK`:

| Service constant | Service name | Schema | Func | Supports response |
| ---------------- | ------------ | ------ | ---- | ----------------- |
| `SERVICE_LIST_USERS` | `list_users` | `SERVICE_LIST_USERS_SCHEMA` | `SERVICE_LIST_USERS` | `SupportsResponse.ONLY` |
| `SERVICE_ADD_USER` | `add_user` | `SERVICE_ADD_USER_SCHEMA` | `SERVICE_ADD_USER` | unchanged default |
| `SERVICE_MODIFY_USER` | `modify_user` | `SERVICE_MODIFY_USER_SCHEMA` | `SERVICE_MODIFY_USER` | unchanged default |
| `SERVICE_DELETE_USER` | `delete_user` | `SERVICE_DELETE_USER_SCHEMA` | `SERVICE_DELETE_USER` | unchanged default |
| `SERVICE_ADD_USER_SCHEDULE_RELAY` | `add_user_schedule_relay` | `SERVICE_ADD_USER_SCHEDULE_RELAY_SCHEMA` | `SERVICE_ADD_USER_SCHEDULE_RELAY` | unchanged default |
| `SERVICE_REMOVE_USER_SCHEDULE_RELAY` | `remove_user_schedule_relay` | `SERVICE_REMOVE_USER_SCHEDULE_RELAY_SCHEMA` | `SERVICE_REMOVE_USER_SCHEDULE_RELAY` | unchanged default |

### _register_contact_services

```python
def _register_contact_services(hass: HomeAssistant) -> None:
    """Register Akuvox contact entity services."""
```

Registers these platform entity services with `DOMAIN` and
`entity_domain=Platform.LOCK`:

| Service constant | Service name | Schema | Func | Supports response |
| ---------------- | ------------ | ------ | ---- | ----------------- |
| `SERVICE_LIST_CONTACTS` | `list_contacts` | `SERVICE_LIST_CONTACTS_SCHEMA` | `SERVICE_LIST_CONTACTS` | `SupportsResponse.ONLY` |
| `SERVICE_ADD_CONTACT` | `add_contact` | `SERVICE_ADD_CONTACT_SCHEMA` | `SERVICE_ADD_CONTACT` | unchanged default |
| `SERVICE_MODIFY_CONTACT` | `modify_contact` | `SERVICE_MODIFY_CONTACT_SCHEMA` | `SERVICE_MODIFY_CONTACT` | unchanged default |
| `SERVICE_DELETE_CONTACT` | `delete_contact` | `SERVICE_DELETE_CONTACT_SCHEMA` | `SERVICE_DELETE_CONTACT` | unchanged default |

### _register_group_services

```python
def _register_group_services(hass: HomeAssistant) -> None:
    """Register Akuvox group entity services."""
```

Registers these platform entity services with `DOMAIN` and
`entity_domain=Platform.LOCK`:

| Service constant | Service name | Schema | Func | Supports response |
| ---------------- | ------------ | ------ | ---- | ----------------- |
| `SERVICE_LIST_GROUPS` | `list_groups` | `SERVICE_LIST_GROUPS_SCHEMA` | `SERVICE_LIST_GROUPS` | `SupportsResponse.ONLY` |
| `SERVICE_ADD_GROUP` | `add_group` | `SERVICE_ADD_GROUP_SCHEMA` | `SERVICE_ADD_GROUP` | unchanged default |
| `SERVICE_MODIFY_GROUP` | `modify_group` | `SERVICE_MODIFY_GROUP_SCHEMA` | `SERVICE_MODIFY_GROUP` | unchanged default |
| `SERVICE_DELETE_GROUP` | `delete_group` | `SERVICE_DELETE_GROUP_SCHEMA` | `SERVICE_DELETE_GROUP` | unchanged default |

## Dependencies

```python
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.helpers import service
```

The helpers use the existing `DOMAIN`, service constants, and schema constants
already defined or imported in `services.py`. No new module dependency is added.

## Compatibility

- `custom_components/local_akuvox/__init__.py` remains unchanged and continues to
  await `async_register_services(hass)`.
- `tests/test_services.py` remains behavior-focused. It asserts that all 18
  services are registered through Home Assistant setup and exercises service
  calls, but it does not assert on helper structure or registration call order.
- Existing Home Assistant automations keep using the same service names and
  fields.

<!-- markdownlint-enable MD013 -->
