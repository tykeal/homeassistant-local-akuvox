<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Internal Module Contract: options_flow.py

**Feature**: 007-config-flow-refactor **Date**: 2026-06-12

## Overview

This contract defines the public interface that `options_flow.py` exposes to
`config_flow.py` (its only consumer within the integration package). Since this
integration does not expose a public API to external consumers, this is an
internal-only contract.

## Exported Symbol

### `AkuvoxOptionsFlow`

```python
class AkuvoxOptionsFlow(OptionsFlow):
    """Handle options flow for Akuvox integration."""

    def __init__(self, config_entry: ConfigEntry) -> None: ...
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any: ...
```

**Consumer**: `AkuvoxConfigFlow.async_get_options_flow` in `config_flow.py`

**Contract**:

- MUST accept a `ConfigEntry` as its sole constructor argument.
- MUST implement `async_step_init` as the entry point (HA convention for options
  flows).
- MUST return flow results compatible with HA's `OptionsFlow` protocol.
- MUST NOT import from `config_flow.py` (prevents circular dependencies).

## Import Contract

The module import chain MUST be acyclic:

```text
config_flow.py → options_flow.py → const.py, webhook.py
config_flow.py → const.py, webhook.py
```

Neither `const.py` nor `webhook.py` may import from `config_flow.py` or
`options_flow.py`.

## Stability Guarantee

This is an internal contract. It may change in future refactors without external
notice, provided all tests continue to pass.
