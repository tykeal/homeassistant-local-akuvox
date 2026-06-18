<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Feature Specification: Coordinator Relay Config Split

**Feature Branch**: `009-coordinator-split` **Created**: 2026-06-18
**Status**: Draft **Input**: User description: "GitHub issue #146 requests
splitting the pure relay-config parsing helpers out of `coordinator.py` so the
file no longer violates the aislop `complexity/file-too-large` rule."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Coordinator Clears Size Gate (Priority: P1)

As a maintainer, I need `custom_components/local_akuvox/coordinator.py` to stay
under the configured 400-line aislop file-size threshold after the relay-config
helpers are extracted, so the code-quality gate no longer blocks the project.

**Why this priority**: Issue #146 is specifically about the
`complexity/file-too-large` finding on `coordinator.py`. Clearing that finding
is the smallest valuable outcome of this refactor.

**Independent Test**: Can be verified by measuring `coordinator.py` after the
refactor and running the aislop rule that currently reports the file as too
large.

**Acceptance Scenarios**:

1. **Given** `coordinator.py` currently exceeds 400 lines, **When** the
   relay-config helpers are extracted, **Then** `coordinator.py` is 400 lines
   or fewer
1. **Given** aislop checks `coordinator.py`, **When** the refactor is complete,
   **Then** `complexity/file-too-large` no longer reports that file
1. **Given** a developer opens `coordinator.py`, **When** they inspect its
   contents, **Then** it focuses on coordinator state, fetching, caching, and
   update orchestration rather than standalone relay-config parsing

______________________________________________________________________

### User Story 2 - Runtime Behavior Is Preserved (Priority: P1)

As a maintainer guarding against regressions, I can verify that Home Assistant
users see no change in relay names, hold delays, relay types, relay modes,
device naming, cache behavior, entity attributes, or error handling after the
refactor.

**Why this priority**: This stage specifies a pure internal refactor. Any
user-visible behavior change would violate the agreed scope.

**Independent Test**: Can be verified by running the existing coordinator,
lock, and integration tests after implementation, with only import-path updates
for moved internal helpers if tests reference them directly.

**Acceptance Scenarios**:

1. **Given** a device config contains relay name, hold-delay, type, and mode
   values, **When** the coordinator parses it after the refactor, **Then** the
   resulting `RelayConfig` values match pre-refactor behavior exactly
1. **Given** a device config has missing, blank, out-of-range, or non-numeric
   relay values, **When** parsing runs after the refactor, **Then** defaults and
   warning logs match pre-refactor behavior exactly
1. **Given** the coordinator falls back to default relay configuration, **When**
   config fetch is unsupported or fails, **Then** default `RelayConfig` objects
   are produced exactly as before
1. **Given** existing user automations and dashboards, **When** the integration
   is upgraded after the refactor, **Then** no configuration, service call, or
   entity usage changes are required

______________________________________________________________________

### User Story 3 - Relay Config Parsing Is Cohesive (Priority: P2)

As a developer maintaining relay behavior, I can find the class-independent
relay-config parsing code in a focused `relay_config` module, with the
coordinator importing and using that module instead of defining the helpers
inline.

**Why this priority**: Moving code only helps maintainability if the new module
has a clear responsibility and keeps the parsing rules together.

**Independent Test**: Can be verified by inspecting the new module and the
coordinator imports without needing any external device interaction.

**Acceptance Scenarios**:

1. **Given** the refactor is complete, **When** a developer opens
   `custom_components/local_akuvox/relay_config.py`, **Then** it contains
   `RelayConfig`, `_parse_config_int`, and `_build_relay_config`
1. **Given** the refactor is complete, **When** a developer opens
   `coordinator.py`, **Then** it imports `RelayConfig` and
   `_build_relay_config` from `.relay_config` rather than defining them inline
1. **Given** the new module is imported, **When** its contents are inspected,
   **Then** it has no dependency on the coordinator class or coordinator state

______________________________________________________________________

### User Story 4 - Existing Quality Gates Remain Green (Priority: P2)

As a maintainer, I need the refactor to keep the existing automated checks
passing, so the file-size fix does not trade one quality failure for another.

**Why this priority**: The project constitution requires linting, type checks,
docstrings, tests, and pre-commit compliance before merge.

**Independent Test**: Can be verified by running the existing test and quality
commands used by the repository after the implementation stage.

**Acceptance Scenarios**:

1. **Given** the existing test suite, **When** it is run after the refactor,
   **Then** every existing test passes
1. **Given** interrogate checks docstring coverage, **When** the refactor is
   complete, **Then** coverage remains at 100%
1. **Given** ruff, mypy, reuse, markdownlint, and gitlint hooks run, **When** the
   refactor is committed, **Then** they complete without errors

### Edge Cases

- Missing relay config keys continue to use the same default values:
  empty names, default hold delay, default relay type, and default relay mode.
- Empty strings for integer config values continue to fall back silently, while
  invalid non-empty values continue to log warnings before returning defaults.
- Hold delays below the minimum continue to fall back to the default hold delay.
- Relay type and relay mode values outside the allowed set `{0, 1}` continue to
  fall back to their defaults and log the same warning patterns.
- Device configs with multiple relay letters continue to parse each relay using
  the existing relay-letter discovery performed by the coordinator.
- External code that imports the internal helpers from `coordinator.py` is not a
  supported public API. Tests may update direct helper imports to the new module
  path, but Home Assistant users receive no public interface change.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The implementation MUST create
  `custom_components/local_akuvox/relay_config.py` for relay-config parsing
  helpers extracted from `coordinator.py`.
- **FR-002**: `relay_config.py` MUST define the frozen `RelayConfig` dataclass
  with the existing fields `name`, `hold_delay`, `relay_type`, and
  `relay_mode`, preserving current defaults.
- **FR-003**: `relay_config.py` MUST define `_parse_config_int` with the same
  arguments, validation rules, return values, and warning behavior currently
  present in `coordinator.py`.
- **FR-004**: `relay_config.py` MUST define `_build_relay_config(config,
  letter)` with the same parsing behavior currently present in
  `coordinator.py`.
- **FR-005**: `coordinator.py` MUST import `RelayConfig` and
  `_build_relay_config` from `.relay_config` and MUST NOT retain duplicate
  definitions of `RelayConfig`, `_parse_config_int`, or `_build_relay_config`.
- **FR-006**: The refactor MUST NOT change coordinator caching behavior, device
  config fetch timing, fallback device-name behavior, user-cache behavior, or
  exception handling.
- **FR-007**: The refactor MUST NOT change any Home Assistant public API,
  entity state, entity attributes, service names, service schemas,
  configuration options, or user-facing behavior.
- **FR-008**: The implementation MUST update internal tests or imports only as
  needed for the new helper module path; test assertions and behavior coverage
  MUST remain equivalent.
- **FR-009**: The implementation MUST keep all existing tests passing.
- **FR-010**: The implementation MUST make aislop stop reporting the
  `complexity/file-too-large` finding for `coordinator.py`.
- **FR-011**: The implementation MUST preserve project standards for new source
  files, including SPDX headers, type annotations, docstrings, ruff compliance,
  mypy compliance, reuse compliance, and 100% interrogate docstring coverage.
- **FR-012**: The implementation MUST avoid circular imports. The new
  `relay_config.py` module may depend on constants from `const.py`, but it MUST
  NOT import from `coordinator.py`.

### Key Entities

- **RelayConfig**: Frozen dataclass representing parsed configuration for one
  relay. It carries the display `name`, `hold_delay` in seconds, `relay_type`
  where `0` means normally open and `1` means normally closed, and `relay_mode`
  where `0` means auto-close and `1` means manual.
- **Relay Config Module**: Internal module that owns class-independent
  relay-config parsing. It exposes `RelayConfig`, `_parse_config_int`, and
  `_build_relay_config` for use by the coordinator and tests.
- **Coordinator Module**: Home Assistant `DataUpdateCoordinator` implementation
  that discovers relay letters, fetches device config, caches parsed relay
  config, handles device errors, and delegates parsing to `relay_config.py`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `custom_components/local_akuvox/coordinator.py` is 400 lines or
  fewer after the implementation stage.
- **SC-002**: The aislop `complexity/file-too-large` rule no longer reports
  `coordinator.py` after the implementation stage.
- **SC-003**: 100% of existing tests pass after the implementation stage.
- **SC-004**: Interrogate docstring coverage remains 100% after the
  implementation stage.
- **SC-005**: The refactor introduces zero user-visible behavior changes and
  zero public API changes.
- **SC-006**: The extracted module contains exactly the cohesive relay-config
  parsing responsibilities identified in this spec, without coordinator class
  state or unrelated device-fetching logic.

## Assumptions

- The implementation stage will move the existing helper code rather than
  redesigning parsing behavior.
- `RelayConfig`, `_parse_config_int`, and `_build_relay_config` are treated as
  internal integration helpers, even though tests currently import them
  directly from `coordinator.py`.
- Updating test imports to `custom_components.local_akuvox.relay_config` is
  acceptable because those imports reference internal helper locations, not a
  public Home Assistant API.
- Issue #146 remains open after this spec stage. A later implementation stage
  will close it when code, tests, and quality gates prove the refactor is done.

## Dependencies

- **GitHub Issue #146**: This specification captures the agreed refactor for
  the `coordinator.py` aislop `complexity/file-too-large` finding.
