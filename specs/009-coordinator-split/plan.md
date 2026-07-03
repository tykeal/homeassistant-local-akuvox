<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Implementation Plan: Coordinator Relay Config Split

**Branch**: `009-coordinator-split` | **Date**: 2026-06-18 | **Spec**:
[spec.md](./spec.md) **Input**: Feature specification from
`/specs/009-coordinator-split/spec.md`

## Summary

Extract the pure relay-config parsing helpers from
`custom_components/local_akuvox/coordinator.py` into a focused
`custom_components/local_akuvox/relay_config.py` module. The new module owns the
frozen `RelayConfig` dataclass plus `_parse_config_int` and
`_build_relay_config`, allowing `coordinator.py` to drop below the aislop
400-line `complexity/file-too-large` gate while preserving behavior, test
coverage, and Home Assistant public APIs.

## Technical Context

**Language/Version**: Python >=3.14.2 (type-annotated, mypy-checked) **Primary
Dependencies**: Home Assistant custom integration APIs, `pylocal-akuvox`
**Storage**: N/A (runtime state comes from the Akuvox device API) **Testing**:
pytest full suite with 100% pass requirement, interrogate 100% docstring
coverage, ruff, mypy, and existing pre-commit hooks **Target Platform**: Home
Assistant custom component **Project Type**: Single-project Python integration
under `custom_components/local_akuvox/` **Performance Goals**: N/A for this pure
refactor; no new I/O, caching, or async behavior **Constraints**: No behavior
change, no public API change, `coordinator.py` must be 400 lines or fewer after
implementation, new source file must include SPDX headers and docstrings
**Scale/Scope**: Move approximately 133 lines from a 470-line coordinator into
one new relay-config module; tests may need import-path-only updates.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| I. Code Quality (NON-NEGOTIABLE) | PASS | The implementation will move existing typed helper code into a new SPDX-covered module with complete docstrings. Ruff, mypy, interrogate, and aislop remain required gates. |
| II. Test-Driven Development (NON-NEGOTIABLE) | PASS | This is a refactor of behavior already covered by existing green tests. No new behavior is introduced; any changed tests should only update internal import paths while keeping assertions equivalent. |
| III. User Experience Consistency | PASS | Relay names, hold delays, relay type/mode parsing, entity names, states, services, and config behavior remain unchanged. |
| IV. Performance Requirements | PASS | The extracted helpers are pure synchronous parsing logic. No new network calls, blocking work, cache semantics, or event-loop behavior are introduced. |
| V. Atomic Commits & Compliance (NON-NEGOTIABLE) | PASS | This stage produces one docs-only commit. Later implementation must use SPDX headers on `relay_config.py`, DCO sign-off, pre-commit, and capitalized Conventional Commits. |
| VI. Phased Development | PASS | This stage produces only plan and design artifacts. `tasks.md` and production/test code changes are deferred to later speckit stages. |

**Gate Result**: PASS — no violations. Phase 1 design re-check remains PASS
because the artifacts keep scope to the planned extraction and introduce no
unsupported behavior or public API changes.

## Project Structure

### Documentation (this feature)

```text
specs/009-coordinator-split/
├── plan.md              # This file
├── research.md          # Phase 0 decisions
├── data-model.md        # Phase 1 entity/helper contracts
├── quickstart.md        # Phase 1 developer guide
├── contracts/           # Phase 1 module interface contract
│   └── relay_config.md
├── spec.md              # Merged Stage 1 source of truth
└── tasks.md             # Phase 2 output; not created in this stage
```

### Source Code (repository root)

```text
custom_components/local_akuvox/
├── relay_config.py      # NEW: RelayConfig and pure parsing helpers
├── coordinator.py       # Modified: imports RelayConfig/_build_relay_config
│                        # and retains coordinator state/fetch/cache logic
├── const.py             # Unchanged: supplies relay config constants
└── ...                  # Other integration modules unchanged

tests/
├── test_coordinator.py  # Import-path updates for moved parser symbols
├── test_lock.py         # Import-path update for RelayConfig construction
└── ...                  # Other tests unchanged unless discovery proves needed
```

**Structure Decision**: Use the existing flat module layout inside
`custom_components/local_akuvox/`. A single new `relay_config.py` is sufficient
because the moved symbols form one cohesive parsing unit and do not require a
subpackage. `coordinator.py` continues to own relay-letter discovery,
configuration fetch/caching, device errors, and `AkuvoxCoordinatorData`.

## Complexity Tracking

> No violations to justify. All constitution gates pass cleanly.

<!-- markdownlint-enable MD013 -->
