<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Tasks: Service Registration Split

**Input**: Design documents from `/specs/010-service-registration-split/`
**Prerequisites**: plan.md (required), spec.md (required for user stories),
research.md, data-model.md, contracts/

**Tests**: No new behavior tests are planned. This is a pure refactor covered by
existing service registration and service behavior tests in `tests/test_services.py`.
Implementation must not edit tests unless review proves a direct regression in the
existing behavior coverage.

**Organization**: Tasks are dependency-ordered and grouped by user story. The
implementation keeps `async_register_services` as the public async setup entry
point while extracting synchronous private helpers inside `services.py`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files or independent checks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Integration**: `custom_components/local_akuvox/`
- **Tests**: `tests/`
- **Spec docs**: `specs/010-service-registration-split/`

______________________________________________________________________

## Phase 1: Setup

**Purpose**: Re-confirm the live service registration shape and baseline quality
before the behavior-preserving move.

- [ ] T001 [US2] Re-confirm all 18 live registration blocks in
  `custom_components/local_akuvox/services.py`, including service constants,
  schema constants, `func` values, `entity_domain=Platform.LOCK`, and the four
  `supports_response=SupportsResponse.ONLY` list services. Record that the live
  source currently begins with `SERVICE_LIST_SCHEDULES`, then
  `SERVICE_LIST_USERS`, before the remaining schedule and user blocks; treat this
  as source context, not a required post-refactor order, because the spec groups
  complete domains into helpers. Covers FR-008, FR-009, FR-010, and SC-004.
- [ ] T002 [US2] Run `uv run pytest tests/ -q` from the repository root and
  record any pre-existing failures before editing. Do not edit tests for this
  refactor. Covers FR-011 and SC-003.
- [ ] T003 [P] [US4] Run `uv run ruff check custom_components/ tests/` and
  `uv run ruff format --check custom_components/ tests/` from the repository
  root to capture the baseline lint and format state. Covers FR-013.

**Checkpoint**: Live registration details and baseline quality status are known.

______________________________________________________________________

## Phase 2: Domain Helper Extraction (Blocking Prerequisite)

**Purpose**: Add four synchronous private helpers inside `services.py`, each with
a docstring, and move the exact registration blocks into their domain groups.

**⚠️ CRITICAL**: Each moved registration must preserve every argument verbatim:
`hass`, `DOMAIN`, the service constant, `entity_domain=Platform.LOCK`, the schema
constant, `func`, and any `supports_response` value. The helpers are plain
`def` functions returning `None`; they are not awaited.

- [ ] T004 [US3] Add
  `_register_schedule_services(hass: HomeAssistant) -> None` with a docstring in
  `custom_components/local_akuvox/services.py`. Move exactly these registration
  blocks into it: `SERVICE_LIST_SCHEDULES`, `SERVICE_ADD_SCHEDULE`,
  `SERVICE_MODIFY_SCHEDULE`, and `SERVICE_DELETE_SCHEDULE`. Preserve
  `SERVICE_LIST_SCHEDULES_SCHEMA`, `SERVICE_ADD_SCHEDULE_SCHEMA`,
  `SERVICE_MODIFY_SCHEDULE_SCHEMA`, `SERVICE_DELETE_SCHEDULE_SCHEMA`, matching
  `func` values, `entity_domain=Platform.LOCK`, and
  `supports_response=SupportsResponse.ONLY` only on `SERVICE_LIST_SCHEDULES`.
  Covers FR-003, FR-004, FR-008, FR-009, FR-013, SC-004, and SC-005.
- [ ] T005 [US3] Add `_register_user_services(hass: HomeAssistant) -> None` with
  a docstring in `custom_components/local_akuvox/services.py`. Move exactly
  these registration blocks into it: `SERVICE_LIST_USERS`, `SERVICE_ADD_USER`,
  `SERVICE_MODIFY_USER`, `SERVICE_DELETE_USER`,
  `SERVICE_ADD_USER_SCHEDULE_RELAY`, and
  `SERVICE_REMOVE_USER_SCHEDULE_RELAY`. Preserve `SERVICE_LIST_USERS_SCHEMA`,
  `SERVICE_ADD_USER_SCHEMA`, `SERVICE_MODIFY_USER_SCHEMA`,
  `SERVICE_DELETE_USER_SCHEMA`, `SERVICE_ADD_USER_SCHEDULE_RELAY_SCHEMA`,
  `SERVICE_REMOVE_USER_SCHEDULE_RELAY_SCHEMA`, matching `func` values,
  `entity_domain=Platform.LOCK`, and `supports_response=SupportsResponse.ONLY`
  only on `SERVICE_LIST_USERS`. Covers FR-003, FR-005, FR-008, FR-009, FR-013,
  SC-004, and SC-005.
- [ ] T006 [US3] Add
  `_register_contact_services(hass: HomeAssistant) -> None` with a docstring in
  `custom_components/local_akuvox/services.py`. Move exactly these registration
  blocks into it: `SERVICE_LIST_CONTACTS`, `SERVICE_ADD_CONTACT`,
  `SERVICE_MODIFY_CONTACT`, and `SERVICE_DELETE_CONTACT`. Preserve
  `SERVICE_LIST_CONTACTS_SCHEMA`, `SERVICE_ADD_CONTACT_SCHEMA`,
  `SERVICE_MODIFY_CONTACT_SCHEMA`, `SERVICE_DELETE_CONTACT_SCHEMA`, matching
  `func` values, `entity_domain=Platform.LOCK`, and
  `supports_response=SupportsResponse.ONLY` only on `SERVICE_LIST_CONTACTS`.
  Covers FR-003, FR-006, FR-008, FR-009, FR-013, SC-004, and SC-005.
- [ ] T007 [US3] Add `_register_group_services(hass: HomeAssistant) -> None`
  with a docstring in `custom_components/local_akuvox/services.py`. Move exactly
  these registration blocks into it: `SERVICE_LIST_GROUPS`, `SERVICE_ADD_GROUP`,
  `SERVICE_MODIFY_GROUP`, and `SERVICE_DELETE_GROUP`. Preserve
  `SERVICE_LIST_GROUPS_SCHEMA`, `SERVICE_ADD_GROUP_SCHEMA`,
  `SERVICE_MODIFY_GROUP_SCHEMA`, `SERVICE_DELETE_GROUP_SCHEMA`, matching `func`
  values, `entity_domain=Platform.LOCK`, and
  `supports_response=SupportsResponse.ONLY` only on `SERVICE_LIST_GROUPS`.
  Covers FR-003, FR-007, FR-008, FR-009, FR-013, SC-004, and SC-005.
- [ ] T008 [US3] Inspect `custom_components/local_akuvox/services.py` and verify
  the four helpers contain only their assigned service groups, no helper is
  async, no helper is exported from another module, and no new service
  registration module was added. Covers FR-002, FR-003, FR-004, FR-005, FR-006,
  FR-007, and SC-006.

**Checkpoint**: The domain helpers own all service registration details while
preserving the exact live registration arguments.

______________________________________________________________________

## Phase 3: User Story 1 — Registration Function Clears Gate (Priority: P1) 🎯 MVP

**Goal**: Make `async_register_services` a thin orchestrator under the 80-line
function-length limit.

**Independent Test**: Measure `async_register_services` and run aislop so
`complexity/function-too-long` no longer reports that function.

### Implementation for User Story 1

- [ ] T009 [US1] Rewrite
  `custom_components/local_akuvox/services.py:async_register_services` so it
  keeps the public `async def async_register_services(hass: HomeAssistant) -> None`
  signature and docstring, then directly calls the synchronous helpers in this
  documented order: `_register_schedule_services(hass)`,
  `_register_user_services(hass)`, `_register_contact_services(hass)`, and
  `_register_group_services(hass)`. This keeps `SERVICE_LIST_SCHEDULES` first
  and preserves the live domain progression while intentionally grouping each
  complete domain together; do not `await` helper calls. Covers FR-001, FR-002,
  FR-010, SC-001, SC-002, and SC-006.
- [ ] T010 [US1] Remove every inline
  `service.async_register_platform_entity_service(...)` block from
  `async_register_services` after the helper calls are in place, leaving no
  registration schema, handler, entity-domain, or response-support details in the
  orchestrator body. Covers FR-001, FR-002, SC-001, and SC-002.
- [ ] T011 [US1] Confirm the public caller stays unchanged by checking
  `custom_components/local_akuvox/__init__.py` still awaits
  `async_register_services(hass)` and no other caller or public API signature was
  changed. Covers FR-001, FR-010, and SC-006.

**Checkpoint**: `async_register_services` is a short async orchestrator and the
public setup contract is unchanged.

______________________________________________________________________

## Phase 4: User Story 2 — Services Remain Identical (Priority: P1)

**Goal**: Prove all 18 service registrations and response semantics still match
the live behavior.

**Independent Test**: Existing `tests/test_services.py` behavior checks pass
without test edits.

### Verification for User Story 2

- [ ] T012 [US2] Run `uv run pytest tests/test_services.py -q` and fix only
  refactor-caused failures in `custom_components/local_akuvox/services.py`. Do
  not edit `tests/test_services.py`; it verifies service names through Home
  Assistant behavior, not helper structure or call order. Covers FR-011, SC-003,
  SC-004, and SC-006.
- [ ] T013 [US2] Re-inspect the helper registrations in
  `custom_components/local_akuvox/services.py` and confirm the exact service
  constant set is still 18 services: four schedule, six user, four contact, and
  four group registrations. Covers FR-004, FR-005, FR-006, FR-007, FR-008,
  FR-009, FR-010, and SC-004.

**Checkpoint**: Service registration behavior remains identical and tests stay
untouched.

______________________________________________________________________

## Phase 5: User Story 3 — Registrations Are Cohesive (Priority: P2)

**Goal**: Ensure related schedule, user, contact, and group registrations are
cohesive private helpers in `services.py`.

**Independent Test**: Inspect `services.py` to confirm every helper owns exactly
one service domain and no domain responsibilities are mixed.

### Verification for User Story 3

- [ ] T014 [US3] Verify `_register_schedule_services` contains only
  `SERVICE_LIST_SCHEDULES`, `SERVICE_ADD_SCHEDULE`,
  `SERVICE_MODIFY_SCHEDULE`, and `SERVICE_DELETE_SCHEDULE`, with the list
  service first inside the helper. Covers FR-004 and SC-004.
- [ ] T015 [US3] Verify `_register_user_services` contains only
  `SERVICE_LIST_USERS`, `SERVICE_ADD_USER`, `SERVICE_MODIFY_USER`,
  `SERVICE_DELETE_USER`, `SERVICE_ADD_USER_SCHEDULE_RELAY`, and
  `SERVICE_REMOVE_USER_SCHEDULE_RELAY`, with the list service first inside the
  helper. Covers FR-005 and SC-004.
- [ ] T016 [P] [US3] Verify `_register_contact_services` contains only
  `SERVICE_LIST_CONTACTS`, `SERVICE_ADD_CONTACT`, `SERVICE_MODIFY_CONTACT`, and
  `SERVICE_DELETE_CONTACT`, with the list service first inside the helper.
  Covers FR-006 and SC-004.
- [ ] T017 [P] [US3] Verify `_register_group_services` contains only
  `SERVICE_LIST_GROUPS`, `SERVICE_ADD_GROUP`, `SERVICE_MODIFY_GROUP`, and
  `SERVICE_DELETE_GROUP`, with the list service first inside the helper. Covers
  FR-007 and SC-004.

**Checkpoint**: Each private helper is cohesive and easy to inspect by service
domain.

______________________________________________________________________

## Phase 6: User Story 4 — Existing Quality Gates Remain Green (Priority: P2)

**Goal**: Prove the refactor keeps tests, linting, formatting, type checking,
docstrings, SPDX compliance, and aislop checks green.

**Independent Test**: All commands in this phase exit 0 before the implementation
PR is opened.

### Verification for User Story 4

- [ ] T018 [US4] Run `uv run pytest tests/ -q` and require 100% pass with no test
  edits. Covers FR-011 and SC-003.
- [ ] T019 [P] [US4] Run `uv run ruff check custom_components/ tests/` and fix
  all lint errors without behavior changes. Covers FR-013.
- [ ] T020 [P] [US4] Run `uv run ruff format --check custom_components/ tests/`
  and fix formatting only if the check reports required changes. Covers FR-013.
- [ ] T021 [P] [US4] Run `uv run pre-commit run mypy --all-files` and fix type
  errors without changing runtime behavior. Covers FR-013.
- [ ] T022 [P] [US4] Run `uv run pre-commit run interrogate --all-files` and
  verify docstring coverage remains 100% for the new helper docstrings. Covers
  FR-013 and SC-005.
- [ ] T023 [US4] Confirm `async_register_services` is 80 lines or fewer with an
  AST-based line-count check or equivalent source inspection. Covers FR-012,
  SC-001, and SC-002.
- [ ] T024 [US4] Stage `custom_components/local_akuvox/services.py`, then run
  `aislop ci --staged` and confirm it no longer reports
  `complexity/function-too-long` for `async_register_services`. Covers FR-012,
  SC-001, and SC-002.
- [ ] T025 [US4] Run `uv run pre-commit run --all-files` before the
  implementation commit so reuse, markdownlint, gitlint, actionlint, aislop,
  interrogate, mypy, ruff, and other configured hooks are clean. Covers FR-013.

**Checkpoint**: All automated quality gates are green and the staged refactor
satisfies the spec success criteria.

______________________________________________________________________

## Phase 7: Implementation PR Commit Hygiene

**Purpose**: Preserve atomic commit history for the later implementation stage.

- [ ] T026 [US4] In the implementation PR, commit production changes in
  `custom_components/local_akuvox/services.py` as one refactor commit after all
  verification passes, then commit the
  `specs/010-service-registration-split/tasks.md` checkbox flips as a separate
  atomic docs commit. Do not bundle checkbox updates with code changes.

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; start immediately.
- **Domain helper extraction (Phase 2)**: Depends on Setup completion and blocks
  the final orchestrator rewrite.
- **US1 size-gate fix (Phase 3)**: Depends on the helpers from Phase 2.
- **US2 behavior preservation (Phase 4)**: Depends on Phases 2 and 3.
- **US3 cohesion checks (Phase 5)**: Depends on Phases 2 and 3.
- **US4 quality gates (Phase 6)**: Depends on Phases 3 through 5.
- **Commit hygiene (Phase 7)**: Depends on all implementation and verification
  tasks.

### User Story Dependencies

- **US1 (P1)**: Requires helper extraction, then independently proves the length
  and aislop gate fix.
- **US2 (P1)**: Requires the orchestrator rewrite, then proves behavior remains
  unchanged through existing service tests.
- **US3 (P2)**: Requires helper extraction, then proves grouping cohesion.
- **US4 (P2)**: Requires all implementation stories, then proves quality gates.

### Parallel Opportunities

- T003 can run in parallel with T001 and T002 because it is a read-only baseline
  quality check.
- T016 and T017 can be inspected in parallel after the helper extraction because
  they cover different helper domains.
- T019, T020, T021, and T022 can be run independently after the code layout is
  complete.

## Implementation Strategy

### MVP First

1. Complete Setup and confirm the live registration inventory.
2. Extract the four synchronous private helpers with docstrings.
3. Rewrite `async_register_services` as the four-call orchestrator.
4. Stop and validate the MVP with service tests, line count, and staged aislop.

### Final Validation

1. Complete the cohesion checks for all four helpers.
2. Run all US4 verification gates.
3. Commit code changes separately from tasks.md checkbox flips in the later
   implementation PR.

## Notes

- `[P]` tasks touch different files or run independent checks.
- No public Home Assistant API, entity state, service schema, handler dispatch,
  response support, or user-visible behavior may change.
- Existing service tests are the behavior-preservation guard; new tests are only
  justified if review identifies a missing observable regression check.
- The implementation PR must not start until this tasks stage is merged.

<!-- markdownlint-enable MD013 -->
