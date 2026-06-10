<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Contract: Group Services

**Feature**: 006-contact-group-services
**Component**: `lock.py` (entity service methods)

## Service: `local_akuvox.list_groups`

### Input Schema: list_groups

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| page | int | No | Page number for pagination |

**Entity targeting**: Uses HA standard entity/device/area targeting.
The service is called on an `AkuvoxLockEntity` instance.

### Behavior: list_groups

1. HA routes the call to the targeted `AkuvoxLockEntity` instance.
2. Entity accesses device via `self.coordinator.device`.
3. Call `await device.list_groups(page=page)`.
4. Convert each `Group` to a dict via `dict(vars(g))`.
5. Return `{"groups": [list of group dicts]}`.

### Response Format: list_groups

```python
{
    "groups": [
        {
            "id": "1",
            "name": "Family",
        },
        {
            "id": "2",
            "name": "Maintenance",
        }
    ]
}
```

### Error Handling: list_groups

| Condition | Exception | Message |
| --------- | --------- | ------- |
| Device offline | HomeAssistantError | "list_groups failed: ..." |
| Auth failure | HomeAssistantError | "list_groups failed: ..." |
| Parse error | HomeAssistantError | "list_groups failed: ..." |
| Validation error | ServiceValidationError | "list_groups: ..." |

---

## Service: `local_akuvox.add_group`

### Input Schema: add_group

| Field | Type | Req | Description |
| ----- | ---- | --- | ----------- |
| name | str | Yes | Group display name |

### Behavior: add_group

1. HA routes the call to the targeted entity.
2. Call `await device.add_group(name=name)`.
3. On success, fire `local_akuvox_group_changed` event with
   `action: "add"`.

### Error Handling: add_group

| Condition | Exception | Message |
| --------- | --------- | ------- |
| Missing name | vol.Invalid (schema) | voluptuous error |
| Empty name | ServiceValidationError | "add_group: ..." |
| Device error | HomeAssistantError | "add_group failed: ..." |

---

## Service: `local_akuvox.modify_group`

### Input Schema: modify_group

| Field | Type | Req | Description |
| ----- | ---- | --- | ----------- |
| id | str | Yes | Device group ID |
| name | str | Yes | New group name |

### Behavior: modify_group

1. HA routes the call to the targeted entity.
2. Call `await device.modify_group(id=id, name=name)`.
3. On success, fire `local_akuvox_group_changed` event with
   `action: "modify"` and `group_id`.

### Error Handling: modify_group

| Condition | Exception | Message |
| --------- | --------- | ------- |
| Missing ID or name | vol.Invalid (schema) | voluptuous error |
| Group not found | HomeAssistantError | "modify_group failed: ..." |
| Device error | HomeAssistantError | "modify_group failed: ..." |

---

## Service: `local_akuvox.delete_group`

### Input Schema: delete_group

| Field | Type | Req | Description |
| ----- | ---- | --- | ----------- |
| id | str | Yes | Device group ID |

### Behavior: delete_group

1. HA routes the call to the targeted entity.
2. Call `await device.delete_group(id=id)`.
3. Best-effort orphan check: call `device.list_contacts()` and log
   a warning for any contact whose `group` field references the
   deleted group.
4. On success, fire `local_akuvox_group_changed` event with
   `action: "delete"` and `group_id`.

### Error Handling: delete_group

| Condition | Exception | Message |
| --------- | --------- | ------- |
| Missing ID | vol.Invalid (schema) | voluptuous error |
| Group not found | HomeAssistantError | "delete_group failed: ..." |
| Device error | HomeAssistantError | "delete_group failed: ..." |

---

## Event: `local_akuvox_group_changed`

Fired after successful group write operations.

### Event Data

| Field | Type | Present | Description |
| ----- | ---- | ------- | ----------- |
| action | str | Always | `"add"`, `"modify"`, or `"delete"` |
| config_entry_id | str | When available | HA config entry ID |
| group_id | str | modify, delete | Target group ID |
