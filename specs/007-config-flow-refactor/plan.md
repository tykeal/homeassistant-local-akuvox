<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Implementation Plan: Config Flow Refactor

**Branch**: `007-config-flow-refactor`
**Date**: 2026-06-12
**Spec**: [spec.md](./spec.md)
**Input**: Feature specification from
`/specs/007-config-flow-refactor/spec.md`

## Summary

Refactor `config_flow.py` (622 lines) by extracting the `AkuvoxOptionsFlow`
class into a dedicated `options_flow.py` module. The `AkuvoxConfigFlow` class
remains in `config_flow.py` per Home Assistant convention. The `_build_schema`
helper stays with `AkuvoxOptionsFlow` since it is only used there. This is a
pure structural refactor with zero behavior changes — all existing tests must
pass with only import path updates.

## Technical Context

- **Language/Version**: Python ≥3.14.2
- **Primary Dependencies**: homeassistant ≥2026.7.0, pylocal-akuvox ≥0.4.2,
  voluptuous (bundled with HA)
- **Storage**: N/A (config entries managed by Home Assistant core)
- **Testing**: pytest + pytest-homeassistant-custom-component +
  pytest-asyncio
- **Target Platform**: Home Assistant (Linux/any OS running HA Core)
- **Project Type**: Home Assistant custom integration (`custom_components`)
- **Performance Goals**: N/A (refactor only — no runtime behavior change)
- **Constraints**: Each resulting module must be under 400 lines, avoid
  circular imports, and add no new dependencies
- **Scale/Scope**: Single integration package
  (`custom_components/local_akuvox/`), splitting one 622-line file into
  roughly two files totaling ~640 lines after header/import overhead

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Code Quality — linting, docstrings, types, SPDX**: ✅ PASS. New file
  gets SPDX header; all existing annotations are preserved.
- **II. TDD — red-green-refactor**: ✅ PASS. Existing tests serve as the
  "green" baseline. No new behavior means no new tests are required, and
  import-path updates remain allowed per FR-004.
- **III. UX Consistency**: ✅ PASS. No user-facing change.
- **IV. Performance**: ✅ PASS. No runtime change.
- **V. Atomic Commits & Compliance**: ✅ PASS. Single logical refactor commit
  with DCO sign-off and SPDX headers.
- **VI. Phased Development**: ✅ PASS. Single-phase refactor with a final
  checkpoint of all tests green post-extraction.

**Gate verdict**: ALL PASS — proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/007-config-flow-refactor/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal — no external API)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
custom_components/local_akuvox/
├── __init__.py          # Integration setup (unchanged)
├── config_flow.py       # AkuvoxConfigFlow only (lines 1–396 post-refactor)
├── options_flow.py      # NEW: AkuvoxOptionsFlow + _build_schema (extracted)
├── const.py             # Constants (unchanged)
├── coordinator.py       # Data coordinator (unchanged)
├── entity.py            # Entity base (unchanged)
├── lock.py              # Lock platform (unchanged)
├── manifest.json        # Manifest (unchanged)
├── sanitize.py          # Sanitization helpers (unchanged)
├── services.yaml        # Service definitions (unchanged)
├── strings.json         # UI strings (unchanged)
├── translations/        # Translation files (unchanged)
└── webhook.py           # Webhook helpers (unchanged)

tests/
├── test_config_flow.py  # Updated: patch paths for options tests
├── test_create_device.py # Updated: import from options_flow
└── ...                  # All other test files unchanged
```

**Structure Decision**: Standard Home Assistant custom component layout. The
only structural change is adding `options_flow.py` alongside `config_flow.py` in
the same package.

## Complexity Tracking

> No violations — no entries needed.

- No violations.
