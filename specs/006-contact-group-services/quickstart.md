<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Quickstart: Contact & Group Management Services

**Feature**: 006-contact-group-services
**Date**: 2026-04-24

> Archived design artifact: this feature has already been implemented
> and merged. Version references in this quickstart are historical;
> see `pyproject.toml` and
> `custom_components/local_akuvox/manifest.json` for current
> dependency requirements.

## Prerequisites

- Existing local-akuvox integration (specs 001–005 implemented)
- Python ≥3.14.2
- uv package manager
- pylocal-akuvox ≥0.3.0

## Modified Files

- `pyproject.toml` — Bump pylocal-akuvox from `>=0.2.3` to `>=0.3.0`
- `custom_components/local_akuvox/manifest.json` — Bump
  pylocal-akuvox from `>=0.2.3` to `>=0.3.0`
- `custom_components/local_akuvox/__init__.py` — Register 8 new
  services in `async_setup()`
- `custom_components/local_akuvox/const.py` — Add 8 service name
  constants and 2 event name constants
- `custom_components/local_akuvox/lock.py` — Add 8 entity service
  methods (list/add/modify/delete for contacts and groups)
- `custom_components/local_akuvox/services.yaml` — Add 8 new
  service definitions with entity target selectors
- `custom_components/local_akuvox/strings.json` — Add service and
  exception strings
- `custom_components/local_akuvox/translations/en.json` — Add
  service and exception translations
- `tests/conftest.py` — Add contact/group mock fixtures

## New Files

```text
tests/
└── test_contact_group_services.py   # Contact/group service tests
```

## No Changes Required

- `coordinator.py` — No changes; entity methods call device directly
- `entity.py` — No changes; base entity unchanged
- `config_flow.py` — No changes; no new config options

## Running Tests

```bash
# All tests
uv run pytest tests/ -x -q

# Only contact/group service tests
uv run pytest tests/test_contact_group_services.py -x -q
```

## Running Linters

```bash
uv run ruff check custom_components/ tests/
uv run ruff format --check custom_components/ tests/
uv run mypy custom_components/
```

## Key Implementation Order

1. `pyproject.toml` + `manifest.json` — Bump pylocal-akuvox to
   `>=0.3.0`
2. `const.py` — Add service name and event name constants
3. `services.yaml` — Define all 8 services with entity target
   selectors (domain: lock, integration: local_akuvox)
4. `strings.json` + `translations/en.json` — Add service and
   exception strings
5. `lock.py` — Add entity service methods matching the `func`
   string parameter names (e.g., `list_contacts`, `add_contact`,
   `list_groups`, `add_group`, etc.)
6. `__init__.py` — Add service registrations to `async_setup()`
   via `service.async_register_platform_entity_service()`
7. `tests/conftest.py` — Add contact/group mock fixtures
8. `tests/test_contact_group_services.py` — Test all 8 services

## Service Call Examples (Developer Tools)

### List Contacts

```yaml
service: local_akuvox.list_contacts
target:
  entity_id: lock.akuvox_front_door
```

### List Contacts (paginated)

```yaml
service: local_akuvox.list_contacts
target:
  entity_id: lock.akuvox_front_door
data:
  page: 2
```

### Add Contact

```yaml
service: local_akuvox.add_contact
target:
  entity_id: lock.akuvox_front_door
data:
  name: "John Doe"
  phone: "555-1234"
  group: "Family"
```

### Add Contact (name only)

```yaml
service: local_akuvox.add_contact
target:
  entity_id: lock.akuvox_front_door
data:
  name: "Jane Smith"
```

### Modify Contact

```yaml
service: local_akuvox.modify_contact
target:
  entity_id: lock.akuvox_front_door
data:
  id: "42"
  phone: "555-9999"
```

### Delete Contact (single)

```yaml
service: local_akuvox.delete_contact
target:
  entity_id: lock.akuvox_front_door
data:
  id: "42"
```

### Delete Contact (batch)

```yaml
service: local_akuvox.delete_contact
target:
  entity_id: lock.akuvox_front_door
data:
  id:
    - "42"
    - "43"
    - "44"
```

### List Groups

```yaml
service: local_akuvox.list_groups
target:
  entity_id: lock.akuvox_front_door
```

### Add Group

```yaml
service: local_akuvox.add_group
target:
  entity_id: lock.akuvox_front_door
data:
  name: "Family"
```

### Modify Group

```yaml
service: local_akuvox.modify_group
target:
  entity_id: lock.akuvox_front_door
data:
  id: "5"
  name: "Friends"
```

### Delete Group

```yaml
service: local_akuvox.delete_group
target:
  entity_id: lock.akuvox_front_door
data:
  id: "5"
```

## New Constants (const.py)

```python
# Service names (contact)
SERVICE_LIST_CONTACTS: Final = "list_contacts"
SERVICE_ADD_CONTACT: Final = "add_contact"
SERVICE_MODIFY_CONTACT: Final = "modify_contact"
SERVICE_DELETE_CONTACT: Final = "delete_contact"

# Service names (group)
SERVICE_LIST_GROUPS: Final = "list_groups"
SERVICE_ADD_GROUP: Final = "add_group"
SERVICE_MODIFY_GROUP: Final = "modify_group"
SERVICE_DELETE_GROUP: Final = "delete_group"

# Event names
EVENT_CONTACT_CHANGED: Final = "local_akuvox_contact_changed"
EVENT_GROUP_CHANGED: Final = "local_akuvox_group_changed"
```
