<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Implementation Plan: Capability Matrix Support

**Branch**: `011-capability-matrix-support` | **Date**: 2026-06-30 |
**Spec**: [spec.md](./spec.md) **Input**: Feature specification from
`/specs/011-capability-matrix-support/spec.md`

## Summary

Adapt Local Akuvox to the breaking `pylocal-akuvox` v1.0.0 capability matrix by
raising the dependency floor to `pylocal-akuvox>=1.0.0`, handling the new
`/api/system/info` context-entry call at every device-entry site, exposing a
safe default-off unknown-capability opt-in, surfacing unsupported operations
through deduplicated Home Assistant repairs issues, and driving relay entity
availability plus diagnostics from the effective `DeviceCapabilities` snapshot.

## Technical Context

**Language/Version**: Python >=3.13.2, with tooling targeted at Python 3.13 and
CI validation covering Python 3.13 and 3.14 **Primary
Dependencies**: Home Assistant custom integration APIs, `pylocal-akuvox>=1.0.0`,
voluptuous, pytest Home Assistant custom component helpers **Storage**: Home
Assistant config entry data/options only; no database or persistent integration
storage beyond repairs issue registry state **Testing**: pytest with 100%
coverage, interrogate 100% docstring coverage, ruff check/format, mypy strict
mode, reuse, markdownlint, gitlint, and aislop `ci` with failBelow 100
**Target Platform**: Home Assistant custom integration running as
`custom_components/local_akuvox` **Project Type**: Single-project Python custom
component with tests under `tests/` and speckit artifacts under `specs/`
**Performance Goals**: Keep setup responsive by avoiding automatic nine-request
capability probes; coordinator refresh must not add blocking work or duplicate
unsupported-issue spam **Constraints**: Preserve safe defaults, do not bypass
confirmed `UNSUPPORTED` capability results, apply
`attempt_unknown_capability=True` only after successful context entry, keep all
existing config entries absent-safe, and keep the implementation in atomic
stages **Scale/Scope**: One dependency upgrade plus capability-aware setup,
flows, coordinator data, lock entities/services, diagnostics, tests, and release
notes for GitHub issue #149.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| I. Code Quality (NON-NEGOTIABLE) | PASS | Stage 5 must keep typed signatures, docstrings for every new helper, SPDX headers for new files, and green ruff, mypy, interrogate, reuse, markdownlint, and aislop gates. |
| II. Test-Driven Development (NON-NEGOTIABLE) | PASS | Stage 5 must write failing tests first for v1.0.0 lifecycle mocks, opt-in defaults, unsupported repairs, entity availability, probe diagnostics, and release-note coverage before production edits. |
| III. User Experience Consistency | PASS | Unsupported capabilities produce actionable repairs issues and controlled Home Assistant errors; the opt-in text explains the breaking change and defaults to safe `False`. |
| IV. Performance Requirements | PASS | The design avoids automatic first-connect probing because the upstream probe performs nine requests; diagnostics probing is user-triggered and bounded by upstream timeout support. |
| V. Atomic Commits & Compliance (NON-NEGOTIABLE) | PASS | This stage produces one docs-only commit with DCO sign-off. Later stages must separate task-list updates from code, keep SPDX compliance, and never bypass pre-commit. |
| VI. Phased Development | PASS | This stage creates only `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, and `contracts/`. `tasks.md`, production code, tests, and release notes are deferred. |

**Gate Result**: PASS — no violations. Phase 1 design re-check remains PASS
because the artifacts keep the scope to the merged spec and selected
Home Assistant surfaces without adding implementation work in this stage.

## Project Structure

### Documentation (this feature)

```text
specs/011-capability-matrix-support/
├── plan.md                         # This file
├── research.md                     # Phase 0 decisions
├── data-model.md                   # Phase 1 capability/config/repair model
├── quickstart.md                   # Phase 1 verification guide
├── contracts/                      # Phase 1 internal contracts
│   └── capability_matrix.md
└── spec.md                         # Merged Stage 1 source of truth
```

### Source Code (repository root)

```text
.github/
└── release-drafter.yml             # Later implementation PR must carry or add
                                     # breaking-change release-note metadata
.pre-commit-config.yaml             # Bump mypy additional_dependency to
                                     # pylocal-akuvox>=1.0.0
pyproject.toml                      # Bump runtime dependency and version comments
uv.lock                             # Refresh lock after dependency bump

custom_components/local_akuvox/
├── manifest.json                   # Bump runtime requirement to >=1.0.0
├── __init__.py                     # Apply opt-in after entry; widen setup and
│                                    # removal-time context-entry/error handling
├── capability_support.py           # NEW: shared capability option, repairs,
│                                    # diagnostics sanitizing, and precheck helpers
├── config_flow.py                  # Add setup opt-in step; apply option in
│                                    # validation and webhook config push
├── options_flow.py                 # Add options opt-in; apply option before
│                                    # webhook config push
├── const.py                        # Add CONF_ATTEMPT_UNKNOWN_CAPABILITY and
│                                    # default False plus repair identifiers
├── coordinator.py                  # Carry DeviceCapabilities snapshot, handle
│                                    # unsupported fetch/config/user paths
├── diagnostics.py                  # NEW: Home Assistant diagnostics surface and
│                                    # user-triggered safe probe
├── lock.py                         # Capability-driven availability and
│                                    # unsupported service/action handling
├── services.py                     # Keep registrations; add probe service only
│                                    # if diagnostics platform cannot trigger it
├── strings.json                    # Add opt-in and repairs/diagnostics strings
├── webhook.py                      # Handle USER_LIST unsupported during
│                                    # background webhook user-cache refresh
└── translations/
    └── en.json                     # Mirror new user-facing strings

tests/
├── conftest.py                     # v1.0.0-aware AkuvoxDevice capabilities,
│                                    # attempt_unknown_capability, and probe mocks
├── test_config_flow.py             # Opt-in setup flow and entry-time failures
├── test_options_flow.py            # Opt-in options edits and webhook pushes
├── test_create_device.py           # Defaults and option application helpers
├── test_init.py                    # Setup/remove entry context and repairs paths
├── test_coordinator.py             # Capability snapshots and unsupported fetches
├── test_lock.py                    # Entity availability and action handling
├── test_services.py                # Registered service unsupported handling
└── test_webhook.py                 # Webhook cleanup/push and USER_LIST
                                     # refresh unsupported regression coverage
```

**Structure Decision**: Keep the existing flat custom component layout. Add one
small shared `capability_support.py` module to avoid duplicating repairs issue,
capability precheck, and option-application logic across setup, flows,
coordinator, and entities. Add Home Assistant `diagnostics.py` because the
selected probe/diagnostics surface is the standard diagnostics platform.

## Complexity Tracking

> No constitution violations are planned. Any later implementation helper that
> approaches aislop or ruff complexity limits must be split before commit.

<!-- markdownlint-enable MD013 -->
