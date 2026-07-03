<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Quickstart: Webhook Endpoint

**Feature**: 004-webhook-endpoint
**Date**: 2026-03-02

## Prerequisites

- Python ≥3.14.2
- uv package manager
- Existing local-akuvox integration (specs 001-003 implemented)
- Home Assistant development environment (or
  pytest-homeassistant-custom-component for testing)

## New Files

```text
custom_components/akuvox/
├── webhook.py           # Webhook handler + registration helpers
└── sanitize.py          # FR-013 payload sanitization

tests/
├── test_webhook.py      # Webhook handler tests
└── test_sanitize.py     # Sanitization rule tests
```

## Modified Existing Files

- `custom_components/akuvox/const.py` — add webhook-related
  constants (config keys, event name, action URL key mapping,
  known event types)
- `custom_components/akuvox/config_flow.py` — add webhook
  setup step and options flow toggle
- `custom_components/akuvox/__init__.py` — add webhook
  lifecycle in `async_setup_entry`, `async_unload_entry`,
  and the new `async_remove_entry` hook
- `custom_components/akuvox/coordinator.py` — extend
  `AkuvoxCoordinatorData` with a user cache (e.g., `users`
  field or PIN→user map) for `valid_code_entered` lookup
- `custom_components/akuvox/manifest.json` — add
  webhook-related metadata if needed (no `iot_class` change;
  polling always remains active and webhooks are optional)
- `custom_components/akuvox/strings.json` — add webhook UI
  strings
- `custom_components/akuvox/translations/en.json` — add
  webhook translations
- `tests/test_config_flow.py` — add webhook config flow tests
- `tests/test_coordinator.py` — add coordinator user cache
  tests for PIN→user lookup
- `tests/test_init.py` — add webhook setup/teardown tests
- `tests/conftest.py` — add webhook fixtures

## No Changes Required

- `custom_components/akuvox/entity.py` — base entity unchanged
- `custom_components/akuvox/lock.py` — lock entity unchanged
- `custom_components/akuvox/services.yaml` — services unchanged

## Running Tests

```bash
uv run pytest tests/ -x -q
```

## Running Linters

```bash
uv run ruff check custom_components/ tests/
uv run ruff format --check custom_components/ tests/
uv run mypy custom_components/
```

## Key Implementation Order

1. `const.py` — Add webhook-related constants (config keys, event
   name, action URL key mapping, known event types)
2. `coordinator.py` — Extend `AkuvoxCoordinatorData` with user
   cache / PIN→user map for `valid_code_entered` identity lookup
3. `sanitize.py` — Payload sanitization (FR-013); standalone module
   with no HA dependencies for easy unit testing
4. `webhook.py` — Webhook handler, registration/unregistration
   helpers, action URL construction
5. `__init__.py` — Wire webhook lifecycle into setup_entry and
   unload_entry
6. `config_flow.py` — Add webhook step to config flow and webhook
   toggle to options flow
7. `strings.json` + `translations/en.json` — Webhook UI strings

## Config Flow User Experience (Updated)

1. User adds "Akuvox" integration
2. Enter device IP, toggle "Use SSL"
3. If SSL → "Verify SSL" checkbox
4. Select auth mode (None/Basic/Digest)
5. If Basic or Digest → enter username/password
6. Integration tests connection
7. **NEW** → "Enable webhook events?" toggle
8. If enabled → integration pushes action URLs to device
9. If push fails → error with retry/skip option
10. Integration creates config entry with lock entities + webhook

## Webhook Event Testing

Simulate a webhook delivery locally:

```bash
# Relay A triggered (status=1 = high; meaning depends on NO/NC)
curl "http://localhost:8123/api/webhook/{webhook_id}?event=relay_a_triggered&status=1"

# Valid code entered (handler resolves user identity from PIN)
curl "http://localhost:8123/api/webhook/{webhook_id}?event=valid_code_entered&code=1234"
```

> **Note**: These examples use plaintext HTTP on localhost for
> local development only. In any non-loopback environment, the
> device and HA must communicate over HTTPS to protect PINs in
> transit (GET query parameters appear in logs and network
> traffic). Listen for events in HA Developer Tools → Events →
> `akuvox_webhook_received`. Code events emit `device_user_id`,
> `user_id`, and `username` (resolved from PIN lookup) — the
> raw PIN is never included in the event payload.
