<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Research: Capability Matrix Support

**Feature**: 011-capability-matrix-support **Date**: 2026-06-30
**Status**: Complete

## Verified upstream facts

The `pylocal-akuvox` v1.0.0 source tree under `src/pylocal_akuvox/` was used as
the load-bearing reference for this plan. Stage 5 should re-check these facts
against the upstream v1.0.0 tag or exact source checkout before implementation.

- `Capability` enum members are exactly: `USER_LIST`, `USER_ADD`,
  `USER_MODIFY`, `USER_DELETE`, `SCHEDULE_LIST`, `SCHEDULE_ADD`,
  `SCHEDULE_MODIFY`, `SCHEDULE_DELETE`, `GROUP_LIST`, `GROUP_ADD`,
  `GROUP_MODIFY`, `GROUP_DELETE`, `CONTACT_LIST`, `CONTACT_ADD`,
  `CONTACT_MODIFY`, `CONTACT_DELETE`, `RELAY_TRIGGER_API`,
  `RELAY_TRIGGER_FCGI`, `RELAY_STATUS`, `DEVICE_CONFIG_GET`,
  `DEVICE_CONFIG_SET`, `LOG_DOOR`, `LOG_CALL`, and `KEY_DISCOVERY`.
- `CapabilityStatus` values are `SUPPORTED`, `UNSUPPORTED`, and `UNKNOWN`.
  `DeviceCapabilities.status_of(capability)` returns `UNKNOWN` when a
  capability is absent from the mapping.
- `DeviceCapabilities.require(capability, allow_unknown=False)` raises
  `AkuvoxUnsupportedError` for `UNSUPPORTED` and disallowed `UNKNOWN` states.
  `allow_unknown=True` lets only `UNKNOWN` proceed; it never bypasses
  `UNSUPPORTED`.
- Unrecognized devices receive a conservative empty profile with a
  `device_not_in_matrix` note. `require()` reports
  `reason="device_unrecognized"` for gated methods on that profile.
- `AkuvoxUnsupportedError` exposes `.reason`, `.capability`, and
  `.device_class`. The reason taxonomy in source is
  `capability_missing`, `capability_unknown`, `device_unrecognized`,
  `adapter_missing`, `envelope_unsupported`, or `None`.
- `AkuvoxDevice.capabilities` is `DeviceCapabilities | None`; it is populated
  by `__aenter__` and cleared by `__aexit__`.
- `AkuvoxDevice.__aenter__()` now opens the HTTP session, calls
  `/api/system/info`, caches `DeviceInfo`, and looks up the capability profile.
  If entry fails, it closes the HTTP session and clears cached runtime state.
- `AkuvoxDevice.attempt_unknown_capability` defaults to `False` and is threaded
  to service-method gates as `allow_unknown`.
- `AkuvoxDevice.probe_capabilities(*, timeout: float | None = None)` returns a
  merged `DeviceCapabilities` profile. The underlying probe function runs a
  deterministic nine-call, read-only sequence with default per-request timeout
  `5.0` seconds.
- Relay trigger support is split into `RELAY_TRIGGER_API` and
  `RELAY_TRIGGER_FCGI`. Default dispatch prefers API before FCGI, and the FCGI
  adapter intentionally raises `AkuvoxUnsupportedError` because it requires
  separate Open Relay Via HTTP credentials.

## Decisions

### 1. Dependency upgrade locations

**Decision**: Raise every maintained dependency constraint to
`pylocal-akuvox>=1.0.0` in `manifest.json`, `pyproject.toml`, the mypy
`additional_dependencies` entry in `.pre-commit-config.yaml`, and refresh
`uv.lock`. Update the pyproject comments that currently reference 0.4.2 or older
mypy-published versions.

**Rationale**: The runtime package, development environment, and pre-commit mypy
environment must all type-check and execute against the v1.0.0 API surface.
Leaving the mypy hook on 0.3.0 would hide imports such as
`AkuvoxUnsupportedError`, `Capability`, `DeviceCapabilities`, and
`probe_capabilities` from the exact environment that gates commits.

**Alternatives considered**:

- Runtime-only bump — rejected because mypy and tests could still resolve an
  older library.
- Pin exactly `==1.0.0` — rejected because the project currently uses minimum
  compatible constraints and should accept future compatible bug fixes.

### 2. Context-entry error handling

**Decision**: Treat setup, config flow validation, config flow webhook push,
options flow webhook push, and removal-time webhook cleanup as context-entry
boundaries. Wrap the `await device.__aenter__()` call in `async_setup_entry` and
every `async with device:` with error handling that catches
`AkuvoxAuthenticationError`, `AkuvoxConnectionError`, `AkuvoxParseError`, and
other `AkuvoxError` failures from the new `/api/system/info` entry call.

- `async_setup_entry`: map authentication failures to `ConfigEntryAuthFailed`
  and connection, parse, device, or generic `AkuvoxError` failures to
  `ConfigEntryNotReady`/controlled setup failure without leaking an entered
  device.
- `_async_test_connection`: keep existing form outcomes, but recognize that the
  failure can now occur before the block body executes.
- `_async_push_webhook_config` and `_async_handle_webhook_change`: return the
  existing `webhook_push_failed` form error for entry-time failures as well as
  `set_device_config` failures.
- `async_remove_entry`: keep best-effort cleanup and warning logging, but log
  unsupported details when the disable push fails at entry or at
  `set_device_config`.

**Rationale**: v0.4.2 deferred many errors until the first method call. v1.0.0
surfaces them at context entry, so the entry line itself must be inside the same
user-facing error mapping that the integration already applies to first calls.

**Alternatives considered**:

- Let setup exceptions bubble — rejected because users would see failed setup
  traces rather than controlled Home Assistant setup states.
- Catch broad `Exception` only — rejected because auth failures need reauth and
  unsupported failures need structured `.reason`/`.capability` reporting.

### 3. Unknown-capability opt-in key and application point

**Decision**: Add `CONF_ATTEMPT_UNKNOWN_CAPABILITY = "attempt_unknown_capability"`
and `DEFAULT_ATTEMPT_UNKNOWN_CAPABILITY = False` in `const.py`. Store the value
in config entry data at setup and in entry options on later edits. Missing values
from existing entries resolve to `False`.

Add a setup flow `capabilities` step after connection validation and before the
webhook step so users can enable the opt-in before a webhook push calls the gated
`set_device_config` method. Add the same boolean field to the options flow form.
Apply the value after successful context entry and before any gated library
method by setting:

```python
device.attempt_unknown_capability = bool(value)
```

This application happens in shared helper logic used by `_create_device` callers
after entry, config-flow validation, config-flow webhook push, options-flow
webhook push, and setup.

**Rationale**: Upstream initializes the flag to `False`; the integration must not
set it before `__aenter__` because the spec requires applying stored options
after the capability profile is established. Showing the setup option before
webhook configuration lets unrecognized devices intentionally attempt
`DEVICE_CONFIG_SET` during setup.

**Alternatives considered**:

- Put the field on the first host step — rejected because users have not yet
  seen validation or device context.
- Store only in options — rejected because setup-time webhook pushes would have
  no way to opt in.
- Default to `True` for compatibility — rejected because it would bypass the
  safe v1.0.0 conservative default for unrecognized devices.

### 4. Unsupported capability surfacing

**Decision**: Use Home Assistant repairs issues via
`homeassistant.helpers.issue_registry` rather than persistent notifications. Add
shared helpers in `capability_support.py` to log and create/update a deduplicated
issue whenever `AkuvoxUnsupportedError` is caught. The issue id is scoped to the
config entry plus normalized reason/capability, for example
`unsupported_<entry_id>_<reason>_<capability>`, and uses translation keys in
`strings.json`/`translations/en.json`.

Create or update issues at these paths:

- coordinator relay status, device config, and user-cache fetches;
- lock `async_lock`, `async_unlock`, and all registered entity service methods;
- runtime webhook background user-cache refreshes that call `list_users`;
- config/options webhook config pushes and removal-time disable pushes;
- diagnostics probe if upstream raises unsupported from a probe-adjacent path.

For setup-flow failures before a `ConfigEntry` exists, scope the issue id to the
flow's known unique id when available, otherwise to the normalized host, and also
return a form error so the user is not sent hunting for a separate repair. Clear
flow-scoped issues when the entry is created successfully or the same flow path
later succeeds. Clear entry-scoped issues after a later successful operation for
the same capability/reason, when a coordinator capability snapshot shows the
capability is no longer unsupported, or when the config entry is permanently
removed. Do not clear confirmed `UNSUPPORTED` issues simply because the entity is
unavailable; those issues remain actionable until the profile or user
configuration changes.

**Rationale**: Repairs issues are the idiomatic Home Assistant surface for
integration-detected problems that need user action. They are deduplicated by
issue id, support translations, survive reloads appropriately, and avoid polling
spam. Persistent notifications are less structured and are better kept as a
fallback if the issue registry cannot represent a future condition.

**Alternatives considered**:

- Persistent notifications — rejected because they are less tied to repairs and
  harder to deduplicate by entry/capability.
- Log only — rejected because the spec requires user-visible guidance.
- Raise raw `AkuvoxUnsupportedError` — rejected because service calls and
  coordinator refreshes must fail in controlled Home Assistant terms.

### 5. Capability-driven coordinator data and entity availability

**Decision**: Extend `AkuvoxCoordinatorData` with a `capabilities` field carrying
the effective `DeviceCapabilities` snapshot from `device.capabilities` after
context entry. Lock entity setup and availability must read from coordinator data
rather than directly from `device.capabilities`.

Relay rules:

| Capability state | Entity behavior |
| ---------------- | --------------- |
| `RELAY_STATUS=UNSUPPORTED` | Do not create usable relay locks from status data; surface a repairs issue and keep refresh controlled. |
| `RELAY_STATUS=UNKNOWN`, opt-in off | Treat relay state as unavailable and surface guidance instead of polling blindly. |
| `RELAY_STATUS=UNKNOWN`, opt-in on | Allow relay status fetch and expose entities if the call succeeds. |
| `RELAY_TRIGGER_API=SUPPORTED` | Keep lock/unlock actions available through the existing API relay path. |
| `RELAY_TRIGGER_API=UNKNOWN`, opt-in off | Mark actions unavailable and surface opt-in guidance. |
| `RELAY_TRIGGER_API=UNKNOWN`, opt-in on | Keep actions available by passing `adapter=Capability.RELAY_TRIGGER_API` so the legacy API endpoint is intentionally attempted. |
| `RELAY_TRIGGER_API=UNSUPPORTED` | Mark actions unavailable even if `RELAY_TRIGGER_FCGI` is supported, because the current lock entity has no Open Relay Via HTTP credentials and the upstream FCGI adapter raises by design. |
| Both trigger variants unsupported | Mark lock entities unavailable for actions because no trigger variant can unlock/lock. |

**Rationale**: The coordinator already centralizes device state for platforms.
Keeping a snapshot there makes entity decisions deterministic and testable. The
relay split must use the two upstream variants instead of inventing a generic
relay-trigger capability. The current lock entity can only use the API trigger
variant; FCGI support is diagnostic evidence until a credentialed Open Relay Via
HTTP action is explicitly designed.

**Alternatives considered**:

- Let every entity call `device.capabilities` directly — rejected because the
  snapshot lifecycle is coupled to context entry and coordinator refreshes.
- Create entities for confirmed unsupported relays and rely on service failures —
  rejected because the spec requires hiding, disabling, or marking unavailable
  unsupported capabilities before doomed calls where possible.

### 6. Service-call capability mapping

**Decision**: Precheck known unsupported capabilities where the mapping is
unambiguous, then still catch `AkuvoxUnsupportedError` from upstream as the
source of truth. The mapping is:

| Integration path | Required and prerequisite upstream capabilities |
| ---------------- | -------------------------------------------- |
| `list_schedules` | `SCHEDULE_LIST` |
| `add_schedule` | `SCHEDULE_ADD` |
| `modify_schedule` | `SCHEDULE_LIST` then `SCHEDULE_MODIFY` |
| `delete_schedule` | `SCHEDULE_LIST`, then `SCHEDULE_DELETE`, then best-effort `USER_LIST` orphan check |
| `list_users` | `USER_LIST` |
| `add_user` | `SCHEDULE_LIST` for schedule validation, then `USER_ADD` |
| `modify_user` | `USER_LIST`, optional `SCHEDULE_LIST`, then `USER_MODIFY` |
| `delete_user` | `USER_LIST`, then `USER_DELETE` |
| `add_user_schedule_relay` | `USER_LIST`, `SCHEDULE_LIST`, then `USER_MODIFY` |
| `remove_user_schedule_relay` | `USER_LIST`, `SCHEDULE_LIST`, then `USER_MODIFY` |
| `list_contacts` | `CONTACT_LIST` |
| `add_contact` | `CONTACT_ADD` |
| `modify_contact` | `CONTACT_MODIFY` |
| `delete_contact` | `CONTACT_DELETE` |
| `list_groups` | `GROUP_LIST` |
| `add_group` | `GROUP_ADD` |
| `modify_group` | `GROUP_MODIFY` |
| `delete_group` | Best-effort `GROUP_LIST`, then `GROUP_DELETE`, then best-effort `CONTACT_LIST` orphan check |
| webhook PIN user-cache refresh | Best-effort `USER_LIST` background refresh |
| `get_relay_status` | `RELAY_STATUS` |
| `trigger_relay` | `RELAY_TRIGGER_API` for current lock actions; `RELAY_TRIGGER_FCGI` is not actionable without separate Open Relay Via HTTP credentials |
| `get_device_config` | `DEVICE_CONFIG_GET` |
| `set_device_config` | `DEVICE_CONFIG_SET` |
| future door/call log services | `LOG_DOOR` / `LOG_CALL` |

**Rationale**: Prechecks produce faster controlled Home Assistant errors, but
upstream remains authoritative because relay adapter selection and envelope
classification can still raise structured unsupported errors.

**Alternatives considered**:

- No prechecks — acceptable for safety, but rejected because it leaves more work
  to upstream and makes entity availability harder to test.
- A single generic relay trigger capability — rejected because v1.0.0 explicitly
  exposes `RELAY_TRIGGER_API` and `RELAY_TRIGGER_FCGI` as separate members.

### 7. Probe trigger strategy

**Decision**: Do not run `device.probe_capabilities()` on first connect. Expose
probing through the Home Assistant diagnostics surface by adding `diagnostics.py`.
When a user downloads diagnostics, include the current capability snapshot and,
where safe, run `device.probe_capabilities(timeout=5.0)` to include the merged
probe result. Probe failures are reported in diagnostics and logs without
breaking setup or normal refresh.

**Rationale**: The upstream probe is read-only but performs nine requests. Running
it automatically during setup would surprise users, lengthen every connect, and
increase the failure surface. Diagnostics download is user-initiated and aligns
with the support workflow of collecting non-sensitive evidence for upstream
matrix updates.

**Alternatives considered**:

- Automatic first-connect probe — rejected due to latency and unexpected network
  traffic.
- A new normal service for probing — deferred unless diagnostics cannot express
  the workflow cleanly; services are more visible to automations and could invite
  accidental repeated probes.

### 8. Diagnostics and logging surface

**Decision**: Add Home Assistant diagnostics output with non-sensitive capability
statuses, profile notes, device class/firmware, and recent unsupported reason
summaries. Redact credentials, PINs, card codes, raw webhook ids, and any note
body that could contain user data. Keep structured logs for every
`AkuvoxUnsupportedError` with `.reason`, `.capability`, entry title/id, and
context path.

**Rationale**: Diagnostics give maintainers the capability evidence needed to add
matrix entries while structured logs help users and developers understand why a
specific call was blocked.

**Alternatives considered**:

- Logs only — rejected because logs are less convenient for upstream support.
- Dump raw upstream notes — rejected because probe notes may include response
  bodies and must be sanitized.

### 9. Breaking-change release notes

**Decision**: The implementation PR must be marked as a breaking change for
release-drafter (either a conventional `!` implementation commit/PR title or a
`breaking-change` label) and include release text covering the v1.0.0 upgrade,
default unrecognized-device failure mode, opt-in mitigation, capability-driven
unavailability, and the extra `/api/system/info` context-entry request.

**Rationale**: The repository release-drafter has a dedicated
`breaking-change` category and major-version resolver. This feature changes
runtime behavior for uncurated devices, so release notes must not be hidden under
normal documentation or maintenance categories.

**Alternatives considered**:

- Mention the break only in README/docs — rejected because users often discover
  upgrades through GitHub/HACS release notes.

## Summary of Decisions

| Item | Decision |
| ---- | -------- |
| Repairs surface | Home Assistant repairs issue registry, not persistent notifications |
| Config key | `CONF_ATTEMPT_UNKNOWN_CAPABILITY = "attempt_unknown_capability"` |
| Default | `DEFAULT_ATTEMPT_UNKNOWN_CAPABILITY = False` |
| Setup flow | New capability opt-in step before webhook setup |
| Option application | Set `device.attempt_unknown_capability` after successful context entry |
| Capability source | `device.capabilities` copied into `AkuvoxCoordinatorData.capabilities` |
| Relay trigger capabilities | Use `RELAY_TRIGGER_API` and `RELAY_TRIGGER_FCGI` separately |
| Probe trigger | User-triggered diagnostics download, not first connect |
| Diagnostics surface | Home Assistant diagnostics platform plus structured logs |
| Release notes | Mark implementation as breaking change in release-drafter metadata |

<!-- markdownlint-enable MD013 -->
