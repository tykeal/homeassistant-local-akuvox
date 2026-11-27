<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Contract: Action URL Payload and Detection

**Module**: `custom_components.local_akuvox.webhook`
**Consumers**: `config_flow`, `options_flow`, `__init__` (removal and
reconciliation), tests.

## `build_action_urls`

```python
def build_action_urls(
    hass: HomeAssistant,
    webhook_id: str,
    *,
    warn_http: bool = True,
    optional_keys: Collection[str] = (),
) -> tuple[dict[str, str], dict[str, str]]: ...
```

- Existing behavior is unchanged when `optional_keys` is empty (default).
- For each logical name in `OPTIONAL_ACTIONURL_KEYS` (stable order) that is
  also in `optional_keys`, adds the config key to both payloads (enable:
  `url + template`; disable: `""`). Unrecognized names are ignored.
- URL-generation exceptions are logged with the masked webhook ID and
  re-raised (unchanged).

## `supported_optional_action_url_keys`

```python
def supported_optional_action_url_keys(device_config: object) -> frozenset[str]: ...
```

- Pure. Returns logical names whose config key satisfies
  `config_key in device_config`.
- Returns `frozenset()` if membership testing raises `TypeError` (e.g.
  `None` or a non-container).

## `async_detect_optional_action_url_keys`

```python
async def async_detect_optional_action_url_keys(device: object) -> frozenset[str]: ...
```

- Must be called with an entered device session.
- If `getattr(device, "get_device_config", None)` is not callable → debug
  log, `frozenset()`.
- Awaits `get_device_config()`; any `Exception` (including
  `AkuvoxUnsupportedError`) → debug log (no URLs, no config values),
  `frozenset()`.
- Otherwise returns `supported_optional_action_url_keys(config)`.

## Push-site usage

| Site | Order inside `async with device:` |
| ---- | --------------------------------- |
| `ConfigFlow._async_push_webhook_config` | `apply_capability_options` → detect → `build_action_urls(..., warn_http=enable, optional_keys=detected)` → `set_device_config(payload)` |
| `OptionsFlow._async_handle_webhook_change` | same; build failure or push failure → `"webhook_push_failed"` |
| `async_remove_entry` | same with `warn_http=False`; any failure → warning log, no raise |
