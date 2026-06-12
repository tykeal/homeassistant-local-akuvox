<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Research: Config Flow Refactor

**Feature**: 007-config-flow-refactor **Date**: 2026-06-12 **Status**: Complete

## Research Questions

### RQ-1: Home Assistant convention for options flow module location

**Context**: FR-001 requires ConfigFlow to remain in `config_flow.py`. Need to
verify whether HA supports options flow in a separate module.

**Decision**: Extract `AkuvoxOptionsFlow` to `options_flow.py` within the same
package, imported by `config_flow.py` in the `async_get_options_flow` callback.

**Rationale**: Home Assistant's integration loader only looks for the
`ConfigFlow` class in `config_flow.py` (discovered via the `domain` class
variable). The options flow handler is resolved at runtime via the
`async_get_options_flow` static method — it can return any `OptionsFlow`
subclass regardless of where it's defined. Many community integrations (e.g.,
HACS-distributed ones) split options into separate modules. The HA core
constraint is solely on `ConfigFlow` location.

**Alternatives considered**:

- Keep everything in one file with better sectioning (comments/regions) —
  rejected because the spec explicitly requires extraction and < 400 lines per
  module.
- Use a `flows/` subpackage — rejected as over-engineering for a two-class
  split; adds unnecessary `__init__.py` and complicates imports.

---

### RQ-2: Circular import risk between config_flow.py and options_flow.py

**Context**: Edge case from spec — both files import from `.const` and
`.webhook`. If `config_flow.py` imports from `options_flow.py`, and
`options_flow.py` imports from `config_flow.py`, a circular import would occur.

**Decision**: The dependency is one-directional: `config_flow.py` imports
`AkuvoxOptionsFlow` from `options_flow.py`. The `options_flow.py` module does
NOT import anything from `config_flow.py`. Both import shared symbols from
`.const` and `.webhook` — these are leaf modules with no back-references.

**Rationale**: Analyzing the current code:

- `AkuvoxConfigFlow.async_get_options_flow()` returns
  `AkuvoxOptionsFlow(config_entry)` — this is the only cross-reference.
- `AkuvoxOptionsFlow` uses: `vol`, `OptionsFlow`, `ConfigEntry`, `secrets`,
  `AkuvoxDevice`, `AuthConfig`, `AuthMethod`, `build_action_urls`, and constants
  from `.const`. None of these come from `config_flow.py`.
- The `_build_schema` method is a `@staticmethod` used only within
  `AkuvoxOptionsFlow` — it moves with the class.

**Alternatives considered**:

- Use `TYPE_CHECKING` guard for the import — rejected because the import is
  needed at runtime (not just for type hints).
- Lazy import inside `async_get_options_flow` — viable but unnecessary since
  there's no circular dependency. A top-level import is cleaner.

---

### RQ-3: Test patch paths that must change

**Context**: Need to identify exactly which tests patch `AkuvoxDevice` through
`config_flow.py` versus other import paths so only the necessary tests change
after extracting `AkuvoxOptionsFlow`.

**Decision**:

- Options flow **basic** tests in `tests/test_config_flow.py` (lines 421–797)
  already patch `custom_components.local_akuvox.AkuvoxDevice` at the package
  (`__init__.py`) level and need **zero changes**.
- Only options flow **webhook** tests in `tests/test_config_flow.py` (lines
  1080+) patch `custom_components.local_akuvox.config_flow.AkuvoxDevice`; those
  targets must change to
  `custom_components.local_akuvox.options_flow.AkuvoxDevice`.
- Tests for `AkuvoxConfigFlow` keep their existing patch targets.

**Rationale**: Python's `unittest.mock.patch` must target the name where the
code under test looks it up. The basic options tests already patch the
package-level `AkuvoxDevice` reference they exercise, so the refactor does not
affect them. The webhook options tests patch the class through `config_flow.py`;
once `AkuvoxOptionsFlow` moves, those specific patches must follow the class to
`options_flow.py`.

**Affected test files**:

1. `tests/test_config_flow.py` — Basic options tests (lines 421–797) need no
   changes; webhook options tests (lines 1080+) must update patch targets from
   `config_flow.AkuvoxDevice` to `options_flow.AkuvoxDevice`.
2. `tests/test_create_device.py` — Imports `AkuvoxOptionsFlow` from
   `config_flow`. Must change to import from `options_flow`.

**Alternatives considered**:

- Re-export `AkuvoxOptionsFlow` from `config_flow.py` to avoid test changes —
  rejected because it defeats the purpose of the refactor and creates a
  confusing re-export layer.

---

### RQ-4: Shared utility extraction needs

**Context**: Spec assumption mentions `_build_schema` as potential shared logic.
Need to verify if ConfigFlow uses it.

**Decision**: No shared utility extraction needed. `_build_schema` is used
exclusively by `AkuvoxOptionsFlow` and moves with it.

**Rationale**: Code analysis of `AkuvoxConfigFlow` shows it builds schemas
inline (small, step-specific schemas with 1-2 fields each). The `_build_schema`
method constructs the comprehensive options form (8 fields) — only relevant to
the options flow. There is no schema-building code shared between the two
classes.

**Alternatives considered**:

- Extract `_build_schema` to a shared `schemas.py` module — rejected as YAGNI;
  no consumer exists outside `AkuvoxOptionsFlow`.

---

### RQ-5: Line count feasibility (< 400 lines per module)

**Context**: SC-002 and SC-003 require each file to be under 400 lines.

**Decision**: Feasible without any code changes beyond the split.

**Rationale**:

- Current file: 622 lines total.
- `AkuvoxConfigFlow` (lines 47–396): ~350 lines including the class +
  module-level imports/logger.
- `AkuvoxOptionsFlow` (lines 398–622): ~225 lines.
- After adding SPDX header (2 lines), module docstring (2 lines), and imports
  (~20 lines) to `options_flow.py`: ~250 lines.
- `config_flow.py` after extraction: ~396 lines (existing header + imports +
  `AkuvoxConfigFlow` + new import of `AkuvoxOptionsFlow`). Well under 400.

**Alternatives considered**: N/A — straightforward arithmetic confirms
feasibility.

---

### RQ-6: `build_action_urls` import strategy

**Context**: Both `AkuvoxConfigFlow._async_push_webhook_config` and
`AkuvoxOptionsFlow._async_handle_webhook_change` use `build_action_urls` from
`.webhook`.

**Decision**: Both modules independently import `from .webhook import
build_action_urls`. This is a leaf dependency with no risk of circular imports.

**Rationale**: `.webhook` imports only from `.const` and standard library / HA
core. Neither `config_flow` nor `options_flow` is imported by `.webhook`.

**Alternatives considered**: N/A — the standard approach works cleanly.

## Summary of Findings

All NEEDS CLARIFICATION items are resolved. The refactor is straightforward:

1. **No shared utility extraction needed** — `_build_schema` is
   AkuvoxOptionsFlow-only.
2. **No circular import risk** — dependency is unidirectional (config_flow →
   options_flow).
3. **Line count is feasible** — both modules will be well under 400 lines.
4. **Test changes are minimal** — update patch paths for options tests and
   direct imports in `test_create_device.py`.
5. **Home Assistant supports this pattern** — options flow can live anywhere;
   only ConfigFlow location is constrained.
