<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Data Model: Config Flow Refactor

**Feature**: 007-config-flow-refactor
**Date**: 2026-06-12

## Overview

This is a pure structural refactor — no data model changes occur. This document
captures the module-level entities (classes) and their relationships to guide
the extraction.

## Entities

### AkuvoxConfigFlow

**Properties**:

- `VERSION`: `int` class variable for config entry schema version (`1`)
- `_data`: `dict[str, Any]` storing accumulated user input across steps

**Location**: `custom_components/local_akuvox/config_flow.py` (unchanged)

**Responsibilities**:

- Initial device setup wizard (host → SSL → auth → credentials → connection test
  → webhook)
- Unique ID assignment from device MAC address
- Config entry creation
- Options flow handler delegation via `async_get_options_flow`

**Methods**:

- `async_get_options_flow(config_entry)` → returns `AkuvoxOptionsFlow`
- `async_step_user(user_input)` → host + SSL form
- `async_step_ssl(user_input)` → SSL verification form
- `async_step_auth(user_input)` → auth method selector
- `async_step_credentials(user_input)` → username/password form
- `_async_test_connection()` → device connectivity validation
- `async_step_webhook(user_input)` → webhook enable/disable
- `_async_push_webhook_config(webhook_id, enable)` → push URLs to device

---

### AkuvoxOptionsFlow

**Properties**:

- `_config_entry`: `ConfigEntry` for the entry being reconfigured

**Location**: `custom_components/local_akuvox/options_flow.py` (NEW)

**Responsibilities**:

- Options form presenting all connection parameters with current values
- Input validation (host, credentials)
- Webhook state change handling (enable/disable push to device)
- Config entry options update triggering reload

**Methods**:

- `async_step_init(user_input)` → main options form
- `_async_handle_webhook_change(user_input)` → webhook state transition logic
- `_build_schema(current)` → `@staticmethod` building the options vol.Schema

---

## Relationships

```text
┌─────────────────────────┐         imports          ┌─────────────────────────┐
│   config_flow.py        │ ───────────────────────► │   options_flow.py       │
│                         │                          │                         │
│  AkuvoxConfigFlow       │                          │  AkuvoxOptionsFlow      │
│    ├── async_get_       │  returns instance of     │    ├── async_step_init  │
│    │   options_flow ────│─────────────────────────►│    ├── _async_handle_   │
│    ├── async_step_user  │                          │    │   webhook_change   │
│    ├── async_step_ssl   │                          │    └── _build_schema    │
│    ├── async_step_auth  │                          │                         │
│    ├── async_step_creds │                          └───────────┬─────────────┘
│    ├── _async_test_conn │                                      │
│    ├── async_step_      │                                      │ imports
│    │   webhook          │                                      ▼
│    └── _async_push_     │         imports          ┌─────────────────────────┐
│        webhook_config   │ ───────────────────────► │   const.py              │
│                         │                          │   webhook.py            │
└─────────────────────────┘                          │   (leaf dependencies)   │
                                                     └─────────────────────────┘
```

## State Transitions

No state machine changes. The config entry lifecycle remains:

```text
[Not Configured] ──setup flow──► [Configured (data)]
[Configured] ──options flow──► [Configured (data + options)] ──reload──► [Running]
```

## Validation Rules

All validation rules are unchanged and move with their respective classes:

- Host must be non-empty and non-whitespace. Enforced inline in
  `ConfigFlow.step_user` and `OptionsFlow.step_init`.
- Auth credentials are required for BASIC/DIGEST. Enforced inline in
  `ConfigFlow.step_auth` and `OptionsFlow.step_init`.
- Connection must succeed before entry creation. Enforced by
  `_async_test_connection` in `ConfigFlow`.
- Request delay must be in the `0.0–5.0` range. Enforced by `vol.Range` in
  `_build_schema`.
- Webhook pushes must succeed for state changes. Enforced with try/except
  handling in both flows.

## Import Maps (Post-Refactor)

### config_flow.py imports

```python
from __future__ import annotations
import logging
import secrets
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow
from homeassistant.core import callback
from pylocal_akuvox import (
    AkuvoxAuthenticationError,
    AkuvoxConnectionError,
    AkuvoxDevice,
    AkuvoxError,
    AuthConfig,
    AuthMethod,
)

from .const import (
    AUTH_BASIC,
    AUTH_DIGEST,
    AUTH_NONE,
    CONF_AUTH_METHOD,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_REQUEST_DELAY,
    CONF_USE_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    CONF_WEBHOOK_ENABLED,
    CONF_WEBHOOK_ID,
    DEFAULT_REQUEST_DELAY,
    DOMAIN,
    get_auth_method_map,
)
from .options_flow import AkuvoxOptionsFlow
from .webhook import build_action_urls
```

### options_flow.py imports

```python
from __future__ import annotations
import secrets
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from pylocal_akuvox import AkuvoxDevice, AuthConfig, AuthMethod

from .const import (
    AUTH_BASIC,
    AUTH_DIGEST,
    AUTH_NONE,
    CONF_AUTH_METHOD,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_REQUEST_DELAY,
    CONF_USE_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    CONF_WEBHOOK_ENABLED,
    CONF_WEBHOOK_ID,
    DEFAULT_REQUEST_DELAY,
    get_auth_method_map,
)
from .webhook import build_action_urls
```

**Key difference**: `options_flow.py` does NOT import `DOMAIN` (not needed) and
does NOT import from `config_flow.py` (no circular dependency).
