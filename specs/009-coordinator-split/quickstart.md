<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Quickstart: Coordinator Relay Config Split

**Feature**: 009-coordinator-split **Date**: 2026-06-18

## Overview

The implementation stage extracts relay-config parsing from
`custom_components/local_akuvox/coordinator.py` into
`custom_components/local_akuvox/relay_config.py`. The change is a mechanical
refactor: no new behavior, services, entity attributes, or configuration options.

## Development Notes

1. Create `relay_config.py` with SPDX headers, docstrings, and these symbols:
   `RelayConfig`, `_parse_config_int`, `_build_relay_config`.
1. Move the existing helper implementations without changing validation rules,
   defaults, warning text, or signatures.
1. Update `coordinator.py` to import `RelayConfig` and `_build_relay_config` from
   `.relay_config` and remove the old inline definitions.
1. Keep `RELAY_KEY_RE` and relay-letter discovery in `coordinator.py`.
1. Update `tests/test_coordinator.py` imports for the moved parser symbols to
   use `custom_components.local_akuvox.relay_config`. Also update the
   `RelayConfig` fixture import in `tests/test_lock.py`.

## How to Verify

```bash
uv run pytest tests/
uv run ruff check custom_components/ tests/
uv run mypy custom_components/local_akuvox/
uv run interrogate custom_components/ tests/
uv run aislop ci --staged
wc -l custom_components/local_akuvox/coordinator.py
```

Expected results:

- All existing tests pass.
- Ruff, mypy, interrogate, and aislop complete successfully.
- Interrogate remains at 100% docstring coverage.
- `coordinator.py` is 400 lines or fewer.
- Relay config tests keep the same assertions after import-path updates.

## Common Pitfalls

- Do not re-export `_parse_config_int` or `_build_relay_config` from
  `coordinator.py`; they are private helpers, not public APIs.
- Do not move `AkuvoxCoordinatorData` or config fetch/cache methods into
  `relay_config.py`.
- Do not rename constants from `const.py` or alter the config key composition.
- Do not add new behavior while clearing the file-size gate.
