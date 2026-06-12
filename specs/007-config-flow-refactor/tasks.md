<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Tasks: Config Flow Refactor

**Input**: Design documents from `/specs/007-config-flow-refactor/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓,
contracts/ ✓, quickstart.md ✓

**Tests**: No new tests required — this is a pure structural refactor. Existing
tests serve as the "green" baseline (per Constitution Check, TDD principle).
Only import path updates are needed in test files.

**Organization**: Tasks are grouped by user story to enable independent
verification of each story's acceptance criteria post-refactor.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Integration source**: `custom_components/local_akuvox/`
- **Tests**: `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new module file with proper headers and imports

- [ ] T001 Create `custom_components/local_akuvox/options_flow.py` with SPDX
  header, module docstring, and import block per data-model.md import map

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extract the AkuvoxOptionsFlow class and wire up the import — MUST
be complete before any verification can proceed

**⚠️ CRITICAL**: No user story verification can succeed until this phase is
complete

- [ ] T002 Copy `AkuvoxOptionsFlow` class (lines 398–622) and `_build_schema`
  staticmethod from `custom_components/local_akuvox/config_flow.py` into
  `custom_components/local_akuvox/options_flow.py`
- [ ] T003 Remove `AkuvoxOptionsFlow` class (lines 398–622) from
  `custom_components/local_akuvox/config_flow.py`
- [ ] T004 Remove `OptionsFlow` from the `homeassistant.config_entries` import
  in `custom_components/local_akuvox/config_flow.py`
- [ ] T005 Remove now-unused imports from `config_flow.py` that are exclusively
  used by the options flow class (e.g., `OptionsFlow` from
  `homeassistant.config_entries`). Note: `secrets` MUST remain — it is used by
  ConfigFlow at line 302.
- [ ] T006 Add `from .options_flow import AkuvoxOptionsFlow` to
  `custom_components/local_akuvox/config_flow.py`
- [ ] T006a Add `custom_components.local_akuvox.options_flow` to the mypy module
  override in `pyproject.toml` to match the existing `config_flow` override.
  Verify with `uv run mypy custom_components/`.
- [ ] T007 Verify no circular import by running `uv run python -c "from
  custom_components.local_akuvox.config_flow import AkuvoxConfigFlow"` from repo
  root

**Checkpoint**: Module extraction complete — both files exist with correct
classes, no circular imports

---

## Phase 3: User Story 1 — Initial Setup Flow Preserved (Priority: P1) 🎯 MVP

**Goal**: Confirm `AkuvoxConfigFlow` remains fully functional in
`config_flow.py` — same steps, same validation, same config entry creation

**Independent Test**: Run config-flow test suite (lines 1–417 of
`tests/test_config_flow.py`) and all tests pass without modification

### Implementation for User Story 1

- [ ] T008 [US1] Verify `AkuvoxConfigFlow.async_get_options_flow` in
  `custom_components/local_akuvox/config_flow.py` correctly references imported
  `AkuvoxOptionsFlow`
- [ ] T009 [US1] Run initial setup flow tests: `uv run pytest
  tests/test_config_flow.py -k "not options" -v` — all must pass without any
  test file changes

**Checkpoint**: User Story 1 verified — initial setup flow works identically to
pre-refactor

---

## Phase 4: User Story 2 — Options Flow Preserved (Priority: P1)

**Goal**: Confirm `AkuvoxOptionsFlow` works from its new location — same forms,
same validation, same config entry updates

**Independent Test**: Run options-flow test suite (lines 418+ of
`tests/test_config_flow.py` and all of `tests/test_create_device.py`) and verify
all tests pass after patch path updates

### Implementation for User Story 2

- [ ] T011 [P] [US2] Update patch targets in `tests/test_config_flow.py` options
  webhook tests (lines 1077–1327): change
  `custom_components.local_akuvox.config_flow.AkuvoxDevice` to
  `custom_components.local_akuvox.options_flow.AkuvoxDevice` (3 occurrences)
- [ ] T012 [P] [US2] Update imports in `tests/test_create_device.py`: change
  `from custom_components.local_akuvox.config_flow import AkuvoxOptionsFlow` to
  `from custom_components.local_akuvox.options_flow import AkuvoxOptionsFlow` (3
  occurrences)
- [ ] T013 [US2] Run options flow tests: `uv run pytest
  tests/test_config_flow.py -k "options" -v` and `uv run pytest
  tests/test_create_device.py -v` — both must pass

**Checkpoint**: User Story 2 verified — options flow works identically from new
module location

---

## Phase 5: User Story 3 — Codebase Maintainability Improved (Priority: P2)

**Goal**: Verify structural quality — single responsibility per module, line
count limits, clean imports

**Independent Test**: Inspect file structure, measure line counts, confirm each
module is focused

### Implementation for User Story 3

- [ ] T014 [P] [US3] Verify `custom_components/local_akuvox/config_flow.py`
  contains only `AkuvoxConfigFlow` class and is under 400 lines: `wc -l
  custom_components/local_akuvox/config_flow.py`
- [ ] T015 [P] [US3] Verify `custom_components/local_akuvox/options_flow.py`
  contains only `AkuvoxOptionsFlow` class and is under 400 lines: `wc -l
  custom_components/local_akuvox/options_flow.py`
- [ ] T016 [US3] Verify SPDX header, type annotations, and docstrings are
  present on `custom_components/local_akuvox/options_flow.py` per project
  constitution

**Checkpoint**: User Story 3 verified — both modules are focused,
well-documented, and within size constraints

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all quality gates

- [ ] T017 [P] Run full test suite: `uv run pytest tests/ -v` — 100% pass rate
  (SC-001)
- [ ] T018 [P] Run linter: `uv run ruff check custom_components/ tests/` — zero
  errors (SC-005)
- [ ] T019 [P] Run type checker: `uv run mypy custom_components/` — zero errors
  (SC-005)
- [ ] T020 Verify no new dependencies added to
  `custom_components/local_akuvox/manifest.json` (FR-009)
- [ ] T021 Run quickstart.md verification checklist (all items green)
- [ ] T022 Verify existing config entry loading: confirm no migration logic is
  introduced and `async_setup_entry` works unchanged with pre-existing config
  entries (covered by existing integration tests)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion
- **User Story 2 (Phase 4)**: Depends on Phase 2 completion
- **User Story 3 (Phase 5)**: Depends on Phase 2 completion
- **Polish (Phase 6)**: Depends on ALL user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can verify after Phase 2 — No test file changes needed
  for config-flow tests
- **User Story 2 (P1)**: Can verify after Phase 2 — Requires options webhook
  patch path and import updates (T011–T012)
- **User Story 3 (P2)**: Can verify after Phase 2 — Pure inspection, no code
  changes

### Within Each Phase

- Phase 2 tasks MUST execute sequentially (T002 → T003 → T004 → T005 → T006 →
  T006a → T007)
- Phase 4 tasks T011 and T012 can run in parallel (different files/sections)
- Phase 5 tasks T014, T015 can run in parallel (different files)
- Phase 6 tasks T017, T018, T019 can run in parallel (independent tools)

### Parallel Opportunities

```text
After Phase 2 completes:
  ├── [US1] T008, T009 (no file changes needed)
  ├── [US2] T011 + T012 (parallel: different files/sections)
  └── [US3] T014 + T015 (parallel: different files)
```

---

## Parallel Example: User Story 2

```bash
# Launch all required test updates together (different files/sections):
Task: "Update patch targets in tests/test_config_flow.py \
options webhook tests (lines 1077–1327)"
Task: "Update imports in tests/test_create_device.py"

# Then verify:
Task: "Run options flow tests"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Create `options_flow.py` shell
2. Complete Phase 2: Extract class + wire import (CRITICAL — blocks all
   verification)
3. Complete Phase 3: Verify initial setup flow works (US1)
4. **STOP and VALIDATE**: `uv run pytest tests/test_config_flow.py -k "not
   options" -v`
5. Config flow refactor is functionally safe at this point

### Incremental Delivery

1. Phase 1 + Phase 2 → Module extraction complete
2. Phase 3 (US1) → Initial setup verified ✓
3. Phase 4 (US2) → Options flow verified ✓ (test patches applied)
4. Phase 5 (US3) → Structural quality confirmed ✓
5. Phase 6 → All quality gates pass → Ready for PR

### Single-Developer Strategy (Recommended)

This refactor is small enough for a single developer in one session:

1. Execute Phases 1–2 sequentially (extraction)
2. Apply required test updates (Phase 4: T011–T012 in parallel)
3. Run full validation (Phase 6: T017–T019 in parallel)
4. Verify line counts and structure (Phase 5: quick checks)
5. Single atomic commit with DCO sign-off

---

## Notes

- This is a **pure refactor** — zero behavior changes, zero new features
- [P] tasks = different files/sections, no dependencies
- [Story] label maps task to specific user story for traceability
- Existing tests are the sole verification mechanism (no new tests needed)
- All changes should result in a single atomic commit per project conventions
- If any test fails, the refactor has introduced a regression — revert and
  investigate
