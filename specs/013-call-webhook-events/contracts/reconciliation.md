<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Contract: Setup-Time Call URL Reconciliation

**Module**: `custom_components.local_akuvox.webhook`
(`async_reconcile_optional_action_urls`), scheduled from
`custom_components.local_akuvox.async_setup_entry`.

## Signature

```python
async def async_reconcile_optional_action_urls(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device: object,
    webhook_id: str,
) -> None: ...
```

## Scheduling

- In `async_setup_entry`, only when `webhook_enabled` is true and
  `webhook_id` is not `None`, and only after
  `async_forward_entry_setups()` succeeds:
  `entry.async_create_background_task(hass, async_reconcile_optional_action_urls(hass, entry, coordinator.device, str(webhook_id)), name="local_akuvox_reconcile_action_urls_<entry_id>")`.
- The returned task is stored on the coordinator as
  `coordinator.action_url_reconcile_task` (attribute defaults to `None`).
- Setup returns `True` without awaiting the task.
- Home Assistant cancels entry background tasks only *after*
  `async_unload_entry` returns, but `async_unload_entry` closes the shared
  device session. Therefore `async_unload_entry` MUST, before
  `coordinator.device.__aexit__`, cancel the task if not done and wait for it
  with `asyncio.wait({task})` (which does not re-raise the task's
  `CancelledError` and does not swallow cancellation of the unload itself).

## Behavior

1. If `get_device_config` is not callable → debug log, return.
2. `config = await device.get_device_config()`.
3. `supported = supported_optional_action_url_keys(config)`; empty → debug
   log, return.
4. `enable_payload, _ = build_action_urls(hass, webhook_id, warn_http=False, optional_keys=supported)`.
5. `updates = {key: enable_payload[key] for supported key if config.get(key) != enable_payload[key]}`.
6. Empty `updates` → debug log, return (no write).
7. `await device.set_device_config(updates)`; info log listing updated
   logical names and the masked webhook ID (no URLs).

## Errors

| Error | Handling |
| ----- | -------- |
| `AkuvoxUnsupportedError` (read or write) | `async_report_unsupported_capability(hass, entry, err, context="webhook call action URL reconciliation")`; return |
| `asyncio.CancelledError` | propagate (entry unloading) |
| any other `Exception` | warning log without URLs/IDs (masked ID only), `exc_info` at debug; return |

Never raises to the caller; never modifies `Enable`, `Method`, or base keys.
