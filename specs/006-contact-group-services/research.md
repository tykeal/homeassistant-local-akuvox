<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->
<!-- markdownlint-disable MD013 -->

# Research: Contact & Group Management Services

**Feature**: 006-contact-group-services
**Date**: 2026-04-24

## Library Analysis: pylocal-akuvox Contact & Group APIs

### Contact Management

The `pylocal-akuvox` library (v0.3.0) provides four async methods
on `AkuvoxDevice` for contact management:

| Method | Purpose | Required Params |
| ------ | ------- | --------------- |
| `list_contacts(page=)` | List all contacts | None |
| `add_contact(name=, phone=, group=)` | Create contact | `name` |
| `modify_contact(id=, name=, phone=, group=)` | Update contact | `id` + at least one field |
| `delete_contact(id=)` | Remove contact(s) | `id` (str or list[str]) |

**Key observations**:

- `add_contact`: Only `name` is required. `phone` and `group` are
  optional keyword arguments.
- `modify_contact`: Requires `id` plus at least one of `name`,
  `phone`, or `group`. The library fetches the current record and
  merges changes (fetch-then-modify pattern). Raises
  `AkuvoxValidationError` if no fields are provided.
- `delete_contact`: Accepts either a single `str` ID or a
  `list[str]` of IDs for batch deletion. The library wraps them
  into the appropriate device payload.
- `list_contacts`: Returns `list[Contact]`. Each `Contact` is a
  frozen dataclass with fields: `name`, `id`, `phone`, `group`.

**Decision**: Expose all four operations as HA services, matching
the spec's 8-service design (4 contact + 4 group).

**Rationale**: The library's API surface maps 1:1 to the spec
requirements. No additional integration-level logic is needed
beyond input validation and event firing.

**Alternatives considered**: None — the library API is a direct
fit.

### Group Management

The library provides four async methods for group management:

| Method | Purpose | Required Params |
| ------ | ------- | --------------- |
| `list_groups(page=)` | List all groups | None |
| `add_group(name=)` | Create group | `name` |
| `modify_group(id=, name=)` | Rename group | `id`, `name` |
| `delete_group(id=)` | Remove group | `id` |

**Key observations**:

- `add_group`: Only `name` is required.
- `modify_group`: Requires both `id` and `name`. The library raises
  `AkuvoxValidationError` if `name` is empty.
- `delete_group`: Single ID only (no batch support), unlike
  contacts.
- `list_groups`: Returns `list[Group]`. Each `Group` is a frozen
  dataclass with fields: `name`, `id`.

**Decision**: Expose all four operations as HA services.

**Rationale**: Direct mapping to spec requirements FR-005 through
FR-008.

### Contact Model (pylocal-akuvox)

```python
@dataclass(frozen=True, kw_only=True)
class Contact:
    name: str
    id: str | None = None
    phone: str | None = None
    group: str | None = None
```

- Created from API response via `Contact.from_api_response(data)`.
- `id` is device-assigned (the API field `ID`).
- `phone` and `group` are normalised: empty strings become `None`.
- No `source_type` field — contacts have no cloud-provisioned
  distinction (unlike schedules/users). No cloud-entity protection
  is needed.

### Group Model (pylocal-akuvox)

```python
@dataclass(frozen=True, kw_only=True)
class Group:
    name: str
    id: str | None = None
```

- Created from API response via `Group.from_api_response(data)`.
- `id` is device-assigned.
- No `source_type` field — no cloud-entity protection needed.

## Exception Mapping

Library exceptions map to Home Assistant service errors. This is
identical to the existing schedule/user exception mapping:

| Library Exception | HA Service Error | When |
| ----------------- | ---------------- | ---- |
| `AkuvoxValidationError` | `ServiceValidationError` | Bad input |
| `AkuvoxConnectionError` | `HomeAssistantError` | Device offline |
| `AkuvoxAuthenticationError` | `HomeAssistantError` | Auth failure |
| `AkuvoxDeviceError` | `HomeAssistantError` | Device-side error |
| `AkuvoxRequestError` | `HomeAssistantError` | HTTP request failure |
| `AkuvoxParseError` | `HomeAssistantError` | Response parse failure |
| `AkuvoxUnsupportedError` | `HomeAssistantError` | Unsupported feature |

**Decision**: Reuse the existing two-tier catch pattern:

1. Catch `AkuvoxValidationError` → raise `ServiceValidationError`
2. Catch `AkuvoxError` (base) → raise `HomeAssistantError`

**Rationale**: Consistent with all existing service handlers.

## Service Registration Pattern

**Decision**: Use `service.async_register_platform_entity_service()`
in `async_setup()`, with each service's `func` parameter being a
string matching the method name on `AkuvoxLockEntity`.

**Rationale**: Identical to the 10 existing services. The pattern
is proven and consistent.

**Alternatives considered**: Standalone `services.py` module with
`hass.services.async_register()` — rejected because it would break
the established pattern and require manual entity resolution.

## Event Bus Integration

**Decision**: Fire events after successful write operations:

- `local_akuvox_contact_changed` for contact create/modify/delete
- `local_akuvox_group_changed` for group create/modify/delete

Event data includes:

- `action`: `"add"`, `"modify"`, or `"delete"`
- `config_entry_id`: The config entry ID (when available)
- `contact_id` / `group_id`: The target entity ID (for
  modify/delete)
- `contact_ids`: List of IDs (for batch contact delete)

**Rationale**: Follows the exact pattern of `EVENT_SCHEDULE_CHANGED`
and `EVENT_USER_CHANGED` from feature 003. Enables automations to
react to directory changes.

## No Cloud-Entity Protection Needed

**Decision**: Unlike schedules and users, contacts and groups have
no `source_type` field in their data models. There is no cloud vs
local distinction for contacts/groups on Akuvox devices.

**Rationale**: The `Contact` and `Group` models in pylocal-akuvox
do not include a `source_type` field. All contacts and groups are
locally managed. The integration does not need to check for
cloud-provisioned entities before write operations.

**Alternatives considered**: Adding a defensive check — rejected
because the library models have no mechanism to report cloud
provenance, and the device API treats all contacts/groups as
mutable.

## Batch Delete for Contacts

**Decision**: The `delete_contact` service accepts either a single
`id` (string) or a list of `ids` (list of strings). The HA service
schema uses `vol.Any(cv.string, vol.All(cv.ensure_list, [cv.string]))`
to accept both formats. The value is passed directly to
`device.delete_contact(id=...)`.

**Rationale**: The pylocal-akuvox library's `delete_contact` method
natively accepts `str | list[str]`. Exposing this in the HA service
enables efficient batch cleanup operations (spec FR-004, SC-007).

**Alternatives considered**: Single-ID-only delete with a separate
batch service — rejected for unnecessary complexity. The library
already handles both cases.

## Group Deletion Warning for Orphaned Contacts

**Decision**: When a group is deleted, log a warning if any contacts
still reference that group. This is best-effort — the device manages
referential integrity. The integration does not block the deletion.

**Rationale**: Spec edge case explicitly states "The system should
allow the deletion (this is device-managed behaviour) but log a
warning about orphaned contact-group assignments." This mirrors the
orphaned schedule-relay warning in `delete_schedule`.

## Input Validation Strategy

**Decision**: The integration validates inputs at two levels:

1. **Schema-level** (voluptuous): Type checking, required fields
2. **Library-level**: The pylocal-akuvox library validates business
   rules (empty name, etc.) and raises `AkuvoxValidationError`

The integration does NOT duplicate library validation. It maps
library validation errors to `ServiceValidationError`.

**Rationale**: Consistent with spec edge case "What happens when
service parameters contain special characters or excessively long
values? The system should validate input lengths and character sets
before sending to the device." The library handles this; the
integration propagates the errors.

## Dependency Version Bump

**Decision**: Bump pylocal-akuvox from `>=0.2.3` to `>=0.3.0` in
both `pyproject.toml` and `manifest.json`.

**Rationale**: The Contact and Group models and CRUD methods are
only available in pylocal-akuvox v0.3.0+. The spec explicitly
requires this (FR-015).

**Alternatives considered**: Conditional import with version check
— rejected for unnecessary complexity. The version constraint
ensures the API surface is available.
