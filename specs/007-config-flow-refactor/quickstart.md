<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Quickstart: Config Flow Refactor

**Feature**: 007-config-flow-refactor
**Date**: 2026-06-12

## What This Refactor Does

Splits `custom_components/local_akuvox/config_flow.py` (622 lines) into two
focused modules:

- `config_flow.py`: `AkuvoxConfigFlow` (initial setup wizard), ~370 lines
- `options_flow.py`: `AkuvoxOptionsFlow` (runtime option editing), ~250 lines

**No behavior changes.** Same forms, same validation, same errors, same data.

## Prerequisites

- Python ≥3.13.2
- `uv` package manager
- Project dependencies installed: `uv sync --group dev`

## Implementation Steps (High-Level)

1. **Create `options_flow.py`** with SPDX header, imports, and the
   `AkuvoxOptionsFlow` class (copy lines 398–622 from current `config_flow.py`).

2. **Update `config_flow.py`**:
   - Remove `AkuvoxOptionsFlow` class and its `OptionsFlow` import.
   - Add `from .options_flow import AkuvoxOptionsFlow` at the top.
   - Remove now-unused imports, but keep `secrets` in `config_flow.py` because
     `AkuvoxConfigFlow._async_push_webhook_config` uses `secrets.token_hex(32)`
     at line 302. If `options_flow.py` also uses `secrets`, it must import it
     independently.

3. **Update test patch paths**:
   - `tests/test_config_flow.py`: Options-flow tests change patch target from
     `custom_components.local_akuvox.config_flow.AkuvoxDevice` to
     `custom_components.local_akuvox.options_flow.AkuvoxDevice`.
   - `tests/test_create_device.py`: Change `from
     custom_components.local_akuvox.config_flow import AkuvoxOptionsFlow` to
     `from custom_components.local_akuvox.options_flow import
     AkuvoxOptionsFlow`.

4. **Verify**:

```bash
# Run all tests
uv run pytest tests/ -v

# Check line counts
wc -l custom_components/local_akuvox/config_flow.py
wc -l custom_components/local_akuvox/options_flow.py

# Lint + type check
uv run ruff check custom_components/ tests/
uv run mypy custom_components/
```

## Verification Checklist

- [ ] `uv run pytest tests/` — all tests pass
- [ ] `wc -l config_flow.py` < 400
- [ ] `wc -l options_flow.py` < 400
- [ ] `uv run ruff check` — zero errors
- [ ] `uv run mypy` — zero errors
- [ ] No circular import: `uv run python -c "from
  custom_components.local_akuvox.config_flow import AkuvoxConfigFlow"`
- [ ] SPDX header present on `options_flow.py`
- [ ] Integration loads in HA dev environment (optional manual check)

## Risk Areas

1. **Patch path misses** — If any test patches `config_flow.AkuvoxDevice` but
   actually exercises options flow code, it will silently pass with real device
   calls (caught by CI since no network available).

2. **Circular import risk** — `config_flow.py` can safely import
   `AkuvoxOptionsFlow` at module scope, but `options_flow.py` must not import
   back from `config_flow.py`. The real failure mode is a circular import, not a
   forward-reference issue.
