<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Feature Specification: Call Webhook Events

**Feature Branch**: `013-call-webhook-events`
**Created**: 2026-11-27
**Status**: Draft
**Input**: User description: "GitHub issue #330 asks for a Home Assistant
event when an Akuvox R20K makes a call. Add `MakeCall` and `HangUp` Action URL
events (`call_made`, `call_ended`) carrying the `$remote` number, configure them
only on devices whose configuration exposes those keys, and upgrade existing
webhook-enabled devices automatically when the integration loads."

This additive feature extends the existing webhook endpoint (feature 004). The
integration already configures ten relay, input, and code Action URL keys on
the device and fires `local_akuvox_webhook_received` for each request. This
feature adds two optional, capability-gated call keys without changing the
payload sent to devices that do not expose them.

## Background

Akuvox documents two call-related Action URL events
(<https://knowledge.akuvox.com/docs/set-up-action-url>):

- **Make Call** (`Config.Features.ACTIONURL.MakeCall`): the device makes an
  outgoing call. `$remote` is the called IP or SIP number.
- **Hang Up** (`Config.Features.ACTIONURL.HangUp`): the device hangs up a call.
  `$remote` is the number in that call. Akuvox does not limit this to outgoing
  calls, so `call_ended` may also fire for incoming calls and is not guaranteed
  to follow a `call_made` event.

Observed evidence: E18 (firmware 18.30.10.118), X916 (916.30.10.114), and A08S
(108.30.10.144) all expose both keys in `/api/config/get`. The R20K datasheet
confirms SIP two-way audio, but the reporter's R20K (firmware 220.30.4.108) has
not been inspected. Key presence does not prove the events fire; the owner will
verify on hardware before release. Akuvox states supported events vary by model,
which is why this feature gates the keys on observed device configuration.

## Clarifications

### Session 2026-11-27

- Q: Which call events are in scope? → A: `MakeCall` → `call_made` and
  `HangUp` → `call_ended`. No incoming-call or answer events.
- Q: Should devices without the keys receive them anyway? → A: No. Devices
  whose configuration lacks a key MUST receive exactly today's payload.
- Q: How do already-configured devices gain the new keys? → A: Automatically
  when the config entry loads, writing only when the stored values differ from
  the expected URLs.
- Q: Is `remote` sensitive? → A: It is a SIP/IP number, not a secret like a PIN.
  It MAY appear in event data, but MUST NOT be logged at info level or above.
- Q: Should the detection helper report unsupported capabilities? → A: No.
  Flow and removal detection silently fall back to the base payload.
  Reconciliation reads the configuration itself so it can report
  `AkuvoxUnsupportedError` through the existing (deduplicated) repairs helper.
- Q: Should call events refresh the coordinator? → A: No. Calls do not change
  relay or user state.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receive Call Events (Priority: P1)

As a Home Assistant user with a webhook-enabled Akuvox intercom, I can trigger
automations when the device places an outgoing call or hangs up, and I can see
which number was called.

**Why this priority**: This is the request in issue #330 and the core value of
the feature.

**Independent Test**: Send `GET /api/webhook/<id>?event=call_made&remote=1001`
to a registered webhook and assert that `local_akuvox_webhook_received` fires
with `event_type: call_made` and `payload.remote: "1001"`.

**Acceptance Scenarios**:

1. **Given** a registered webhook, **When** the device requests
   `?event=call_made&remote=<number>`, **Then** Home Assistant fires
   `local_akuvox_webhook_received` with `event_type` `call_made` and
   `payload.remote` equal to the number.
1. **Given** a registered webhook, **When** the device requests
   `?event=call_ended&remote=<number>`, **Then** the event fires with
   `event_type` `call_ended` and `payload.remote` equal to the number.
1. **Given** a call event, **When** it is handled, **Then** no coordinator
   refresh is scheduled and no user lookup is attempted.
1. **Given** a call event without a `remote` parameter, **When** it is handled,
   **Then** the event still fires with `payload.remote` set to `null`.

______________________________________________________________________

### User Story 2 - Capability-Gated Configuration (Priority: P1)

As a user enabling webhooks during setup or in options, I want call Action URLs
configured only when my device supports them, so that devices without those
keys keep working exactly as before.

**Why this priority**: Writing unknown keys to unsupported models risks
breaking existing webhook configuration, which is worse than missing the new
events.

**Independent Test**: Mock `get_device_config()` with and without the call keys
and assert the payload passed to `set_device_config()` includes the call keys
only when they are present.

**Acceptance Scenarios**:

1. **Given** a device whose configuration contains both call keys, **When**
   webhooks are enabled in the config flow or options flow, **Then** the pushed
   enable payload contains the ten existing keys plus both call keys.
1. **Given** a device whose configuration contains only one call key, **When**
   webhooks are enabled, **Then** only that call key is added.
1. **Given** a device whose configuration lacks the call keys, **When**
   webhooks are enabled, **Then** the pushed payload is identical to the
   pre-feature payload.
1. **Given** reading the device configuration fails or is unsupported, **When**
   webhooks are enabled, **Then** the base payload is pushed, the failure is
   logged at debug or warning level, and setup does not fail because of the
   read.
1. **Given** webhooks are disabled in options or the entry is removed, **When**
   the disable payload is pushed, **Then** call keys are blanked only if the
   device configuration exposes them.

______________________________________________________________________

### User Story 3 - Automatic Upgrade of Existing Devices (Priority: P2)

As an existing user who enabled webhooks before this feature, I want my device
to start sending call events after upgrading the integration, without having to
disable and re-enable webhooks.

**Why this priority**: Existing users would otherwise never receive the new
events, because the options flow only pushes configuration when the enabled
state changes.

**Independent Test**: Set up a webhook-enabled entry with a mocked device whose
call keys are empty, and assert that after setup a background task calls
`set_device_config()` with only the call keys. Repeat with matching values and
assert no write occurs.

**Acceptance Scenarios**:

1. **Given** a webhook-enabled entry and a device exposing call keys with
   values that differ from the expected URLs, **When** the entry loads, **Then**
   the integration writes only the differing call keys.
1. **Given** the device's call keys already hold the expected URLs, **When**
   the entry loads, **Then** no configuration write occurs.
1. **Given** the device lacks the call keys, **When** the entry loads, **Then**
   no configuration write occurs.
1. **Given** webhooks are disabled or no webhook ID exists, **When** the entry
   loads, **Then** no reconciliation read or write occurs.
1. **Given** the configuration read, URL generation, or write fails (including
   `AkuvoxUnsupportedError`), **When** the entry loads, **Then** the error is
   logged (and unsupported capabilities are reported through the existing
   repairs helper), and entry setup still succeeds.

### Edge Cases

- A device exposes `MakeCall` but not `HangUp` (or vice versa): only the
  exposed key is configured, reconciled, or blanked.
- `remote` is very long: for known events it is passed through as-is, exactly
  like `status` today; for unknown events the existing sanitizer truncates it
  at 1024 characters.
- An unknown event arrives with a `remote` parameter: it is preserved in the
  fired event's sanitized payload because `remote` does not match a sensitive
  key pattern.
- A request without an `event` parameter includes `remote`: the existing
  warning log of sanitized parameters MUST redact `remote` (FR-005).
- The device normalizes or escapes stored Action URL values so read-back does
  not equal the written string: reconciliation would rewrite on every load.
  Exact read-back equality is part of the owner's hardware verification.
- The device's Action URL `Enable` flag is off: reconciliation still updates
  only call keys and never changes `Enable` or `Method`.
- The Home Assistant external/internal URL changes: reconciliation rewrites
  only the call keys; relay, input, and code keys keep today's behavior
  (re-enable webhooks to refresh them).
- The coordinator's first refresh fails: setup fails as today and no
  reconciliation is scheduled.
- The entry unloads while reconciliation is running: the background task is
  tied to the entry lifecycle and is cancelled with it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The integration MUST define optional Action URL keys
  `Config.Features.ACTIONURL.MakeCall` and `Config.Features.ACTIONURL.HangUp`
  separately from the ten base keys.
- **FR-002**: The URL template for `MakeCall` MUST be
  `?event=call_made&remote=$remote` and for `HangUp` MUST be
  `?event=call_ended&remote=$remote`.
- **FR-003**: `call_made` and `call_ended` MUST be added to the known event
  types and MUST NOT be added to the refresh event types.
- **FR-004**: The fired event payload for known events MUST include a `remote`
  field populated from the `remote` query parameter (or `null` when absent).
  Existing payload fields MUST remain unchanged.
- **FR-005**: The `remote` value MUST NOT be logged at info level or above.
  Existing log lines that include sanitized query parameters (the missing
  `event` warning) MUST redact `remote`; the fired event data is not a log and
  keeps it.
- **FR-006**: Building action URLs MUST accept an optional set of supported
  optional keys. With no supported optional keys the enable and disable
  payloads MUST be identical to the pre-feature payloads.
- **FR-007**: The integration MUST provide a helper that determines which
  optional Action URL keys a device supports by checking for their presence in
  the device configuration returned by `get_device_config()`. A key is
  supported only if it is present; its value is irrelevant.
- **FR-008**: Detection used by the config flow, options flow, and entry
  removal MUST be defensive: if `get_device_config` is missing,
  raises any exception (including `AkuvoxUnsupportedError`), or returns an
  unexpected object, detection MUST return no supported optional keys and log
  at debug or warning level.
- **FR-009**: The config flow webhook push MUST detect supported optional keys
  on the same device session before pushing the enable payload.
- **FR-010**: The options flow MUST detect supported optional keys before
  pushing an enable or disable payload when the webhook state changes.
- **FR-011**: Entry removal MUST detect supported optional keys before pushing
  the disable payload, so only exposed call keys are blanked.
- **FR-012**: When an entry loads with webhooks enabled and a webhook ID, after
  the coordinator's first refresh and platform setup both succeed, the
  integration MUST schedule a background reconciliation task bound to the
  config entry (so it is cancelled on unload).
- **FR-013**: Reconciliation MUST read the device configuration, compute the
  expected URL for each exposed optional key, and call `set_device_config()`
  with only the keys whose current values differ. It MUST NOT write when no
  key differs or when no optional key is exposed. Comparison is exact string
  equality. URL generation for reconciliation MUST NOT emit the HTTP warning
  (`warn_http=False`).
- **FR-014**: Reconciliation MUST NOT modify the base keys, `Enable`, or
  `Method`.
- **FR-015**: Reconciliation MUST NOT block or fail entry setup. All exceptions
  MUST be caught and logged; `AkuvoxUnsupportedError` from the read or write
  MUST be reported through `async_report_unsupported_capability`. To make this
  possible, reconciliation reads the configuration directly rather than through
  the FR-008 fallback helper, and reuses the pure presence check from FR-007.
- **FR-016**: Logs MUST NOT contain unmasked webhook IDs or webhook URLs; use
  `mask_webhook_id` when referencing the webhook.
- **FR-017**: User documentation (README and wiki webhook events page) MUST
  describe `call_made`, `call_ended` (noting it may also fire for incoming
  calls), the `remote` payload field, the capability gating, and the automatic
  upgrade on load.
- **FR-018**: The implementation MUST include a Reno release note under
  `releasenotes/notes/` describing the new events, capability gating, and
  automatic upgrade behavior.
- **FR-019**: Tests MUST cover payload gating, detection fallback, event
  dispatch with `remote`, `remote` redaction in the missing-event warning,
  options/config flow/removal integration, and
  reconciliation (differs, matches, missing keys, errors, webhook disabled).

### Key Entities

- **Optional Action URL Key**: A call-related device configuration key that is
  configured only when present in the device configuration. Maps a logical name
  (`MakeCall`, `HangUp`) to a config key and URL template.
- **Supported Optional Keys**: The set of logical optional key names detected
  for a device at push or reconciliation time.
- **Call Event**: A `local_akuvox_webhook_received` event with `event_type`
  `call_made` or `call_ended` and `payload.remote`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a device exposing both call keys, enabling webhooks pushes
  twelve Action URL keys plus `Enable` and `Method`.
- **SC-002**: On a device exposing no call keys, the pushed payload is
  byte-for-byte identical to the pre-feature payload.
- **SC-003**: A webhook-enabled entry whose device already has correct call
  URLs performs zero configuration writes on restart.
- **SC-004**: Reconciliation failures never prevent an entry from reaching the
  loaded state.
- **SC-005**: The implementation completes with the full test suite green,
  coverage not reduced, interrogate at 100, and ruff, mypy, and pre-commit
  clean.

## Assumptions & Out of Scope

- Hardware firing of `MakeCall`/`HangUp`, `$remote` substitution, and exact
  read-back of written Action URL values are not verified by this feature; the
  owner will test before release.
- Incoming call, answer, and call-log events are out of scope.
- No new configuration option is added; call events follow the existing
  webhook enable toggle.
- Reconciliation of base relay/input/code keys on load is out of scope.
