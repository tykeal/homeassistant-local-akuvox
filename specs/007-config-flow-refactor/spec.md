<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Feature Specification: Config Flow Refactor

**Feature Branch**: `007-config-flow-refactor` **Created**: 2026-06-12
**Status**: Draft **Input**: User description: "Refactor config_flow.py
(currently 622 lines) by extracting the options flow into its own module. This
is a pure refactor — no behavior changes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Initial Setup Flow Preserved (Priority: P1)

As a user adding a new Akuvox device to Home Assistant, I configure the device
through the initial setup flow (host, SSL, authentication, webhook). After the
refactor, this experience remains identical — the same steps, same validation,
same error messages, and same resulting configuration entry.

**Why this priority**: The initial setup flow is the first-contact experience.
If it breaks, no new devices can be added. This is the highest-risk area of the
refactor because the ConfigFlow class must remain in `config_flow.py` per Home
Assistant convention.

**Independent Test**: Can be fully tested by running the existing initial setup
test suite against the refactored code and verifying all tests pass without
modification (aside from import paths).

**Acceptance Scenarios**:

1. **Given** the integration is installed with the refactored code, **When** a
   user adds a new Akuvox device via the UI, **Then** the setup wizard presents
   host, SSL, auth, credentials, and webhook steps in the same order with the
   same behavior as before.
2. **Given** an invalid host is entered during setup, **When** the form is
   submitted, **Then** the same validation error appears as before the refactor.
3. **Given** all setup steps are completed successfully, **When** the config
   entry is created, **Then** the entry data structure is byte-for-byte
   identical to what the pre-refactor code would produce.

---

### User Story 2 - Options Flow Preserved (Priority: P1)

As a user modifying runtime settings (host, SSL, auth method, webhook, request
delay) of an already-configured Akuvox device, I access the options flow. After
the refactor, this experience remains identical — the same form fields, same
validation, same save behavior.

**Why this priority**: Options flow is the primary way users reconfigure devices
after initial setup. Breaking it renders existing installations unmanageable
without removing and re-adding the integration.

**Independent Test**: Can be fully tested by running the existing options flow
test suite against the refactored code and verifying all tests pass without
modification (aside from import paths).

**Acceptance Scenarios**:

1. **Given** a configured Akuvox device exists, **When** the user opens the
   options flow, **Then** the form displays current values for host, SSL, auth,
   webhook, and request delay identically to the pre-refactor behavior.
2. **Given** the user changes the host in the options flow, **When** the form is
   submitted, **Then** the config entry is updated with the same existing
   options-flow logic as before (non-empty host and credentials checks only,
   with device I/O only for webhook enable/disable changes).
3. **Given** the user toggles webhook settings in the options flow, **When** the
   form is submitted, **Then** the webhook configuration is pushed to the device
   with the same behavior as before.

---

### User Story 3 - Codebase Maintainability Improved (Priority: P2)

As a developer contributing to the integration, I can navigate, understand, and
modify the config flow and options flow independently. Each module is focused on
a single responsibility, under 400 lines, making it easier to reason about
changes and review pull requests.

**Why this priority**: This is the motivating goal of the refactor — improve
developer experience. It has lower priority than functional preservation because
developer experience is moot if the integration breaks.

**Independent Test**: Can be verified by inspecting the file structure, line
counts, and confirming each module has a single, clearly-defined responsibility.

**Acceptance Scenarios**:

1. **Given** the refactor is complete, **When** a developer inspects the module
   structure, **Then** `config_flow.py` contains only the ConfigFlow class and
   `options_flow.py` contains only the AkuvoxOptionsFlow class.
2. **Given** the refactored codebase, **When** the line count of each module is
   measured, **Then** each file is under 400 lines.
3. **Given** the refactored codebase, **When** a developer needs to modify
   option handling logic, **Then** they only need to work in `options_flow.py`
   without touching `config_flow.py`.

---

### Edge Cases

- What happens when a shared schema builder is used by both ConfigFlow and
  AkuvoxOptionsFlow? The shared logic must be accessible to both modules without
  circular imports.
- What happens when Home Assistant resolves the options flow handler? The
  `async_get_options_flow` callback in ConfigFlow must successfully import and
  return the AkuvoxOptionsFlow class from its new module.
- What happens when existing config entries created by the pre-refactor code are
  loaded? They must continue to work without migration since no data schema has
  changed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The initial setup flow (ConfigFlow) MUST remain in the
  `config_flow.py` module, as required by the Home Assistant platform
  convention.
- **FR-002**: The options flow (AkuvoxOptionsFlow) MUST be extracted into a
  dedicated `options_flow.py` module within the same integration package.
- **FR-003**: The `async_get_options_flow` callback in ConfigFlow MUST reference
  the AkuvoxOptionsFlow class from its new module location.
- **FR-004**: All existing test cases MUST pass after the refactor, with only
  import path changes permitted in test files.
- **FR-005**: The behavior of every user-facing flow step (forms, validation,
  error handling, data persistence) MUST remain identical to the pre-refactor
  implementation.
- **FR-006**: Each resulting module MUST be under 400 lines of code.
- **FR-007**: Any schema-building logic shared between modules MUST be extracted
  into a helper that both modules can import without circular dependencies.
- **FR-008**: All new and modified files MUST include proper SPDX license
  headers, type annotations, and docstrings as required by the project
  constitution.
- **FR-009**: The refactor MUST NOT introduce any new dependencies or change the
  integration's manifest.
- **FR-010**: Existing config entries MUST continue to load and function without
  any data migration.

## Assumptions

- The `_build_schema` helper method (currently in AkuvoxOptionsFlow at line 575)
  is the primary candidate for shared extraction if ConfigFlow also uses schema
  builders. If it is only used by the options flow, it moves with the class.
- The `build_action_urls` import from `.webhook` is used by both flows and will
  remain importable from either module.
- No other integrations or external code imports directly from `config_flow.py`
  other than through the Home Assistant integration loader which only looks for
  the ConfigFlow class.
- There is no separate reconfiguration flow in the current integration;
  `AkuvoxOptionsFlow` already handles all runtime configuration changes and
  moves with it entirely.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of existing integration tests pass after the refactor (import
  path updates in test files are acceptable).
- **SC-002**: The `config_flow.py` module contains fewer than 400 lines of code.
- **SC-003**: The `options_flow.py` module contains fewer than 400 lines of
  code.
- **SC-004**: No user-visible behavior change is detectable — the same inputs
  produce the same outputs, errors, and config entries as before.
- **SC-005**: The refactored code passes all project linting and type-checking
  rules without new suppressions.
- **SC-006**: Zero circular import errors occur when the integration is loaded.
