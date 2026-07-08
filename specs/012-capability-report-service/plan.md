<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Implementation Plan: Capability Report Service

**Branch**: `docs/012-capability-report-service-plan` | **Date**: 2026-07-02 |
**Spec**: [spec.md](./spec.md) **Input**: Feature specification from
`/specs/012-capability-report-service/spec.md`

## Summary

Add a response-only Home Assistant action named
`local_akuvox.run_capability_report` for Local Akuvox lock entities. The service
will create a fresh `pylocal-akuvox` device from the entity config entry, enter it
with the same option-application pattern used by diagnostics, call
`pylocal_akuvox.run_capability_report()` from `pylocal-akuvox>=1.4.0`, hard-gate
write-mode and OpenDoor inputs, return the upstream redacted report dictionary,
and optionally save the same redacted JSON beneath the Home Assistant config
directory.

## Technical Context

**Language/Version**: Python >=3.14.2, with tooling targeted at Python 3.14 and
CI validation covering Python 3.14
**Primary Dependencies**: Home Assistant custom integration APIs,
`pylocal-akuvox>=1.4.0`, voluptuous service schemas, pytest Home Assistant
custom component helpers **Storage**: Home
Assistant config entry data/options plus optional JSON report files under the
Home Assistant config directory; no database or persistent secrets **Testing**:
pytest with 100% coverage, interrogate 100% docstring coverage, ruff
check/format, mypy strict mode, reuse, markdownlint, gitlint, hassfest, and
`aislop ci` with failBelow 100
**Target Platform**: Home Assistant custom integration running as `custom_components/local_akuvox` **Project Type**:
Single-project Python custom component with tests under `tests/` and speckit
artifacts under `specs/` **Performance Goals**: Do not run the report during
setup or polling; run it only when the user explicitly calls the service, and do
not block the event loop with file I/O or long synchronous work **Constraints**:
Keep read-only diagnostics passive, preserve safe defaults, reject OpenDoor unless
`write=True` and both relay credentials are supplied, do not store or log relay
passwords, keep all file paths inside the config directory, and avoid tasks or
implementation code in this stage **Scale/Scope**: One dependency-floor bump plus
one response-only lock entity service, service metadata/translations, optional
file output, error handling, and tests for GitHub issue #189.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| I. Code Quality (NON-NEGOTIABLE) | PASS | Stage 5 must keep typed signatures, docstrings for every new helper, SPDX headers for new source files, and green ruff, mypy, interrogate, reuse, markdownlint, hassfest, and aislop gates. |
| II. Test-Driven Development (NON-NEGOTIABLE) | PASS | Stage 5 must write failing tests first for service schema validation, default read-only reporting, write-mode pass-through, OpenDoor hard gates, file output, dependency pins, translations, and error handling before production edits. |
| III. User Experience Consistency | PASS | The service follows existing lock entity service patterns, uses Home Assistant service descriptions/selectors, returns structured response data, and uses actionable validation/error messages. |
| IV. Performance Requirements | PASS | The report runs only on explicit user service calls. Fresh device entry avoids interfering with coordinator state; report execution remains asynchronous, and any JSON file write must use Home Assistant executor helpers if it would otherwise block. |
| V. Atomic Commits & Compliance (NON-NEGOTIABLE) | PASS | This stage produces one docs-only commit with DCO sign-off and no production code. Later stages must keep task-list updates separate from implementation commits and never bypass pre-commit. |
| VI. Phased Development | PASS | This stage creates only `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, and `contracts/`. `tasks.md`, production code, tests, and dependency lock updates are deferred. |

**Gate Result**: PASS — no violations. Phase 1 design re-check remains PASS
because the artifacts keep the scope to the merged spec and selected Home
Assistant service/file-output surfaces without implementing code in this stage.

## Project Structure

### Documentation (this feature)

```text
specs/012-capability-report-service/
├── plan.md                         # This file
├── research.md                     # Phase 0 decisions
├── data-model.md                   # Phase 1 service/report/file model
├── quickstart.md                   # Phase 1 operator and developer guide
├── contracts/                      # Phase 1 service contracts
│   ├── capability_report_service.md
│   └── file_output.md
└── spec.md                         # Merged Stage 1 source of truth
```

### Source Code (repository root)

```text
.pre-commit-config.yaml             # Keep validation hooks; update comments or
                                     # dependency assumptions if v1.4.0 requires it
pyproject.toml                      # Bump pylocal-akuvox dependency to >=1.4.0
                                     # and update stale dependency comments
uv.lock                             # Refresh after dependency bump

custom_components/local_akuvox/
├── manifest.json                   # Bump runtime requirement to >=1.4.0
├── const.py                        # Add SERVICE_RUN_CAPABILITY_REPORT and
│                                    # service/file-output field constants
├── __init__.py                     # Existing async_setup remains the service
│                                    # registration entry point; update final
│                                    # unload cleanup if a reserved report-lock
│                                    # key is stored under hass.data[DOMAIN]
├── capability_support.py           # Reuse apply_capability_options,
│                                    # get_effective_attempt_unknown,
│                                    # sanitize_value, and repairs helpers; add
│                                    # shared sanitizing/error/file helpers only
│                                    # if implementation needs them
├── diagnostics.py                  # Reference pattern for _create_device +
│                                    # async with + apply_capability_options;
│                                    # read-only diagnostics behavior unchanged
├── services.py                     # Add report schema and a fifth private
│                                    # _register_* helper registering the
│                                    # response-only Platform.LOCK entity service
├── services.yaml                   # Add target, fields, selectors, examples,
│                                    # save_to_file/file_name, and warnings
├── strings.json                    # Add service labels, field descriptions,
│                                    # OpenDoor warnings, validation strings, and
│                                    # update pylocal-akuvox version text to 1.4.0
├── translations/
│   └── en.json                     # Mirror user-facing service strings and the
│                                    # pylocal-akuvox 1.4.0 version text
└── lock.py                         # Add the entity service method that creates
                                     # a fresh device, calls run_capability_report,
                                     # returns response data, and handles errors

tests/
├── conftest.py                     # Extend mocks for run_capability_report,
│                                    # fresh device entry, and optional file paths
├── test_services.py                # Service registration/schema/metadata tests
├── test_lock.py                    # Entity service behavior, pass-through,
│                                    # validation, file output, and error handling
├── test_diagnostics.py             # Regression: diagnostics remain read-only
├── test_init.py                    # Setup still registers services once
│                                    # and final unload cleans reserved lock data
├── test_capability_support.py      # Shared sanitizing/error helper tests if
│                                    # new helpers are added
└── test_*                          # Pin, translation, and hassfest-adjacent
                                     # coverage where existing tests locate it
```

**Structure Decision**: Keep the existing flat custom component layout. Service
registration stays in `services.py` as another private helper coordinated by
`async_register_services()`, and execution stays on `AkuvoxLockEntity` because
platform entity services provide the target entity, coordinator, and config entry
context needed to build the fresh report device.

## Complexity Tracking

> No constitution violations are planned. Any later implementation helper that
> approaches ruff or aislop complexity limits must be split before commit.

<!-- markdownlint-enable MD013 -->
