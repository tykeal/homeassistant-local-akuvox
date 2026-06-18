<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Tasks: Coordinator Relay Config Split

**Input**: Design documents from `/specs/009-coordinator-split/`
**Prerequisites**: plan.md (required), spec.md (required for user stories),
research.md, data-model.md, contracts/

**Tests**: No new behavior tests are planned. This is a pure refactor covered
by existing coordinator and lock tests; implementation should update only
internal import paths unless review proves a focused relay-config test module is
needed.

**Organization**: Tasks are dependency-ordered and grouped by user story. The
foundational phase creates the new leaf module first so tests can be repointed
before the old coordinator definitions are removed.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Integration**: `custom_components/local_akuvox/`
- **Tests**: `tests/`
- **Spec docs**: `specs/009-coordinator-split/`

______________________________________________________________________

## Phase 1: Setup

**Purpose**: Re-confirm the live code shape and establish a green baseline.

- [ ] T001 [US3] Re-confirm the extraction surface against live source with
  `rg "RelayConfig|_build_relay_config|_parse_config_int" custom_components/ tests/`
  and verify only `coordinator.py`, `tests/test_coordinator.py`, and
  `tests/test_lock.py` reference the moved symbols. Map findings to FR-005,
  FR-008, and FR-012 before editing.
- [ ] T002 [US2] Run `uv run pytest tests/ -q` from the repository root and
  record any pre-existing failures before making changes. This guards FR-006,
  FR-007, and FR-009.
- [ ] T003 [US4] Run `uv run ruff check` and
  `uv run ruff format --check` from the repository root to capture the baseline
  lint/format state before the refactor. This guards FR-011.

**Checkpoint**: Live symbol usage and baseline quality status are known.

______________________________________________________________________

## Phase 2: Foundational Leaf Module (Blocking Prerequisite)

**Purpose**: Create `relay_config.py` as a coordinator-free leaf module above
`const.py` in the dependency graph.

**⚠️ CRITICAL**: `relay_config.py` may import constants from `.const`, but it
MUST NOT import from `coordinator.py` or any Home Assistant coordinator state.

- [ ] T004 [US3] Create
  `custom_components/local_akuvox/relay_config.py` with SPDX header,
  module docstring, `from __future__ import annotations`, `import logging`,
  `from dataclasses import dataclass`, `from typing import Any`, and its own
  `_LOGGER = logging.getLogger(__name__)`. Import exactly these constants from
  `.const`: `CONFIG_KEY_RELAY_HOLD_DELAY`, `CONFIG_KEY_RELAY_MODE_SUFFIX`,
  `CONFIG_KEY_RELAY_NAME`, `CONFIG_KEY_RELAY_PREFIX`,
  `CONFIG_KEY_RELAY_TYPE_SUFFIX`, `DEFAULT_HOLD_DELAY_SECONDS`,
  `DEFAULT_RELAY_MODE`, and `DEFAULT_RELAY_TYPE`. Do not import
  `CONFIG_KEY_LOCATION` or `RELAY_KEY_RE`. Covers FR-001, FR-011, and FR-012.
- [ ] T005 [US3] Move the frozen `RelayConfig` dataclass into
  `custom_components/local_akuvox/relay_config.py`, preserving the class
  docstring, `frozen=True`, fields `name`, `hold_delay`, `relay_type`,
  `relay_mode`, and existing defaults. Covers FR-002 and SC-006.
- [ ] T006 [US2] Move `_parse_config_int` into
  `custom_components/local_akuvox/relay_config.py` without logic changes,
  preserving its signature, full docstring, `None` handling, empty-string
  fallback, invalid-integer warning text, min/max checks, allowed-set checks,
  and return values. Covers FR-003, FR-006, and FR-007.
- [ ] T007 [US2] Move `_build_relay_config` into
  `custom_components/local_akuvox/relay_config.py` without logic changes,
  preserving its signature, full docstring, name key
  `f"{CONFIG_KEY_RELAY_NAME}{letter}"`, hold-delay key
  `f"{CONFIG_KEY_RELAY_HOLD_DELAY}{letter}"`, relay type key
  `f"{CONFIG_KEY_RELAY_PREFIX}{letter}{CONFIG_KEY_RELAY_TYPE_SUFFIX}"`,
  relay mode key
  `f"{CONFIG_KEY_RELAY_PREFIX}{letter}{CONFIG_KEY_RELAY_MODE_SUFFIX}"`,
  defaults, `min_val=1`, and `allowed={0, 1}` validation. Covers FR-004,
  FR-006, and FR-007.
- [ ] T008 [US3] Verify the new module imports independently by running
  `python -c "from custom_components.local_akuvox.relay_config import RelayConfig, _build_relay_config, _parse_config_int"`
  and confirm `rg "coordinator" custom_components/local_akuvox/relay_config.py`
  returns no matches. Covers FR-012.

**Checkpoint**: `relay_config.py` is importable and owns the cohesive parsing
helpers while `coordinator.py` still preserves the old behavior.

______________________________________________________________________

## Phase 3: User Story 1 — Coordinator Clears Size Gate (Priority: P1) 🎯 MVP

**Goal**: Remove the inline relay-config helpers from `coordinator.py` so the
file is 400 lines or fewer and delegates parsing to `relay_config.py`.

**Independent Test**: `wc -l custom_components/local_akuvox/coordinator.py`
reports 400 or fewer lines, and aislop no longer reports
`complexity/file-too-large` for the staged coordinator change.

### Implementation for User Story 1

- [ ] T009 [US1] Add
  `from .relay_config import RelayConfig, _build_relay_config` to
  `custom_components/local_akuvox/coordinator.py` so
  `AkuvoxCoordinatorData`, `_cached_relay_configs`, `_fetch_config_from_device_config`,
  and `_apply_default_config` continue using the same symbols from the new
  module. Covers FR-005.
- [ ] T010 [US1] Remove the inline `RelayConfig`, `_parse_config_int`, and
  `_build_relay_config` definitions from
  `custom_components/local_akuvox/coordinator.py`. Do not re-export aliases for
  private helper compatibility. Covers FR-005 and SC-006.
- [ ] T011 [US1] Remove now-unused imports from
  `custom_components/local_akuvox/coordinator.py`: drop relay parsing constants
  that moved to `relay_config.py` while keeping `CONFIG_KEY_LOCATION`,
  `DEFAULT_SCAN_INTERVAL`, `DOMAIN`, `RELAY_KEY_RE`, `Any`, `dataclass`, and
  `field` where still used. Verify with `uv run ruff check`. Covers FR-011.
- [ ] T012 [US1] Verify the size and duplicate-definition cleanup with
  `wc -l custom_components/local_akuvox/coordinator.py` and
  `rg "class RelayConfig|def _parse_config_int|def _build_relay_config" custom_components/local_akuvox/coordinator.py`.
  The line count must be 400 or fewer and the `rg` command must return no moved
  definitions. Covers FR-005, FR-010, SC-001, and SC-002.

**Checkpoint**: The coordinator is below the file-size threshold and contains
only coordinator state, fetch, cache, and update orchestration logic.

______________________________________________________________________

## Phase 4: User Story 2 — Runtime Behavior Is Preserved (Priority: P1)

**Goal**: Keep existing behavior coverage intact while updating white-box tests
to the new internal helper module path.

**Independent Test**: Existing coordinator and lock tests pass with unchanged
assertions after import-path updates.

### Implementation for User Story 2

- [ ] T013 [US2] Update `tests/test_coordinator.py` imports so
  `AkuvoxCoordinatorData` and `AkuvoxDataUpdateCoordinator` still come from
  `custom_components.local_akuvox.coordinator`, while `RelayConfig`,
  `_build_relay_config`, and `_parse_config_int` come from
  `custom_components.local_akuvox.relay_config`. Do not change assertions or
  expected warning text. Covers FR-008 and FR-009.
- [ ] T014 [P] [US2] Update the local import in
  `tests/test_lock.py::test_relay_defaults_when_no_config_entry` so
  `AkuvoxCoordinatorData` still comes from
  `custom_components.local_akuvox.coordinator` and `RelayConfig` comes from
  `custom_components.local_akuvox.relay_config`. Do not change behavior
  assertions. Covers FR-008 and FR-009.
- [ ] T015 [US2] Keep the existing helper tests in `tests/test_coordinator.py`
  rather than adding `tests/test_relay_config.py`, because this repo already has
  direct regression coverage for the moved helpers. Only add a focused
  `tests/test_relay_config.py` if review finds the existing convention requires
  per-module helper tests; if added, move assertions without behavior changes and
  include SPDX header plus module docstring. Covers FR-008 and FR-009.
- [ ] T016 [US2] Run
  `uv run pytest tests/test_coordinator.py tests/test_lock.py -q` and fix only
  import-path or move-related failures. All assertions must remain behaviorally
  equivalent. Covers FR-006, FR-007, and FR-009.

**Checkpoint**: Existing tests exercise the same relay parsing, coordinator,
and lock behavior through the new helper module path.

______________________________________________________________________

## Phase 5: User Story 3 — Relay Config Parsing Is Cohesive (Priority: P2)

**Goal**: Ensure the new module owns only relay-config parsing and avoids
circular imports or unrelated coordinator responsibilities.

**Independent Test**: Inspect imports and module contents without any device
interaction.

### Implementation for User Story 3

- [ ] T017 [US3] Inspect
  `custom_components/local_akuvox/relay_config.py` and confirm it contains only
  `RelayConfig`, `_parse_config_int`, `_build_relay_config`, their required
  imports, `_LOGGER`, SPDX header, and docstrings. Do not move
  `AkuvoxCoordinatorData`, `RELAY_KEY_RE`, config fetch/cache methods, or device
  error handling into the new module. Covers FR-001, FR-012, and SC-006.
- [ ] T018 [US3] Verify import direction with
  `python -c "from custom_components.local_akuvox import coordinator, relay_config"`
  and confirm there is no circular import. Covers FR-012.

**Checkpoint**: The extracted module is cohesive and the dependency graph is
`const.py` → `relay_config.py` → `coordinator.py`.

______________________________________________________________________

## Phase 6: User Story 4 — Existing Quality Gates Remain Green (Priority: P2)

**Goal**: Prove the refactor keeps tests, linting, formatting, type checking,
docstrings, SPDX compliance, and aislop checks green.

**Independent Test**: All commands in this phase exit 0 before the
implementation PR is opened.

### Verification for User Story 4

- [ ] T019 [US4] Run `uv run pytest tests/ -q` and require 100% pass before any
  manual validation. Covers FR-009 and SC-003.
- [ ] T020 [US4] Run `uv run ruff check` and fix all lint errors without
  behavior changes. Covers FR-011.
- [ ] T021 [US4] Run `uv run ruff format --check` and fix formatting only if the
  check reports required changes. Covers FR-011.
- [ ] T022 [US4] Run `uv run pre-commit run mypy --all-files` and fix any type
  errors without changing runtime behavior. Covers FR-011.
- [ ] T023 [US4] Run `uv run pre-commit run interrogate --all-files` and verify
  docstring coverage remains 100%. Covers FR-011 and SC-004.
- [ ] T024 [US4] Stage the implementation files, then run
  `aislop ci --staged` and confirm it no longer reports
  `complexity/file-too-large` for
  `custom_components/local_akuvox/coordinator.py`. Covers FR-010, SC-001, and
  SC-002.
- [ ] T025 [US4] Run `uv run pre-commit run --all-files` before the
  implementation commit so reuse, markdownlint, gitlint, actionlint, aislop,
  interrogate, mypy, ruff, and other configured hooks are clean. Covers FR-011.

**Checkpoint**: All automated quality gates are green and the staged refactor
satisfies the spec success criteria.

______________________________________________________________________

## Phase 7: Implementation PR Commit Hygiene

**Purpose**: Preserve atomic commit history for the later implementation stage.

- [ ] T026 [US4] In the implementation PR, commit production and test changes as
  one refactor commit, then commit the `specs/009-coordinator-split/tasks.md`
  checkbox flips as a separate atomic docs commit after verification passes.
  Do not bundle checkbox updates with code/test changes.

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; start immediately.
- **Foundational leaf module (Phase 2)**: Depends on Setup completion and blocks
  coordinator/test import rewiring.
- **US1 coordinator size cleanup (Phase 3)**: Depends on the new module from
  Phase 2.
- **US2 behavior preservation (Phase 4)**: Depends on Phase 2 and should be
  completed after coordinator imports are updated in Phase 3.
- **US3 cohesion checks (Phase 5)**: Depends on Phases 2 and 3.
- **US4 quality gates (Phase 6)**: Depends on Phases 3 through 5.
- **Commit hygiene (Phase 7)**: Depends on all implementation and verification
  tasks.

### User Story Dependencies

- **US1 (P1)**: Requires Phase 2, then independently proves the size-gate fix.
- **US2 (P1)**: Requires Phase 2 and import rewiring; proves behavior remains
  unchanged through existing tests.
- **US3 (P2)**: Requires Phase 2 and Phase 3; proves cohesion and dependency
  direction.
- **US4 (P2)**: Requires all implementation stories; proves quality gates.

### Parallel Opportunities

- T001 and T003 can run in parallel after checkout because they read different
  state.
- T014 can run in parallel with T013 after `relay_config.py` exists because it
  edits a different test file.
- T020 and T021 can be checked independently after test imports compile.
- T022 and T023 can run independently after the code layout is complete.

## Implementation Strategy

### MVP First

1. Complete Setup and the foundational `relay_config.py` module.
2. Complete US1 to reduce `coordinator.py` below 400 lines.
3. Complete US2 import updates and targeted tests.
4. Stop and validate the MVP with line count, targeted tests, and aislop.

### Final Validation

1. Complete US3 cohesion checks.
2. Run all US4 verification gates.
3. Commit code/test changes separately from tasks.md checkbox flips in the later
   implementation PR.

## Notes

- `[P]` tasks touch different files or run independent checks.
- No public Home Assistant API, entity state, service schema, or user-facing
  behavior may change.
- Existing parser assertions are the red/green guard for this behavior-preserving
  move; new tests are only justified if review requires per-module placement.

<!-- markdownlint-enable MD013 -->
