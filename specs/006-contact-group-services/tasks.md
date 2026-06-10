<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->
<!-- markdownlint-disable MD013 -->

# Tasks: Contact & Group Management Services

**Input**: Design documents from `/specs/006-contact-group-services/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/
**Worktree**: `../worktrees/local-akuvox/006-contact-group-services`

**Tests**: TDD is mandatory — write tests first, verify they fail, then implement.

**Organization**: Tasks are grouped by user story to enable independent
implementation and testing of each story. Contact and group services
follow the identical pattern established by schedule/user services
(feature 003).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Integration source**: `custom_components/local_akuvox/`
- **Tests**: `tests/`
- **Project root**: `pyproject.toml`, `custom_components/local_akuvox/manifest.json`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependency bump and constant definitions required by all
services

- [X] T001 Bump pylocal-akuvox from `>=0.2.3` to `>=0.3.0` in pyproject.toml (line ~15, project dependencies)
- [X] T002 Bump pylocal-akuvox from `>=0.2.3` to `>=0.3.0` in custom_components/local_akuvox/manifest.json (requirements array)
- [X] T003 Run `uv lock` to regenerate uv.lock after dependency bump
- [X] T004 Add 8 service name constants and 2 event name constants to custom_components/local_akuvox/const.py (SERVICE_LIST_CONTACTS, SERVICE_ADD_CONTACT, SERVICE_MODIFY_CONTACT, SERVICE_DELETE_CONTACT, SERVICE_LIST_GROUPS, SERVICE_ADD_GROUP, SERVICE_MODIFY_GROUP, SERVICE_DELETE_GROUP, EVENT_CONTACT_CHANGED, EVENT_GROUP_CHANGED)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Service definitions, UI strings, and test fixtures that
MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is
complete

- [X] T005 [P] Add 8 service definitions (list_contacts, add_contact, modify_contact, delete_contact, list_groups, add_group, modify_group, delete_group) with entity target selectors in custom_components/local_akuvox/services.yaml following existing list_schedules/add_schedule pattern
- [X] T006 [P] Add service name/description strings for all 8 services and exception translation keys in custom_components/local_akuvox/strings.json under the `services` key
- [X] T007 [P] Add service name/description translations for all 8 services and exception translations in custom_components/local_akuvox/translations/en.json matching strings.json keys
- [X] T008 [P] Add contact/group mock fixtures to tests/conftest.py: mock_contact_list (list[Contact]), mock_group_list (list[Group]) using pylocal_akuvox Contact and Group dataclasses, following existing mock_schedule_list/mock_user_list pattern

**Checkpoint**: Foundation ready — service YAML, strings, translations,
and test fixtures in place. User story implementation can now begin.

---

## Phase 3: User Story 1 — List Contacts (Priority: P1) 🎯 MVP

**Goal**: Retrieve all contacts from the device, with optional
pagination, returning contact details (id, name, phone, group).

**Independent Test**: Call `local_akuvox.list_contacts` targeting a lock
entity and verify the returned dict matches device contacts. Test empty
list, pagination, and device-offline error.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before
> implementation**

- [X] T009 [P] [US1] Write test `test_list_contacts_returns_all_contacts` in tests/test_contact_group_services.py — mock device.list_contacts() returning mock_contact_list, call service, assert response contains all contacts with correct fields (id, name, phone, group)
- [X] T010 [P] [US1] Write test `test_list_contacts_empty` in tests/test_contact_group_services.py — mock device.list_contacts() returning empty list, assert response `{"contacts": []}`
- [X] T011 [P] [US1] Write test `test_list_contacts_with_page` in tests/test_contact_group_services.py — call service with `page: 2`, assert device.list_contacts called with `page=2`
- [X] T012 [P] [US1] Write test `test_list_contacts_device_offline` in tests/test_contact_group_services.py — mock device.list_contacts() raising AkuvoxConnectionError, assert HomeAssistantError raised

### Implementation for User Story 1

- [X] T013 [US1] Implement `async list_contacts(self, call)` method on AkuvoxLockEntity in custom_components/local_akuvox/lock.py — extract optional `page` param, call `await self.coordinator.device.list_contacts(page=page)`, convert Contact objects to dicts, return `{"contacts": [...]}`, with two-tier exception mapping (AkuvoxValidationError → ServiceValidationError, AkuvoxError → HomeAssistantError)
- [X] T014 [US1] Register list_contacts service in `custom_components/local_akuvox/__init__.py` via `service.async_register_platform_entity_service()` with optional `page` vol.Schema and `func=SERVICE_LIST_CONTACTS`

**Checkpoint**: `local_akuvox.list_contacts` is callable and returns
device contacts. All US1 tests pass green.

---

## Phase 4: User Story 2 — List Groups (Priority: P1) 🎯 MVP

**Goal**: Retrieve all groups from the device, with optional pagination,
returning group details (id, name).

**Independent Test**: Call `local_akuvox.list_groups` targeting a lock
entity and verify the returned dict matches device groups. Test empty
list, pagination, and device-offline error.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before
> implementation**

- [X] T015 [P] [US2] Write test `test_list_groups_returns_all_groups` in tests/test_contact_group_services.py — mock device.list_groups() returning mock_group_list, call service, assert response contains all groups with correct fields (id, name)
- [X] T016 [P] [US2] Write test `test_list_groups_empty` in tests/test_contact_group_services.py — mock device.list_groups() returning empty list, assert response `{"groups": []}`
- [X] T017 [P] [US2] Write test `test_list_groups_with_page` in tests/test_contact_group_services.py — call service with `page: 3`, assert device.list_groups called with `page=3`
- [X] T018 [P] [US2] Write test `test_list_groups_device_offline` in tests/test_contact_group_services.py — mock device.list_groups() raising AkuvoxConnectionError, assert HomeAssistantError raised

### Implementation for User Story 2

- [X] T019 [US2] Implement `async list_groups(self, call)` method on AkuvoxLockEntity in custom_components/local_akuvox/lock.py — extract optional `page` param, call `await self.coordinator.device.list_groups(page=page)`, convert Group objects to dicts, return `{"groups": [...]}`, with two-tier exception mapping
- [X] T020 [US2] Register list_groups service in `custom_components/local_akuvox/__init__.py` via `service.async_register_platform_entity_service()` with optional `page` vol.Schema and `func=SERVICE_LIST_GROUPS`

**Checkpoint**: Both list services (`list_contacts`, `list_groups`) are
callable. All US1 + US2 tests pass green.

---

## Phase 5: User Story 3 — Add Contact (Priority: P2)

**Goal**: Create a new contact on the device with a required name and
optional phone/group, firing a `local_akuvox_contact_changed` event on
success.

**Independent Test**: Call `local_akuvox.add_contact` with valid params,
verify device.add_contact was called, verify event fired. Test missing
name validation.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before
> implementation**

- [X] T021 [P] [US3] Write test `test_add_contact_with_all_fields` in tests/test_contact_group_services.py — call service with name+phone+group, assert device.add_contact called with correct kwargs, assert `local_akuvox_contact_changed` event fired with `action: "add"`
- [X] T022 [P] [US3] Write test `test_add_contact_name_only` in tests/test_contact_group_services.py — call service with name only, assert device.add_contact called with name and phone=None, group=None
- [X] T023 [P] [US3] Write test `test_add_contact_missing_name` in tests/test_contact_group_services.py — call service without name, assert vol.Invalid or ServiceValidationError raised
- [X] T024 [P] [US3] Write test `test_add_contact_device_error` in tests/test_contact_group_services.py — mock device.add_contact() raising AkuvoxDeviceError, assert HomeAssistantError raised and no event fired

### Implementation for User Story 3

- [X] T025 [US3] Implement `async add_contact(self, call)` method on AkuvoxLockEntity in custom_components/local_akuvox/lock.py — extract name (required), phone/group (optional), call `await self.coordinator.device.add_contact(name=, phone=, group=)`, fire EVENT_CONTACT_CHANGED with `action: "add"` and config_entry_id, with two-tier exception mapping
- [X] T026 [US3] Register add_contact service in `custom_components/local_akuvox/__init__.py` with vol.Schema requiring `name` (cv.string) and optional `phone`/`group` (cv.string), `func=SERVICE_ADD_CONTACT`

**Checkpoint**: Contacts can be listed and created. All US1–US3 tests
pass green.

---

## Phase 6: User Story 4 — Add Group (Priority: P2)

**Goal**: Create a new group on the device with a required name, firing
a `local_akuvox_group_changed` event on success.

**Independent Test**: Call `local_akuvox.add_group` with a valid name,
verify device.add_group was called, verify event fired. Test missing
name validation.

### Tests for User Story 4 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before
> implementation**

- [X] T027 [P] [US4] Write test `test_add_group_success` in tests/test_contact_group_services.py — call service with name, assert device.add_group called with correct name, assert `local_akuvox_group_changed` event fired with `action: "add"`
- [X] T028 [P] [US4] Write test `test_add_group_missing_name` in tests/test_contact_group_services.py — call service without name, assert vol.Invalid or ServiceValidationError raised
- [X] T029 [P] [US4] Write test `test_add_group_device_error` in tests/test_contact_group_services.py — mock device.add_group() raising AkuvoxDeviceError, assert HomeAssistantError raised and no event fired

### Implementation for User Story 4

- [X] T030 [US4] Implement `async add_group(self, call)` method on AkuvoxLockEntity in custom_components/local_akuvox/lock.py — extract name (required), call `await self.coordinator.device.add_group(name=name)`, fire EVENT_GROUP_CHANGED with `action: "add"` and config_entry_id, with two-tier exception mapping
- [X] T031 [US4] Register add_group service in `custom_components/local_akuvox/__init__.py` with vol.Schema requiring `name` (cv.string), `func=SERVICE_ADD_GROUP`

**Checkpoint**: Groups can be listed and created. All US1–US4 tests pass
green.

---

## Phase 7: User Story 5 — Modify Contact (Priority: P2)

**Goal**: Update an existing contact's fields (name, phone, group) by
ID, firing a `local_akuvox_contact_changed` event on success.

**Independent Test**: Call `local_akuvox.modify_contact` with a valid ID
and updated fields, verify device.modify_contact was called, verify
event fired. Test missing ID and not-found errors.

### Tests for User Story 5 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before
> implementation**

- [X] T032 [P] [US5] Write test `test_modify_contact_success` in tests/test_contact_group_services.py — call service with id and updated phone, assert device.modify_contact called with correct kwargs, assert `local_akuvox_contact_changed` event fired with `action: "modify"` and `contact_id`
- [X] T033 [P] [US5] Write test `test_modify_contact_not_found` in tests/test_contact_group_services.py — mock device.modify_contact() raising AkuvoxDeviceError (contact not found), assert HomeAssistantError raised
- [X] T034 [P] [US5] Write test `test_modify_contact_no_fields` in tests/test_contact_group_services.py — mock device.modify_contact() raising AkuvoxValidationError (no fields), assert ServiceValidationError raised
- [X] T035 [P] [US5] Write test `test_modify_contact_missing_id` in tests/test_contact_group_services.py — call service without id, assert vol.Invalid raised

### Implementation for User Story 5

- [X] T036 [US5] Implement `async modify_contact(self, call)` method on AkuvoxLockEntity in custom_components/local_akuvox/lock.py — extract id (required), name/phone/group (optional), call `await self.coordinator.device.modify_contact(id=, name=, phone=, group=)`, fire EVENT_CONTACT_CHANGED with `action: "modify"`, contact_id, and config_entry_id, with two-tier exception mapping
- [X] T037 [US5] Register modify_contact service in `custom_components/local_akuvox/__init__.py` with vol.Schema requiring `id` (cv.string), optional `name`/`phone`/`group` (cv.string), `func=SERVICE_MODIFY_CONTACT`

**Checkpoint**: Contacts support full read + create + update. All
US1–US5 tests pass green.

---

## Phase 8: User Story 6 — Modify Group (Priority: P2)

**Goal**: Rename an existing group by ID, firing a
`local_akuvox_group_changed` event on success.

**Independent Test**: Call `local_akuvox.modify_group` with a valid ID
and new name, verify device.modify_group was called, verify event fired.
Test not-found and missing-name errors.

### Tests for User Story 6 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before
> implementation**

- [X] T038 [P] [US6] Write test `test_modify_group_success` in tests/test_contact_group_services.py — call service with id and new name, assert device.modify_group called correctly, assert `local_akuvox_group_changed` event fired with `action: "modify"` and `group_id`
- [X] T039 [P] [US6] Write test `test_modify_group_not_found` in tests/test_contact_group_services.py — mock device.modify_group() raising AkuvoxDeviceError, assert HomeAssistantError raised
- [X] T040 [P] [US6] Write test `test_modify_group_missing_id` in tests/test_contact_group_services.py — call service without id, assert vol.Invalid raised
- [X] T041 [P] [US6] Write test `test_modify_group_missing_name` in tests/test_contact_group_services.py — call service without name, assert vol.Invalid raised

### Implementation for User Story 6

- [X] T042 [US6] Implement `async modify_group(self, call)` method on AkuvoxLockEntity in custom_components/local_akuvox/lock.py — extract id and name (both required), call `await self.coordinator.device.modify_group(id=id, name=name)`, fire EVENT_GROUP_CHANGED with `action: "modify"`, group_id, and config_entry_id, with two-tier exception mapping
- [X] T043 [US6] Register modify_group service in `custom_components/local_akuvox/__init__.py` with vol.Schema requiring `id` (cv.string) and `name` (cv.string), `func=SERVICE_MODIFY_GROUP`

**Checkpoint**: Groups support full read + create + update. All US1–US6
tests pass green.

---

## Phase 9: User Story 7 — Delete Contact (Priority: P3)

**Goal**: Delete one or more contacts by ID (single string or list of
strings for batch), firing a `local_akuvox_contact_changed` event on
success.

**Independent Test**: Call `local_akuvox.delete_contact` with a single
ID (and separately with a list of IDs), verify device.delete_contact was
called, verify event fired. Test not-found error.

### Tests for User Story 7 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before
> implementation**

- [X] T044 [P] [US7] Write test `test_delete_contact_single` in tests/test_contact_group_services.py — call service with single id string, assert device.delete_contact called with `id="42"`, assert `local_akuvox_contact_changed` event fired with `action: "delete"` and `contact_id`
- [X] T045 [P] [US7] Write test `test_delete_contact_batch` in tests/test_contact_group_services.py — call service with list of ids `["42", "43", "44"]`, assert device.delete_contact called with `id=["42", "43", "44"]`, assert event fired with `contact_ids`
- [X] T046 [P] [US7] Write test `test_delete_contact_not_found` in tests/test_contact_group_services.py — mock device.delete_contact() raising AkuvoxDeviceError, assert HomeAssistantError raised
- [X] T047 [P] [US7] Write test `test_delete_contact_missing_id` in tests/test_contact_group_services.py — call service without id, assert vol.Invalid raised

### Implementation for User Story 7

- [X] T048 [US7] Implement `async delete_contact(self, call)` method on AkuvoxLockEntity in custom_components/local_akuvox/lock.py — extract id (str or list[str]), call `await self.coordinator.device.delete_contact(id=id_value)`, fire EVENT_CONTACT_CHANGED with `action: "delete"` and contact_id (single) or contact_ids (batch) plus config_entry_id, with two-tier exception mapping
- [X] T049 [US7] Register delete_contact service in `custom_components/local_akuvox/__init__.py` with vol.Schema requiring `id` via `vol.Any(cv.string, vol.All(cv.ensure_list, [cv.string]))`, `func=SERVICE_DELETE_CONTACT`

**Checkpoint**: Contact CRUD is complete (list + add + modify + delete).
All US1–US7 tests pass green.

---

## Phase 10: User Story 8 — Delete Group (Priority: P3)

**Goal**: Delete a group by ID, with best-effort orphan warning for
contacts still referencing the group, firing a
`local_akuvox_group_changed` event on success.

**Independent Test**: Call `local_akuvox.delete_group` with a valid ID,
verify device.delete_group was called, verify event fired. Test orphan
warning logged when contacts reference deleted group. Test not-found
error.

### Tests for User Story 8 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before
> implementation**

- [X] T050 [P] [US8] Write test `test_delete_group_success` in tests/test_contact_group_services.py — call service with id, assert device.delete_group called correctly, assert `local_akuvox_group_changed` event fired with `action: "delete"` and `group_id`
- [X] T051 [P] [US8] Write test `test_delete_group_orphan_warning` in tests/test_contact_group_services.py — mock device.list_contacts() returning contacts referencing the deleted group, assert warning logged for each orphaned contact
- [X] T052 [P] [US8] Write test `test_delete_group_not_found` in tests/test_contact_group_services.py — mock device.delete_group() raising AkuvoxDeviceError, assert HomeAssistantError raised
- [X] T053 [P] [US8] Write test `test_delete_group_missing_id` in tests/test_contact_group_services.py — call service without id, assert vol.Invalid raised

### Implementation for User Story 8

- [X] T054 [US8] Implement `async delete_group(self, call)` method on AkuvoxLockEntity in custom_components/local_akuvox/lock.py — extract id (required), call `await self.coordinator.device.delete_group(id=id)`, best-effort orphan check via `device.list_contacts()` logging warning for contacts with matching group, fire EVENT_GROUP_CHANGED with `action: "delete"`, group_id, and config_entry_id, with two-tier exception mapping
- [X] T055 [US8] Register delete_group service in `custom_components/local_akuvox/__init__.py` with vol.Schema requiring `id` (cv.string), `func=SERVICE_DELETE_GROUP`

**Checkpoint**: Group CRUD is complete (list + add + modify + delete).
All 8 services functional. All US1–US8 tests pass green.

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Linting, type checking, and final validation across all
services

- [X] T056 Run `uv run ruff check custom_components/ tests/` and fix any linting violations
- [X] T057 Run `uv run ruff format --check custom_components/ tests/` and fix any formatting issues
- [X] T058 Run `uv run mypy custom_components/` and fix any type errors
- [X] T059 Run `uv run pytest tests/test_contact_group_services.py -x -q` — all tests green
- [X] T060 Run `uv run pytest tests/ -x -q` — full test suite green (no regressions)
- [X] T061 Verify SPDX headers on all new/modified files (REUSE compliance)
- [X] T062 Run quickstart.md validation — verify all service call examples from specs/006-contact-group-services/quickstart.md work against mocked device

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (constants must exist
  for services.yaml references) — BLOCKS all user stories
- **User Stories (Phases 3–10)**: All depend on Phase 2 completion
  - US1 + US2 (P1 reads) can proceed in parallel
  - US3 + US4 (P2 creates) can proceed in parallel after US1/US2
  - US5 + US6 (P2 modifies) can proceed in parallel after US3/US4
  - US7 + US8 (P3 deletes) can proceed in parallel after US5/US6
- **Polish (Phase 11)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 — List Contacts (P1)**: After Phase 2. No story dependencies.
- **US2 — List Groups (P1)**: After Phase 2. No story dependencies.
- **US3 — Add Contact (P2)**: After Phase 2. Independent of US1/US2
  (but benefits from list being available for verification).
- **US4 — Add Group (P2)**: After Phase 2. Independent of US1/US2.
- **US5 — Modify Contact (P2)**: After Phase 2. Independent (library
  handles fetch-then-modify internally).
- **US6 — Modify Group (P2)**: After Phase 2. Independent.
- **US7 — Delete Contact (P3)**: After Phase 2. Independent.
- **US8 — Delete Group (P3)**: After Phase 2. Independent (orphan check
  is best-effort and uses device.list_contacts directly).

### Within Each User Story

1. Tests MUST be written and FAIL before implementation (TDD red phase)
2. Entity method in lock.py before service registration in `__init__.py`
3. Verify tests pass green after implementation (TDD green phase)
4. Atomic commit after each task or logical group

### Parallel Opportunities

- T001 + T002 can run in parallel (different files)
- T005 + T006 + T007 + T008 can all run in parallel (different files)
- All test tasks within a user story marked [P] can run in parallel
- US1 + US2 (both P1 reads) can be worked on simultaneously
- US3 + US4 (both P2 creates) can be worked on simultaneously
- US5 + US6 (both P2 modifies) can be worked on simultaneously
- US7 + US8 (both P3 deletes) can be worked on simultaneously

---

## Parallel Example: User Story 1 (List Contacts)

```bash
# Launch all US1 tests together (they target different test functions):
Task: T009 "test_list_contacts_returns_all_contacts"
Task: T010 "test_list_contacts_empty"
Task: T011 "test_list_contacts_with_page"
Task: T012 "test_list_contacts_device_offline"

# Then implement sequentially:
Task: T013 "Implement list_contacts on AkuvoxLockEntity"
Task: T014 "Register list_contacts service in __init__.py"
```

## Parallel Example: P1 Read Stories (US1 + US2)

```bash
# Both read stories can be worked on simultaneously by different agents:
Agent A: US1 (T009–T014) — List Contacts
Agent B: US2 (T015–T020) — List Groups
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup (dependency bump + constants)
2. Complete Phase 2: Foundational (services.yaml, strings, fixtures)
3. Complete Phase 3: US1 — List Contacts
4. Complete Phase 4: US2 — List Groups
5. **STOP and VALIDATE**: Both list services work independently
6. Deploy/demo read-only contact & group visibility

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 + US2 (P1 reads) → Test independently → **MVP: Read-only
   visibility**
3. US3 + US4 (P2 creates) → Test independently → **Create capability**
4. US5 + US6 (P2 modifies) → Test independently → **Update capability**
5. US7 + US8 (P3 deletes) → Test independently → **Full CRUD**
6. Polish → Final validation → **Release ready**

### Parallel Team Strategy

With multiple developers/agents:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Agent A: US1 (List Contacts) + US3 (Add Contact) + US5 (Modify
     Contact) + US7 (Delete Contact) — full contact CRUD
   - Agent B: US2 (List Groups) + US4 (Add Group) + US6 (Modify Group)
     - US8 (Delete Group) — full group CRUD
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- TDD mandatory: tests fail → implement → tests pass → commit
- Atomic commits required per task or logical group
- All 8 services follow identical patterns from feature 003
  (schedule/user services)
- No cloud-entity protection needed (contacts/groups have no
  source_type)
- Event names: `local_akuvox_contact_changed`,
  `local_akuvox_group_changed`
- Batch delete: contacts only (list[str]); groups are single-ID only
- Orphan warning: delete_group does best-effort list_contacts check
