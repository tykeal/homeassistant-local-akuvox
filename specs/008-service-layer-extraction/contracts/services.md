<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Contract: services.py Module Interface

**Module**: `custom_components/local_akuvox/services.py` **Type**: Internal
module API (not user-facing) **Consumer**: `__init__.py`

## Public Functions

### async_register_services

```python
async def async_register_services(hass: HomeAssistant) -> None:
    """Register all platform entity services for the Akuvox integration.

    Registers 18 services bound to the lock entity domain using
    ``async_register_platform_entity_service``. Each service is
    registered with its voluptuous schema and the corresponding
    entity method name as the handler function string.

    This function is idempotent — calling it multiple times has no
    adverse effect (HA ignores duplicate service registrations).

    Args:
        hass: The Home Assistant instance.

    """
```

**Contract**:

- After calling, all 18 services are registered under `DOMAIN` with
  `entity_domain=Platform.LOCK`
- Service names match the constants defined in `const.py`
- Schemas are identical to pre-refactor definitions
- `func` parameters are method name strings matching `AkuvoxLockEntity` methods
- `supports_response` is set to `SupportsResponse.ONLY` for list services
  (`list_schedules`, `list_users`, `list_contacts`, `list_groups`)
- All other services have no `supports_response` (default behavior)

## Registered Services

<!-- markdownlint-disable MD013 -->

| Service Name                 | Schema Key Fields                                                                                            | Func                           | Response |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------ | -------- |
| `list_schedules`             | `page?`                                                                                                      | `"list_schedules"`             | ONLY     |
| `list_users`                 | `page?`                                                                                                      | `"list_users"`                 | ONLY     |
| `add_schedule`               | `schedule_type!`, `name!`, `week?`, `date_start?`, `date_end?`, `time_start!`, `time_end!`                   | `"add_schedule"`               | —        |
| `modify_schedule`            | `id!`, `schedule_type?`, `name?`, `week?`, `date_start?`, `date_end?`, `time_start?`, `time_end?`            | `"modify_schedule"`            | —        |
| `delete_schedule`            | `id!`                                                                                                        | `"delete_schedule"`            | —        |
| `add_user`                   | `name!`, `schedules!`, `lift_floor_num!`, `user_id?`, `web_relay?`, `private_pin?`, `card_code?`             | `"add_user"`                   | —        |
| `modify_user`                | `id!`, `name?`, `user_id?`, `schedule_relay?`, `lift_floor_num?`, `web_relay?`, `private_pin?`, `card_code?` | `"modify_user"`                | —        |
| `delete_user`                | `id!`                                                                                                        | `"delete_user"`                | —        |
| `add_user_schedule_relay`    | `id!`, `schedule_id!`, `relay_id!`                                                                           | `"add_user_schedule_relay"`    | —        |
| `remove_user_schedule_relay` | `id!`, `schedule_id!`, `relay_id!`                                                                           | `"remove_user_schedule_relay"` | —        |
| `list_contacts`              | `page?`                                                                                                      | `"list_contacts"`              | ONLY     |
| `add_contact`                | `name!`, `phone?`, `group?`                                                                                  | `"add_contact"`                | —        |
| `modify_contact`             | `id!`, `name?`, `phone?`, `group?`                                                                           | `"modify_contact"`             | —        |
| `delete_contact`             | `id!`                                                                                                        | `"delete_contact"`             | —        |
| `list_groups`                | `page?`                                                                                                      | `"list_groups"`                | ONLY     |
| `add_group`                  | `name!`                                                                                                      | `"add_group"`                  | —        |
| `modify_group`               | `id!`, `name!`                                                                                               | `"modify_group"`               | —        |
| `delete_group`               | `id!`                                                                                                        | `"delete_group"`               | —        |

Legend: `!` = Required, `?` = Optional

<!-- markdownlint-enable MD013 -->

## Dependencies

```python
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import service
import voluptuous as vol

from .const import (
    DOMAIN,
    SERVICE_ADD_CONTACT,
    SERVICE_ADD_GROUP,
    SERVICE_ADD_SCHEDULE,
    SERVICE_ADD_USER,
    SERVICE_ADD_USER_SCHEDULE_RELAY,
    SERVICE_DELETE_CONTACT,
    SERVICE_DELETE_GROUP,
    SERVICE_DELETE_SCHEDULE,
    SERVICE_DELETE_USER,
    SERVICE_LIST_CONTACTS,
    SERVICE_LIST_GROUPS,
    SERVICE_LIST_SCHEDULES,
    SERVICE_LIST_USERS,
    SERVICE_MODIFY_CONTACT,
    SERVICE_MODIFY_GROUP,
    SERVICE_MODIFY_SCHEDULE,
    SERVICE_MODIFY_USER,
    SERVICE_REMOVE_USER_SCHEDULE_RELAY,
    VALID_DAYS,
)
from .validation import csv_to_list
```
