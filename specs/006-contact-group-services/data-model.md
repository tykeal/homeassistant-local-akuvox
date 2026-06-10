<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Data Model: Contact & Group Management Services

**Feature**: 006-contact-group-services
**Date**: 2026-04-24

## Service Response Models

These models represent the data returned by list services and
accepted by write services. They mirror the library's data classes
but are documented here for contract purposes.

### Contact (read from device)

| Field | Type | Description | Mutable |
| ----- | ---- | ----------- | ------- |
| id | str \| None | Device-assigned contact ID | No |
| name | str | Contact display name | Yes |
| phone | str \| None | Phone number | Yes |
| group | str \| None | Group assignment (group name or ID) | Yes |

**Notes**:

- `id` is device-assigned and returned in list responses. It is
  required for modify and delete operations.
- `phone` and `group` are normalised by the library: empty strings
  become `None`.
- There is no `source_type` field — all contacts are locally
  managed. No cloud-entity protection is needed.

### Group (read from device)

| Field | Type | Description | Mutable |
| ----- | ---- | ----------- | ------- |
| id | str \| None | Device-assigned group ID | No |
| name | str | Group display name | Yes |

**Notes**:

- `id` is device-assigned and returned in list responses. It is
  required for modify and delete operations.
- There is no `source_type` field — all groups are locally managed.

## Validation Rules

### Contact Input Validation

**add_contact** schema-level (vol.Invalid on failure):

| Field | Rule |
| ----- | ---- |
| name | Required; non-empty string |
| phone | Optional; string |
| group | Optional; string |

**modify_contact** schema-level:

| Field | Rule |
| ----- | ---- |
| id | Required; non-empty string |
| name | Optional; non-empty string (when provided) |
| phone | Optional; string |
| group | Optional; string |

The library enforces that at least one of `name`, `phone`, or
`group` must be provided for modify operations. This is mapped to
`ServiceValidationError` if violated.

**delete_contact** schema-level:

| Field | Rule |
| ----- | ---- |
| id | Required; single string or list of strings |

The schema accepts both `"42"` and `["42", "43"]` via
`vol.Any(cv.string, vol.All(cv.ensure_list, [cv.string]))`.

### Group Input Validation

**add_group** schema-level:

| Field | Rule |
| ----- | ---- |
| name | Required; non-empty string |

**modify_group** schema-level:

| Field | Rule |
| ----- | ---- |
| id | Required; non-empty string |
| name | Required; non-empty string |

**delete_group** schema-level:

| Field | Rule |
| ----- | ---- |
| id | Required; non-empty string |

## Relationships

```text
ConfigEntry (1)
  │
  ├── AkuvoxDevice (1) ─── pylocal-akuvox client instance
  │
  ├── DataUpdateCoordinator (1) ─── existing, unchanged
  │     └── AkuvoxCoordinatorData (unchanged)
  │
  ├── LockEntity (1..N) ─── existing, unchanged
  │
  └── Services (8 new + 10 existing = 18 total)
        │
        │  ── Existing (feature 003) ──
        ├── list_schedules ─────────→ device.list_schedules()
        ├── add_schedule ───────────→ device.add_schedule()
        ├── modify_schedule ────────→ device.modify_schedule()
        ├── delete_schedule ────────→ device.delete_schedule()
        ├── list_users ─────────────→ device.list_users()
        ├── add_user ───────────────→ device.add_user()
        ├── modify_user ────────────→ device.modify_user()
        ├── delete_user ────────────→ device.delete_user()
        ├── add_user_schedule_relay → fetch + modify_user()
        ├── remove_user_schedule_relay → fetch + modify_user()
        │
        │  ── New (feature 006) ──
        ├── list_contacts ──────────→ device.list_contacts()
        ├── add_contact ────────────→ device.add_contact()
        ├── modify_contact ─────────→ device.modify_contact()
        ├── delete_contact ─────────→ device.delete_contact()
        ├── list_groups ────────────→ device.list_groups()
        ├── add_group ──────────────→ device.add_group()
        ├── modify_group ───────────→ device.modify_group()
        └── delete_group ───────────→ device.delete_group()

Contact
  └── references Group by group name/ID

Events (fired after write operations)
  ├── local_akuvox_contact_changed {action, config_entry_id, contact_id?}
  └── local_akuvox_group_changed {action, config_entry_id, group_id?}
```

## State Transitions

### Service Call Flow

```text
Service Call Received (HA routes to AkuvoxLockEntity)
  │
  ├── Entity accesses device via self.coordinator.device
  │
  ├── Validate input parameters → ServiceValidationError if invalid
  │
  ├── Call library method on device
  │   ├── Success → return result (list) or fire event (write)
  │   └── Exception → map to HomeAssistantError or ServiceValidationError
  │
  └── [For write operations]
      └── Fire event: local_akuvox_{contact|group}_changed
```

**Note**: Unlike schedule/user services, there is no cloud-entity
protection step. Contacts and groups have no `source_type` field
and are always mutable.

### Delete Group with Orphan Check

```text
delete_group called with group_id
  │
  ├── Call device.delete_group(id=group_id)
  │   ├── Success → continue
  │   └── Exception → map to error, stop
  │
  ├── Best-effort orphan check:
  │   ├── Call device.list_contacts() (no pagination, best-effort)
  │   ├── For each contact: check if contact.group references
  │   │   the deleted group
  │   └── Log warning for each orphaned contact
  │
  └── Fire event: local_akuvox_group_changed {action: "delete"}
```

### Batch Delete Contact Flow

```text
delete_contact called with id (str or list[str])
  │
  ├── Normalize: if str, pass as-is; if list, pass as list
  │
  ├── Call device.delete_contact(id=normalized_id)
  │   ├── Success → continue
  │   └── Exception → map to error, stop
  │
  └── Fire event: local_akuvox_contact_changed
      {action: "delete", contact_id or contact_ids}
```
