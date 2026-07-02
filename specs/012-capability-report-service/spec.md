<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Feature Specification: Capability Report Service

**Feature Branch**: `012-capability-report-service`
**Created**: 2026-07-02
**Status**: Draft
**Input**: User description: "GitHub issue #189 requests a Home Assistant
service/action that returns the full redacted `pylocal-akuvox` capability
report, including optional write-mode and hard-gated OpenDoor evidence for
upstream `new_device` submissions."

This additive feature complements the existing read-only diagnostics download.
Diagnostics stay passive; the new service is the deliberate report-generation
surface for maintainers and advanced users.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Return Read-Only Report (Priority: P1)

As a maintainer or owner of a not-yet-curated Akuvox device, I can call a Home
Assistant service for a configured Local Akuvox lock entity and receive the
full redacted capability report without running the upstream CLI.

**Why this priority**: The read-only report is the minimum useful evidence for
an upstream `new_device` issue and does not mutate device data.

**Independent Test**: Can be tested by calling
`local_akuvox.run_capability_report` against a mocked configured lock entity
with default parameters and asserting the service response is the upstream
redacted report dictionary.

**Acceptance Scenarios**:

1. **Given** a configured Local Akuvox lock entity and default service fields,
   **When** the user calls `local_akuvox.run_capability_report`, **Then** Home
   Assistant returns a response containing the redacted report dictionary and
   does not create, modify, delete, or open anything on the device.
1. **Given** the report service completes successfully, **When** the response is
   inspected, **Then** it includes the upstream report sections for device
   identity, authentication mode, observed schemas, tests, and HTTP event
   evidence suitable for the `pylocal-akuvox` `new_device` template.
1. **Given** integration credentials contain a password, PIN, card code, phone,
   MAC address, IP address, or user identifier, **When** the service response is
   returned, **Then** those values are redacted and no raw secret is exposed.

______________________________________________________________________

### User Story 2 - Run Full Write Evidence (Priority: P2)

As a maintainer or device owner who accepts temporary test writes and the full
upstream write-suite side effects, I can set `write=True` so the report records
whether throwaway users, schedules, groups, and contacts can be created,
modified, verified, and deleted, plus any non-OpenDoor relay and device-config
write checks the upstream report suite performs.

**Why this priority**: Write-mode evidence is what changes capability status
from `unknown` or inconclusive to `supported` for devices that are not yet in
the curated upstream matrix.

**Independent Test**: Can be tested by invoking the service with `write=True`
against mocked library behavior and asserting that `run_capability_report()` is
called with `write=True` and the returned report preserves each upstream
write-test result, including skipped, failed, and deletion-verification steps.

**Acceptance Scenarios**:

1. **Given** a supported device and `write=True`, **When** the service runs,
   **Then** the upstream write suite attempts the full create, modify, verify,
   and delete chain for throwaway users, schedules, groups, and contacts.
1. **Given** a write step creates a throwaway entity, **When** later steps fail
   or skip, **Then** the library attempts best-effort cleanup and the final
   report preserves the upstream step results and any explicit deletion
   verification results the library records.
1. **Given** `write=True` and `open_door` remains omitted or `False`, **When**
   the report runs, **Then** write-mode evidence is collected, upstream
   non-OpenDoor write checks run as designed, and the OpenDoor HTTP relay test
   is skipped with a clear reason.
1. **Given** an unrecognized device and the existing
   `attempt_unknown_capability` option is disabled, **When** write-mode runs,
   **Then** unknown-gated steps remain skipped or inconclusive with guidance
   rather than silently attempting unproven operations.
1. **Given** the same unrecognized device and
   `attempt_unknown_capability=True`, **When** write-mode runs, **Then**
   `UNKNOWN` capability gates are allowed through while confirmed
   `UNSUPPORTED` capabilities remain blocked and reported.

______________________________________________________________________

### User Story 3 - Hard-Gated OpenDoor Test (Priority: P3)

As a maintainer or owner who is physically present and intentionally testing a
relay, I can opt in to the OpenDoor HTTP test only by setting `open_door=True`
and supplying the relay credentials needed by the device.

**Why this priority**: OpenDoor provides valuable matrix evidence, but it can
physically actuate a relay or open a door. It must remain impossible to run by
accident.

**Independent Test**: Can be tested by service calls that omit OpenDoor fields,
set only one credential field, and set all required fields, asserting that only
the fully explicit call passes `open_door=True`, `open_door_user`, and
`open_door_password` to the library.

**Acceptance Scenarios**:

1. **Given** the user does not provide `open_door`, **When** the service runs,
   **Then** OpenDoor is skipped and no relay credential fields are required.
1. **Given** `open_door=True` without both `open_door_user` and
   `open_door_password`, **When** the service is called, **Then** Home
   Assistant rejects the call before invoking the report API.
1. **Given** `open_door=True` with both relay credential fields and `write=True`,
   **When** the service runs, **Then** the OpenDoor HTTP step is passed to the
   library and the report records the result.
1. **Given** `open_door=True` but `write=False`, **When** the service is
   called, **Then** Home Assistant rejects the call before invoking the report
   API because OpenDoor is only valid for write-mode reports.
1. **Given** the Home Assistant service UI displays the OpenDoor fields, **When**
   a user reads the descriptions, **Then** prominent warnings state that the
   action can physically actuate a relay, unlock a door, or affect access.

### Edge Cases

- The configured entity may be unavailable or unloaded when the service is
  called. The service must fail with an actionable Home Assistant error and
  must not return a partial report as success.
- `AkuvoxDevice.__aenter__` performs network and authentication work. Connection,
  authentication, parse, and device errors may occur before report execution and
  must be logged and surfaced consistently with existing integration behavior.
- The report API may skip steps whose capabilities are `UNSUPPORTED` or
  `UNKNOWN`. Skips are valid evidence and must be returned to the caller.
- `attempt_unknown_capability=True` allows only `UNKNOWN` gates to be attempted;
  it does not bypass confirmed `UNSUPPORTED` capabilities, adapter failures,
  validation errors, or device/network/authentication errors.
- The OpenDoor relay credentials are separate from the integration connection
  credentials and must not be stored in config entries or logs.
- The upstream write suite is broader than throwaway CRUD. In v1.1.0 it also
  includes relay-trigger and device-config set/read-back checks, so write-mode
  descriptions must warn about temporary device mutations beyond entity cleanup.
- The upstream report API accepts `emit` and `redact_stdout`, but the Home
  Assistant service returns the dictionary directly and does not need live
  stdout emission.
- If optional file output is enabled, the file path must stay inside the Home
  Assistant config directory and path traversal must be rejected.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The integration MUST add an entity-targeted Home Assistant service
  named `local_akuvox.run_capability_report` for Local Akuvox lock entities.
- **FR-002**: The service MUST be registered with
  `supports_response=SupportsResponse.ONLY` and MUST return response data on
  every successful call.
- **FR-003**: The service MUST call the public `pylocal_akuvox` API
  `run_capability_report(device, *, write, open_door, open_door_user,
  open_door_password, timeout, redact_stdout, emit)` introduced in
  `pylocal-akuvox` v1.1.0.
- **FR-004**: The service schema MUST expose `write` as an optional boolean that
  defaults to `False` and passes through to the library unchanged.
- **FR-005**: The service schema MUST expose `open_door` as an optional boolean
  that defaults to `False` and passes through to the library unchanged only
  after validation succeeds.
- **FR-006**: The service schema MUST expose `open_door_user` as an optional
  non-empty string and MUST require it when `open_door=True`.
- **FR-007**: The service schema MUST expose `open_door_password` as an optional
  password field and MUST require it when `open_door=True`.
- **FR-008**: The service MUST reject `open_door=True` unless `write=True` is
  also provided, because the upstream API only runs OpenDoor during write mode.
- **FR-009**: The service MUST NOT persist, log, translate, or return the raw
  `open_door_password` value.
- **FR-010**: The service MUST reuse the existing
  `attempt_unknown_capability` config entry option by applying it to the device
  after context entry and before invoking the report API.
- **FR-011**: The default behavior MUST preserve the safe existing posture:
  unknown capabilities are not attempted unless the stored opt-in is enabled.
- **FR-012**: The service MUST preserve confirmed `UNSUPPORTED` capability
  behavior by reporting or surfacing the unsupported result rather than forcing
  device calls.
- **FR-013**: The service response MUST contain the redacted report dictionary
  returned by the library. It MUST be suitable to copy into the upstream
  `new_device` issue template without additional manual redaction.
- **FR-014**: The returned report MUST include device, authentication,
  observed-schema, test-result, and HTTP-event evidence as produced by the
  upstream v1.1.0 report API.
- **FR-015**: The service MUST avoid upstream process-wide stdout/stderr
  redirection by passing a non-`None` no-op `emit` callback, because Home
  Assistant returns the report dictionary directly and does not need live
  progress output.
- **FR-016**: The service MUST handle `AkuvoxUnsupportedError` by reusing the
  repairs issue and structured logging helpers introduced for issue #149.
- **FR-017**: The service MUST handle `AkuvoxError` subclasses with sanitized,
  actionable Home Assistant service errors and structured logs.
- **FR-018**: The integration MUST raise the minimum `pylocal-akuvox` dependency
  pin from `>=1.0.0` to `>=1.1.0` in runtime and project metadata.
- **FR-019**: `services.yaml` MUST define the service target and all fields with
  selectors, examples, and descriptions that match the runtime schema.
- **FR-020**: `strings.json` and `translations/en.json` MUST include service and
  field labels/descriptions for every new field.
- **FR-021**: The service and translation descriptions for OpenDoor MUST include
  strong physical-safety warnings that it can actuate a relay, unlock a door, or
  affect access, and that the caller must be physically present and authorized.
- **FR-022**: The read-only diagnostics download MUST remain read-only and MUST
  NOT gain write-mode or OpenDoor behavior.
- **FR-023**: The `write` field descriptions MUST warn that write mode creates,
  modifies, verifies, and deletes throwaway device data and may run additional
  upstream relay-trigger or device-config write checks.
- **FR-024**: The service SHOULD expose a secondary `save_to_file` option that
  defaults to `False`. When enabled, it MUST write the same redacted report to a
  JSON file under the Home Assistant config directory.
- **FR-025**: If file output is enabled, the service MUST use a deterministic,
  collision-resistant file name or a validated relative file name supplied by
  the caller, and MUST reject absolute paths or path traversal.
- **FR-026**: If file output is enabled, the service response MUST identify the
  config-relative report path alongside the report without exposing host
  filesystem details outside the Home Assistant config directory.
- **FR-027**: Tests in the implementation stage MUST cover default read-only,
  write-mode, OpenDoor validation, OpenDoor pass-through, unsupported capability
  handling, redaction, translations, service registration, and dependency pins.

### Safety

OpenDoor is a physical action. The service must make it clear that enabling
`open_door` can actuate a relay, unlock a door, or otherwise affect building
access. The default must be safe (`False`), required relay credentials must be
provided in the same service call, and the implementation must treat the call as
an intentional, authorized, physically supervised action. Write mode is also a
deliberate mutation path: it creates and deletes test data and follows the
upstream write suite for relay-trigger and device-config checks.

### Key Entities

- **Capability Report**: The redacted dictionary returned by the upstream
  library. It contains device identity, auth mode, observed schemas, test
  results, and HTTP event evidence for matrix authoring.
- **Report Service**: The Home Assistant action
  `local_akuvox.run_capability_report`, targeted at Local Akuvox lock entities
  and registered with response-only semantics.
- **Service Parameters**: `write`, `open_door`, `open_door_user`,
  `open_door_password`, and the secondary file-output fields. The existing
  `attempt_unknown_capability` option is read from the config entry rather than
  supplied as a new service field.
- **Report File**: An optional JSON copy of the returned redacted report stored
  beneath the Home Assistant config directory when file output is enabled.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a supported configured device, calling the service with default
  fields returns a redacted report dictionary and performs no write operations.
- **SC-002**: With `write=True`, the report records upstream create, modify,
  verify, delete, skipped, and failed results for throwaway users, schedules,
  groups, and contacts, plus relay-trigger and device-config set/read-back
  checks, including any explicit deletion-verification results the library
  records.
- **SC-003**: OpenDoor never actuates unless the caller provides `write=True`,
  `open_door=True`, `open_door_user`, and `open_door_password` in the same
  service call.
- **SC-004**: Raw passwords, PINs, card codes, phone numbers, MAC addresses, IP
  addresses, and user identifiers never appear in the service response, saved
  report file, logs, repairs issues, or translations.
- **SC-005**: For unrecognized devices, disabling
  `attempt_unknown_capability` leaves unknown steps skipped or inconclusive;
  enabling it allows `UNKNOWN` gates to run while confirmed `UNSUPPORTED` gates
  remain blocked.
- **SC-006**: The implementation stage completes with the full test suite green
  at 100% coverage, interrogate at 100, ruff and mypy clean, and hassfest valid.
