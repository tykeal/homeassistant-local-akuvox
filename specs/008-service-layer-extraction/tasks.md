<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Tasks: Service Layer Extraction

**Input**: Design documents from `/specs/008-service-layer-extraction/`
**Prerequisites**: plan.md (required), spec.md (required for user stories),
research.md, data-model.md, contracts/

**Tests**: No new tests required — this is a pure refactor. Existing tests
validate behavior; only import/reference-path updates should be needed.

**Organization**: Tasks are grouped by user story to enable incremental
delivery. Since this is a refactor, the foundational phase creates the new leaf
module, and US1 handles the core extraction work.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Integration**: `custom_components/local_akuvox/`
- **Tests**: `tests/`
- **Spec docs**: `specs/008-service-layer-extraction/`

______________________________________________________________________

## Phase 1: Setup

**Purpose**: Verify baseline and prepare for extraction

- [ ] T001 Verify all tests pass on current branch by running
  `uv run pytest tests/ -v`
- [ ] T002 Verify lint passes by running
  `uv run ruff check custom_components/local_akuvox/`
- [ ] T003 [P] Verify type checking passes by running
  `uv run mypy custom_components/local_akuvox/`

______________________________________________________________________

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the leaf validation module that all other modules will
depend on. This MUST be complete before services.py or lock.py refactoring can
begin.

**⚠️ CRITICAL**: `validation.py` is the leaf module in the dependency graph —
both `services.py` and `lock.py` will import from it.

- [ ] T004 Create `custom_components/local_akuvox/validation.py` with SPDX
  header (`# SPDX-FileCopyrightText: 2026 Andrew Grimberg
  <tykeal@bardicgrove.org>` plus the Apache-2.0 SPDX license line), module
  docstring,
  `from __future__ import annotations`, and the complete import set:
  `import datetime as dt`, `import re`, `from typing import TYPE_CHECKING, Any`,
  `from homeassistant.exceptions import ServiceValidationError`,
  `from homeassistant.helpers import config_validation as cv`,
  `from .const import DAY_NAME_TO_DIGIT`, plus
  `if TYPE_CHECKING: from pylocal_akuvox import AccessSchedule, User`
- [ ] T005 Add constants `REQUIRED_SCHEDULE_FIELDS` (dict mapping schedule type
  to required field tuples: `"0"` → `("week", "date_start", "date_end")`, `"1"`
  → `("week",)`, `"2"` → `()`) and `FACTORY_SCHEDULE_IDS`
  (`frozenset({"1001", "1002"})`) to
  `custom_components/local_akuvox/validation.py`; these are the moved
  module-level homes for `lock.py`'s `_REQUIRED_FIELDS` and
  `_FACTORY_SCHEDULE_IDS`
- [ ] T006 Copy `_csv_to_list` logic from
  `custom_components/local_akuvox/__init__.py` (line 67) into
  `custom_components/local_akuvox/validation.py` as
  `csv_to_list(value: Any) -> list[str]` — add the new function without removing
  the original yet, drop the underscore prefix, and preserve exact logic
- [ ] T007 Copy `AkuvoxLockEntity._validate_pin` from
  `custom_components/local_akuvox/lock.py` (line 948) into
  `custom_components/local_akuvox/validation.py` as
  `validate_pin(pin: str | None) -> None` — convert from instance method to
  module-level function, remove `self`, preserve `ServiceValidationError`
  behavior, and leave the original method in place until T018/T020
- [ ] T008 Copy `AkuvoxLockEntity._is_cloud_provisioned_user` from
  `custom_components/local_akuvox/lock.py` (line 905) into
  `custom_components/local_akuvox/validation.py` as
  `is_cloud_provisioned_user(user: User) -> bool` — convert from `@staticmethod`
  to module-level function and leave the original method in place until
  T018/T020
- [ ] T009 Copy `AkuvoxLockEntity._is_cloud_provisioned_schedule` from
  `custom_components/local_akuvox/lock.py` (line 927) into
  `custom_components/local_akuvox/validation.py` as
  `is_cloud_provisioned_schedule(schedule: AccessSchedule) -> bool` — convert
  from `@staticmethod` to module-level function, replace
  `AkuvoxLockEntity._FACTORY_SCHEDULE_IDS` with `FACTORY_SCHEDULE_IDS` in
  `validation.py`, and leave the original method in place until T018/T020
- [ ] T010 Copy `AkuvoxLockEntity._check_required_schedule_fields` from
  `custom_components/local_akuvox/lock.py` (line 646) into
  `custom_components/local_akuvox/validation.py` as
  `check_required_schedule_fields(schedule_type: str, **kwargs: Any) -> None` —
  replace `_REQUIRED_FIELDS` with `REQUIRED_SCHEDULE_FIELDS` and leave the
  original method in place until T018/T020
- [ ] T011 Copy `AkuvoxLockEntity` static methods from
  `custom_components/local_akuvox/lock.py` (lines 607, 621, 634) into
  `custom_components/local_akuvox/validation.py` as
  `convert_week(days: list[str]) -> str`, `convert_date(value: dt.date) -> str`,
  and `convert_time(value: dt.time) -> str` — leave the originals in place until
  T018/T020
- [ ] T012 Copy `AkuvoxLockEntity._parse_schedule_relay_pairs` from
  `custom_components/local_akuvox/lock.py` (line 1080) into
  `custom_components/local_akuvox/validation.py` as
  `parse_schedule_relay_pairs(raw: str, *, allow_empty: bool = False) -> list[str]`
  — leave the original method in place until T018/T020
- [ ] T013 Copy `AkuvoxLockEntity._build_schedule_relay` logic from
  `custom_components/local_akuvox/lock.py` (line 1058) into
  `custom_components/local_akuvox/validation.py` as
  `build_schedule_relay(display_ids: list[str], relay_number: int) -> str` — add
  explicit `relay_number` parameter (was `self._relay_number`) and leave caller
  updates for T020

### T013A — Checkpoint: Verify tests pass after validation extraction

| Field            | Value          |
| ---------------- | -------------- |
| Phase            | 2              |
| Priority         | P0 — must-have |
| Estimated effort | 1 min          |
| Dependencies     | T004–T013      |

#### T013A Description

Run `uv run pytest tests/ -v` to confirm all tests still pass after creating
validation.py. At this stage validation.py is importable but unused by
production code, so no breakage is expected. This checkpoint ensures the module
can be imported without errors before Phase 3 begins destructive changes.

#### T013A Acceptance criteria

- [ ] `uv run pytest tests/ -v` exits 0 with all tests passing
- [ ] No import errors related to `validation.py`

**Checkpoint**: `validation.py` is complete as a standalone leaf module (~200
lines). Can be verified with
`python -c "from custom_components.local_akuvox.validation import csv_to_list, validate_pin"`
(no import errors).

______________________________________________________________________

## Phase 3: User Story 1 — Service Calls Continue Working Identically (Priority: P1) 🎯 MVP

**Goal**: Extract service registration into `services.py`, update `__init__.py`
and `lock.py` to delegate to the new modules. All 18 services continue
functioning identically.

**Independent Test**: Run `uv run pytest tests/ -v` — all tests pass with
identical behavior.

### Implementation for User Story 1

- [ ] T014 [US1] Create `custom_components/local_akuvox/services.py` with SPDX
  header, module docstring, and imports (voluptuous,
  homeassistant.const.Platform,
  homeassistant.core.HomeAssistant/SupportsResponse,
  homeassistant.helpers.config_validation/service, `.const` service name
  constants, `.validation.csv_to_list`)
- [ ] T015 [US1] Implement
  `async_register_services(hass: HomeAssistant) -> None` in
  `custom_components/local_akuvox/services.py` — move all 18
  `service.async_register_platform_entity_service()` calls from
  `custom_components/local_akuvox/__init__.py` (lines 101–357) with their inline
  voluptuous schema definitions, preserving exact schema logic and
  `supports_response=SupportsResponse.ONLY` for list services
- [ ] T016 [US1] Update `custom_components/local_akuvox/__init__.py` — remove
  `_csv_to_list` function (line 67), remove all 18
  `service.async_register_platform_entity_service()` calls and their schema
  imports, add `from .services import async_register_services`, change
  `async_setup()` to call `await async_register_services(hass)` then
  `return True`
- [ ] T017 [US1] Remove unused imports from
  `custom_components/local_akuvox/__init__.py` — remove `voluptuous`, `cv`,
  `service`, `SupportsResponse`, `Platform`, and all `SERVICE_*` constants that
  are no longer used directly
- [ ] T018 [US1] Update `custom_components/local_akuvox/lock.py` — remove
  extracted methods (`_validate_pin`, `_is_cloud_provisioned_user`,
  `_is_cloud_provisioned_schedule`, `_check_required_schedule_fields`,
  `_convert_week`, `_convert_date`, `_convert_time`,
  `_parse_schedule_relay_pairs`, `_build_schedule_relay`), remove the
  module-level `_REQUIRED_FIELDS` dict after it is moved to `validation.py` as
  `REQUIRED_SCHEDULE_FIELDS`, and remove the `_FACTORY_SCHEDULE_IDS` class
  variable (`ClassVar`, defined near line 924) after it is moved to
  `validation.py` as `FACTORY_SCHEDULE_IDS`
- [ ] T019 [US1] Add imports to `custom_components/local_akuvox/lock.py` — add
  `from .validation import (build_schedule_relay, check_required_schedule_fields, convert_date, convert_time, convert_week, is_cloud_provisioned_schedule, is_cloud_provisioned_user, parse_schedule_relay_pairs, validate_pin)`
- [ ] T020 [US1] Update all service handler method bodies in `AkuvoxLockEntity`
  in `custom_components/local_akuvox/lock.py` — replace
  `self._validate_pin(...)` with `validate_pin(...)`,
  `self._is_cloud_provisioned_user(...)` with `is_cloud_provisioned_user(...)`,
  `self._is_cloud_provisioned_schedule(...)` with
  `is_cloud_provisioned_schedule(...)`,
  `self._check_required_schedule_fields(...)` with
  `check_required_schedule_fields(...)`, `self._convert_week(...)` with
  `convert_week(...)`, `self._convert_date(...)` with `convert_date(...)`,
  `self._convert_time(...)` with `convert_time(...)`,
  `self._parse_schedule_relay_pairs(...)` with
  `parse_schedule_relay_pairs(...)`, `self._build_schedule_relay(ids)` with
  `build_schedule_relay(ids, self._relay_number)`
- [ ] T021 [US1] Remove unused imports from
  `custom_components/local_akuvox/lock.py` that were only needed by extracted
  methods (e.g., `ClassVar` if no longer used, redundant
  `ServiceValidationError` if validation.py now raises it)
- [ ] T022 [US1] Verify no circular imports by running
  `python -c "from custom_components.local_akuvox import services; from custom_components.local_akuvox import validation; from custom_components.local_akuvox import lock"`
  from repository root

**Checkpoint**: All 18 services are registered and functional.
`uv run pytest tests/ -v` should pass (or fail only on import/reference updates
addressed in Phase 4).

______________________________________________________________________

## Phase 4: User Story 4 — Existing Tests Pass With Import/Reference Updates Only (Priority: P2)

**Goal**: All existing tests pass. Only import/reference updates are permitted —
no test logic modifications.

**Independent Test**: `uv run pytest tests/ -v` — all tests green.

### Implementation for User Story 4

- [ ] T023 [US4] Run `uv run pytest tests/ -v` and identify any import failures
  caused by moved code
- [ ] T024 [US4] Update imports in `tests/test_services.py` if any validation
  helpers were previously imported from `lock`, and verify direct helper
  references that move to `validation.py` are tracked separately in T025A
- [ ] T025 [US4] Update import paths in `tests/test_init.py` if `_csv_to_list`
  was tested directly (verify — research indicates it is tested indirectly via
  service calls only)

### T025A — Update test imports for moved validation helpers

| Field            | Value          |
| ---------------- | -------------- |
| Phase            | 4              |
| Priority         | P0 — must-have |
| Estimated effort | S              |
| Dependencies     | T008, T009     |

#### T025A Description

Update `tests/test_services.py` to import the moved cloud-provisioning check
functions from `validation.py` instead of calling them as class methods on
`AkuvoxLockEntity`.

Change:

- `AkuvoxLockEntity._is_cloud_provisioned_user(user)` →
  `is_cloud_provisioned_user(user)` (import from
  `custom_components.local_akuvox.validation`)
- `AkuvoxLockEntity._is_cloud_provisioned_schedule(schedule)` →
  `is_cloud_provisioned_schedule(schedule)` (import from
  `custom_components.local_akuvox.validation`)

Affected locations in `tests/test_services.py` include the direct helper
assertions around the existing cloud-provisioning checks (currently near lines
2829/2848 for users and 2870/2896/2918/2945 for schedules).

#### T025A Acceptance criteria

- [ ] No references to `AkuvoxLockEntity._is_cloud_provisioned_user` remain in
  tests

- [ ] No references to `AkuvoxLockEntity._is_cloud_provisioned_schedule` remain
  in tests

- [ ] Tests import from `custom_components.local_akuvox.validation` instead

- [ ] All tests still pass

- [ ] T026 [US4] Update any mock target paths in test files if mock patches
  reference moved function locations (e.g.,
  `patch("custom_components.local_akuvox.lock._validate_pin")` →
  `patch("custom_components.local_akuvox.validation.validate_pin")`)

- [ ] T027 [US4] Run `uv run pytest tests/ -v` and confirm all tests pass with
  zero test logic changes

**Checkpoint**: Full test suite passes. `git diff tests/` shows only
import/symbol-reference updates to moved helpers (if any).

______________________________________________________________________

## Phase 5: User Story 2 — Module Boundaries Are Clean and Focused (Priority: P2)

**Goal**: Each module has a single, coherent responsibility with no leaked
concerns.

**Independent Test**: Manual inspection of module contents confirms single
responsibility per module.

### Implementation for User Story 2

- [ ] T028 [US2] Verify `custom_components/local_akuvox/__init__.py` contains
  ONLY lifecycle orchestration: `CONFIG_SCHEMA`, `async_setup`,
  `async_setup_entry`, `async_unload_entry`, `async_remove_entry`,
  `_get_config_value`, `_create_device`, `_async_update_listener` — no service
  schemas, no validation helpers
- [ ] T029 [US2] Verify `custom_components/local_akuvox/services.py` contains
  ONLY schema definitions and registration: `async_register_services` with all
  18 service registrations — no validation logic, no entity code
- [ ] T030 [US2] Verify `custom_components/local_akuvox/validation.py` contains
  ONLY pure validation/conversion functions: `csv_to_list`, `validate_pin`,
  `is_cloud_provisioned_user`, `is_cloud_provisioned_schedule`,
  `check_required_schedule_fields`, `convert_week`, `convert_date`,
  `convert_time`, `parse_schedule_relay_pairs`, `build_schedule_relay`, and
  constants `REQUIRED_SCHEDULE_FIELDS`, `FACTORY_SCHEDULE_IDS` — no HA framework
  lifecycle code
- [ ] T031 [US2] Verify `custom_components/local_akuvox/lock.py` contains ONLY
  entity/platform code: relay helpers, `async_setup_entry`, `AkuvoxLockEntity`
  class with lifecycle, lock/unlock, and thin service handler methods that
  delegate to validation.py — no schema definitions, no service registration

**Checkpoint**: Each module has single responsibility. Dependency direction is
strictly `const → validation → services → __init__` and
`const/validation → lock`.

______________________________________________________________________

## Phase 6: User Story 3 — File Sizes Are Within Maintainable Limits (Priority: P3)

**Goal**: Keep helper/orchestration modules near or under ~500 lines, with
`lock.py` allowed as the documented HA-dispatch exception.

**Independent Test**: `wc -l custom_components/local_akuvox/*.py | sort -n` —
`__init__.py`, `services.py`, and `validation.py` should be approximately 500
lines or less; `lock.py` may remain larger if it contains only entity lifecycle
plus HA-dispatch-bound service handlers.

### Implementation for User Story 3

- [ ] T032 [US3] Run `wc -l custom_components/local_akuvox/*.py | sort -n` and
  verify `__init__.py`, `services.py`, and `validation.py` are approximately 500
  lines or less; accept `lock.py` as the documented exception only if it retains
  just entity lifecycle + HA-dispatch-bound service handlers
- [ ] T033 [US3] Verify `custom_components/local_akuvox/__init__.py` is
  approximately 100–150 lines (70%+ reduction from 549)
- [ ] T034 [US3] Verify `custom_components/local_akuvox/lock.py` no longer owns
  the extracted validation/utility helpers; the remaining large body is entity
  lifecycle + service handlers that must stay on the entity for Home Assistant
  dispatch
- [ ] T035 [US3] If `services.py`, `validation.py`, or `__init__.py` exceed
  approximately 500 lines, identify further extraction opportunities and adjust;
  do not split `lock.py` service handlers solely to chase the line-count
  guideline

**Checkpoint**: `__init__.py`, `services.py`, and `validation.py` are within the
maintainability target, and `lock.py` is the only documented size exception.

______________________________________________________________________

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final verification and compliance checks

- [ ] T036 [P] Run `uv run ruff check custom_components/local_akuvox/` and fix
  any lint errors in new/modified files
- [ ] T037 [P] Run `uv run mypy custom_components/local_akuvox/` and fix any
  type errors in new/modified files
- [ ] T038 [P] Run `uv run reuse lint` to verify SPDX headers on `validation.py`
  and `services.py`
- [ ] T039 Verify service count:
  `grep -c "async_register_platform_entity_service" custom_components/local_akuvox/services.py`
  should output `18`
- [ ] T040 Run full test suite one final time: `uv run pytest tests/ -v` — all
  tests pass
- [ ] T041 Run quickstart.md validation commands from
  `specs/008-service-layer-extraction/quickstart.md`

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — verify baseline
- **Foundational (Phase 2)**: Depends on Setup — creates `validation.py` (leaf
  module)
- **US1 (Phase 3)**: Depends on Foundational — creates `services.py`, updates
  `__init__.py` and `lock.py`
- **US4 (Phase 4)**: Depends on US1 — updates test imports if needed
- **US2 (Phase 5)**: Depends on US1 and US4 — verification only
- **US3 (Phase 6)**: Depends on US1 — verification only
- **Polish (Phase 7)**: Depends on all previous phases

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational (Phase 2) — the core extraction
- **User Story 4 (P2)**: Depends on US1 — can only update test imports after
  code moves
- **User Story 2 (P2)**: Depends on US1 and US4 — verification that boundaries
  are clean
- **User Story 3 (P3)**: Depends on US1 — measurement of file sizes after
  extraction

### Within Phase 3 (US1)

- T014 (create services.py shell) before T015 (implement registration function)
- T015 (move service registration) before T016 (update **init**.py to delegate)
- T016 (update **init**.py) before T017 (clean unused imports in **init**.py)
- T018 (remove methods from lock.py) and T019 (add imports to lock.py) are
  coupled — do together
- T020 (update method bodies) depends on T018+T019
- T021 (clean unused imports in lock.py) depends on T020
- T022 (verify no circular imports) depends on all prior US1 tasks

### Parallel Opportunities

- **Phase 1**: T001 and T002+T003 can run in parallel (independent checks)
- **Phase 2**: T008-T013 have no logical dependency chain, but they all edit
  `validation.py`; apply them sequentially to avoid conflicts
- **Phase 5+6**: US2 and US3 verification can run in parallel (both are
  read-only checks)
- **Phase 7**: T036+T037+T038 can run in parallel (independent lint/type/reuse
  checks)

______________________________________________________________________

## Sequencing Note: Phase 2 (Foundational)

```text
After T004-T007 establish `validation.py`, complete T008-T013 sequentially.

These extractions are logically independent, but they all modify the same
file (`custom_components/local_akuvox/validation.py`), so parallel execution
would create unnecessary edit conflicts.
```

______________________________________________________________________

## Parallel Example: Phase 7 (Polish)

```bash
# Launch all independent checks together:
Task: "Run ruff check" (T036)
Task: "Run mypy" (T037)
Task: "Run reuse lint" (T038)
```

______________________________________________________________________

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify baseline)
1. Complete Phase 2: Foundational (create validation.py)
1. Complete Phase 3: User Story 1 (extract services.py, update **init**.py +
   lock.py)
1. **STOP and VALIDATE**: Run `uv run pytest tests/ -v` — all services work
   identically
1. This is a complete, working refactor at this point

### Incremental Delivery

1. Complete Setup + Foundational → validation.py exists as leaf module
1. Complete User Story 1 → Core extraction done, services work ✓
1. Complete User Story 4 → Tests confirmed passing with path updates ✓
1. Complete User Story 2 → Module boundaries verified clean ✓
1. Complete User Story 3 → Helper module sizes verified; `lock.py` exception
   documented ✓
1. Complete Polish → Lint, type check, REUSE compliance all pass ✓

### Commit Strategy (Atomic Commits per Constitution)

1. **Commit 1**: `feat(008): add validation.py with extracted helpers` (Phase 2)
1. **Commit 2**: `feat(008): add services.py with extracted registration`
   (T014-T015)
1. **Commit 3**: `refactor(008): update __init__.py to delegate to services`
   (T016-T017)
1. **Commit 4**: `refactor(008): update lock.py to delegate to validation`
   (T018-T021)
1. **Commit 5**: `test(008): update test import/reference paths` (Phase 4, if
   changes needed)
1. **Commit 6**: `chore(008): lint and type fixes` (Phase 7, if needed)

______________________________________________________________________

## Notes

- [P] tasks = different files or independent operations, no dependencies
- [Story] label maps task to specific user story for traceability
- This is a **pure refactor** — zero behavior changes permitted
- `validation.py` imports only from `const.py` (and HA core for
  `ServiceValidationError`)
- `services.py` imports from `const.py` and `validation.py` (for `csv_to_list`)
- `lock.py` imports from `validation.py` and `const.py`
- `__init__.py` imports from `services.py`, `const.py`, `coordinator.py`,
  `webhook.py`
- Service handler methods STAY on `AkuvoxLockEntity` (HA dispatch requires
  entity methods)
- `_build_schedule_relay` gains explicit `relay_number` parameter (was
  `self._relay_number`)
- `_csv_to_list` → `csv_to_list` (public API, no underscore prefix)
- `_REQUIRED_FIELDS` → `REQUIRED_SCHEDULE_FIELDS` (renamed for clarity at module
  level)
- `_FACTORY_SCHEDULE_IDS` → `FACTORY_SCHEDULE_IDS` (same reasoning)

<!-- markdownlint-enable MD013 -->
