<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Contract: Schedule Services

**Feature**: 003-schedule-user-services
**Component**: `lock.py` (entity service methods)

## Service: `akuvox.list_schedules`

### Input Schema: list_schedules

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| page | int | No | Page number for pagination |

**Entity targeting**: Uses HA standard entity/device/area targeting.
The service is called on an `AkuvoxLockEntity` instance.

### Behavior: list_schedules

1. HA routes the call to the targeted `AkuvoxLockEntity` instance.
2. Entity accesses device via `self.coordinator.device`.
3. Call `await device.list_schedules(page=page)`.
4. Convert each `AccessSchedule` to a dict.
5. Return `{"schedules": [list of schedule dicts]}`.

### Response Format: list_schedules

```python
{
    "schedules": [
        {
            "id": "1",
            "schedule_type": "0",
            "name": "Holiday Access",
            "week": "12345",
            "daily": None,
            "date_start": "20260101",
            "date_end": "20260115",
            "time_start": "08:00",
            "time_end": "18:00",
            "display_id": "1",
            "source_type": "1",  # "1" = local, "2" = cloud
            "mode": None,
            "sun": None,
            "mon": "1",
            "tue": "1",
            "wed": "1",
            "thur": "1",
            "fri": "1",
            "sat": None,
        }
    ]
}
```

Cloud-provisioned schedules (`source_type` of `"2"`) appear in
the list but are clearly identifiable by the `source_type` field.

### Error Handling: list_schedules

| Condition | Exception | Message |
| --------- | --------- | ------- |
| Device offline | HomeAssistantError | "Device unavailable..." |
| Auth failure | HomeAssistantError | "Authentication failed..." |
| Parse error | HomeAssistantError | "Failed to parse device response" |

---

## Service: `akuvox.add_schedule`

### Input Schema: add_schedule

| Field | Type | Req | Description |
| ----- | ---- | --- | ----------- |
| schedule_type | str | Yes | "0"/"1"/"2" |
| name | str | Yes | Display name |
| week | list | Cond | Day names; types 0, 1 |
| date_start | date | Cond | YYYY-MM-DD; type 0 |
| date_end | date | Cond | YYYY-MM-DD; type 0 |
| time_start | time | Yes | HH:MM; all types |
| time_end | time | Yes | HH:MM; all types |

**Entity targeting**: Uses HA standard entity/device/area targeting.

**UI selectors**: schedule_type uses labeled select, week uses
multi-select checkboxes, date fields use date picker, time
fields use time picker.

**Type-specific required fields**:

- Type 0 (Date Range): week + date_start + date_end + times
- Type 1 (Weekly): week + times
- Type 2 (Daily): times only

### Behavior: add_schedule

1. HA routes the call to the targeted `AkuvoxLockEntity` instance.
2. Schema validates `schedule_type` is "0", "1", or "2".
3. Schema validates field types (cv.date, cv.time, day names).
4. Entity validates type-specific required fields are present.
5. Entity converts inputs to device format:
   - Day names list → digit string (e.g. ["mon","fri"] → "15")
   - Date objects → YYYYMMDD strings
   - Time objects → HH:MM strings
6. Call `await device.add_schedule(...)` with converted values.
7. Fire event `akuvox_schedule_changed` with
   `{"action": "add", "config_entry_id": entry_id}`.

### Error Handling: add_schedule

| Condition | Exception | Message |
| --------- | --------- | ------- |
| Invalid schedule_type | vol.Invalid | Schema rejection |
| Missing schema field | vol.Invalid | Schema rejection |
| Invalid time/date/name | vol.Invalid | Schema rejection |
| Missing type field | ServiceValidationError | "Field 'X' required..." |
| Library validation | ServiceValidationError | Forwarded message |
| Device error | HomeAssistantError | "Device error..." |

---

## Service: `akuvox.modify_schedule`

### Input Schema: modify_schedule

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| id | str | Yes | Schedule ID to modify |
| schedule_type | str | No | Updated type ("0"/"1"/"2") |
| name | str | No | Updated name |
| week | list[str] | No | Updated day names (sun-sat) |
| date_start | date | No | Updated start date (YYYY-MM-DD) |
| date_end | date | No | Updated end date (YYYY-MM-DD) |
| time_start | time | No | Updated start time (HH:MM) |
| time_end | time | No | Updated end time (HH:MM) |

**Entity targeting**: Uses HA standard entity/device/area targeting.

### Behavior: modify_schedule

1. HA routes the call to the targeted `AkuvoxLockEntity` instance.
2. Validate provided fields (same rules as add).
3. **Cloud check**: Fetch current schedule list, find schedule by
   `id`, check `source_type`. If `"2"` (cloud), raise
   `ServiceValidationError` with message "Cannot modify
   cloud-provisioned schedule".
4. Call `await device.modify_schedule(id=id, ...)`.
5. Fire event `akuvox_schedule_changed` with
   `{"action": "modify", "schedule_id": id,
   "config_entry_id": entry_id}`.

### Error Handling: modify_schedule

Inherits from add_schedule, plus:

| Condition | Exception | Message |
| --------- | --------- | ------- |
| Cloud schedule | ServiceValidationError | "Cannot modify cloud schedule" |
| Schedule not found | HomeAssistantError | "Schedule not found" |

---

## Service: `akuvox.delete_schedule`

### Input Schema: delete_schedule

| Field | Type | Required | Description |
| ----- | ---- | -------- | ----------- |
| id | str | Yes | Schedule ID to delete |

**Entity targeting**: Uses HA standard entity/device/area targeting.

### Behavior: delete_schedule

1. HA routes the call to the targeted `AkuvoxLockEntity` instance.
2. **Cloud check**: Fetch current schedule list, find schedule by
   `id`, check `source_type`. If `"2"` (cloud), raise
   `ServiceValidationError`.
3. Call `await device.delete_schedule(id=id)`.
4. Fire event `akuvox_schedule_changed` with
   `{"action": "delete", "schedule_id": id,
   "config_entry_id": entry_id}`.

### Error Handling: delete_schedule

| Condition | Exception | Message |
| --------- | --------- | ------- |
| Cloud schedule | ServiceValidationError | "Cannot delete cloud schedule" |
| Schedule not found | HomeAssistantError | "Schedule not found" |
| Device error | HomeAssistantError | "Device error..." |
