<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Tasks: Capability Matrix Support

**Input**: Design documents from `/specs/011-capability-matrix-support/`
**Prerequisites**: plan.md (required), spec.md (required for user stories),
research.md, data-model.md, contracts/

**Tests**: Required. The constitution mandates code-level TDD, so every
production change below is preceded by focused failing tests or fixture work.
FR-022 and `quickstart.md` require the final implementation to keep pytest
coverage at 100%, the aislop score at 100%, interrogate at 100%, and all
configured pre-commit hooks passing.

**Organization**: Tasks are dependency-ordered and grouped by user story. The
MVP is the safe `pylocal-akuvox>=1.0.0` upgrade with controlled entry-time and
unsupported-capability behavior; later stories add the opt-in, entity
availability, and diagnostics/probe support.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel after its prerequisites are complete because it
  touches different files or runs an independent check.
- **[Story]**: User story from `spec.md` (US1, US2, US3, US4) or cross-cutting
  quality work (US5).
- Include exact file paths and map each task to functional requirements (FR) and
  success criteria (SC).

## Path Conventions

- **Integration**: `custom_components/local_akuvox/`
- **Tests**: `tests/`
- **Spec docs**: `specs/011-capability-matrix-support/`
- **Release metadata**: `.github/release-drafter.yml` and PR labels/title

______________________________________________________________________

## Phase 1: Setup and Live-Source Reconfirmation

**Purpose**: Re-check the live repository and upstream v1.0.0 API before any
implementation edits, then create a baseline for the breaking dependency bump.

- [ ] T001 [US1] Re-confirm upstream v1.0.0 symbols against the checked-out
  `pylocal-akuvox` v1.0.0 source or the upstream v1.0.0 tag, especially
  `_capability_types.py`, `_capability_profile.py`, `exceptions.py`,
  `device.py`, and `_capability_probe.py`:
  `Capability` members `USER_LIST`, `USER_ADD`, `USER_MODIFY`, `USER_DELETE`,
  `SCHEDULE_LIST`, `SCHEDULE_ADD`, `SCHEDULE_MODIFY`, `SCHEDULE_DELETE`,
  `GROUP_LIST`, `GROUP_ADD`, `GROUP_MODIFY`, `GROUP_DELETE`, `CONTACT_LIST`,
  `CONTACT_ADD`, `CONTACT_MODIFY`, `CONTACT_DELETE`, `RELAY_TRIGGER_API`,
  `RELAY_TRIGGER_FCGI`, `RELAY_STATUS`, `DEVICE_CONFIG_GET`,
  `DEVICE_CONFIG_SET`, `LOG_DOOR`, `LOG_CALL`, and `KEY_DISCOVERY`;
  `CapabilityStatus` values `SUPPORTED`, `UNSUPPORTED`, and `UNKNOWN`;
  `DeviceCapabilities.status_of()`, `require(..., allow_unknown=False)`,
  `supported_set`; `AkuvoxUnsupportedError.reason`, `.capability`, and
  `.device_class`; `AkuvoxDevice.capabilities`,
  `.attempt_unknown_capability`, and `probe_capabilities(timeout: float | None
  = None)`. Covers FR-001, FR-009, FR-013, FR-014, FR-018, and SC-001 through
  SC-007.
- [ ] T002 [US1] Inventory every current dependency pin and stale version comment
  with `rg "pylocal-akuvox|0\\.4\\.2|0\\.3\\.0" manifest.json pyproject.toml .pre-commit-config.yaml uv.lock`,
  confirming the implementation must update
  `custom_components/local_akuvox/manifest.json`, `pyproject.toml`,
  `.pre-commit-config.yaml`, and `uv.lock`. Covers FR-001 and SC-001.
- [ ] T003 [US1] Run `uv run pytest tests/ -q` from the repository root before
  edits and record any pre-existing failures in the implementation PR notes.
  This guards FR-021, FR-022, and SC-008.
- [ ] T004 [P] [US5] Run `uv run ruff check custom_components/ tests/` and
  `uv run ruff format --check custom_components/ tests/` before edits to capture
  the baseline lint and format state. Covers FR-022 and SC-008.

**Checkpoint**: Upstream capability facts, live paths, and baseline quality
status are known.

______________________________________________________________________

## Phase 2: Foundational Capability Plumbing

**Purpose**: Add dependency, option, repairs, and fixture foundations that block
all user stories.

**⚠️ CRITICAL**: No user story implementation may start until these tasks are
complete. Do not run `device.probe_capabilities()` from setup or config flow.

### Tests for foundational behavior

- [ ] T005 [P] [US1] Update `tests/conftest.py` so the shared `AkuvoxDevice`
  mock models the v1.0.0 lifecycle: `.capabilities` is `None` before entry and a
  `DeviceCapabilities` after `__aenter__`, `.attempt_unknown_capability` starts
  `False`, `__aenter__` can raise entry-time errors, and
  `probe_capabilities` is an `AsyncMock`. Include supported, unsupported,
  recognized-unknown, and unrecognized conservative-empty profile fixtures.
  Covers FR-002, FR-004, FR-014, FR-018, FR-021, SC-001, SC-002, and SC-008.
- [ ] T006 [P] [US1] Add failing tests in `tests/test_create_device.py` for an
  effective option reader and post-entry option application: missing
  `attempt_unknown_capability` resolves to `False`, options override data, and
  the helper sets `device.attempt_unknown_capability = True` only after entry.
  Covers FR-004, FR-005, FR-013, SC-004, and SC-008.
- [ ] T007 [P] [US1] Add failing repairs-helper tests in a new
  `tests/test_capability_support.py` for deduplicated
  `homeassistant.helpers.issue_registry` issue creation, safe placeholders from
  `AkuvoxUnsupportedError.reason`, `.capability`, `.device_class`, structured
  logging fields, and clearing by entry/reason/capability. Covers FR-009,
  FR-010, FR-011, FR-012, SC-003, SC-005, and SC-007.
- [ ] T008 [P] [US2] Add failing translation/schema tests in
  `tests/test_config_flow.py` and `tests/test_options_flow.py` proving the
  config flow and options flow expose `attempt_unknown_capability` with default
  `False`, preserve the current value, and include user-facing text in
  `custom_components/local_akuvox/strings.json` and
  `custom_components/local_akuvox/translations/en.json`. Covers FR-005 through
  FR-008,
  SC-004, and SC-008.

### Foundational implementation

- [ ] T009 [US1] Raise the dependency floor to `pylocal-akuvox>=1.0.0` in
  `custom_components/local_akuvox/manifest.json`, `pyproject.toml`, the
  `pyproject.toml` comments that reference 0.4.2 or older mypy-published
  versions, and the mypy `additional_dependencies` entry in
  `.pre-commit-config.yaml`. Covers FR-001 and SC-001.
- [ ] T010 [US1] Run `uv sync` or the repository's equivalent `uv lock` workflow
  after T009 and commit the resulting `uv.lock` update so the lockfile resolves
  `pylocal-akuvox>=1.0.0`. Verify with `uv lock --check`. Covers FR-001,
  FR-022, SC-001, and SC-008.
- [ ] T011 [US2] Add `CONF_ATTEMPT_UNKNOWN_CAPABILITY =
  "attempt_unknown_capability"` and `DEFAULT_ATTEMPT_UNKNOWN_CAPABILITY = False`
  to `custom_components/local_akuvox/const.py`, keeping existing config keys
  absent-safe. Covers FR-004, FR-005, FR-013, and SC-004.
- [ ] T012 [US2] Add setup-flow and options-flow strings for
  `attempt_unknown_capability`, plus repairs text for unsupported reasons, to
  `custom_components/local_akuvox/strings.json` and
  `custom_components/local_akuvox/translations/en.json`. The text must explain
  the breaking v1.0.0 default, the explicit opt-in, and that confirmed
  `UNSUPPORTED` remains blocked. Covers FR-006, FR-007, FR-008, FR-011,
  FR-020, SC-003, SC-004, SC-007, and SC-009.
- [ ] T013 [US1] Create `custom_components/local_akuvox/capability_support.py`
  with SPDX header, module docstring, `get_effective_attempt_unknown()`,
  `apply_capability_options()`, `is_capability_usable()`,
  `async_report_unsupported_capability()`, and
  `async_clear_unsupported_capability_issue()` helpers. Use
  `homeassistant.helpers.issue_registry`, map `AkuvoxUnsupportedError.reason`,
  `.capability`, and `.device_class` into safe repairs placeholders, and never
  log credentials, PINs, card codes, webhook ids, or raw response bodies. Covers
  FR-004, FR-009 through FR-014, FR-017, SC-003, SC-005, and SC-007.
- [ ] T014 [P] [US1] Update imports and typing in tests for `Capability`,
  `CapabilityStatus`, `DeviceCapabilities`, `FieldAliases`, and
  `AkuvoxUnsupportedError` from `pylocal_akuvox`, matching the v1.0.0 exported
  API. Covers FR-001, FR-021, FR-022, and SC-008.

**Checkpoint**: Dependency metadata, constants, translations, repairs helpers,
and capability-aware fixtures are in place.

______________________________________________________________________

## Phase 3: User Story 1 — Safe v1.0.0 Runtime (Priority: P1) 🎯 MVP

**Goal**: Supported devices continue to set up and run, while context-entry and
unsupported-capability failures become controlled Home Assistant outcomes.

**Independent Test**: With v1.0.0 mocks, setup, config validation, webhook
pushes, coordinator refreshes, lock actions, and services all handle entry-time
and `AkuvoxUnsupportedError` failures without uncaught exceptions.

### Tests for User Story 1

- [ ] T015 [P] [US1] Add failing tests in `tests/test_init.py` for
  `async_setup_entry` catching `AkuvoxAuthenticationError` as
  `ConfigEntryAuthFailed` and `AkuvoxConnectionError`, `AkuvoxParseError`,
  `AkuvoxDeviceError`, generic `AkuvoxError`, and `AkuvoxUnsupportedError` from
  `await device.__aenter__()` as controlled setup failures with cleanup. Covers
  FR-002, FR-003, FR-009, FR-012, SC-001, SC-002, SC-003, and SC-008.
- [ ] T016 [P] [US1] Add failing tests in `tests/test_config_flow.py` for
  `_async_test_connection` and `_async_push_webhook_config` when the
  v1.0.0 `/api/system/info` call fails at `async with device:` entry. Preserve
  existing `cannot_connect`, `invalid_auth`, `unknown`, and
  `webhook_push_failed` form outcomes. Covers FR-002, FR-003, FR-009, FR-012,
  SC-002, and SC-008.
- [ ] T017 [P] [US1] Add failing tests in `tests/test_options_flow.py` and
  `tests/test_init.py` for `_async_handle_webhook_change` and
  `async_remove_entry` handling entry-time and `set_device_config`
  `AkuvoxUnsupportedError` failures by creating repairs issues, logging details,
  and returning or logging the existing controlled webhook failure. Covers
  FR-002, FR-003, FR-009 through FR-012, SC-002, SC-003, and SC-008.
- [ ] T018 [P] [US1] Add failing coordinator tests in `tests/test_coordinator.py`
  for `AkuvoxCoordinatorData.capabilities`, `device.capabilities is None`,
  `RELAY_STATUS`, `DEVICE_CONFIG_GET`, and `USER_LIST` unsupported handling,
  fallback relay config or unchanged user cache behavior, repairs issue creation,
  and issue clearing after recovery. Covers FR-009 through FR-014, FR-017,
  SC-001, SC-003, SC-005, and SC-008.
- [ ] T019 [P] [US1] Add failing service-call tests in `tests/test_lock.py`,
  `tests/test_services.py`, and `tests/test_webhook.py` proving
  `AkuvoxUnsupportedError` from lock actions, schedule/user/contact/group entity
  services, and webhook background `USER_LIST` refresh is reported through
  repairs plus structured logs and converted to controlled Home Assistant errors
  where a user action cannot complete. Covers FR-009 through FR-012, FR-017,
  SC-003, SC-005, and SC-008.

### Implementation for User Story 1

- [ ] T020 [US1] Update `custom_components/local_akuvox/__init__.py` so
  `_create_device()` remains the config-entry device factory, setup reads the
  effective `attempt_unknown_capability` option, applies it immediately after
  `await device.__aenter__()`, catches v1.0.0 entry-time `AkuvoxError` failures,
  reports `AkuvoxUnsupportedError` through repairs, and clears entry-scoped
  unsupported issues on successful setup or permanent removal. Covers FR-002
  through FR-005, FR-009 through FR-014, SC-001 through SC-005.
- [ ] T021 [US1] Update `custom_components/local_akuvox/config_flow.py` to wrap
  every `async with device:` entry in the same error mapping used for first
  calls, apply `attempt_unknown_capability` after entry and before
  `get_info()` or `set_device_config()`, and report/clear flow-scoped repairs
  using a unique id or normalized host when `AkuvoxUnsupportedError` occurs
  before a `ConfigEntry` exists. Covers FR-002 through FR-006, FR-009 through
  FR-013, SC-002, SC-003, and SC-004.
- [ ] T022 [US1] Update `custom_components/local_akuvox/options_flow.py` so
  `_async_handle_webhook_change` applies the effective opt-in after context
  entry and before `set_device_config()`, catches entry-time and method
  `AkuvoxUnsupportedError`, reports repairs with entry context, and preserves
  `webhook_push_failed` for form errors. Covers FR-002 through FR-004, FR-007,
  FR-009 through FR-013, SC-002, SC-003, and SC-004.
- [ ] T023 [US1] Update `custom_components/local_akuvox/coordinator.py` to add
  `capabilities: DeviceCapabilities` to `AkuvoxCoordinatorData`, copy
  `device.capabilities` after context entry, fail controlled if it is `None`,
  handle `AkuvoxUnsupportedError` from `get_relay_status()`,
  `get_device_config()`, and `list_users()`, and clear repairs issues when later
  snapshots or successful operations prove recovery. Covers FR-009 through
  FR-014, FR-017, SC-001, SC-003, SC-005, and SC-008.
- [ ] T024 [US1] Update `custom_components/local_akuvox/lock.py` service and
  helper paths so every gated schedule, user, contact, group, and relay call
  catches `AkuvoxUnsupportedError` before the generic `AkuvoxError`, calls the
  repairs helper, logs `.reason` and `.capability`, and raises a controlled
  `HomeAssistantError` or `ServiceValidationError` without leaking secrets.
  Verify `custom_components/local_akuvox/services.py` registrations still map
  all 18 service names to these handled entity methods. Covers FR-009 through
  FR-012, FR-017, SC-003, SC-005, and SC-008.
- [ ] T025 [US1] Update `custom_components/local_akuvox/webhook.py` background
  user-cache refresh so a `USER_LIST` `AkuvoxUnsupportedError` reports repairs
  and logs structured reason/capability data without blocking the webhook
  response or spamming duplicate issues. Covers FR-009 through FR-012, FR-017,
  SC-003, SC-005, and SC-008.
- [ ] T026 [US1] Run targeted MVP tests with
  `uv run pytest tests/test_init.py tests/test_config_flow.py` plus
  `tests/test_options_flow.py tests/test_coordinator.py tests/test_lock.py` and
  `tests/test_services.py tests/test_webhook.py -q`, then fix only failures
  caused by the v1.0.0 adaptation. Covers FR-021,
  FR-022, SC-001 through SC-005, and SC-008.

**Checkpoint**: The integration has a safe supported-device MVP on
`pylocal-akuvox>=1.0.0` and all entry/unsupported failures are controlled.

______________________________________________________________________

## Phase 4: User Story 2 — Opt In Unknown Devices (Priority: P1)

**Goal**: Users can explicitly opt in to attempting `UNKNOWN` capabilities during
setup and later options, while confirmed `UNSUPPORTED` is never bypassed.

**Independent Test**: A new or existing entry absent the option defaults to
`False`; enabling it sets `device.attempt_unknown_capability` after entry and
allows only `UNKNOWN` gates to reach the device.

### Tests for User Story 2

- [ ] T027 [P] [US2] Extend `tests/test_config_flow.py` with failing tests for a
  new setup capability step after connection validation and before webhook
  setup. Assert the field defaults to `False`, stores in config entry data, and
  lets unrecognized `DEVICE_CONFIG_SET` proceed only when enabled. Covers
  FR-004 through FR-008, FR-013, SC-004, and SC-008.
- [ ] T028 [P] [US2] Extend `tests/test_options_flow.py` with failing tests that
  the editable opt-in is prefilled from options/data, updates entry options,
  reloads the integration, and is applied before webhook enable/disable pushes.
  Covers FR-004, FR-005, FR-007, FR-008, FR-013, SC-004, and SC-008.
- [ ] T029 [P] [US2] Extend `tests/test_lock.py` and `tests/test_services.py`
  with failing tests proving `UNKNOWN` capability calls are blocked with opt-in
  off, attempted with opt-in on, and confirmed `UNSUPPORTED` remains blocked for
  `RELAY_TRIGGER_API`, `CONTACT_ADD`, and representative user/schedule
  capabilities. Covers FR-013, FR-015 through FR-017, SC-004, SC-005, and
  SC-008.

### Implementation for User Story 2

- [ ] T030 [US2] Update `custom_components/local_akuvox/config_flow.py` to add a
  capability opt-in step after `_async_test_connection()` succeeds and before
  `async_step_webhook()`. Store `CONF_ATTEMPT_UNKNOWN_CAPABILITY` in entry data,
  default it to `DEFAULT_ATTEMPT_UNKNOWN_CAPABILITY`, and use it for any later
  setup-time webhook push. Covers FR-004 through FR-008, FR-013, and SC-004.
- [ ] T031 [US2] Update `custom_components/local_akuvox/options_flow.py` to add
  the same opt-in to `_build_schema()`, preserve the effective current value,
  save changes in entry options, and apply the changed value before any webhook
  config push in that options flow. Covers FR-004, FR-005, FR-007, FR-008,
  FR-013, and SC-004.
- [ ] T032 [US2] Update `custom_components/local_akuvox/__init__.py`,
  `config_flow.py`, and `options_flow.py` callers to consistently use the shared
  effective-option helper so existing config entries without the new key behave
  as `False` and options override data. Covers FR-004, FR-005, FR-013, and
  SC-004.
- [ ] T033 [US2] Run targeted opt-in tests with
  `uv run pytest tests/test_create_device.py tests/test_config_flow.py` plus
  `tests/test_options_flow.py tests/test_lock.py tests/test_services.py -q`,
  then fix only opt-in regressions. Covers FR-004 through FR-008, FR-013,
  FR-021, FR-022, SC-004, SC-005, and SC-008.

**Checkpoint**: Unknown-capability opt-in behavior is user-visible, persisted,
applied at the correct lifecycle point, and safe by default.

______________________________________________________________________

## Phase 5: User Story 3 — Capability-Driven Lock Availability (Priority: P2)

**Goal**: Relay entities and actions reflect the coordinator capability snapshot
instead of exposing controls for unsupported device features.

**Independent Test**: Lock entities read `coordinator.data.capabilities`; relay
state uses `RELAY_STATUS`; lock/unlock actions require usable
`RELAY_TRIGGER_API`; `RELAY_TRIGGER_FCGI` remains diagnostic-only.

### Tests for User Story 3

- [ ] T034 [P] [US3] Add failing `tests/test_lock.py` cases where
  `Capability.RELAY_STATUS` is `UNSUPPORTED` or `UNKNOWN` with opt-in off, and
  assert relay locks are not exposed as usable controls or remain unavailable
  with repairs guidance instead of polling blindly. Covers FR-014 through
  FR-017, SC-005, SC-006, and SC-008.
- [ ] T035 [P] [US3] Add failing `tests/test_lock.py` cases for
  `Capability.RELAY_TRIGGER_API`: `SUPPORTED` keeps actions usable, `UNKNOWN`
  plus opt-in passes `adapter=Capability.RELAY_TRIGGER_API`, `UNKNOWN` with
  opt-in off is unavailable, and `UNSUPPORTED` is unavailable even when
  `RELAY_TRIGGER_FCGI` is `SUPPORTED`. Covers FR-013 through FR-017, SC-004,
  SC-005, SC-006, and SC-008.

### Implementation for User Story 3

- [ ] T036 [US3] Update `custom_components/local_akuvox/lock.py` entity setup and
  entity properties to evaluate relay state availability with
  `is_capability_usable(coordinator.data.capabilities, Capability.RELAY_STATUS,
  attempt_unknown=...)` and avoid creating or using relay locks when status is
  confirmed unsupported. Covers FR-014 through FR-017, SC-005, and SC-006.
- [ ] T037 [US3] Update `custom_components/local_akuvox/lock.py` lock/unlock
  action paths to require usable `Capability.RELAY_TRIGGER_API`, to pass
  `adapter=Capability.RELAY_TRIGGER_API` only for supported or opted-in unknown
  API trigger attempts, and to treat `Capability.RELAY_TRIGGER_FCGI` as
  diagnostics evidence only. Covers FR-013 through FR-017, SC-004, SC-005, and
  SC-006.
- [ ] T038 [US3] Run `uv run pytest tests/test_lock.py tests/test_coordinator.py -q`
  and fix only capability-availability regressions. Covers FR-014 through
  FR-017, FR-021, FR-022, SC-005, SC-006, and SC-008.

**Checkpoint**: Lock entity state and actions are driven by the coordinator
capability snapshot.

______________________________________________________________________

## Phase 6: User Story 4 — Diagnostics and Capability Probe (Priority: P3)

**Goal**: Diagnostics expose sanitized capability evidence and run the upstream
safe probe only from the user-triggered diagnostics platform.

**Independent Test**: Diagnostics include current capability data, optionally run
`device.probe_capabilities(timeout=5.0)`, redact secrets, and report safe probe
errors without affecting setup.

### Tests for User Story 4

- [ ] T039 [P] [US4] Add failing tests in a new `tests/test_diagnostics.py` for
  `async_get_config_entry_diagnostics()` returning sanitized config-entry
  metadata, current `DeviceCapabilities` fields, non-sensitive notes, and no
  username, password, PIN, card code, webhook id, or raw response body. Covers
  FR-018, FR-019, FR-021, SC-007, and SC-008.
- [ ] T040 [P] [US4] Add failing diagnostics tests proving the user-triggered
  path calls `device.probe_capabilities(timeout=5.0)`, includes a successful
  merged probe profile, and records safe error summaries for
  `AkuvoxAuthenticationError`, `AkuvoxConnectionError`, `AkuvoxParseError`, and
  `AkuvoxUnsupportedError` without making setup depend on probe success. Covers
  FR-018, FR-019, FR-021, SC-007, and SC-008.

### Implementation for User Story 4

- [ ] T041 [US4] Create `custom_components/local_akuvox/diagnostics.py` with SPDX
  header and `async_get_config_entry_diagnostics(hass, entry) -> dict[str, Any]`.
  Read the coordinator capability snapshot, enter a device only for diagnostics
  probing when needed, call `device.probe_capabilities(timeout=5.0)` from this
  path only, and sanitize credentials, PINs, card codes, webhook ids, and raw
  response bodies. Covers FR-018, FR-019, FR-021, SC-007, and SC-008.
- [ ] T042 [US4] Add shared serialization/sanitization support in
  `custom_components/local_akuvox/capability_support.py` for
  `DeviceCapabilities` fields (`device_class`, `firmware_version`, capability
  statuses, field aliases, schema shapes, safe notes, and provenance summary)
  so diagnostics and repairs avoid raw secrets. Covers FR-010, FR-011, FR-018,
  FR-019, SC-007, and SC-008.
- [ ] T043 [US4] Run `uv run pytest tests/test_diagnostics.py tests/test_capability_support.py -q`
  and fix only diagnostics/probe failures. Covers FR-018, FR-019, FR-021,
  FR-022, SC-007, and SC-008.

**Checkpoint**: Capability diagnostics and the bounded probe path are available
without adding setup latency or exposing secrets.

______________________________________________________________________

## Phase 7: Release Notes and Final Validation

**Purpose**: Communicate the breaking change, run all quality gates, and prepare
clean implementation-stage commit hygiene.

- [ ] T044 [P] [US5] Update release metadata for the implementation PR: because
  no CHANGELOG file exists and `.github/release-drafter.yml` categorizes PRs by
  labels and `!` titles, ensure the implementation PR uses the `breaking-change`
  label or a conventional breaking title. The release text must cover
  `pylocal-akuvox>=1.0.0`, the extra `/api/system/info` context-entry request,
  default unrecognized-device failures, the **Attempt unknown capabilities**
  mitigation, confirmed `UNSUPPORTED` remaining blocked, and diagnostics/probe
  guidance. Covers FR-020 and SC-009.
- [ ] T045 [US5] Run the full test suite with coverage:
  `uv run pytest --cov=custom_components.local_akuvox --cov-report=term-missing tests/`
  and require 100% coverage before manual validation. Covers FR-021, FR-022, and
  SC-008.
- [ ] T046 [P] [US5] Run `uv run ruff check custom_components/ tests/` and fix
  all lint errors without changing intended behavior. Covers FR-022 and SC-008.
- [ ] T047 [P] [US5] Run `uv run ruff format --check custom_components/ tests/`
  and fix formatting only if the check reports required changes. Covers FR-022
  and SC-008.
- [ ] T048 [P] [US5] Run `uv run mypy custom_components tests` and fix all type
  errors against the v1.0.0 dependency surface. Covers FR-001, FR-022, and
  SC-008.
- [ ] T049 [P] [US5] Run
  `uv run interrogate -vv --fail-under=100 custom_components tests` and add or
  correct docstrings for every new helper, diagnostics function, and test helper
  until coverage remains 100%. Covers FR-022 and SC-008.
- [ ] T050 [P] [US5] Run `npx --yes aislop@0.12.0 ci` and split helpers if any
  finding drops below 100, especially in `lock.py`, `coordinator.py`,
  `capability_support.py`, and `diagnostics.py`. Covers FR-022 and SC-008.
- [ ] T051 [US5] Run `uv run pre-commit run --all-files` before the
  implementation commit so reuse, markdownlint, gitlint, actionlint, aislop,
  interrogate, mypy, ruff, and all configured hooks are clean. Covers FR-022 and
  SC-008.
- [ ] T052 [US5] In the implementation PR, use a breaking conventional commit
  with `!` and `Closes #149` for the code/release-note change after all quality
  gates pass, then commit the
  `specs/011-capability-matrix-support/tasks.md` checkbox flips as a separate
  atomic docs commit. Do not bundle checkbox updates with code, tests,
  dependency updates, or release metadata. Covers FR-020, FR-022, SC-008, and
  SC-009.

______________________________________________________________________

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies; start immediately.
- **Phase 2 (Foundational capability plumbing)**: Depends on Phase 1 and blocks
  all user stories.
- **Phase 3 (US1 safe runtime MVP)**: Depends on Phase 2.
- **Phase 4 (US2 opt-in)**: Depends on Phases 2 and 3 because setup, flow, and
  repairs helpers must exist before option behavior is user-visible.
- **Phase 5 (US3 lock availability)**: Depends on Phases 2 through 4 because it
  consumes coordinator capability data and the effective opt-in.
- **Phase 6 (US4 diagnostics)**: Depends on Phases 2 and 3; it may run in
  parallel with Phase 5 after the coordinator snapshot exists.
- **Phase 7 (Release and validation)**: Depends on all implementation stories.

### User Story Dependencies

- **US1 (P1)**: Requires dependency and helper foundations, then delivers the
  safe v1.0.0 MVP independently.
- **US2 (P1)**: Requires US1 entry/error handling, then adds the explicit
  unknown-capability opt-in.
- **US3 (P2)**: Requires coordinator capabilities and opt-in evaluation from US1
  and US2.
- **US4 (P3)**: Requires coordinator capabilities and shared sanitization but not
  lock availability.
- **US5 (Quality/release)**: Requires all desired user stories.

### Parallel Opportunities

- T004 can run in parallel with T001 through T003 because it is a read-only
  baseline quality check.
- T005 through T008 can be written in parallel after Phase 1 because they touch
  different test files.
- T014 can run in parallel with T009 through T013 after the v1.0.0 dependency
  surface is selected.
- T015 through T019 can be written in parallel after foundational helpers exist.
- T027 through T029 can be written in parallel after the opt-in constants exist.
- T034 and T035 can be written in parallel because they cover different lock
  capability rules.
- T039 and T040 can be written in parallel because they cover different
  diagnostics outcomes.
- T046 through T050 can run independently after all code and tests are complete.

## Implementation Strategy

### MVP First

1. Complete Phases 1 and 2 to establish the v1.0.0 dependency, constants,
   translations, repairs helpers, and capability-aware fixtures.
2. Complete Phase 3 so supported devices keep working and every entry-time or
   unsupported-capability failure is controlled.
3. Stop and validate the MVP with T026 before adding opt-in and availability
   refinements.

### Incremental Delivery

1. Add Phase 4 opt-in behavior and validate with T033.
2. Add Phase 5 lock availability and validate with T038.
3. Add Phase 6 diagnostics/probe support and validate with T043.
4. Finish Phase 7 release metadata and full quality gates.

### Final Validation

1. Run every command from `quickstart.md` before opening the implementation PR.
2. Verify release-drafter breaking-change metadata is present on the
   implementation PR.
3. Keep the implementation commit and later checkbox-flip commit atomic and
   signed off.

## Notes

- `[P]` tasks touch different files or run independent checks.
- Import capability symbols from `pylocal_akuvox`; do not invent integration
  string literals for enum members.
- `Capability.RELAY_TRIGGER_API` is required for current lock actions;
  `Capability.RELAY_TRIGGER_FCGI` is diagnostics-only until credentialed Open
  Relay Via HTTP support is designed.
- `device.probe_capabilities(timeout=5.0)` belongs to diagnostics only and must
  not run on first connect.
- Confirmed `UNSUPPORTED` capabilities are never bypassed by
  `attempt_unknown_capability`.
- The implementation PR must not start until this tasks stage is merged.

<!-- markdownlint-enable MD013 -->
