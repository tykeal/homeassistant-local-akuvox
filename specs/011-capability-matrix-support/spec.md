<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Feature Specification: Capability Matrix Support

**Feature Branch**: `011-capability-matrix-support` **Created**: 2026-06-30
**Status**: Draft **Input**: User description: "GitHub issue #149 requests
adapting Local Akuvox to the breaking `pylocal-akuvox` v1.0.0 capability
matrix, safe probe, and capability-aware API surface."

> **BREAKING CHANGE**: Devices whose model or firmware is not yet in the
> upstream curated capability matrix now fail service calls by default with
> `AkuvoxUnsupportedError(reason="device_unrecognized")`. Users can mitigate
> this only by enabling the explicit opt-in for unknown capabilities.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Safely on v1.0.0 (Priority: P1)

As a Home Assistant user with a supported Akuvox device, I need the integration
to set up and operate after upgrading to `pylocal-akuvox` v1.0.0, while users
with unsupported or unrecognized capabilities receive actionable Home Assistant
feedback instead of crashed entities, failed setup traces, or swallowed errors.

**Why this priority**: The dependency upgrade is required before any other
capability-matrix behavior can be used. The upstream library now performs an
HTTP `/api/system/info` call at context entry and gates every service method, so
current setup, config-flow, coordinator, and entity paths must be safe first.

**Independent Test**: Can be tested by installing the v1.0.0 dependency and
exercising setup, config flow validation, options flow webhook updates,
coordinator refreshes, lock actions, and registered services with mocked
`SUPPORTED`, `UNSUPPORTED`, and unrecognized-device profiles.

**Acceptance Scenarios**:

1. **Given** a curated device whose required capability is `SUPPORTED`, **When**
   setup enters `AkuvoxDevice`, refreshes data, and a service method is called,
   **Then** the call proceeds with the same user-visible behavior as before the
   library upgrade.
1. **Given** credentials, network, or parse failures now surface from
   `/api/system/info` during `async with AkuvoxDevice`, **When** setup, config
   flow, options flow, or webhook cleanup enters the context, **Then** existing
   Home Assistant error handling catches the failure at the entry site and
   reports the appropriate setup, reauth, form, or logged failure state.
1. **Given** a curated matrix entry marks a capability `UNSUPPORTED`, **When** an
   entity action, coordinator fetch, webhook configuration push, or registered
   entity service calls the corresponding library method, **Then** the
   integration logs `AkuvoxUnsupportedError.reason` and `.capability`, creates or
   updates an actionable Home Assistant repairs issue or notification, and does
   not crash setup or the entity.
1. **Given** no matrix entry exists for the device model or firmware, **When** a
   service method is called with the opt-in disabled, **Then** the library raises
   `AkuvoxUnsupportedError(reason="device_unrecognized")` and the integration
   surfaces a migration message telling the user how to enable the opt-in.

______________________________________________________________________

### User Story 2 - Opt In Unknown Devices (Priority: P1)

As a user whose device or firmware is not yet curated upstream, I can choose an
explicit `attempt_unknown_capability` option during setup and later in options,
so I can intentionally retain pre-upgrade behavior for `UNKNOWN` capabilities
while still respecting confirmed `UNSUPPORTED` capabilities.

**Why this priority**: Without this opt-in, unrecognized devices hard-fail on
every gated call. The default must remain safe (`False`) because attempting
unknown device operations can produce real device-side errors.

**Independent Test**: Can be tested by completing the config flow with the new
option absent, disabled, and enabled; editing the same value in options; and
asserting that every newly entered `AkuvoxDevice` receives
`device.attempt_unknown_capability = True` only after context entry when the
stored option is enabled.

**Acceptance Scenarios**:

1. **Given** a new user is configuring the integration, **When** the setup flow
   shows capability options, **Then** `attempt_unknown_capability` is present,
   defaults to `False`, and explains the breaking behavior and safety tradeoff.
1. **Given** an existing config entry, **When** the user opens the options flow,
   **Then** the same option is shown with its current value and can be changed
   without recreating the entry.
1. **Given** an unrecognized device whose capabilities resolve to all
   `UNKNOWN`, **When** the option is enabled and a service method is called,
   **Then** `UNKNOWN` gates are allowed through to the device and normal network,
   parse, validation, or device errors still surface normally.
1. **Given** a curated device whose capability is confirmed `UNSUPPORTED`,
   **When** the option is enabled, **Then** the call still raises
   `AkuvoxUnsupportedError` and the integration does not bypass the confirmed
   negative matrix entry.

______________________________________________________________________

### User Story 3 - Hide Unsupported Entities (Priority: P2)

As a Home Assistant user, I only see or can operate entities whose underlying
Akuvox capability is available for my device, so unsupported device features do
not appear as broken controls.

**Why this priority**: Capability-driven availability is the primary user-visible
benefit of the upstream matrix after the dependency upgrade and opt-in safety
paths are in place.

**Independent Test**: Can be tested by seeding coordinator data with
`DeviceCapabilities` profiles that mark relay status or relay trigger variants
as `SUPPORTED`, `UNSUPPORTED`, or `UNKNOWN`, then asserting which lock entities
are added, unavailable, or disabled and whether service calls are blocked before
network dispatch.

**Acceptance Scenarios**:

1. **Given** `device.capabilities.status_of(Capability.RELAY_STATUS)` is
   `UNSUPPORTED`, **When** the coordinator refreshes, **Then** relay state fetch
   is treated as unsupported and relay lock entities are not exposed as usable
   controls.
1. **Given** both relay trigger variants are confirmed unsupported
   (`Capability.RELAY_TRIGGER_API` and `Capability.RELAY_TRIGGER_FCGI`), **When**
   lock entities are built, **Then** relay-trigger actions are unavailable or the
   entities are disabled rather than attempting a doomed command.
1. **Given** a capability is `UNKNOWN` and the opt-in remains disabled, **When**
   a related entity or service is evaluated, **Then** the integration behaves
   conservatively and surfaces guidance rather than silently attempting the
   operation.
1. **Given** a capability is `UNKNOWN` and the opt-in is enabled, **When** a
   related entity or service is evaluated, **Then** the integration may keep the
   entity usable while preserving diagnostics for any resulting device failure.

______________________________________________________________________

### User Story 4 - Probe and Diagnose Capabilities (Priority: P3)

As a maintainer or advanced user troubleshooting firmware compatibility, I can
obtain capability diagnostics, optionally run the upstream safe probe, and send
structured details upstream without guessing which API path failed.

**Why this priority**: Probe and diagnostics improve support for new firmware but
are not required for the minimum safe v1.0.0 adaptation.

**Independent Test**: Can be tested with mocked `probe_capabilities()` profiles
and `AkuvoxUnsupportedError` instances that carry each known reason code:
`device_unrecognized`, `capability_missing`, `capability_unknown`,
`adapter_missing`, and `envelope_unsupported`.

**Acceptance Scenarios**:

1. **Given** a user or diagnostic path requests probing, **When**
   `device.probe_capabilities()` runs, **Then** the integration records or uses
   the merged profile returned by the library without regressing curated
   `SUPPORTED` or `UNSUPPORTED` evidence.
1. **Given** a probe sees unsupported or unknown read endpoints, **When**
   diagnostics are generated, **Then** they include the capability statuses,
   relevant notes, and non-sensitive failure context.
1. **Given** any capability gate raises `AkuvoxUnsupportedError`, **When** the
   integration logs and surfaces it, **Then** the log includes `.reason`,
   `.capability`, and device context where available.

### Edge Cases

- `AkuvoxDevice.capabilities` is `None` before context entry. The integration
  must only read it after `__aenter__` succeeds, and tests must model that
  lifecycle.
- `__aenter__` now calls `/api/system/info`. Auth, connection, and parse errors
  that used to happen on `device.get_info()` or the first service call may now
  happen before the body of an `async with` block executes.
- The library tears down the HTTP session if `__aenter__` raises. The integration
  must widen exception handling but must not add duplicate cleanup that masks the
  original error.
- `attempt_unknown_capability=True` permits `UNKNOWN` capability calls to reach
  the device. It does not permit `UNSUPPORTED` capabilities, validation errors,
  adapter-missing errors, or real network, auth, parse, and device failures.
- A device can be recognized while one specific capability is `UNKNOWN`; that
  uses `reason="capability_unknown"`, not `device_unrecognized`.
- A device not in the matrix receives a conservative-empty profile with a
  `device_not_in_matrix` note; `require()` reports
  `reason="device_unrecognized"` for gated service methods.
- Relay trigger support is represented by two variant capabilities,
  `RELAY_TRIGGER_API` and `RELAY_TRIGGER_FCGI`, not one generic relay-trigger
  enum member.
- The upstream probe is read-only and deterministic but performs nine requests;
  user-facing flows must account for the added latency and timeout behavior.
- Repair or persistent-notification records must be deduplicated so a polling
  coordinator does not spam users on every refresh.
- Existing test fixtures mock `AkuvoxDevice` heavily. They must be updated in the
  implementation stage so mocked context entry, `.capabilities`,
  `.attempt_unknown_capability`, and `probe_capabilities()` match v1.0.0.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The integration MUST upgrade every `pylocal-akuvox`
  dependency version requirement or constraint used by runtime, development,
  and type-checking metadata by raising the minimum accepted version to
  `pylocal-akuvox>=1.0.0`. This includes
  `custom_components/local_akuvox/manifest.json`, `pyproject.toml`, and the mypy
  `additional_dependencies` entry in `.pre-commit-config.yaml`.
- **FR-002**: The integration MUST adapt all device context-entry sites to the
  v1.0.0 `__aenter__` behavior that performs `/api/system/info`. Covered sites
  include `async_setup_entry` in `__init__.py`, webhook cleanup in
  `__init__.py`, `_async_test_connection` and `_async_push_webhook_config` in
  `config_flow.py`, and `_async_handle_webhook_change` in `options_flow.py`.
- **FR-003**: Each context-entry site MUST catch and map authentication,
  connection, parse, and other `AkuvoxError` failures that now surface at entry
  to the same Home Assistant outcomes users already receive for those failures.
- **FR-004**: After every successful context entry, the integration MUST apply
  the stored `attempt_unknown_capability` setting to the device by setting
  `device.attempt_unknown_capability = True` only when the option is enabled.
- **FR-005**: The new config key for the opt-in MUST be stored with config entry
  data or options using the existing `CONF_*` constant pattern, MUST default to
  `False`, and MUST be absent-safe for existing entries.
- **FR-006**: The setup config flow MUST expose the opt-in with clear text that
  states unrecognized devices fail by default after the v1.0.0 upgrade and that
  enabling the option attempts unproven operations.
- **FR-007**: The options flow MUST expose the same opt-in, preserve the current
  value, and reload the integration when it changes.
- **FR-008**: `strings.json` and all translation files MUST include labels and
  descriptions for the opt-in and any new errors, repair text, or notification
  text introduced by this feature.
- **FR-009**: The implementation MUST handle `AkuvoxUnsupportedError` at every
  path that calls a gated library service method, including coordinator fetches,
  lock entity actions, registered schedule/user/contact/group services, webhook
  configuration pushes, and removal-time webhook disable pushes.
- **FR-010**: `AkuvoxUnsupportedError` handling MUST log structured information
  from `.reason` and `.capability` whenever present and include device or config
  entry context when available.
- **FR-011**: `AkuvoxUnsupportedError` handling MUST create or update an
  actionable Home Assistant repairs issue or persistent notification that tells
  users whether the device is unrecognized, a capability is unsupported, a
  capability is unknown, no adapter exists, or the device returned an unsupported
  envelope. The exact Home Assistant surface may be selected during planning,
  but it must be user-visible and deduplicated.
- **FR-012**: Unsupported capability handling MUST prevent setup, coordinator
  refresh, and entity/service calls from crashing due solely to an
  `AkuvoxUnsupportedError`. Home Assistant errors may still be raised when a
  user action cannot be completed, but they must be controlled and actionable.
- **FR-013**: The opt-in MUST NOT bypass confirmed `UNSUPPORTED` statuses,
  relay adapter validation, missing relay adapters, or real network, auth,
  parse, validation, and device errors.
- **FR-014**: The coordinator MUST make the effective `DeviceCapabilities`
  profile available to platforms after context entry by reading
  `device.capabilities` and carrying or exposing it with coordinator state.
- **FR-015**: Entity setup and availability logic MUST use the coordinator's
  capabilities to hide, disable, or mark unavailable entities whose required
  capabilities resolve to `UNSUPPORTED`.
- **FR-016**: Relay lock behavior MUST account for both relay state and relay
  trigger capabilities. `RELAY_STATUS` governs state polling, and
  `RELAY_TRIGGER_API`/`RELAY_TRIGGER_FCGI` govern trigger actions.
- **FR-017**: Service handlers SHOULD avoid dispatching to the library when the
  required capability is already known to be `UNSUPPORTED`; if dispatch still
  occurs, the resulting `AkuvoxUnsupportedError` MUST be handled per FR-009
  through FR-012.
- **FR-018**: The integration MUST optionally support
  `device.probe_capabilities()` either on first successful connect or behind a
  diagnostic/debug action. Probe results MUST be treated as a merged profile
  returned by the library, where probe `SUPPORTED` or `UNSUPPORTED` evidence
  wins and probe `UNKNOWN` does not regress curated matrix evidence.
- **FR-019**: Capability diagnostics MUST expose non-sensitive capability
  statuses, relevant profile notes, and unsupported-error reason details useful
  for upstream matrix updates.
- **FR-020**: Release documentation MUST describe this as a breaking change,
  including the new default failure mode for uncurated devices, the mitigation by
  enabling the opt-in, and the extra `/api/system/info` round trip at context
  entry.
- **FR-021**: Tests MUST be updated for v1.0.0 lifecycle behavior, including
  capability-aware mocks, entry-time `/api/system/info` failures,
  `AkuvoxUnsupportedError` handling, opt-in defaults, options edits, entity
  availability, and diagnostics/probe behavior.
- **FR-022**: The implementation MUST keep all configured quality gates green,
  including ruff, mypy, reuse, markdown linting, pre-commit, full pytest coverage
  at 100%, aislop passing with no findings, and interrogate docstring coverage
  at 100%.

### Key Entities

- **Capability**: Upstream enum of canonical capability identifiers. Current
  members are `USER_LIST`, `USER_ADD`, `USER_MODIFY`, `USER_DELETE`,
  `SCHEDULE_LIST`, `SCHEDULE_ADD`, `SCHEDULE_MODIFY`, `SCHEDULE_DELETE`,
  `GROUP_LIST`, `GROUP_ADD`, `GROUP_MODIFY`, `GROUP_DELETE`, `CONTACT_LIST`,
  `CONTACT_ADD`, `CONTACT_MODIFY`, `CONTACT_DELETE`, `RELAY_TRIGGER_API`,
  `RELAY_TRIGGER_FCGI`, `RELAY_STATUS`, `DEVICE_CONFIG_GET`,
  `DEVICE_CONFIG_SET`, `LOG_DOOR`, `LOG_CALL`, and `KEY_DISCOVERY`.
- **CapabilityStatus**: Upstream three-valued status: `SUPPORTED` proceeds,
  `UNSUPPORTED` fails fast regardless of opt-in, and `UNKNOWN` fails fast unless
  `attempt_unknown_capability` is enabled.
- **DeviceCapabilities**: Immutable effective capability profile populated after
  context entry. It includes device class, firmware version, capability statuses,
  field aliases, schema shapes, notes, and optional provenance. Its
  `require(capability, allow_unknown=False)` method raises structured
  `AkuvoxUnsupportedError` for unsupported or disallowed unknown capabilities.
- **Attempt Unknown Capability Option**: Home Assistant config entry setting that
  defaults to `False` and maps to `AkuvoxDevice.attempt_unknown_capability` after
  context entry. It allows only `UNKNOWN` capabilities to proceed.
- **Unsupported Capability Repair/Notification**: Deduplicated user-visible Home
  Assistant issue that records the unsupported reason, capability, affected
  entry or entity, and mitigation guidance.
- **Capability Probe Result**: Profile returned by `device.probe_capabilities()`
  after the upstream deterministic nine-call, read-only probe sequence. It can
  augment diagnostics or the runtime profile without mutating user secrets.

## Breaking Changes & Migration

Existing users can see a behavior change immediately after the dependency moves
to `pylocal-akuvox` v1.0.0:

- `async with AkuvoxDevice(...)` performs one extra HTTP request to
  `/api/system/info` to identify the device and populate the capability profile.
  Connection, authentication, and parse failures may therefore happen earlier in
  setup, config flow, options flow, and webhook cleanup.
- Service methods no longer blindly call the device. They first check the
  effective capability profile.
- Curated devices with `SUPPORTED` capabilities continue to operate normally.
- Curated devices with `UNSUPPORTED` capabilities now fail fast before network
  dispatch for those operations. The integration must hide, disable, or report
  those operations as unsupported.
- Devices or firmware not yet in the upstream matrix receive a conservative
  profile where capabilities are effectively `UNKNOWN`. By default, every gated
  method raises `AkuvoxUnsupportedError(reason="device_unrecognized")`.

Migration and mitigation:

1. Users with unrecognized devices can open setup or options and enable the
   `attempt_unknown_capability` opt-in.
1. After the opt-in is enabled, `UNKNOWN` operations are attempted against the
   device, preserving pre-upgrade behavior for those calls.
1. The opt-in is intentionally not enabled by default and does not bypass
   confirmed `UNSUPPORTED` capabilities.
1. Users should share diagnostics or probe results upstream so their model and
   firmware can be added to the curated capability matrix.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With `pylocal-akuvox` v1.0.0 installed, a curated device profile
  with required capabilities marked `SUPPORTED` sets up, refreshes, exposes lock
  entities, and executes existing supported services without user-visible
  regressions.
- **SC-002**: Every context-entry path handles `/api/system/info` authentication,
  connection, and parse failures at the entry line and maps them to controlled
  Home Assistant form, setup, options, cleanup, or log outcomes.
- **SC-003**: An unrecognized device with the opt-in disabled produces a
  deduplicated repairs issue or notification that identifies
  `reason="device_unrecognized"`, explains the breaking change, and tells the
  user how to enable the opt-in.
- **SC-004**: The same unrecognized device with the opt-in enabled allows
  `UNKNOWN` capability calls to proceed to the device while still reporting
  normal device, network, auth, parse, validation, and confirmed unsupported
  failures.
- **SC-005**: A capability marked `UNSUPPORTED` never reaches network dispatch
  because the integration pre-checks it or the library raises first, and the
  user sees an actionable controlled failure rather than a crash.
- **SC-006**: Entities whose required capabilities are `UNSUPPORTED` are hidden,
  disabled, or unavailable according to the final design, and tests assert the
  chosen behavior.
- **SC-007**: Capability diagnostics include reason and capability details for
  all known unsupported reason codes without exposing credentials, PINs, card
  codes, or raw secrets.
- **SC-008**: The implementation stage updates the existing tests and adds new
  coverage so the full test suite passes with 100% coverage, aislop reports
  no findings, and interrogate reports 100% docstring coverage.
- **SC-009**: Release notes or release-drafter content mark the upgrade as a
  breaking change and document the opt-in migration path.

## Assumptions

- This stage produces only `spec.md`. Planning, task generation, implementation,
  tests, and release-note edits are deferred to later stages.
- Issue #149 remains open after this spec stage. A later implementation stage
  will close it when code, tests, quality gates, and release documentation are
  complete.
- The exact Home Assistant mechanism for user-visible unsupported-capability
  surfacing may be selected during planning. Repairs issues are preferred when
  supported by the target Home Assistant APIs; persistent notifications are an
  acceptable fallback if repairs cannot represent the condition cleanly.
- Existing config entries do not contain the new opt-in key. Missing values are
  interpreted as `False`.
- Capability-driven entity behavior may be implemented as disabled entities,
  unavailable entities, or omitted entities, but the final design must be
  consistent, documented, and tested.
- Probe execution may be automatic on first successful connect or manually
  triggered through diagnostics/debug tooling. The implementation must choose the
  least surprising behavior for users and avoid unexpected long setup delays.

## Dependencies

- **GitHub Issue #149**: Source of the agreed scope for the breaking
  capability-matrix adaptation.
- **Upstream `pylocal-akuvox` v1.0.0**: Provides `Capability`,
  `CapabilityStatus`, `DeviceCapabilities`, `FieldAliases`, `SchemaShape`,
  `AkuvoxDevice.capabilities`, `AkuvoxDevice.attempt_unknown_capability`,
  `AkuvoxDevice.probe_capabilities()`, and structured
  `AkuvoxUnsupportedError` fields.
- **Home Assistant Config and Options Flows**: Must expose and persist the
  opt-in setting while preserving current connection, SSL, auth, request-delay,
  and webhook options.
- **Coordinator and Lock Platform**: Must consume capabilities after context
  entry and drive entity availability, refresh behavior, and service error
  handling.
- **Existing Tests and Fixtures**: Must be updated to model the v1.0.0 lifecycle
  and capability-aware service gating.
