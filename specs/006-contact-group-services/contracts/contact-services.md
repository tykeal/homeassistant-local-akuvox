<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Contract: Contact Services

**Feature**: 006-contact-group-services
**Component**: `lock.py` (entity service methods)

## Service: `local_akuvox.list_contacts`

### Input Schema: list_contacts

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| page | int | No | Page number for pagination |

**Entity targeting**: Uses HA standard entity/device/area targeting.
The service is called on an `AkuvoxLockEntity` instance.

### Behavior: list_contacts

1. HA routes the call to the targeted `AkuvoxLockEntity` instance.
2. Entity accesses device via `self.coordinator.device`.
3. Call `await device.list_contacts(page=page)`.
4. Convert each `Contact` to a dict via `dict(vars(c))`.
5. Return `{"contacts": [list of contact dicts]}`.

### Response Format: list_contacts

```python
{
    "contacts": [
        {
            "id": "1",
            "name": "John Doe",
            "phone": "555-1234",
            "group": "Family",
        },
        {
            "id": "2",
            "name": "Jane Smith",
            "phone": None,
            "group": None,
        },
    ]
}
```

### Error Handling: list_contacts

| Condition | Exception | Message |
| --------- | --------- | ------- |
| Device offline | HomeAssistantError | "list_contacts failed: ..." |
| Auth failure | HomeAssistantError | "list_contacts failed: ..." |
| Parse error | HomeAssistantError | "list_contacts failed: ..." |
| Validation error | ServiceValidationError | "list_contacts: ..." |

---

## Service: `local_akuvox.add_contact`

### Input Schema: add_contact

| Field | Type | Req | Description |
| ----- | ---- | --- | ----------- |
| name | str | Yes | Contact display name |
| phone | str | No | Phone number |
| group | str | No | Group assignment |

### Behavior: add_contact

1. HA routes the call to the targeted entity.
2. Call `await device.add_contact(name=, phone=, group=)`.
3. On success, fire `local_akuvox_contact_changed` event with
   `action: "add"`.

### Error Handling: add_contact

| Condition | Exception | Message |
| --------- | --------- | ------- |
| Missing name | vol.Invalid (schema) | voluptuous error |
| Empty name | ServiceValidationError | "add_contact: ..." |
| Device error | HomeAssistantError | "add_contact failed: ..." |

---

## Service: `local_akuvox.modify_contact`

### Input Schema: modify_contact

| Field | Type | Req | Description |
| ----- | ---- | --- | ----------- |
| id | str | Yes | Device contact ID |
| name | str | No | Updated display name |
| phone | str | No | Updated phone number |
| group | str | No | Updated group assignment |

At least one of `name`, `phone`, or `group` must be provided
(enforced by the library, not the schema).

### Behavior: modify_contact

1. HA routes the call to the targeted entity.
2. Call `await device.modify_contact(id=, name=, phone=, group=)`.
3. Library fetches the current record, merges changes, and sends
   the updated record to the device.
4. On success, fire `local_akuvox_contact_changed` event with
   `action: "modify"` and `contact_id`.

### Error Handling: modify_contact

| Condition | Exception | Message |
| --------- | --------- | ------- |
| Missing ID | vol.Invalid (schema) | voluptuous error |
| No fields to update | ServiceValidationError | "modify_contact: ..." |
| Contact not found | HomeAssistantError | "modify_contact failed: ..." |
| Device error | HomeAssistantError | "modify_contact failed: ..." |

---

## Service: `local_akuvox.delete_contact`

### Input Schema: delete_contact

| Field | Type | Req | Description |
| ----- | ---- | --- | ----------- |
| id | str \| list[str] | Yes | Contact ID(s) to delete |

Accepts either a single string or a list of strings for batch
deletion.

### Behavior: delete_contact

1. HA routes the call to the targeted entity.
2. Call `await device.delete_contact(id=id_value)`.
3. The library normalizes the input (single or list) and sends
   the appropriate payload to the device.
4. On success, fire `local_akuvox_contact_changed` event with
   `action: "delete"` and either `contact_id` (single) or
   `contact_ids` (batch).

### Error Handling: delete_contact

| Condition | Exception | Message |
| --------- | --------- | ------- |
| Missing ID | vol.Invalid (schema) | voluptuous error |
| Contact not found | HomeAssistantError | "delete_contact failed: ..." |
| Device error | HomeAssistantError | "delete_contact failed: ..." |

---

## Event: `local_akuvox_contact_changed`

Fired after successful contact write operations.

### Event Data

| Field | Type | Present | Description |
| ----- | ---- | ------- | ----------- |
| action | str | Always | `"add"`, `"modify"`, or `"delete"` |
| config_entry_id | str | When available | HA config entry ID |
| contact_id | str | modify, single delete | Target contact ID |
| contact_ids | list[str] | batch delete | List of deleted IDs |
