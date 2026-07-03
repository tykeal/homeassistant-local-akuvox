<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Implementation Plan: Add Lock Action

**Branch**: `005-add-lock-action` | **Date**: 2026-03-05
**Spec**: [spec.md](spec.md)
**Input**: Feature specification from
`/specs/005-add-lock-action/spec.md`

## Summary

Replace the current `async_lock` stub (which raises
`HomeAssistantError`) with a mode-aware lock implementation on
all Akuvox lock entities. For **bistable (manual) relays**, the
lock action refreshes device state (FR-009), sends a
`trigger_relay` command only when the relay is confirmed unlocked
(FR-001, FR-008), sets `_optimistic_locked = True`, and schedules
a delayed state refresh. For **auto-close (monostable) relays**,
the lock action performs only a synchronous state refresh (no relay
command is ever sent) to avoid initiating or extending an unlock
window (FR-008).

The implementation reuses the existing relay configuration
(`RelayConfig`), `trigger_relay` device API, optimistic state
pattern (`_optimistic_locked`, `_async_finish_optimistic_unlock`),
and `_schedule_delayed_refresh` infrastructure established in the
unlock action and refined in spec 004.

## Technical Context

**Language/Version**: Python ≥3.14.2
**Primary Dependencies**: pylocal-akuvox ≥0.2.3 (device
communication via `trigger_relay()`), homeassistant ≥2026.7.0
(LockEntity, coordinator, async helpers)
**Storage**: N/A (uses existing coordinator data and entity state)
**Testing**: pytest, pytest-homeassistant-custom-component,
pytest-asyncio, pytest-cov
**Target Platform**: Home Assistant (any platform running HA Core)
**Project Type**: Home Assistant custom integration (HACS)
**Performance Goals**: Lock action completes and entity state
updates within 5 seconds for bistable relays (SC-002)
**Constraints**: MUST NOT block the HA event loop; all device I/O
MUST be async; must preserve existing unlock behavior (SC-005)
**Scale/Scope**: Single file modification (`lock.py`) plus tests;
no new modules, no new dependencies

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1
design.*

| Principle        | Status  | Notes                           |
| ---------------- | ------- | ------------------------------- |
| I. Code Quality  | ✅ PASS | ruff/mypy/interrogate; SPDX     |
| II. TDD          | ✅ PASS | pytest + HA test helpers; TDD   |
| III. UX          | ✅ PASS | Standard HA lock interface      |
| IV. Performance  | ✅ PASS | Async; ≤5s; no blocking calls   |
| V. Atomic Cmts   | ✅ PASS | Pre-commit; DCO sign-off        |
| VI. Phased Dev   | ✅ PASS | Multi-phase TDD per tasks.md    |

No violations. Complexity tracking not needed.

### Post-Design Re-Check

| Principle        | Status  | Notes                           |
| ---------------- | ------- | ------------------------------- |
| I. Code Quality  | ✅ PASS | Single method; CC under 10      |
| II. TDD          | ✅ PASS | Tests precede implementation    |
| III. UX          | ✅ PASS | Standard HA lock; clear errors  |
| IV. Performance  | ✅ PASS | Async; ≤5s update (SC-002)      |
| V. Atomic Cmts   | ✅ PASS | Pre-commit; DCO; SPDX           |
| VI. Phased Dev   | ✅ PASS | Six phases; tests before impl   |

No new violations introduced by design.

## Project Structure

### Documentation (this feature)

```text
specs/005-add-lock-action/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── lock-service.md  # Lock service interface contract
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
custom_components/akuvox/
├── lock.py              # Modified: replace async_lock stub with implementation
└── (no other files modified)

tests/
└── test_lock.py         # Modified: replace stub and add lock tests
```

**Structure Decision**: No new files needed. The lock action is
implemented entirely within the existing `AkuvoxLockEntity` class
in `lock.py`. Tests extend the existing `test_lock.py` file.
