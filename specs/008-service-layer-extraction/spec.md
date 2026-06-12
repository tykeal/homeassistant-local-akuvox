<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Feature Specification: Service Layer Extraction

**Feature Branch**: `008-service-layer-extraction` **Created**: 2026-06-12
**Status**: Draft **Input**: User description: "Extract the service layer from
`__init__.py` (~550 lines) and `lock.py` (~1,735 lines) into focused modules. This
is a pure refactor — no behavior changes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Service Calls Continue Working Identically (Priority: P1)

As a Home Assistant user with the Local Akuvox integration configured, I can
continue invoking all 18 services (add_user, modify_schedule, list_contacts,
etc.) exactly as before with no changes to my automations, scripts, or service
call data.

**Why this priority**: This is a pure refactor — zero regression is the primary
acceptance criterion. If any service call breaks, the refactor has failed.

**Independent Test**: Can be fully tested by invoking every registered service
with valid parameters and verifying identical responses/side-effects to
pre-refactor behavior.

**Acceptance Scenarios**:

1. **Given** the integration is loaded after the refactor, **When** a user
   invokes any of the 18 services with valid parameters, **Then** the service
   executes with identical behavior to pre-refactor (same validations, same
   errors, same state changes)
1. **Given** an existing automation calls a service (e.g.,
   `local_akuvox.add_user`), **When** the automation triggers after the
   refactor, **Then** it succeeds without modification
1. **Given** a service call with invalid parameters, **When** the call is made
   after the refactor, **Then** the same validation errors are raised as before
   (same error types, same messages)

______________________________________________________________________

### User Story 2 - Module Boundaries Are Clean and Focused (Priority: P2)

As a developer maintaining this integration, I can find service-related code in
predictable locations: schemas and registration in the services module,
validation helpers in the validation module, and lock entity lifecycle in
lock.py.

**Why this priority**: Code discoverability and maintainability are the primary
motivation for this refactor. Without clear module boundaries, the refactor has
no value.

**Independent Test**: Can be verified by inspecting module contents and
confirming each module has a single, coherent responsibility with no leaked
concerns.

**Acceptance Scenarios**:

1. **Given** the refactor is complete, **When** a developer opens `lock.py`,
   **Then** it contains only lock entity/platform code plus HA-dispatch-bound
   service handler methods that delegate to extracted helpers, and no service
   schema definitions or registration logic
1. **Given** the refactor is complete, **When** a developer opens `__init__.py`,
   **Then** it is a thin orchestrator (approximately 100–150 lines) that
   delegates service registration to the services module
1. **Given** the refactor is complete, **When** a developer opens the services
   module, **Then** it co-locates service schemas with their registration and
   dispatch logic
1. **Given** the refactor is complete, **When** a developer opens the validation
   module, **Then** it contains PIN validation, cloud-provisioning checks,
   schedule verification helpers, and related utility functions (schedule_relay
   building, CSV parsing)

______________________________________________________________________

### User Story 3 - File Sizes Are Within Maintainable Limits (Priority: P3)

As a developer, Python modules in the integration stay within maintainable size
targets, with a documented architectural exception for `lock.py` because Home
Assistant binds service handlers to entity methods.

**Why this priority**: Large files are a code smell that increases cognitive
load and merge conflict frequency. Reducing file sizes everywhere feasible —
while documenting why `lock.py` remains larger — is a concrete, measurable
outcome of the refactor.

**Independent Test**: Can be verified by running a line count on all Python
files in the integration directory and confirming all files except `lock.py` are
approximately 500 lines or less, while `lock.py` retains only entity/platform
code plus HA-dispatch-bound service handlers.

**Acceptance Scenarios**:

1. **Given** the refactor is complete, **When** line counts are measured for all
   Python modules in `custom_components/local_akuvox/`, **Then** no single file
   exceeds approximately 500 lines except `lock.py`, which is the documented
   architectural exception
1. **Given** `lock.py` currently has ~1,735 lines, **When** the refactor is
   complete, **Then** `lock.py` retains only lock entity/platform code plus
   HA-dispatch-bound service handlers, with validation/utility helpers extracted
   to `validation.py`
1. **Given** `__init__.py` currently has ~550 lines, **When** the refactor is
   complete, **Then** `__init__.py` is reduced to approximately 100–150 lines

______________________________________________________________________

### User Story 4 - Existing Tests Pass (Priority: P2)

As a developer, the existing test suite passes after the refactor. The only
allowed test changes are import or symbol-reference updates to reflect moved
code — no test logic changes are permitted.

**Why this priority**: Test stability proves the refactor is
behavior-preserving. This is second only to runtime service correctness.

**Independent Test**: Can be verified by running the full test suite and
confirming all tests pass with only import/reference-path modifications.

**Acceptance Scenarios**:

1. **Given** the existing test suite, **When** the full test suite is run after
   the refactor, **Then** all tests pass
1. **Given** a test that imports or references a helper from `lock.py`, **When**
   that helper has moved to `validation.py`, **Then** updating the import or
   symbol reference is the only change needed for the test to pass
1. **Given** the test suite, **When** comparing test file diffs, **Then** only
   import statements or symbol references to moved helpers have changed — no
   assertion logic, no mock targets (beyond moved helper paths), no test flow
   changes

______________________________________________________________________

### Edge Cases

- What happens if a third-party integration or custom automation references
  internal module paths (e.g., imports from `lock.py`)? — External consumers
  should only use the public service interface; internal module paths are not
  part of the public contract.
- What happens during a Home Assistant restart mid-refactor (partial deploy)? —
  Not applicable; the integration loads atomically from a single version of
  files.
- What happens if the services module fails to import? — Standard Home Assistant
  integration loading behavior applies; the integration fails to set up and logs
  an error.
- How are circular imports prevented between modules that previously lived in
  the same file? — Validation/utility modules must not import from lock or
  services; `services.py` imports from `validation.py`, and `lock.py` imports
  only from `validation.py` and `const.py`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All 18 existing services MUST remain registered with identical
  service names, schemas, and behavior after the refactor
- **FR-002**: Service schemas (voluptuous definitions) MUST be co-located with
  their registration logic in a dedicated services module
- **FR-003**: Validation helpers (PIN validation, cloud-provisioning checks,
  schedule verification) MUST be extracted into a dedicated validation module
- **FR-004**: Utility functions (schedule_relay building, CSV parsing, date/time
  conversions) MUST be extracted into the validation module or a dedicated
  utilities module
- **FR-005**: The lock entity class MUST retain only lock platform
  responsibilities: entity lifecycle, state properties, lock/unlock actions, and
  HA-dispatch-bound service handler methods that delegate to extracted helpers
- **FR-006**: `__init__.py` MUST delegate service registration to the services
  module and contain only setup/teardown orchestration (target: ~100–150 lines)
- **FR-007**: No single Python file in the integration SHOULD exceed
  approximately 500 lines, with the exception of `lock.py` whose service handler
  methods are architecturally bound to the entity class by Home Assistant's
  service dispatch mechanism
- **FR-008**: The refactor MUST NOT introduce any new user-facing features or
  behavior changes
- **FR-009**: The refactor MUST NOT change any service call interface (service
  names, parameter names, parameter types, response formats)
- **FR-010**: The refactor MUST maintain backwards compatibility — no breaking
  changes to service call data structures
- **FR-011**: All extracted modules MUST follow project conventions: SPDX
  license headers, type annotations, docstrings, and Home Assistant platform
  file conventions
- **FR-012**: The lock entity class MUST remain the service target (services are
  entity-bound per Home Assistant conventions)
- **FR-013**: Circular imports between the new modules MUST be prevented by
  maintaining a one-way dependency chain (`const.py` ← `validation.py` ←
  `services.py` ← `__init__.py`) plus a separate branch where `lock.py` imports
  only from `validation.py` and `const.py`
- **FR-014**: Service handler methods on the lock entity MUST delegate to
  extracted validation/utility helpers rather than containing inline logic

### Key Entities

- **Services Module**: Co-locates the 18 service schemas (voluptuous
  definitions) with their registration logic and dispatch configuration.
  Responsible for calling the platform entity service registration mechanism.
- **Validation Module**: Contains reusable validation and utility functions —
  PIN validation, cloud-provisioning checks, schedule field verification,
  schedule_relay building, CSV parsing, date/time format conversions.
- **Lock Entity**: The lock platform entity class that implements entity
  lifecycle (init, state, attributes, will_remove), lock/unlock actions, and
  service handler methods that delegate to validation helpers.
- **Integration Init**: The thin orchestrator that handles integration setup,
  teardown, config entry lifecycle, and delegates service registration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of existing tests pass after the refactor (with only
  import/reference-path updates permitted)
- **SC-002**: All 18 registered services respond identically to pre-refactor
  behavior for both valid and invalid inputs
- **SC-003**: No Python file in `custom_components/local_akuvox/` exceeds 500
  lines, except `lock.py` which retains entity-bound service handlers
- **SC-004**: `__init__.py` is reduced from ~550 lines to approximately 100–150
  lines (70%+ reduction)
- **SC-005**: `lock.py` is reduced by extracting all validation/utility helpers
  to `validation.py` (~190 lines removed); service handlers remain on the entity
  class per Home Assistant dispatch requirements
- **SC-006**: A developer can locate any service-related code (schema,
  registration, validation) within one file navigation step from the services or
  validation module
- **SC-007**: No circular import errors occur during integration loading
- **SC-008**: The refactor introduces zero new user-visible behaviors or service
  call interface changes

## Assumptions

- **Option 1 architecture**: Service handler methods remain on the lock entity
  class (entity-bound per HA conventions), but validation/utility helpers and
  schema definitions are extracted into separate modules. This is the safest
  first-pass approach.
- **HA dispatch constraint**: Service handler methods (e.g., `add_user`,
  `modify_user`, `add_schedule`) cannot be extracted from the entity class
  because Home Assistant's `async_register_platform_entity_service` dispatches
  calls via `func=` parameters that must resolve to entity methods. A future
  effort could reduce `lock.py` further using mixin classes or thin-delegate
  patterns.
- **Module naming**: The services module will be `services.py` (single file)
  unless the extracted schemas and registration exceed 500 lines, in which case
  a `services/` subpackage is acceptable.
- **Validation module scope**: `validation.py` encompasses both strict
  validation (PIN checks, cloud-provisioning guards) and utility/conversion
  functions (date formatting, CSV parsing, schedule_relay building) since these
  are tightly coupled to service correctness.
- **Import direction**: `validation.py` has no dependencies on other integration
  modules (except `const.py`). `services.py` imports from `validation.py` and
  `const.py`. `lock.py` imports from `validation.py` and `const.py` only.
  `__init__.py` imports from `services.py`.
- **Test changes**: Only import paths or symbol references to moved helpers
  should need updating in tests; mock targets that reference moved functions
  will need path updates but no logic changes.
- **Line count flexibility**: The "~500 lines" limit is a guideline, not a hard
  boundary — files up to ~520 lines are acceptable if splitting further would
  harm cohesion.

## Dependencies

- **007 refactor complete**: The options_flow extraction (007) should be merged
  first to avoid merge conflicts in `__init__.py` and establish the extraction
  pattern.
- **GitHub Issue #139**: This specification implements the work described in
  issue #139.
- **Supersedes #135 and #137**: This spec consolidates the service extraction
  work previously tracked in those issues.
