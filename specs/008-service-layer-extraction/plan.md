<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Implementation Plan: Service Layer Extraction

**Branch**: `008-service-layer-extraction` | **Date**: 2026-06-12 | **Spec**:
[spec.md](./spec.md) **Input**: Feature specification from
`/specs/008-service-layer-extraction/spec.md`

## Summary

Extract the service layer from `__init__.py` (~550 lines) and `lock.py` (~1,735
lines) into focused, single-responsibility modules. Service schemas and
registration move to `services.py`; validation helpers, cloud-provisioning
checks, and utility functions move to `validation.py`. The result is a thin
`__init__.py` (~100–150 lines) and a focused `lock.py` (entity lifecycle +
HA-dispatch-bound service handlers, ~1,545 lines — validation helpers
extracted). This is a pure refactor with zero behavior changes — all 18 services
continue working identically.

## Technical Context

**Language/Version**: Python 3.x (type-annotated, mypy-checked) **Primary
Dependencies**: Home Assistant Core, voluptuous, pylocal_akuvox **Storage**: N/A
(device API via pylocal_akuvox) **Testing**: pytest (~12,000 lines across 11 test
files) **Target Platform**: Home Assistant (custom integration) **Project
Type**: Home Assistant custom component (integration) **Performance Goals**: N/A
(pure refactor, no performance-sensitive changes) **Constraints**: No behavior
changes; all 18 services must remain identical; clear module boundaries;
validation helpers fully extracted from `lock.py` **Scale/Scope**: 4,138 LOC in
integration, ~12,000 LOC in tests; 18 registered services

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle                                       | Status  | Notes                                                                                                                                                            |
| ----------------------------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| I. Code Quality (NON-NEGOTIABLE)                | ✅ PASS | All new modules will include SPDX headers, docstrings, type annotations. No new complexity — code is moved, not rewritten.                                       |
| II. Test-Driven Development (NON-NEGOTIABLE)    | ✅ PASS | Pure refactor — existing tests validate behavior. Only import/reference-path updates should be needed in tests. TDD applies to any *new* test helpers if needed. |
| III. User Experience Consistency                | ✅ PASS | Zero changes to public service interfaces.                                                                                                                       |
| IV. Performance Requirements                    | ✅ PASS | No performance-sensitive changes; no new async paths.                                                                                                            |
| V. Atomic Commits & Compliance (NON-NEGOTIABLE) | ✅ PASS | Each phase produces an atomic commit. New files get SPDX headers. DCO sign-off required.                                                                         |
| VI. Phased Development                          | ✅ PASS | Plan defines clear phases with testable checkpoints.                                                                                                             |

**Gate Result**: PASS — no violations. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/008-service-layer-extraction/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (module dependency model)
├── quickstart.md        # Phase 1 output (developer guide)
├── contracts/           # Phase 1 output (module interfaces)
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
custom_components/local_akuvox/
├── __init__.py          # Thin orchestrator (~100-150 lines)
├── services.py          # NEW: schemas, registration, dispatch config
├── validation.py        # NEW: PIN validation, cloud checks, schedule helpers, CSV parsing
├── lock.py              # Entity + service handlers (~1,545 lines; validation extracted)
├── config_flow.py       # Unchanged
├── const.py             # Unchanged
├── coordinator.py       # Unchanged
├── entity.py            # Unchanged
├── options_flow.py      # Unchanged
├── sanitize.py          # Unchanged
├── webhook.py           # Unchanged
├── services.yaml        # Unchanged
└── manifest.json        # Unchanged

tests/
├── test_init.py         # Import/reference updates only
├── test_lock.py         # Import/reference updates only
├── test_services.py     # Import/reference updates only
├── test_contact_group_services.py  # Import/reference updates only
└── ...                  # Other test files unchanged
```

**Structure Decision**: Flat module layout within the existing
`custom_components/local_akuvox/` package. Two new files (`services.py`,
`validation.py`) are added. No subpackages needed — the extracted helper modules
fit comfortably under 500 lines, while `lock.py` remains larger by necessity
because Home Assistant dispatch binds service handlers to the entity class.

## Complexity Tracking

> No violations to justify. All constitution gates pass cleanly.

<!-- markdownlint-enable MD013 -->
