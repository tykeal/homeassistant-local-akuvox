<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Tasks: Capability Report Service

**Input**: Design documents from
`/specs/012-capability-report-service/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
quickstart.md, and contracts/

**Tests**: Required. The constitution mandates code-level TDD, so
behavioral tests or fixture updates precede every production behavior
change except the early dependency-floor bump needed to import
`pylocal_akuvox.run_capability_report`.

**Organization**: Tasks are dependency-ordered and grouped by user story.
The MVP returns the default read-only report from a lock entity service;
later phases add write-mode pass-through, hard-gated OpenDoor evidence,
config-dir file output, metadata, and final verification.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel after prerequisites because it touches
  different files or runs an independent check.
- **[Story]**: User story from `spec.md` (US1, US2, US3) or
  cross-cutting quality work (US4).
- Each task names exact paths and maps to functional requirements (FR)
  and success criteria (SC).

## Path Conventions

- **Integration**: `custom_components/local_akuvox/`
- **Tests**: `tests/`
- **Spec docs**: `specs/012-capability-report-service/`
- **Upstream reference**:
  `/home/tykeal/repos/personal/homeassistant/pylocal-akuvox/`

______________________________________________________________________

## Phase 1: Setup and Dependency Floor

**Purpose**: Re-confirm live source facts, then make the v1.2.0 report API
importable before any tests import the new symbol.

- [X] T001 [US1] Re-confirm the checked-out upstream signature and export in
  the adjacent `pylocal-akuvox` checkout at
  `src/pylocal_akuvox/_capability_report.py` and
  `src/pylocal_akuvox/__init__.py` with this async API:

  ```python
  async def run_capability_report(
      device,
      *,
      write=False,
      open_door=False,
      open_door_user=None,
      open_door_password=None,
      timeout=None,
      redact_stdout=False,
      emit=None,
  ) -> dict[str, object]
  ```

  Also confirm custom/no-op emitters redirect stdout/stderr and therefore
  require serialized service execution. Covers FR-003, FR-015, SC-001,
  SC-002, SC-003, and SC-006.
- [X] T002 [US1] Raise the `pylocal-akuvox` floor from `>=1.0.0` to
  `>=1.2.0` in `custom_components/local_akuvox/manifest.json`,
  `pyproject.toml`, the `pyproject.toml` comments that mention v1.0.0,
  and any `.pre-commit-config.yaml` mypy hook dependency or comment that
  constrains the library version. Covers FR-018 and SC-006.
- [X] T003 [US1] Run `uv sync` from the repository root, commit the
  resulting `uv.lock` resolution in the implementation PR, and verify
  `uv lock --check` accepts `pylocal-akuvox>=1.2.0`. Covers FR-018 and
  SC-006.
- [X] T004 [P] [US1] Add dependency/import regression tests in the
  existing pin or service test location, such as `tests/test_services.py`,
  proving `manifest.json`, `pyproject.toml`, `uv.lock`, and the runtime
  import all resolve `pylocal-akuvox>=1.2.0` and export
  `run_capability_report`. This follows the documented dependency-floor TDD
  exception because T002 and T003 must make the symbol importable first.
  Covers FR-003, FR-018, FR-027, and SC-006.

**Checkpoint**: The v1.2.0 API is importable and live-source facts are
known before service tests import the symbol.

______________________________________________________________________

## Phase 2: Constants and Service Schema

**Purpose**: Add the stable service and field constants, then build the
schema with safe defaults and OpenDoor rejection before device entry.

### Tests for schema behavior

- [X] T005 [P] [US3] Add failing schema tests in `tests/test_services.py`
  for rejected `open_door=True` without `write=True`, missing
  `open_door_user`, missing `open_door_password`, and unused credentials
  when `open_door=False`; assert `_create_device` and upstream report are
  not invoked. Covers FR-005 through FR-009, FR-027, SC-003, and SC-004.
- [X] T006 [P] [US1] Add failing schema tests in `tests/test_services.py`
  for default `write=False`, default `open_door=False`, optional
  `save_to_file=False`, absent `file_name`, non-empty relay credential
  strings, and rejection of `file_name` when `save_to_file=False`.
  Covers FR-004 through FR-007, FR-024, FR-025, FR-027, and SC-001.

### Foundational implementation

- [X] T007 [US1] Add `SERVICE_RUN_CAPABILITY_REPORT` plus service field
  constants such as `CONF_REPORT_WRITE`, `CONF_REPORT_OPEN_DOOR`,
  `CONF_REPORT_OPEN_DOOR_USER`, `CONF_REPORT_OPEN_DOOR_PASSWORD`,
  `CONF_REPORT_SAVE_TO_FILE`, `CONF_REPORT_FILE_NAME`, and a reserved
  report-lock data key to `custom_components/local_akuvox/const.py`.
  Covers FR-001, FR-004 through FR-010, FR-024, FR-025, and SC-003.
- [X] T008 [US3] Add `SERVICE_RUN_CAPABILITY_REPORT_SCHEMA` and any
  private validation helper in `custom_components/local_akuvox/services.py`
  using `cv.make_entity_service_schema()`, voluptuous booleans, non-empty
  strings, and hard OpenDoor/file-output post-validation. Covers FR-004
  through FR-009, FR-019, FR-024, FR-025, FR-027, SC-001, and SC-003.

**Checkpoint**: Invalid OpenDoor and file-output combinations fail schema
validation before network, device-entry, write-mode, or relay effects.

______________________________________________________________________

## Phase 3: User Story 1 - Read-Only Report (Priority: P1) 🎯 MVP

**Goal**: A Local Akuvox lock entity service returns the upstream redacted
capability report with safe read-only defaults.

**Independent Test**: Call `local_akuvox.run_capability_report` against a
mocked lock entity with default fields and assert the response contains the
upstream redacted report under `report`, with no write or OpenDoor options.

### Tests for User Story 1

- [X] T009 [P] [US1] Extend `tests/conftest.py` with reusable mocks for a
  fresh `_create_device` path, context entry, `apply_capability_options`,
  and `pylocal_akuvox.run_capability_report`; keep existing coordinator
  device mocks separate. Covers FR-003, FR-010, FR-022, FR-027, SC-001,
  SC-004, and SC-005.
- [X] T010 [P] [US1] Add failing service behavior tests in
  `tests/test_lock.py` for a default read-only call: `_create_device(entry)`
  is used, `async with device` is entered, `apply_capability_options()` runs
  after entry, upstream receives `write=False`, `open_door=False`, no relay
  credentials, `timeout=None`, `redact_stdout=True`, and a no-op `emit`, and
  the response is `{"report": <redacted dict>}`. Include entry-time and
  upstream `AkuvoxValidationError` or generic `AkuvoxError` failure cases
  that raise controlled errors with no partial success. Covers FR-003,
  FR-010 through FR-017, FR-022, FR-027, SC-001, SC-004, and SC-005.
- [X] T011 [P] [US1] Add failing concurrency and unload tests in
  `tests/test_lock.py` and `tests/test_init.py` proving all config entries
  share one Home Assistant instance-wide report lock, concurrent upstream
  calls are serialized, and final unload removes only the reserved lock key
  while preserving existing domain-data cleanup. Covers FR-015, FR-027, and
  SC-006.
- [X] T012 [P] [US1] Add failing registration tests in
  `tests/test_services.py` proving `SERVICE_RUN_CAPABILITY_REPORT` is a
  `Platform.LOCK` entity service, dispatches to `run_capability_report`, and
  registers with `supports_response=SupportsResponse.ONLY`. Covers FR-001,
  FR-002, FR-019, FR-027, SC-001, and SC-006.

### Implementation for User Story 1

- [X] T013 [US1] Implement `AkuvoxLockEntity.run_capability_report()` in
  `custom_components/local_akuvox/lock.py` with a docstring, typed
  `ServiceResponse`, sanitized argument extraction, fresh `_create_device`,
  `async with device`, post-entry `apply_capability_options()` using
  `get_effective_attempt_unknown(entry)`, serialized upstream execution,
  and response `{"report": report}`. Covers FR-003, FR-010 through FR-015,
  FR-022, SC-001, SC-004, and SC-005.
- [X] T014 [US1] Update `custom_components/local_akuvox/services.py` to
  import the new constants and add `_register_report_services(hass)` after
  the existing domain helpers; register the new service on `Platform.LOCK`
  with `SERVICE_RUN_CAPABILITY_REPORT_SCHEMA`, `func` equal to the service
  name, and `SupportsResponse.ONLY`. Covers FR-001, FR-002, FR-019, and
  SC-001.
- [X] T015 [US1] Extend `async_register_services()` in
  `custom_components/local_akuvox/services.py` to call
  `_register_report_services(hass)` without changing existing schedule,
  user, contact, or group registrations. Covers FR-001, FR-002, FR-019,
  and SC-001.
- [X] T016 [US1] Update `custom_components/local_akuvox/__init__.py` so the
  reserved report-lock runtime key is ignored as a coordinator entry and is
  removed on final unload when no real config-entry coordinators or other
  runtime data remain. Covers FR-015 and SC-006.

**Checkpoint**: The MVP service is registered, response-only, read-only by
default, and isolated from the coordinator's long-lived device.

______________________________________________________________________

## Phase 4: User Story 2 - Write Evidence (Priority: P2)

**Goal**: `write=True` deliberately opts into the upstream write suite while
preserving unknown-capability safety and response redaction.

**Independent Test**: Invoke the service with `write=True` and assert the
mocked upstream report is called with `write=True`, OpenDoor disabled, and
all returned write, skip, failure, and deletion-verification data preserved.

### Tests for User Story 2

- [X] T017 [P] [US2] Add failing tests in `tests/test_lock.py` for
  `write=True` pass-through without OpenDoor credentials, preserving the
  upstream redacted report exactly under `response["report"]` and not
  storing, logging, or returning service credentials. Covers FR-004,
  FR-009, FR-013, FR-014, FR-023, FR-027, SC-002, and SC-004.
- [X] T018 [P] [US2] Add failing tests in `tests/test_lock.py` proving
  `attempt_unknown_capability` is read from the config entry, applied to the
  fresh entered device before upstream execution, lets UNKNOWN gates run
  only when opted in, never bypasses confirmed UNSUPPORTED behavior, and
  reports upstream `AkuvoxUnsupportedError` through the issue #149 repairs
  path with context `capability report service`. Covers FR-010 through
  FR-012, FR-016, FR-027, and SC-005.
- [X] T019 [P] [US2] Add failing diagnostics regression tests in
  `tests/test_diagnostics.py` proving diagnostics remain read-only, never
  imports or calls `run_capability_report`, and do not expose write-mode or
  OpenDoor service fields. Covers FR-022, FR-027, SC-001, and SC-006.

### Implementation for User Story 2

- [X] T020 [US2] Complete write-mode plumbing in
  `custom_components/local_akuvox/lock.py` so `write` is passed unchanged,
  upstream skipped/failed/write-test evidence is not reshaped, and raw
  relay or integration credentials are absent from logs, repairs, response
  metadata, and saved artifacts controlled by the integration. Covers
  FR-004, FR-009, FR-013, FR-014, FR-023, SC-002, and SC-004.
- [X] T021 [US2] Reuse the issue #149 repairs/logging path in
  `custom_components/local_akuvox/lock.py` for `AkuvoxUnsupportedError`,
  mapping context to `capability report service`; map other `AkuvoxError`
  subclasses to sanitized, actionable `HomeAssistantError` or
  `ServiceValidationError` without returning partial reports. Covers
  FR-016, FR-017, FR-027, SC-004, and SC-005.

**Checkpoint**: Write-mode evidence is opt-in, redacted, unknown-aware, and
uses existing controlled error surfaces.

______________________________________________________________________

## Phase 5: User Story 3 - Hard-Gated OpenDoor (Priority: P3)

**Goal**: OpenDoor can run only when the caller explicitly supplies
`write=True`, `open_door=True`, and both relay credentials in one call.

**Independent Test**: Invalid OpenDoor service calls fail before device
entry; the single valid combination passes relay credentials to upstream and
records the returned redacted report.

### Tests for User Story 3

- [X] T022 [P] [US3] Add failing tests in `tests/test_services.py` and
  `tests/test_lock.py` proving invalid OpenDoor combinations are rejected
  before `_create_device`, before `async with device`, and before upstream
  report invocation. Covers FR-005 through FR-008, FR-027, SC-003, and
  SC-004.
- [X] T023 [P] [US3] Add failing tests in `tests/test_lock.py` for the
  valid OpenDoor path: `write=True`, `open_door=True`, non-empty
  `open_door_user`, and non-empty `open_door_password` are passed to
  upstream, and neither credential is emitted by integration-controlled
  logs, errors, repairs, response metadata, or file metadata. Covers FR-005
  through FR-009, FR-021, FR-027, SC-003, and SC-004.

### Implementation for User Story 3

- [X] T024 [US3] Ensure `custom_components/local_akuvox/services.py` and
  `custom_components/local_akuvox/lock.py` enforce OpenDoor's hard gate,
  reject unused relay credentials when `open_door=False`, pass valid relay
  credentials only to upstream, and document the upstream v1.2.0 username
  debug-log caveat where user-facing text discusses OpenDoor. Covers FR-005
  through FR-009, FR-021, FR-027, SC-003, and SC-004.

**Checkpoint**: OpenDoor cannot actuate unless all explicit gate fields are
present and valid in the same write-mode service call.

______________________________________________________________________

## Phase 6: Config-Dir Report File Output

**Purpose**: Optionally save the same redacted report JSON below the Home
Assistant config directory without overwriting existing support evidence.

### Tests for file output

- [X] T025 [P] [US1] Add failing file-output tests in `tests/test_lock.py`
  for generated config-relative names under
  `local_akuvox/capability_reports/`, caller-provided relative `.json`
  names, nested relative names that stay inside the report directory, and
  response `file.path` without absolute host paths. Covers FR-024 through
  FR-026, FR-027, SC-004, and SC-006.
- [X] T026 [P] [US1] Add failing validation tests in `tests/test_lock.py`
  for empty `file_name`, absolute paths, `..` traversal, paths resolving
  outside the report directory, non-`.json` suffixes, existing targets,
  validated parent-directory creation failures, and late exclusive-create
  collisions; assert predictable path and directory failures occur before
  device entry. Covers FR-024 through FR-027, SC-004, and SC-006.
- [X] T027 [P] [US1] Add failing tests in `tests/test_lock.py` proving the
  saved file content is exactly `response["report"]` serialized as pretty
  UTF-8 JSON with a trailing newline, and file write failures do not leak
  secrets or raw host paths. Covers FR-013, FR-024 through FR-027, SC-004,
  and SC-006.

### Implementation for file output

- [X] T028 [US1] Implement config-dir path validation and response metadata
  in `custom_components/local_akuvox/lock.py`: base directory
  `<config>/local_akuvox/capability_reports/`, generated
  `<entry_id>-<YYYYMMDDTHHMMSSffffffZ>.json`, relative caller names only,
  `.json` suffix, containment checks, existing-target rejection, validated
  parent-directory creation before `_create_device()`, and config-relative
  `file.path`. Covers FR-024 through FR-026 and SC-004.
- [X] T029 [US1] Implement the non-blocking JSON write in
  `custom_components/local_akuvox/lock.py` using Home Assistant executor
  helpers for synchronous file work, reuse the already created validated
  parent directories, use exclusive creation for no-overwrite, and write
  only the upstream redacted report object, not the response wrapper. Covers
  FR-024 through FR-027, SC-004, and SC-006.

**Checkpoint**: Report file output is optional, safe, redacted,
config-relative, and never overwrites existing files.

______________________________________________________________________

## Phase 7: Service Metadata and Translations

**Purpose**: Expose the new service in Home Assistant with selectors,
examples, and strong physical-safety warnings.

### Tests for metadata

- [X] T030 [P] [US3] Add failing metadata tests in `tests/test_services.py`
  or existing translation tests proving `services.yaml`, `strings.json`, and
  `translations/en.json` define every new field, selector, label, and
  description. Covers FR-019, FR-020, FR-027, and SC-006.
- [X] T031 [P] [US3] Add failing text tests proving OpenDoor descriptions
  contain prominent warnings that it can actuate a relay, unlock a door, or
  affect access and that the caller must be authorized and physically
  present. Covers FR-021, FR-027, SC-003, and SC-004.
- [X] T032 [P] [US2] Add failing text tests proving `write` descriptions
  warn about throwaway create, modify, verify, delete operations plus
  upstream relay-trigger and device-config write checks. Covers FR-023,
  FR-027, SC-002, and SC-004.

### Metadata implementation

- [X] T033 [US1] Add `run_capability_report` to
  `custom_components/local_akuvox/services.yaml` with lock target,
  selectors, examples, `write`, `open_door`, `open_door_user`,
  `open_door_password` password selector, `save_to_file`, `file_name`, and
  strong write/OpenDoor warnings matching the runtime schema. Covers FR-019,
  FR-021, FR-023 through FR-025, and SC-003.
- [X] T034 [US1] Add matching service labels, field labels,
  descriptions, validation text, and pylocal-akuvox v1.2.0 capability text
  to `custom_components/local_akuvox/strings.json`. Covers FR-020,
  FR-021, FR-023, FR-027, SC-003, SC-004, and SC-006.
- [X] T035 [US1] Mirror the new service strings and v1.2.0 capability text
  in `custom_components/local_akuvox/translations/en.json`, keeping raw
  OpenDoor credentials out of translated errors and repairs placeholders.
  Covers FR-020, FR-021, FR-023, FR-027, SC-003, SC-004, and SC-006.

**Checkpoint**: Home Assistant users see safe defaults, response behavior,
write-mode warnings, file-output guidance, and OpenDoor physical-safety
warnings before calling the service.

______________________________________________________________________

## Phase 8: Error Paths, Coverage, and Final Validation

**Purpose**: Close remaining error-path coverage and run all local quality
gates required before the implementation PR.

- [X] T036 [P] [US4] Audit `tests/test_capability_error_paths.py`,
  `tests/test_lock.py`, and `tests/test_capability_support.py` after the
  targeted TDD tasks to confirm coverage for validation, unsupported,
  generic Akuvox, entry-time, and file-write failures; add only missing
  regression cases discovered by coverage or review. Covers FR-016, FR-017,
  FR-024, FR-027, SC-004, SC-005, and SC-006.
- [X] T037 [US4] Run targeted tests and fix only failures caused by this
  feature. Covers FR-027 and SC-006.

  ```bash
  uv run pytest tests/test_services.py tests/test_lock.py \
    tests/test_diagnostics.py tests/test_init.py \
    tests/test_capability_error_paths.py -q
  ```

- [X] T038 [US4] Run the full test suite and require 100% coverage with all
  tests passing. Covers FR-027 and SC-006.

  ```bash
  uv run pytest tests/ --cov=custom_components.local_akuvox \
    --cov-report=term-missing
  ```

- [X] T039 [P] [US4] Run
  `uv run ruff check custom_components/ tests/` and
  `uv run ruff format --check custom_components/ tests/`, fixing all lint
  or format failures without unrelated changes. Covers SC-006.
- [X] T040 [P] [US4] Run `uv run mypy custom_components tests` and fix all
  type errors, including any new mocks for `run_capability_report`, fresh
  devices, executor file writes, and response shapes. Covers SC-006.
- [X] T041 [P] [US4] Run
  `uv run interrogate custom_components tests -vv --fail-under=100` and
  keep docstring coverage at 100 for every new helper and service method.
  Covers SC-006.
- [X] T042 [US4] Stage the implementation files, run
  `npx --yes aislop@0.12.0 ci --staged`, and keep the aislop score at 100
  without broad suppressions. Covers SC-006.
- [X] T043 [US4] Run the configured hassfest validation through the
  existing GitHub Actions `validate.yaml` workflow or the supported local
  hassfest command if one is added before implementation, and require it to
  pass before merge. Covers FR-019, FR-020, and SC-006.
- [X] T044 [US4] Run `uv run pre-commit run --all-files` before the
  implementation commit so reuse, markdownlint, gitlint, actionlint,
  aislop, interrogate, mypy, ruff, and other configured hooks are clean.
  Covers SC-006.

**Checkpoint**: The feature is fully tested, type checked, linted,
documented, and validated with the repository's configured quality gates.

______________________________________________________________________

## Phase 9: Implementation PR Commit Hygiene

**Purpose**: Preserve atomic commit history for the later implementation
stage and close the GitHub issue only from that implementation PR.

- [X] T045 [US4] In the implementation PR, commit code, tests, metadata,
  dependency pins, and `uv.lock` as one or more atomic implementation
  commits whose final implementation commit message or PR body includes
  `Closes #189`; do not close the issue from this tasks-only stage. Covers
  SC-006.
- [X] T046 [US4] In the same implementation PR, flip completed checkboxes
  in `specs/012-capability-report-service/tasks.md` as a separate atomic
  docs commit after the implementation commits and successful verification.
  Covers SC-006.

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; start immediately. T002 and T003
  must complete before tests import `run_capability_report`.
- **Constants and schema (Phase 2)**: Depends on Phase 1 and blocks every
  service story.
- **US1 read-only report (Phase 3)**: Depends on schema constants and
  produces the MVP lock entity service.
- **US2 write evidence (Phase 4)**: Depends on US1 handler plumbing.
- **US3 OpenDoor gate (Phase 5)**: Depends on schema validation and US2
  write-mode pass-through.
- **File output (Phase 6)**: Depends on the US1 response wrapper and shares
  the same handler.
- **Metadata (Phase 7)**: Depends on the final runtime schema fields.
- **Final validation (Phase 8)**: Depends on all implementation phases.
- **Commit hygiene (Phase 9)**: Depends on all implementation and
  verification tasks.

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 1; delivers the read-only MVP and
  file-output foundations.
- **US2 (P2)**: Requires US1's upstream invocation and response wrapper.
- **US3 (P3)**: Requires US2 because OpenDoor is only valid in write mode.
- **US4**: Cross-cutting verification after all selected user stories.

### Parallel Opportunities

- T004 can run after T003 while schema planning starts.
- T005 and T006 can be written in parallel because they cover separate
  schema outcomes.
- T009 through T012 can be written in parallel after the schema exists.
- T017 through T019 can be written in parallel after the MVP handler exists.
- T022 and T023 can be written in parallel after OpenDoor schema is present.
- T025 through T027 can be written in parallel for independent file cases.
- T030 through T032 can be written in parallel for separate metadata text.
- T039 through T041 can run independently after the code is complete.

## Implementation Strategy

### MVP First

1. Complete the v1.2.0 pin bump and lock refresh.
2. Add constants, schema tests, and hard-gate schema validation.
3. Add mocks and the default read-only service tests.
4. Implement the fresh-device handler and lock service registration.
5. Stop and validate the MVP with targeted service and lock tests.

### Incremental Delivery

1. Add write-mode tests and pass-through without OpenDoor.
2. Add OpenDoor rejection and valid-pass-through tests.
3. Add config-dir file-output validation and exclusive write tests.
4. Add service metadata and translation warnings.
5. Run all verification tasks before opening the implementation PR.

## Notes

- `[P]` tasks touch different files or run independent checks.
- Keep diagnostics passive and read-only; do not move this feature into
  `diagnostics.py`.
- Use the fresh `_create_device(entry)` report path, not the coordinator's
  entered device.
- Do not re-litigate locked design decisions from `plan.md`.
- The implementation PR must not start until this tasks stage is merged.
