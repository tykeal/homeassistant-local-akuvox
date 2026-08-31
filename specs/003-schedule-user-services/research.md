<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Research: Schedule & User Management Services

**Feature**: 003-schedule-user-services
**Date**: 2026-02-27

## Library Analysis: pylocal-akuvox Schedule & User APIs

### Schedule Management

The `pylocal-akuvox` library provides four async methods on
`AkuvoxDevice` for schedule management:

| Method | Purpose | Required Params |
| ------ | ------- | --------------- |
| `list_schedules(page=)` | List all schedules | None |
| `add_schedule(...)` | Create schedule | `schedule_type` |
| `modify_schedule(...)` | Update schedule | `id` |
| `delete_schedule(id=)` | Remove schedule | `id` |

**Schedule Types**: The `schedule_type` field accepts `"0"`, `"1"`, or
`"2"`. The library validates this before sending to the device.

**Time Fields**: The library validates these formats before sending:

- `time_start` / `time_end`: `HH:MM` (24-hour)
- `date_start` / `date_end`: `YYYYMMDD`
- `week`: Digits `0`-`6` (day codes)
- `daily`: `HH:MM-HH:MM` (time range)

### User Management

The library provides four async methods for user management:

| Method | Purpose | Required Params |
| ------ | ------- | --------------- |
| `list_users(page=)` | List all users | None |
| `add_user(...)` | Create user | `name`, `user_id`, `schedule_relay`, etc. |
| `modify_user(...)` | Update user | `id` |
| `delete_user(id=)` | Remove user | `id` |

**User Validation** (library-enforced):

- `private_pin`: 4-8 digits only (regex `^[0-9]{4,8}$`)
- `schedule_relay`: Comma-separated `<int>-<int>` pairs (for example, `1-1,2-3`)
- Empty strings are normalized to `None` before sending

### Cloud vs Local Entities

Both `AccessSchedule` and `User` models have a `source_type` field
returned by the device:

- **Locally created**: `source_type` is `"1"`
- **Cloud provisioned**: `source_type` is `"2"`

**Decision**: Cloud-provisioned entities MUST be returned in list
operations as read-only data. The integration MUST NOT allow modify
or delete operations on cloud-provisioned entities. Cloud-provisioned
schedules MUST NOT be offered as valid targets when creating local
users (their schedule IDs cannot be used in `schedule_relay`
assignments for locally created users).

**Rationale**: Cloud-provisioned entities are managed by the Akuvox
cloud platform. Attempting to modify or delete them via the local
API would either fail or create inconsistencies between the cloud
and device state. The user has confirmed this behavior requirement.

### Exception Mapping

Library exceptions map to Home Assistant service errors:

| Library Exception | HA Service Error | When |
| ----------------- | ---------------- | ---- |
| `AkuvoxValidationError` | `ServiceValidationError` | Bad input |
| `AkuvoxConnectionError` | `HomeAssistantError` | Device offline |
| `AkuvoxAuthenticationError` | `HomeAssistantError` | Auth failure |
| `AkuvoxDeviceError` | `HomeAssistantError` | Device error |
| `AkuvoxRequestError` | `HomeAssistantError` | Bad request |
| `AkuvoxParseError` | `HomeAssistantError` | Malformed response |
| `AkuvoxUnsupportedError` | `HomeAssistantError` | API unsupported |

## Home Assistant Service Registration Patterns

### Decision: Registration in async_setup

Services MUST be registered in `async_setup()` (the integration-level
setup function), NOT in `async_setup_entry()`. This follows the
current Home Assistant best practice and quality scale requirement
(`action-setup` rule), as directed by HA core developers.

**Registration method**: Use
`service.async_register_platform_entity_service()` from
`homeassistant.helpers.service`. This registers entity-level
services that are routed to methods on entity instances. Each
service call targets an entity via HA's standard entity targeting,
and HA calls the named async method on the matched entity.

**Rationale**: `async_register_platform_entity_service` is the
modern API (introduced 2025.10) that decouples service registration
from platform setup. Services are always discoverable by the
automation UI and validation engine. Entity methods have direct
access to the coordinator and device, eliminating the need for
manual config entry resolution in the handler.

**Implementation pattern** (modeled on Schlage integration):

```python
import voluptuous as vol
from homeassistant.components.lock import DOMAIN as LOCK_DOMAIN
from homeassistant.core import SupportsResponse
from homeassistant.helpers import config_validation as cv, service

from .const import DOMAIN, SERVICE_LIST_SCHEDULES, SERVICE_ADD_SCHEDULE


async def async_setup(hass, config):
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_LIST_SCHEDULES,
        entity_domain=LOCK_DOMAIN,
        schema=None,
        func=SERVICE_LIST_SCHEDULES,
        supports_response=SupportsResponse.ONLY,
    )
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_ADD_SCHEDULE,
        entity_domain=LOCK_DOMAIN,
        schema={
            vol.Required("schedule_type"): vol.In(["0", "1", "2"]),
            vol.Optional("name"): cv.string,
            # ... additional fields
        },
        func=SERVICE_ADD_SCHEDULE,
    )
    # ... repeat for all 10 services
    return True
```

Entity class implements matching methods (method name = `func`
string = service name constant):

```python
class AkuvoxLockEntity(AkuvoxEntity, LockEntity):
    async def list_schedules(self) -> ServiceResponse:
        device = self.coordinator.device
        schedules = await device.list_schedules()
        return {"schedules": [...]}

    async def add_schedule(self, schedule_type, **kwargs):
        device = self.coordinator.device
        await device.add_schedule(
            schedule_type=schedule_type, ...
        )
```

**Alternative considered**: `hass.services.async_register()` for
integration-level (non-entity) services. Rejected per HA core
developer guidance to use `async_register_platform_entity_service`
for this integration.

### Decision: Entity-Targeted Services

Services are registered as platform entity services using
`async_register_platform_entity_service`. Service calls target
entities via HA's standard entity targeting (entity_id, device_id,
area_id). HA routes the call to the matched entity instance, which
has direct access to the coordinator and device via `self`.

**Rationale**: This follows HA core developer guidance and the
modern entity service API. Entity targeting is the standard HA
pattern and integrates naturally with the automation UI, device
registry, and area assignments. Since every Akuvox device has at
least one lock entity, targeting any lock entity for a device is
sufficient to reach the device's schedule/user APIs.

**Alternative considered**: Integration-level services with manual
`config_entry_id` routing. Rejected per HA core developer guidance.

### Decision: Service YAML + Strings for UI

Services are defined in `services.yaml` with selectors for the
Developer Tools UI. String translations go in `strings.json` under
a `"services"` key.

### Decision: Event Firing for Write Operations

After successful create, modify, or delete operations, the
integration fires an `akuvox_schedule_changed` or
`akuvox_user_changed` event with the operation type and affected
entity ID. This enables automations to react to access changes.

**Rationale**: Home Assistant's event bus is the standard mechanism
for notifying automations of state changes that don't map to
entity attributes.

## Resolved Clarifications

1. **Cloud entity handling**: Cloud-provisioned schedules and users
   are read-only. They appear in list results with a `source_type`
   indicator but cannot be modified or deleted. Cloud schedules
   cannot be used when creating local user codes. (User directive)

2. **Service scoping**: Services target lock entities via HA's
   standard entity targeting (entity_id, device_id, area_id).
   HA routes calls to the matched `AkuvoxLockEntity` instance.
   (HA core developer guidance; Schlage integration pattern)

3. **PIN/card code exposure**: Plain text in service responses for
   automation consumption; masked in log output. (User directive
   from spec)

4. **Schedule-relay pair operations**: A single user can have
   multiple schedule+relay pairs in their `schedule_relay` field
   (e.g. `"1-1,2-3"`). The pylocal-akuvox library provides no
   atomic add/remove for individual pairs. Two convenience
   services (`add_user_schedule_relay`, `remove_user_schedule_relay`)
   will be implemented at the entity level by:
   - Fetching the current user via `list_users`
   - Parsing the `schedule_relay` string into individual pairs
   - Adding or removing the specified pair
   - Calling `modify_user` with the updated string
   The existing `delete_user` service handles deletion regardless
   of how many schedule+relay pairs are attached. (User directive)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| ---- | ---------- | ------ | ---------- |
| Cloud entity modify | Medium | Low | Pre-validate source_type; reject |
| Concurrent writes | Low | Medium | Document serial access |
| Pagination edge cases | Low | Low | Pass page param; empty = end |
| Validation mismatch | Low | Medium | Mirror library validation |
| Large sched/user counts | Low | Low | Pagination; no caching |
| Race on relay pair ops | Low | Medium | Fetch-then-modify pattern |

## Schedule-Relay Pair Operations

### Analysis

The `schedule_relay` field on `User` is a single string with
format `"<ScheduleID>-<RelayID>,..."` (e.g., `"1-1,2-3"`).
Validation regex: `^[0-9]+-[0-9]+(,[0-9]+-[0-9]+)*$`.

The pylocal-akuvox library provides **no atomic operations** for
individual pairs. `modify_user()` accepts an optional
`schedule_relay` parameter that **replaces the entire string**.

### Convenience Service Design

Two entity-level services handle pair manipulation:

**`add_user_schedule_relay`**: Adds a single pair to an existing
user's schedule_relay string.

1. Fetch user by `id` via `list_users()` (paginated search)
2. Parse current `schedule_relay` into list of pairs
3. Validate new pair (format, cloud schedule check)
4. Check for duplicate pair; raise error if already present
5. Append new pair; rebuild string
6. Call `modify_user(id=id, schedule_relay=updated_string)`

**`remove_user_schedule_relay`**: Removes a specific pair from
an existing user's schedule_relay string.

1. Fetch user by `id` via `list_users()` (paginated search)
2. Parse current `schedule_relay` into list of pairs
3. Find and remove the specified pair
4. If pair not found, raise error
5. If removal would leave empty string, raise error (at least
   one pair is required per library validation)
6. Call `modify_user(id=id, schedule_relay=updated_string)`

### Race Condition Consideration

Both operations use a fetch-then-modify pattern. Concurrent
modifications could cause lost updates. Mitigation: document
that callers should serialize operations targeting the same
user. The device API does not support optimistic concurrency.
