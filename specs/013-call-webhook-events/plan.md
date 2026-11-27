<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Implementation Plan: Call Webhook Events

**Branch**: `docs/013-call-webhook-events-plan` | **Date**: 2026-11-27 |
**Spec**: [spec.md](./spec.md) **Input**: Feature specification from
`/specs/013-call-webhook-events/spec.md`

## Summary

Add two optional, capability-gated Action URL keys — `MakeCall` (`call_made`)
and `HangUp` (`call_ended`) — whose URL templates carry `remote=$remote`. A pure
presence check over the device's `DeviceConfig` decides which optional keys a
device supports; `build_action_urls()` gains an `optional_keys` argument so the
enable/disable payloads stay byte-identical for devices without the keys. The
config flow, options flow, and entry removal detect supported keys on the same
device session before pushing. At entry load, a config-entry background task
reconciles only the optional keys, writing when the device's stored values
differ from the expected URLs. The webhook handler adds `remote` to known-event
payloads and redacts it from the missing-`event` warning log.

## Technical Context

**Language/Version**: Python >=3.14.2 (CI on 3.14)
**Primary Dependencies**: Home Assistant custom integration APIs,
`pylocal-akuvox` (`AkuvoxDevice.get_device_config()` → `DeviceConfig` with
`__contains__`/`get`, `AkuvoxDevice.set_device_config(dict[str, str])`),
`homeassistant.components.webhook`
**Storage**: None new. Webhook state stays in config entry data/options.
**Testing**: pytest + pytest-homeassistant-custom-component with
`fail_under = 100` line coverage, interrogate 100, ruff check/format, mypy,
reuse, markdownlint, gitlint, codespell, aislop (all via pre-commit)
**Target Platform**: Home Assistant custom integration
`custom_components/local_akuvox`
**Project Type**: Single-project Python custom component
**Performance Goals**: Reconciliation adds at most one `GET /api/config/get`
per entry load when webhooks are enabled and at most one
`POST /api/config/set` only when call URLs differ; it never blocks setup.
Flows add one config read per webhook push.
**Constraints**: Devices without the keys receive exactly today's payload;
never log unmasked webhook IDs/URLs; never log `remote` at info or above; never
fail setup because of detection or reconciliation; do not touch `Enable`,
`Method`, or base keys during reconciliation.
**Scale/Scope**: Two constants/templates, two event types, one payload field,
three helpers, three push-site updates, one setup hook, docs, release note,
tests. Closes #330.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| I. Code Quality (NON-NEGOTIABLE) | PASS | New helpers are typed, documented, and kept below C901 10 by splitting detection, payload building, and reconciliation. No new source files are required; any added file gets SPDX headers. |
| II. Test-Driven Development (NON-NEGOTIABLE) | PASS | Implementation writes failing tests first for templates/payload gating, detection fallbacks, handler `remote` dispatch and log redaction, each push site, and reconciliation branches. |
| III. User Experience Consistency | PASS | Reuses `local_akuvox_webhook_received` and the existing payload shape (additive `remote`). No new options; call events follow the existing webhook toggle. Docs describe gating and auto-upgrade. |
| IV. Performance Requirements | PASS | Reconciliation runs as a config-entry background task (non-blocking, cancelled on unload) and writes only when values differ. |
| V. Atomic Commits & Compliance (NON-NEGOTIABLE) | PASS | This stage is one docs-only commit. Implementation keeps code+tests, docs/release note, and tasks.md updates in separate commits. |
| VI. Phased Development | PASS | Phases: setup/foundation (constants, templates, payload builder), US1 handler, US2 push sites, US3 reconciliation, polish (docs, release note). Each ends with green tests. |

**Gate Result**: PASS. Phase 1 re-check: PASS — design adds no new
configuration surface, no new dependencies, and keeps failures non-fatal.

## Project Structure

### Documentation (this feature)

```text
specs/013-call-webhook-events/
├── spec.md                    # Merged Stage 1 source of truth
├── plan.md                    # This file
├── research.md                # Phase 0 decisions
├── data-model.md              # Phase 1 keys, payloads, event data
├── quickstart.md              # Phase 1 developer + hardware verification
└── contracts/
    ├── action-url-payload.md  # build_action_urls + detection helpers
    ├── webhook-call-events.md # handler dispatch contract
    └── reconciliation.md      # setup-time reconciliation contract
```

### Source Code (repository root)

```text
custom_components/local_akuvox/
├── const.py           # OPTIONAL_ACTIONURL_KEYS (MakeCall, HangUp);
│                      # call_made/call_ended in KNOWN_EVENT_TYPES only
├── webhook.py         # _URL_TEMPLATES entries; build_action_urls(optional_keys=);
│                      # supported_optional_action_url_keys(device_config);
│                      # async_detect_optional_action_url_keys(device);
│                      # async_reconcile_optional_action_urls(hass, entry,
│                      # device, webhook_id); handler adds payload.remote and
│                      # redacts remote in the missing-event warning
├── config_flow.py     # _async_push_webhook_config: detect on the same
│                      # session, then build/push
├── options_flow.py    # _async_handle_webhook_change: detect on the same
│                      # session, then build/push enable or disable payload
├── coordinator.py     # action_url_reconcile_task attribute (None default)
└── __init__.py        # async_setup_entry: schedule reconciliation after
                       # platform setup and store the task; async_unload_entry:
                       # cancel/await it before closing the device;
                       # async_remove_entry: detect before building the
                       # disable payload

tests/
├── test_webhook.py       # templates, payload gating, detection, handler,
│                         # reconciliation unit tests
├── test_config_flow.py   # push includes call keys only when supported;
│                         # read failure falls back to base payload
├── test_options_flow.py  # enable/disable payload gating and fallback
└── test_init.py          # setup schedules reconciliation (enabled only);
                          # unload cancels an in-flight task before closing
                          # the device;
                          # setup survives reconciliation errors; removal
                          # blanks call keys only when exposed

README.md, wiki/Webhook-Events.md   # call events, remote, gating, upgrade
releasenotes/notes/<slug>.yaml      # Reno feature note
```

**Structure Decision**: Keep all Action URL logic in `webhook.py`, which
already owns templates, payload generation, and imports the unsupported
capability helper. No new modules.

## Design Notes

1. **Two detection layers.** `supported_optional_action_url_keys()` is a pure
   function (presence check, tolerant of non-container inputs). The async
   wrapper `async_detect_optional_action_url_keys()` is used by flows and
   removal and swallows every exception (debug log) returning `frozenset()`.
   Reconciliation calls `get_device_config()` directly so it can route
   `AkuvoxUnsupportedError` to `async_report_unsupported_capability`.
2. **Push-site ordering.** Detection requires an entered device session, so
   `build_action_urls()` moves inside the existing `async with device:` blocks
   after `apply_capability_options()`. URL-generation errors keep their
   current outcome (config flow raises → `webhook_push_failed`; options flow
   returns `webhook_push_failed`; removal logs a warning).
3. **Reconciliation scheduling.** Scheduled with
   `entry.async_create_background_task(...)` after
   `async_forward_entry_setups()` succeeds, so a platform-setup failure (which
   closes the device) never races the task. Because HA cancels entry
   background tasks only after `async_unload_entry` returns (and that function
   closes the shared device), the task is stored on the coordinator
   (`action_url_reconcile_task`) and `async_unload_entry` cancels and awaits it
   via `asyncio.wait` before closing the device.
4. **Logging.** Reconciliation logs at debug for "nothing to do" and at info
   only the count/names of updated keys with the masked webhook ID; failures
   at warning without URLs. `remote` is never logged.

## Complexity Tracking

No constitution violations planned. If `async_reconcile_optional_action_urls`
approaches C901 10, split the diff computation into a pure helper.

<!-- markdownlint-enable MD013 -->
