<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Contract: User Services

**Feature**: 003-schedule-user-services
**Component**: `lock.py` (entity service methods)

## Service: `akuvox.list_users`

### Input Schema: list_users

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| page | int | No | Page number for pagination |

**Entity targeting**: Uses HA standard entity/device/area targeting.
The service is called on an `AkuvoxLockEntity` instance.

### Behavior: list_users

1. HA routes the call to the targeted `AkuvoxLockEntity` instance.
2. Entity accesses device via `self.coordinator.device`.
3. Call `await device.list_users(page=page)`.
4. Convert each `User` to a dict with all fields in plain text
   (including `private_pin` and `card_code`).
5. Return `{"users": [list of user dicts]}`.

### Response Format: list_users

```python
{
    "users": [
        {
            "id": "42",
            "name": "John Doe",
            "user_id": "john.doe",
            "schedule_relay": "1001-1,1002-1",
            "web_relay": None,
            "private_pin": "1234",  # Plain text
            "card_code": "ABC123",  # Plain text
            "lift_floor_num": "3",
            "user_type": None,
            "source": None,
            "source_type": "1",  # "1" = local, "2" = cloud
        }
    ]
}
```

Cloud-provisioned users (`source_type` of `"2"`) appear in the
list but are clearly identifiable by the `source_type` field.

**Logging**: When debug logging is enabled, `private_pin` and
`card_code` values MUST be masked as `"****"` in log output.

### Error Handling: list_users

| Condition | Exception | Message |
| --------- | --------- | ------- |
| Device offline | HomeAssistantError | "Device unavailable..." |
| Auth failure | HomeAssistantError | "Authentication failed..." |
| Parse error | HomeAssistantError | "Failed to parse device response" |

---

## Service: `akuvox.add_user`

### Input Schema: add_user

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| name | str | Yes | User display name |
| schedules | list[str] | Yes | Schedule display_ids (CSV also accepted) |
| lift_floor_num | str | Yes | Elevator floor access |
| user_id | str | No | User ID (auto-timestamp) |
| web_relay | str | No | Web relay assignment |
| private_pin | str | No | 4-8 digit PIN |
| card_code | str | No | Card/badge code |

**Entity targeting**: Uses HA standard entity/device/area targeting.
The entity's relay number is used to auto-build the
`schedule_relay` string.

### Behavior: add_user

1. HA routes the call to the targeted `AkuvoxLockEntity` instance.
2. Validate `schedules` is a non-empty list.
3. Validate `private_pin` is 4-8 digits if provided.
4. **Schedule validation**: Fetch schedule list, look up each
   schedule by `display_id` (not internal `id`). Verify each
   exists and is not cloud-provisioned (`source_type` != `"2"`).
5. **Build schedule_relay**: For each schedule `display_id`,
   pair it with the entity's relay number as `<display_id>-<relay_num>`,
   and join all pairs with commas (e.g. `"10-1,30-1"`).
6. Call `await device.add_user(...)` with built `schedule_relay`
   and `user_id` (numeric timestamp if not provided).
7. Fire event `akuvox_user_changed` with
   `{"action": "add", "config_entry_id": entry_id}`.

### Error Handling: add_user

| Condition | Exception | Message |
| --------- | --------- | ------- |
| No schedules | vol.Invalid (schema) | Length min 1 |
| Not found | ServiceValidationError | (schedule not found) |
| Bad PIN | ServiceValidationError | (4-8 digits) |
| Cloud ref | ServiceValidationError | (cloud schedule) |
| Lib error | ServiceValidationError | Forwarded message |
| Device err | HomeAssistantError | "Device error..." |

---

## Service: `akuvox.modify_user`

### Input Schema: modify_user

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| id | str | Yes | User device ID to modify |
| name | str | No | Updated name |
| user_id | str | No | Updated external ID |
| schedule_relay | str | No | Updated schedule-relay pairs |
| lift_floor_num | str | No | Updated floor access |
| web_relay | str | No | Updated web relay |
| private_pin | str | No | Updated PIN (4-8 digits) |
| card_code | str | No | Updated card code |

**Entity targeting**: Uses HA standard entity/device/area targeting.

### Behavior: modify_user

1. HA routes the call to the targeted `AkuvoxLockEntity` instance.
2. Validate provided fields (same rules as add).
3. **Cloud check**: Fetch current user list, find user by `id`,
   check `source_type`. If `"2"` (cloud), raise
   `ServiceValidationError` with message "Cannot modify
   cloud-provisioned user".
4. **Cloud schedule check** (if `schedule_relay` provided): Parse
   schedule IDs, verify none are cloud-provisioned.
5. Call `await device.modify_user(id=id, ...)`.
6. Fire event `akuvox_user_changed` with
   `{"action": "modify", "device_user_id": id,
   "config_entry_id": entry_id}`.

### Error Handling: modify_user

Inherits from add_user, plus:

| Condition | Exception | Message |
| --------- | --------- | ------- |
| Cloud user | ServiceValidationError | "Cannot modify cloud user" |
| User not found | HomeAssistantError | "User not found" |

---

## Service: `akuvox.delete_user`

### Input Schema: delete_user

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| id | str | Yes | User device ID to delete |

**Entity targeting**: Uses HA standard entity/device/area targeting.

### Behavior: delete_user

1. HA routes the call to the targeted `AkuvoxLockEntity` instance.
2. **Cloud check**: Fetch current user list, find user by `id`,
   check `source_type`. If `"2"` (cloud), raise
   `ServiceValidationError`.
3. Call `await device.delete_user(id=id)`.
4. Fire event `akuvox_user_changed` with
   `{"action": "delete", "device_user_id": id,
   "config_entry_id": entry_id}`.

### Error Handling: delete_user

| Condition | Exception | Message |
| --------- | --------- | ------- |
| Cloud user | ServiceValidationError | "Cannot delete cloud user" |
| User not found | HomeAssistantError | "User not found" |
| Device error | HomeAssistantError | "Device error..." |

---

## Service: `akuvox.add_user_schedule_relay`

### Input Schema: add_user_schedule_relay

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| id | str | Yes | User device ID to update |
| schedule_id | str | Yes | Schedule ID to assign |
| relay_id | str | Yes | Relay ID to assign |

**Entity targeting**: Uses HA standard entity/device/area targeting.

### Behavior: add_user_schedule_relay

1. HA routes the call to the targeted `AkuvoxLockEntity` instance.
2. Fetch current user by `id` via `device.list_users()`.
3. If user not found, raise `HomeAssistantError`.
4. **Cloud check**: If user is cloud-provisioned, raise
   `ServiceValidationError`.
5. **Cloud schedule check**: Fetch schedule list, verify the
   referenced `schedule_id` is not cloud-provisioned.
6. Parse current `schedule_relay` into list of pairs.
7. Check if `schedule_id-relay_id` pair already exists.
   If duplicate, raise `ServiceValidationError`.
8. Append `"<schedule_id>-<relay_id>"` to the pair list and rebuild
   the comma-separated `schedule_relay` string from all pairs.
9. Call `await device.modify_user(id=id,
   schedule_relay=updated_string)`.
10. Fire event `akuvox_user_changed` with
    `{"action": "add_schedule_relay", "device_user_id": id,
    "schedule_id": schedule_id, "relay_id": relay_id,
    "config_entry_id": config_entry_id}`.

### Error Handling: add_user_schedule_relay

| Condition | Exception | Message |
| --------- | --------- | ------- |
| User not found | HomeAssistantError | "User not found" |
| Cloud user | ServiceValidationError | "Cannot modify cloud user" |
| Cloud schedule ref | ServiceValidationError | "Cannot assign cloud schedule" |
| Duplicate pair | ServiceValidationError | "Pair already assigned" |
| Device error | HomeAssistantError | "Device error..." |

---

## Service: `akuvox.remove_user_schedule_relay`

### Input Schema: remove_user_schedule_relay

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| id | str | Yes | User device ID to update |
| schedule_id | str | Yes | Schedule ID to remove |
| relay_id | str | Yes | Relay ID to remove |

**Entity targeting**: Uses HA standard entity/device/area targeting.

### Behavior: remove_user_schedule_relay

1. HA routes the call to the targeted `AkuvoxLockEntity` instance.
2. Fetch current user by `id` via `device.list_users()`.
3. If user not found, raise `HomeAssistantError`.
4. **Cloud check**: If user is cloud-provisioned, raise
   `ServiceValidationError`.
5. Parse current `schedule_relay` into list of pairs.
6. Find `"<schedule_id>-<relay_id>"` in the pair list.
   If not found, raise `ServiceValidationError`.
7. Remove the pair from the list.
8. If removal would leave zero pairs, raise
   `ServiceValidationError` (at least one pair required per
   library validation).
9. Rebuild `schedule_relay` string from remaining pairs.
10. Call `await device.modify_user(id=id,
    schedule_relay=updated_string)`.
11. Fire event `akuvox_user_changed` with
    `{"action": "remove_schedule_relay", "device_user_id": id,
    "schedule_id": schedule_id, "relay_id": relay_id,
    "config_entry_id": config_entry_id}`.

### Error Handling: remove_user_schedule_relay

| Condition | Exception | Message |
| --------- | --------- | ------- |
| User not found | HomeAssistantError | "User not found" |
| Cloud user | ServiceValidationError | "Cannot modify cloud user" |
| Pair not found | ServiceValidationError | "Pair not assigned" |
| Would leave empty | ServiceValidationError | "Cannot remove last pair" |
| Device error | HomeAssistantError | "Device error..." |
