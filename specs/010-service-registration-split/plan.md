<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Implementation Plan: Service Registration Split

**Branch**: `010-service-registration-split` | **Date**: 2026-06-18 |
**Spec**: [spec.md](./spec.md) **Input**: Feature specification from
`/specs/010-service-registration-split/spec.md`

## Summary

Group the 18 platform entity service registrations in
`custom_components/local_akuvox/services.py` into four private domain helpers so
`async_register_services` becomes a thin orchestrator under the 80-line aislop
`complexity/function-too-long` limit. The refactor preserves the public
`async_register_services(hass)` name, signature, awaited setup contract, service
names, schemas, entity domain, handler function names, and response semantics.

## Technical Context

**Language/Version**: Python >=3.14.2 (type-annotated, mypy-checked) **Primary
Dependencies**: Home Assistant custom integration APIs, `pylocal-akuvox`,
voluptuous service schemas **Storage**: N/A (service registration only; no data
persistence) **Testing**: pytest full suite with 100% pass requirement,
interrogate 100% docstring coverage, ruff, mypy, aislop, and existing
pre-commit hooks **Target Platform**: Home Assistant custom component **Project
Type**: Single-project Python integration under
`custom_components/local_akuvox/` **Performance Goals**: N/A for this pure
refactor; no new I/O, awaits, caching, or runtime work beyond existing
registrations **Constraints**: No behavior change, no public API change,
`async_register_services` must be 80 lines or fewer after implementation, all
new private helpers need docstrings, and no new source files are introduced
**Scale/Scope**: Split one 168-line registration function into four private
helpers for schedule, user, contact, and group service domains inside
`services.py`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| I. Code Quality (NON-NEGOTIABLE) | PASS | The implementation keeps typed signatures, adds docstrings for the four private helpers, and must pass ruff, mypy, interrogate, and aislop. |
| II. Test-Driven Development (NON-NEGOTIABLE) | PASS | This is a behavior-preserving refactor of registrations already covered by existing service setup and call tests. Existing tests stay green; no new behavior is planned. |
| III. User Experience Consistency | PASS | Service names, schemas, handler function names, entity domain, response support, automations, and setup behavior remain unchanged. |
| IV. Performance Requirements | PASS | Registration calls remain synchronous Home Assistant helper calls. No blocking I/O, network calls, cache changes, or async-flow changes are introduced. |
| V. Atomic Commits & Compliance (NON-NEGOTIABLE) | PASS | This stage produces one docs-only commit with DCO sign-off. No new source file means no SPDX impact beyond normal Markdown headers. |
| VI. Phased Development | PASS | This stage produces only plan and design artifacts. `tasks.md`, production code, and test edits are deferred to later speckit stages. |

**Gate Result**: PASS — no violations. Phase 1 design re-check remains PASS
because the artifacts keep the work to a private helper split inside
`services.py` with no public behavior or API change.

## Project Structure

### Documentation (this feature)

```text
specs/010-service-registration-split/
├── plan.md              # This file
├── research.md          # Phase 0 decisions
├── data-model.md        # Phase 1 function inventory
├── quickstart.md        # Phase 1 developer guide
├── contracts/           # Phase 1 module/function contract
│   └── service_registration.md
├── spec.md              # Merged Stage 1 source of truth
└── tasks.md             # Phase 2 output; not created in this stage
```

### Source Code (repository root)

```text
custom_components/local_akuvox/
├── services.py          # Modified only in implementation stage:
│                        # add four private helper functions and keep
│                        # async_register_services as the public orchestrator
├── __init__.py          # Unchanged: continues to await
│                        # async_register_services(hass)
└── ...                  # Other integration modules unchanged

tests/
├── test_services.py     # Unchanged: verifies service setup and behavior
└── ...                  # Other tests unchanged unless discovery proves needed
```

**Structure Decision**: Use the existing flat module layout inside
`custom_components/local_akuvox/`. All helpers remain in `services.py` because
the spec forbids a new service-registration module, and the only public caller in
`__init__.py` continues to await `async_register_services(hass)` unchanged.

## Complexity Tracking

> No violations to justify. All constitution gates pass cleanly.

<!-- markdownlint-enable MD013 -->
