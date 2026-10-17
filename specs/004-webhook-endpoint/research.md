<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Research: Webhook Endpoint

**Feature**: 004-webhook-endpoint
**Date**: 2026-03-02

## Akuvox Action URL System

### Overview

Akuvox devices support an Action URL feature that sends HTTP requests
to configured URLs when specific events occur on the device. The
configuration is stored in the device's config tree under
`Config.Features.ACTIONURL.*` keys.

### Enable Flag

- **Config.Features.ACTIONURL.Enable**: Must be set to `'1'` to
  activate the Action URL system. Setting to `'0'` disables all
  action URLs.
- **Config.Features.ACTIONURL.Method**: HTTP method for requests
  (observed empty on live device, implying default GET).

### Supported Action URL Keys

Observed from a live device at `<device-ip>`:

| Config Key (suffix after `ACTIONURL.`) | Variable | Event |
| -------------------------------------- | -------- | ----- |
| `RelayATriggered` | `$relay1status` | Relay A open |
| `RelayAClosed` | `$relay1status` | Relay A close |
| `RelayBTriggered` | `$relay2status` | Relay B open |
| `RelayBClosed` | `$relay2status` | Relay B close |
| `InputATriggered` | `$relay1status` | Input A trig |
| `InputAClosed` | `$relay1status` | Input A close |
| `InputBTriggered` | `$relay2status` | Input B trig |
| `InputBClosed` | `$relay2status` | Input B close |
| `ValidCodeEntered` | `$code` | Valid code |
| `InvalidCodeEntered` | (none — omitted by design) | Invalid code \* |

\* While a `$code` variable exists on the device, it is
deliberately omitted from the `InvalidCodeEntered` URL template
by design; see Resolved Clarifications #3.

All keys are prefixed with `Config.Features.ACTIONURL.`.

These 10 keys are the core Action URLs present on all PIN-controlled
Akuvox devices, which is the target audience for this integration.

Additional keys observed on some models (not in scope for this
feature but recognized for future extension via the generic event
path):

| Key suffix (after `ACTIONURL.`) | Description | Models |
| ------------------------------- | ----------- | ------ |
| `InputCTriggered` | Input C trig | 3+ relay |
| `InputCClosed` | Input C close | 3+ relay |
| `ValidCardEntered` | Valid card | Card reader |
| `InvalidCardEntered` | Invalid card | Card reader |
| `ValidFaceRecognition` | Valid face | Face recog |
| `InvalidFaceRecognition` | Invalid face | Face recog |
| `AlarmLog` | Alarm log | Alarm |
| `AlarmTriggered` | Alarm trig | Alarm |
| `CallLog` | Call log | SIP |
| `Card` | Card event | Card reader |
| `DoorLog` | Door log | Varies |
| `HangUp` | Call hang-up | SIP |
| `InputAlarm` | Input alarm | Alarm |
| `InputBreakIn` | Break-in | Alarm |
| `MakeCall` | Outgoing call | SIP |

All keys prefixed with `Config.Features.ACTIONURL.`.

### Variable Substitution

The device substitutes variables in the URL before sending:

- `$relay1status` — Relay A / Input A electrical state (0=low, 1=high).
  Interpretation depends on relay type: for normally-open (NO) relays,
  0=open and 1=closed; for normally-closed (NC) relays,
  0=closed and 1=open. Here, "open"/"closed" describe the
  relay contact position (electrical circuit state), not
  the physical door state: following the lock entity's
  `_parse_int_state()` / `_parse_relay_state()` logic,
  NO maps 0→locked, 1→unlocked and NC maps 0→unlocked,
  1→locked.
- `$relay2status` — Relay B / Input B electrical state (same semantics)
- `$relay3status` — Relay C / Input C electrical state (3-relay models)
- `$code` — PIN or access code entered
- `$mac`, `$ip`, `$model`, `$firmware` — Device identifiers
- `$card_sn` — Card serial number (card events)

### URL Pattern (Observed)

The live device has URLs configured as:

```text
https://homeassistant.example.local/api/webhook/intercom?relaya_triggered=$relay1status
```

This confirms:

- Device sends HTTP GET with query parameters
- Variable substitution happens in query string values
- All action URLs can reuse the same base webhook endpoint and differ
  only in query parameters. Note: the observed device uses parameter
  names that embed the event type (e.g., `relaya_triggered=<status>`),
  whereas the integration's proposed design uses a cleaner
  `event=<name>&status=<value>` scheme for easier parsing.

### Device Configuration API

The `pylocal-akuvox` library provides:

```python
# Read current config
config = await device.get_device_config()  # → DeviceConfig
value = config.get("Config.Features.ACTIONURL.Enable")

# Write config
await device.set_device_config(
    {
        "Config.Features.ACTIONURL.Enable": "1",
        "Config.Features.ACTIONURL.RelayATriggered": "http://ha:8123/api/webhook/{id}?event=relay_a_triggered"
        "&status=$relay1status",
    }
)
```

- `get_device_config()` calls `/api/config/get`
- `set_device_config(dict[str, str])` calls `/api/config/set`
- All config values are strings
- Multiple keys can be set in a single call

## Home Assistant Webhook Infrastructure

### Registration API

```python
from homeassistant.components.webhook import (
    async_register,
    async_unregister,
    async_generate_url,
)

# Register
async_register(
    hass,
    domain="akuvox",  # Integration domain
    name="Akuvox {device}",  # Human-readable name
    webhook_id=webhook_id,  # Unique random ID
    handler=async_handle_webhook,  # Async callback
    allowed_methods=["GET"],  # Akuvox sends GET requests
    # local_only intentionally omitted — see webhook-handler
    # contract for rationale (NAT/VPN/proxy compatibility)
)

# Generate URL for external access
url = async_generate_url(hass, webhook_id)
# → "http://homeassistant.local:8123/api/webhook/{webhook_id}"

# Unregister
async_unregister(hass, webhook_id)
```

### Handler Signature

```python
async def async_handle_webhook(
    hass: HomeAssistant,
    webhook_id: str,
    request: aiohttp.web.Request,
) -> aiohttp.web.Response | None:
    """Handle incoming webhook."""
```

The handler receives the raw `aiohttp.web.Request` and can return
an optional response. For Action URLs the device sends GET requests
with query parameters.

### Webhook ID Generation

Home Assistant convention uses `secrets.token_hex(32)` for 256-bit
random webhook IDs (64 hex characters). The spec requires at least
128 bits of entropy (FR-003). Using `secrets.token_hex(32)` exceeds
this requirement.

### Lifecycle

- Register in `async_setup_entry()` when `webhook_enabled=True`
  (covers initial setup, reload after options change, and restart)
- Unregister in `async_unload_entry()` (reload/remove)

## Valid Code as Primary Relay Change Signal

When a valid code is entered on the device, one or more relays may
be triggered. However, based on observed device behavior, the
relay-specific action URLs (`RelayATriggered`, `RelayAClosed`, etc.)
may NOT fire when the relay change was initiated by a valid code
entry. The `ValidCodeEntered` action URL *always* fires reliably.

Therefore, `valid_code_entered` is the primary and most reliable
signal that relay state has changed due to code entry. The
integration MUST trigger an immediate coordinator refresh on
`valid_code_entered` to capture all relay state changes. Relay
action URL events remain useful for relay changes initiated by
other means (e.g., SIP call open, web relay trigger, physical
button) and should still trigger a refresh when received.

## Interaction with Speculative Lock States

The integration currently uses an optimistic (speculative) lock state
pattern in the lock entity. When `async_unlock()` is called, the
entity immediately sets `_optimistic_locked = False` and writes that
state to HA, then schedules a delayed coordinator refresh after the
hold delay expires. The `_optimistic_locked` value takes priority
over coordinator data in `is_locked`.

**The speculative state mechanism MUST remain unchanged regardless
of whether webhooks are enabled.** It is the primary state feedback
path and the only one available when webhooks are not configured.
Webhook relay events provide an *additional*, faster path to clear
speculative state — they do not replace the existing delayed refresh.

When webhooks ARE enabled:

- **Relay triggered event** (e.g., `relay_a_triggered` with
  `status=1`): Confirms the relay actually opened. The webhook
  handler schedules `coordinator.async_refresh()` as a background
  task (not awaited inline) so the HTTP response returns
  immediately. The refresh fetches real device state into the
  coordinator. This does **not** itself clear
  `_optimistic_locked`; the optimistic override is only cleared
  when the separately-scheduled delayed timer fires
  `_async_finish_optimistic_unlock()`. The webhook refresh
  ensures the coordinator has current data when that happens.
- **Relay closed event** (e.g., `relay_a_closed` with `status=0`):
  Confirms the relay returned to its resting state. The
  coordinator refresh fetches current data, but the optimistic
  override is still cleared via the delayed timer path.
- **Valid code event**: Triggers immediate coordinator refresh.
  Since a valid code may unlock one or more relays, the refresh
  ensures the coordinator has current state for all relays. The
  optimistic override for each lock is still cleared by its own
  delayed timer's `_async_finish_optimistic_unlock()` call.

When webhooks are NOT enabled:

- The existing behavior is completely unchanged: speculative state
  is set on unlock, held until the delayed refresh fires after the
  hold delay, then cleared via `_async_finish_optimistic_unlock()`.

In both cases, the delayed refresh scheduled by `async_unlock()`
remains active as a safety net. If the webhook-triggered refresh
arrives first, the delayed refresh still runs
`_async_finish_optimistic_unlock()` to clear the optimistic
override, but typically finds the device state already current.

## Resolved Clarifications

1. **Action URL enable flag**: `Config.Features.ACTIONURL.Enable`
   must be set to `'1'` when webhooks are enabled, `'0'` when
   disabled (user directive).
2. **HTTP method**: Device sends GET requests with query parameters;
   the webhook handler must accept GET (observed from live device
   configuration).
3. **Variable mapping**: Relay A=`$relay1status`, Relay B=
   `$relay2status`; only `ValidCodeEntered` includes `$code`
   in its URL template. `InvalidCodeEntered` deliberately
   omits `$code` to avoid transmitting failed PIN attempts
   (user directive and device observation).
4. **Config write API**: `device.set_device_config(dict)` supports
   batch writes; all 10 action URLs plus the enable flag can be set
   in a single API call.
5. **Webhook URL generation**: Use `async_generate_url(hass, id)` to
   produce the URL the device should call; the integration must
   encode each action URL with the appropriate query parameters and
   variable placeholders.
6. **Scope**: 10 action URL keys are in scope — these are the core
   set present on all PIN-controlled Akuvox devices (the target
   audience of this integration). Other Akuvox models may expose
   additional action URL keys (InputC, Card, Face, Alarm, Call,
   etc.); these are model-specific and handled via the generic
   event path without code changes.
7. **PIN security in events**: The raw PIN (`$code`) MUST NEVER
   appear in HA event payloads. The handler resolves user identity
   (device-assigned ID, user-defined ID, username) by matching
   the PIN against coordinator-cached user data (`private_pin`),
   falling back to `device.list_users(page=None)` on cache
   miss.

   > **Note**: The current `AkuvoxCoordinatorData` does not
   > include a user cache. This feature requires extending the
   > coordinator to cache user data (e.g., a `users` field or
   > PIN→user map populated during `_async_update_data()`).

   Events emit identity fields only. Invalid codes emit
   `None` for all user fields (no lookup possible).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| ---- | ---------- | ------ | ---------- |
| Missing action URL keys | Low | Medium | Ignore; log warning |
| HA URL unreachable | Medium | High | Document; config flow |
| set_device_config fails | Low | Medium | Retry/skip in flow |
| Rapid-fire webhooks | Medium | Low | Stateless handler |
| Webhook ID in logs | Low | Medium | FR-013 masking |
| PIN exposure over HTTP | Medium | High | Log warning; document HTTPS |
| Unexpected query params | Low | Low | Generic event path |
