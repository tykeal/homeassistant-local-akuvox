<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Implementation Plan: Webhook Endpoint

**Branch**: `004-webhook-endpoint` | **Date**: 2026-03-02
**Spec**: [spec.md](spec.md)
**Input**: Feature specification from
`/specs/004-webhook-endpoint/spec.md`

## Summary

Add real-time event delivery to the Akuvox integration by receiving
device Action URL webhooks. The Akuvox device sends HTTP GET requests
with query parameters to configured URLs when events occur (relay
open/close, input trigger, code entry). The integration registers a
per-device webhook endpoint via Home Assistant's webhook
infrastructure, parses incoming requests, fires events on the HA
event bus, and triggers an immediate coordinator refresh on valid
code entry (since multiple relays may change simultaneously).

The integration also manages the device-side configuration: when
the user enables webhooks, the integration pushes all 10 core action
URLs plus the `Config.Features.ACTIONURL.Enable` and
`Config.Features.ACTIONURL.Method` keys to the device
via `set_device_config()` (with `Method` set to `""` to
ensure default GET behavior). The 10 action URLs are the
core set present on all PIN-controlled Akuvox devices:
relay A/B triggered/closed, input A/B triggered/closed,
and valid/invalid code entered. Model-specific action
URLs (InputC, Card, Face, Alarm, Call) are handled
through the generic event path without code changes.

## Technical Context

**Language/Version**: Python ≥3.14.2
**Primary Dependencies**: pylocal-akuvox ≥0.2.3 (device
communication, `set_device_config()`), homeassistant ≥2026.7.0
(webhook infrastructure via `homeassistant.components.webhook`)
**Storage**: Home Assistant config entries (webhook_id and
webhook_enabled persisted in entry data)
**Testing**: pytest, pytest-homeassistant-custom-component,
pytest-asyncio, pytest-cov
**Target Platform**: Home Assistant (any platform running HA Core)
**Project Type**: Home Assistant custom integration (HACS)
**Performance Goals**: Webhook events delivered to HA event bus
within 2 seconds of device trigger (SC-001); valid code entry
triggers immediate coordinator refresh
**Constraints**: MUST NOT block the HA event loop; all device I/O
MUST be async; webhook handler MUST be stateless and concurrent-safe
(FR-014); payload sanitization per FR-013
**Scale/Scope**: Single integration supporting multiple Akuvox
devices, each with its own webhook endpoint; 10 core action URL
event types

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1
design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| I. Code Quality | ✅ PASS | ruff/mypy/interrogate; SPDX |
| II. TDD | ✅ PASS | pytest + HA test helpers |
| III. UX Consistency | ✅ PASS | Follows config flow patterns |
| IV. Performance | ✅ PASS | Async; no blocking |
| V. Atomic Commits | ✅ PASS | Pre-commit; DCO sign-off |
| VI. Phased Dev | ✅ PASS | Three phases match stories |

### Post-Design Re-Check

| Principle | Status | Notes |
| --------- | ------ | ----- |
| I. Code Quality | ✅ PASS | New modules fully typed |
| II. TDD | ✅ PASS | Tests before implementation |
| III. UX Consistency | ✅ PASS | Standard HA webhook patterns |
| IV. Performance | ✅ PASS | Trivial query param parsing |
| V. Atomic Commits | ✅ PASS | Module-per-commit |
| VI. Phased Dev | ✅ PASS | Each phase testable alone |

## Project Structure

### Documentation (this feature)

```text
specs/004-webhook-endpoint/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   └── requirements.md
├── contracts/
│   ├── webhook-handler.md
│   ├── config-flow-webhook.md
│   └── payload-sanitization.md
└── tasks.md             # Created by /speckit.tasks
```

### Source Code (repository root)

HACS requires the integration at
`custom_components/DOMAIN_NAME/` at the repository root.

```text
custom_components/akuvox/
├── __init__.py          # + webhook lifecycle in setup/unload/remove
├── config_flow.py       # + webhook setup step + options toggle
├── const.py             # + webhook constants, action URL keys
├── coordinator.py       # + user cache for PIN→user lookup
├── entity.py            # (unchanged)
├── lock.py              # (unchanged)
├── manifest.json        # + webhook-related metadata (no iot_class change)
├── sanitize.py          # NEW: FR-013 payload sanitization
├── services.yaml        # (unchanged)
├── strings.json         # + webhook UI strings
├── translations/
│   └── en.json          # + webhook translations
└── webhook.py           # NEW: handler + registration helpers

tests/
├── conftest.py          # + webhook fixtures
├── test_config_flow.py  # + webhook config flow tests
├── test_coordinator.py  # + coordinator user cache tests
├── test_init.py         # + webhook setup/teardown tests
├── test_sanitize.py     # NEW: sanitization rule tests
└── test_webhook.py      # NEW: webhook handler tests
```

**Structure Decision**: Standard HACS custom integration layout.
Two new modules (`webhook.py`, `sanitize.py`) added alongside
existing files. `sanitize.py` is kept separate for clean unit
testing with no HA dependencies. `webhook.py` contains the HA
webhook handler and all registration/URL-construction logic.

## Complexity Tracking

> No constitution violations to justify.
