<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Research: Call Webhook Events

**Feature**: 013-call-webhook-events **Date**: 2026-11-27
**Status**: Complete

## Verified facts

### Akuvox Action URL documentation

Source: <https://knowledge.akuvox.com/docs/set-up-action-url>

- **Make Call**: triggered when the device makes an outgoing call. `$remote`
  is replaced with the called IP or SIP number.
- **Hang Up**: triggered when the device hangs up a call. `$remote` is the
  number in that call. The documentation does not restrict Hang Up to
  outgoing calls.
- Supported events and variables vary by model and firmware.

### Device evidence

| Model | Firmware | `MakeCall` key | `HangUp` key | Source |
| ----- | -------- | -------------- | ------------ | ------ |
| E18 | 18.30.10.118 | present (empty) | present (empty) | Owner's device, read-only `GET /api/config/get` |
| X916 | 916.30.10.114 | present | present | Prior capability evidence |
| A08S | 108.30.10.144 | present | present | Prior capability evidence |
| R20K | 220.30.4.108 | unverified | unverified | Reporter (#330); datasheet confirms SIP two-way audio |

`specs/004-webhook-endpoint/research.md` already lists `MakeCall` (outgoing
call) and `HangUp` (call hang-up) as SIP-related Action URL keys. Key presence
proves the device accepts the configuration; it does **not** prove the event
fires, that `$remote` is substituted, or that read-back equals the written
value. These are left to owner hardware verification (see quickstart).

### Existing code facts

- `webhook.build_action_urls()` iterates `const.ACTIONURL_KEYS` (ten keys) and
  `_URL_TEMPLATES`, producing `(enable_payload, disable_payload)` with
  `Enable`/`Method` plus all keys. It logs an HTTPS warning when
  `warn_http=True` and the URL is HTTP.
- Push sites: `config_flow._async_push_webhook_config` (enable only),
  `options_flow._async_handle_webhook_change` (only when enabled state
  changes), `__init__.async_remove_entry` (disable on deletion). All open a
  fresh `AkuvoxDevice` session except removal, which also creates one via
  `_create_device`.
- The options flow pushes only on enabled-state changes, so existing
  webhook-enabled devices never receive new keys without a load-time path.
- `pylocal_akuvox.DeviceConfig` wraps `dict[str, str]` and supports `in`,
  `get`, and `keys()`. `AkuvoxDevice.get_device_config()` requires
  `Capability.DEVICE_CONFIG_GET` and may raise `AkuvoxUnsupportedError`.
- The coordinator already calls `get_device_config()` during refresh (guarded
  by `getattr(..., callable)`) but does not retain the raw config.
- The webhook handler builds the known-event payload explicitly
  (`event`, `status`, `device_user_id`, `user_id`, `username`); only unknown
  events pass through `sanitize_payload`. The missing-`event` branch logs
  sanitized query parameters at WARNING, and `remote` is not a sensitive key
  pattern, so it would be logged unless redacted.
- `async_report_unsupported_capability` deduplicates repairs issues by entry,
  reason, and capability, so a second report of `DEVICE_CONFIG_GET` from
  reconciliation reuses the coordinator's issue.
- `ConfigEntry.async_create_background_task(hass, coro, name)` ties a task to
  the entry lifecycle (cancelled on unload); `hass.async_block_till_done()`
  waits for it only with `wait_background_tasks=True`.
- Coverage is enforced at 100% (`[tool.coverage.report] fail_under = 100`).

## Decisions

### D1: Separate optional keys from base keys

**Decision**: Add `OPTIONAL_ACTIONURL_KEYS = {"MakeCall": ..., "HangUp": ...}`
in `const.py`; keep `ACTIONURL_KEYS` unchanged.
**Rationale**: Base payload stays byte-identical for unsupported devices and
for every existing caller that passes no optional keys.
**Alternatives**: A single dict with a "required" flag — more invasive for
existing iteration and tests.

### D2: Presence-based capability detection

**Decision**: A key is supported iff it is a member of the `DeviceConfig`.
Values (often empty) are ignored.
**Rationale**: Matches observed E18/X916/A08S behavior and Akuvox's
"varies by model" guidance without relying on the capability matrix, which
has no Action URL granularity.
**Alternatives**: Model allowlist — brittle and would exclude the R20K until
evidence exists.

### D3: Fallback to base payload on detection failure

**Decision**: Flow/removal detection swallows all exceptions and returns no
optional keys, logging at debug.
**Rationale**: A missing optional event is strictly better than failing setup
or options for a feature the user did not explicitly request.

### D4: Reconciliation at load, call keys only, write-on-difference

**Decision**: Background task after platform setup compares the exposed call
keys' current values to expected URLs and writes only differing keys.
**Rationale**: Owner chose automatic upgrade; diff-only writes avoid flash
wear and noise on every restart; leaving base keys alone preserves today's
behavior.
**Alternatives**: Options-flow "re-push" button (requires user action);
reconcile all keys (scope creep, risks overwriting user customizations).

### D5: `remote` in event data, not logs

**Decision**: Add `payload.remote` to every known event (null when absent);
redact `remote` from the missing-`event` warning.
**Rationale**: SIP/IP numbers are useful automation data but are personal
data that should not land in logs at warning level.

### D6: No coordinator refresh for call events

**Decision**: `call_made`/`call_ended` are not in `REFRESH_EVENT_TYPES`.
**Rationale**: Calls do not change relay or user state.

## Open items (hardware, owner-verified before release)

1. `MakeCall` fires on an outgoing call on the R20K and other models.
2. `HangUp` fires on hang-up (outgoing and possibly incoming).
3. `$remote` substitutes to the called number.
4. `GET /api/config/get` returns the exact string written, so reconciliation
   is idempotent across restarts.

<!-- markdownlint-enable MD013 -->
