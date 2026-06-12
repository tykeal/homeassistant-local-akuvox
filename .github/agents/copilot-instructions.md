---
description: Development guidelines and conventions for the local-akuvox Home Assistant integration.
applyTo: '**'
---

<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# local-akuvox Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-06-12

## Active Technologies
- Python ≥3.13.2 with pylocal-akuvox (001-akuvox-lock-integration)
- Home Assistant config entries (001-akuvox-lock-integration)
- Python ≥3.13.2 with homeassistant, pylocal-akuvox ≥0.2.3, voluptuous (002-device-config-discovery)
- Python ≥3.13.2 + pylocal-akuvox ≥0.2.3 schedule/user services (003-schedule-user-services)
- Python ≥3.13.2 + pylocal-akuvox ≥0.2.3, HA webhook infra (004-webhook-endpoint)
- HA config entries with webhook_id, webhook_enabled (004-webhook-endpoint)
- Python ≥3.13.2 + pylocal-akuvox ≥0.2.3 device communication (005-add-lock-action)
- N/A storage, uses existing coordinator data and entity state (005-add-lock-action)
- Python ≥3.13.2 (type-annotated, mypy-checked) + homeassistant, voluptuous, pylocal-akuvox (008-service-layer-extraction)
- N/A (device API via pylocal-akuvox) (008-service-layer-extraction)

## Project Structure

```text
custom_components/local_akuvox/
tests/
```

## Commands

```bash
uv run pytest tests/ -x -q
uv run ruff check custom_components/ tests/
uv run ruff format --check custom_components/ tests/
uv run mypy custom_components/
```

## Code Style

Python ≥3.13.2: Follow standard HA integration conventions

## Recent Changes
- 008-service-layer-extraction: Added service-layer extraction
  plan artifacts (plan, research, data model, quickstart,
  contracts)

- 005-add-lock-action: Added lock action plan artifacts
  (plan, research, data model, quickstart, contracts)
- 004-webhook-endpoint: Planned (design phase) Python ≥3.13.2 +
  pylocal-akuvox ≥0.2.3 (device communication)
- 004-webhook-endpoint: Planned (design phase) webhook handler,
  sanitize module, config/options flow webhook step, action URL
  push to device, coordinator refresh on relay/valid-code events
- 003-schedule-user-services: Implemented all 10 schedule/user
  CRUD services (list, add, modify, delete for schedules and
  users, plus add/remove user schedule_relay pair convenience
  services)
- 002-device-config-discovery: Added relay naming, hold delay,
  NO/NC relay type awareness, edge case tests, reload coverage,
  pylocal-akuvox-based device communication

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
