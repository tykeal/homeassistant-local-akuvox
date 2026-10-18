<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Contracts: Webhook Handler

**Feature**: 004-webhook-endpoint
**Component**: `webhook.py` (new module)

## Webhook Registration

### Register Webhook

Webhook registration is only performed in `async_setup_entry()`
when `webhook_enabled` is `True`. The config flow and options flow
do not directly register the webhook; they store `webhook_id` and
set `webhook_enabled=True`, and `async_setup_entry()` performs
registration when the config entry is created or after a reload
triggered by options changes.

```python
from homeassistant.components.webhook import async_register

async_register(
    hass,
    domain=DOMAIN,  # "akuvox"
    name=f"Akuvox {device_name}",  # Human-readable
    webhook_id=_get_config_value(entry, "webhook_id"),
    handler=async_handle_webhook,  # Callback
    allowed_methods=["GET"],  # Akuvox sends GET
)
```

> **Note on `local_only`**: The `local_only` parameter is
> intentionally **omitted**. While Akuvox devices are typically
> on the local network, some deployments route through NAT,
> VPN tunnels, or reverse proxies where HA may not recognize
> the source IP as local. Setting `local_only=True` would
> silently reject such requests (HTTP 200, body
> `"Webhook not registered."`), making failures hard to
> diagnose. The existing `allowed_methods=["GET"]` restriction
> and webhook ID secrecy (64-char random hex) provide adequate
> access control.

**Postconditions**:

- Webhook ID added to `hass.data[DOMAIN]["webhook_registry"]`
  **only after** `async_register()` succeeds (avoids stale
  registry entries if HA registration fails)
- Endpoint `/api/webhook/{webhook_id}` accepts GET requests

### Unregister Webhook

Called during `async_unload_entry()`, which is invoked on reload
and removal of the config entry (including reloads triggered by
options changes such as disabling webhooks). The options flow
does **not** call `async_unregister()` directly.

```python
from homeassistant.components.webhook import async_unregister

async_unregister(hass, webhook_id)
```

**Postconditions**:

- Webhook ID removed from `hass.data[DOMAIN]["webhook_registry"]`
- Endpoint returns 200 with `"Webhook not registered."` (HA default)

## Webhook Handler

### Signature

```python
async def async_handle_webhook(
    hass: HomeAssistant,
    webhook_id: str,
    request: web.Request,
) -> web.Response | None:
```

### Request Processing

1. Look up `config_entry_id` from webhook registry.
   If the `webhook_id` is not found in the integration's
   `webhook_registry` (e.g., race during startup or
   registration ordering bug), log a warning and return
   200 OK with an empty body — do not proceed further.
2. Retrieve the `device_id` from the HA device registry
   using `config_entry_id` (needed for event payload).
3. Parse query parameters from `request.query`
4. Extract `event` parameter → determines `event_type`.
   If `event` is missing, log a warning with a sanitized
   view of the request, then return 400 Bad Request.
5. Extract additional parameters (`status`, `code`)
6. Validate event type against known set
7. **User lookup** (valid code events only): If `code` parameter
   is present and event is `valid_code_entered`, look up the PIN
   against the coordinator's cached user data (match on
   `private_pin`). On cache miss, fall back to
   `device.list_users(page=None)` to fetch fresh data, but
   this fallback MUST NOT delay the webhook HTTP response
   (SC-001). Implementations SHOULD apply a short timeout on
   the device call or emit the event immediately with `None`
   identity fields and perform the lookup asynchronously.
   Resolve `device_user_id`, `user_id`, and `username`. If
   still no match after fallback, set all three to `None`.
8. Fire Home Assistant event (with user identity, never
   raw PIN)

### Response Codes

| Condition | HTTP Status | Body |
| --------- | ----------- | ---- |
| Valid known event | 200 OK | Empty |
| Valid unknown event (generic) | 200 OK | Empty |
| Missing `event` parameter | 400 Bad Request | `"Bad Request"` |
| Webhook ID unregistered in HA | 200 OK (HA) | `"Webhook not registered."` |
| Webhook ID in HA but not in registry (race) | 200 OK | Empty |
| Registry hit but coordinator missing | 200 OK | Empty |

> **Note**: For unknown event types, a warning-level message
> identifying the unknown type MUST also be logged per FR-013.

Note: HA's webhook infrastructure handles the routing. If the
webhook ID is not registered, HA itself returns a 200 with
`"Webhook not registered."`. FR-004 in `spec.md` has been
updated to reflect this (HTTP 200 instead of 404). The
security goal (no diagnostic details, no event fired) is met
since the response body is generic and the handler is never
invoked.

If the `webhook_id` is found in the registry but the
corresponding coordinator is no longer in
`hass.data[DOMAIN][config_entry_id]` (e.g., due to a race
during unload), the handler MUST catch the `KeyError`, log a
warning, and return HTTP 200 with an empty body rather than
raising an unhandled exception.

### Event Firing

```python
hass.bus.async_fire(
    f"{DOMAIN}_webhook_received",
    {
        "device_id": device_id,
        "config_entry_id": config_entry_id,
        "event_type": event_type,
        "payload": {
            "event": raw_event,
            "status": status_value,  # or None
            "device_user_id": user.id if user else None,
            "user_id": user.user_id if user else None,
            "username": user.name if user else None,
        },
    },
)
```

For **unknown event types** (`unknown_{normalized}`), the payload
MUST consist solely of sanitized raw query parameters per FR-013.
Do not include `status`, `device_user_id`, `user_id`, or
`username` fields. Example:

```python
hass.bus.async_fire(
    f"{DOMAIN}_webhook_received",
    {
        "device_id": device_id,
        "config_entry_id": config_entry_id,
        "event_type": f"unknown_{normalized}",
        "payload": sanitized_query_params,
    },
)
```

**Security**: The raw PIN (`$code` query parameter) is used ONLY
for the user lookup and MUST NOT appear in the event payload or
be stored anywhere. Log entries that include the raw query string
MUST apply FR-013 sanitization (the `code` key is in the
sensitive pattern list).

### Coordinator Refresh

When `event_type` is a relay event (`relay_a_triggered`,
`relay_a_closed`, `relay_b_triggered`, `relay_b_closed`) or
`valid_code_entered`:

```python
coordinator = hass.data[DOMAIN][config_entry_id]
hass.async_create_task(coordinator.async_refresh())
```

The refresh is scheduled as a background task so the HTTP response
is returned to the device immediately, avoiding slow-device
timeouts. This is consistent with the existing
`_schedule_delayed_refresh()` pattern in `lock.py`.

Input events (`input_a_triggered`, `input_a_closed`,
`input_b_triggered`, `input_b_closed`) do NOT trigger a refresh.
Inputs report external sensor state, not relay-controlled lock
state, so a coordinator refresh would not yield new lock data.
Invalid code events also do not trigger a refresh.

This is an *additional* faster path to update entity state. It does
**not** replace the existing speculative (optimistic) lock state
mechanism, which MUST remain intact for devices without webhooks
enabled. The delayed refresh scheduled by `async_unlock()` always
stays active as a safety net.

**Important**: When a valid code is entered on the device, the
relay-specific action URLs (`RelayATriggered`, etc.) may NOT fire
even though relays change state. `valid_code_entered` is the only
reliable signal for code-initiated relay changes. The refresh on
`valid_code_entered` is therefore critical — it is the primary
path for updating lock entity state after code entry.
