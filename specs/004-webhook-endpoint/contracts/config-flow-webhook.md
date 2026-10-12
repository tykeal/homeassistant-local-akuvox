<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Contracts: Config Flow (Webhook Additions)

**Feature**: 004-webhook-endpoint
**Component**: `config_flow.py` (modifications to existing)

## Config Flow — Webhook Step (New)

Added after the existing connection test step (Step 5 from spec 001).

### Step: Webhook Setup

**Input Schema**:

```python
vol.Schema(
    {
        vol.Required(CONF_WEBHOOK_ENABLED, default=False): bool,
    }
)
```

**Behavior**:

- Shown after successful connection test during initial setup
- User toggles whether to enable webhook event delivery
- If enabled:
  1. Generate `webhook_id = secrets.token_hex(32)`
  2. Build action URLs using `async_generate_url(hass, webhook_id)`
     with appropriate query parameters and variable placeholders
  3. Using the credentials stored in `self._data`, open a new
     `AkuvoxDevice` connection (e.g., via
     `async with AkuvoxDevice(...) as device:`) since the
     connection from the test step is already closed
  4. Push all 10 action URL keys + enable flag + Method key
     to device via `device.set_device_config()`
  5. Store `webhook_id` and `webhook_enabled=True` in entry data;
     the actual HA webhook endpoint will be registered during
     `async_setup_entry()` immediately after the config entry is
     created, so the config flow itself does not perform webhook
     registration

> **Warning**: If `async_generate_url()` produces an HTTP (not
> HTTPS) base URL, the `ValidCodeEntered` action URL will
> transmit PINs in plaintext. Implementations SHOULD log a
> warning when the generated URL scheme is not HTTPS, alerting
> the operator to configure an external URL with TLS.

- If skipped (disabled):
  1. Store `webhook_id=None` and `webhook_enabled=False`
  2. No device configuration changes

**Errors**:

- `webhook_push_failed` — `set_device_config()` raised an exception;
  user shown option to retry or skip

## Options Flow — Webhook Section

Added to the existing options flow.

### Webhook Toggle

**Input Schema**:

```python
vol.Schema(
    {
        # ... existing connection fields ...
        vol.Required(CONF_WEBHOOK_ENABLED, default=current_value): bool,
    }
)
```

**Behavior on Enable** (was disabled → now enabled):

1. Reuse existing `webhook_id` from config entry (looked up
   via `_get_config_value()`) if present; otherwise generate
   new `webhook_id = secrets.token_hex(32)`
2. Build action URLs and push all 10 URL keys plus
   `Config.Features.ACTIONURL.Enable='1'` and
   `Config.Features.ACTIONURL.Method=''` in a single
   `set_device_config()` call
3. Update config entry with `webhook_enabled=True` and the
   existing or newly generated `webhook_id`

> **Note**: The options flow does NOT inline-register the HA
> webhook endpoint. The existing `_async_update_listener`
> triggers a full reload on every options change
> (`async_unload_entry` → `async_setup_entry`), and
> `async_setup_entry` handles webhook registration when
> `webhook_enabled=True`. Inline registration would create
> redundant churn and a brief window where the endpoint is
> absent during the reload cycle.

**Behavior on Disable** (was enabled → now disabled):

1. Push empty strings for all 10 action URL keys plus
   `Config.Features.ACTIONURL.Enable='0'` and
   `Config.Features.ACTIONURL.Method=''` in a single
   `set_device_config()` call
2. Update config entry with `webhook_enabled=False`
   (preserve `webhook_id` for potential re-enable)

> **Note**: The options flow does NOT inline-unregister the HA
> webhook endpoint or remove the registry entry. Instead, the
> integration ensures that `async_unload_entry` always
> unregisters the webhook whenever `webhook_id` is not `None`
> and is present in the `webhook_registry`, regardless of the
> `webhook_enabled` flag in the config entry. This avoids
> double-unregistration in the options flow itself (which
> could raise if HA's `async_unregister` rejects unknown IDs),
> while still guaranteeing that a previously registered
> endpoint is cleaned up on unload — including when webhooks
> are disabled via the options flow.

**Behavior on No Change**:

- No device configuration or webhook registration changes

**Errors**:

- `webhook_push_failed` — Device config push failed; show error
  and allow retry or cancel.
  - **Enable path — cancel**: Keep `webhook_enabled=False` in
    the config entry. No HA webhook cleanup needed since the
    options flow does not register the endpoint.
  - **Disable path — cancel**: Keep `webhook_enabled=True`
    unchanged (preserving the current working state). The
    reload will keep the HA endpoint registered.

## Action URL Construction

### URL Template

For each of the 10 action URL keys, the integration constructs:

```python
base_url = async_generate_url(hass, webhook_id)
# Example: "http://homeassistant.local:8123/api/webhook/abc123..."

action_urls = {
    "Config.Features.ACTIONURL.RelayATriggered": f"{base_url}?event=relay_a_triggered&status=$relay1status",
    "Config.Features.ACTIONURL.RelayAClosed": f"{base_url}?event=relay_a_closed&status=$relay1status",
    "Config.Features.ACTIONURL.RelayBTriggered": f"{base_url}?event=relay_b_triggered&status=$relay2status",
    "Config.Features.ACTIONURL.RelayBClosed": f"{base_url}?event=relay_b_closed&status=$relay2status",
    "Config.Features.ACTIONURL.InputATriggered": f"{base_url}?event=input_a_triggered&status=$relay1status",
    "Config.Features.ACTIONURL.InputAClosed": f"{base_url}?event=input_a_closed&status=$relay1status",
    "Config.Features.ACTIONURL.InputBTriggered": f"{base_url}?event=input_b_triggered&status=$relay2status",
    "Config.Features.ACTIONURL.InputBClosed": f"{base_url}?event=input_b_closed&status=$relay2status",
    "Config.Features.ACTIONURL.ValidCodeEntered": f"{base_url}?event=valid_code_entered&code=$code",
    "Config.Features.ACTIONURL.InvalidCodeEntered": f"{base_url}?event=invalid_code_entered",
}
```

### Enable/Disable Payload

```python
# Enable
enable_payload = {
    "Config.Features.ACTIONURL.Enable": "1",
    "Config.Features.ACTIONURL.Method": "",
    **action_urls,
}

# Disable
disable_payload = {
    "Config.Features.ACTIONURL.Enable": "0",
    "Config.Features.ACTIONURL.Method": "",
    **{key: "" for key in action_urls},
}
```
