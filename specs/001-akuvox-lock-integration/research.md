<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Research: Akuvox Lock Integration

**Feature**: 001-akuvox-lock-integration
**Date**: 2026-02-23

## Library Analysis: pylocal-akuvox

### Overview

`pylocal-akuvox` is an async Python library for controlling Akuvox
intercom/access devices via their local HTTP API. It uses `aiohttp`
as its sole dependency and provides a fully async, type-safe API
designed for Home Assistant integration.

- **Package**: pylocal-akuvox
- **Python**: ≥3.14 (required by pylocal-akuvox)
- **Dependencies**: aiohttp ≥3.14
- **License**: Apache-2.0

### Public API Surface (Integration-Relevant)

#### Device Connection

```python
from pylocal_akuvox import AkuvoxDevice, AuthConfig, AuthMethod

device = AkuvoxDevice(
    host="192.168.1.100",
    auth=AuthConfig(method=AuthMethod.BASIC, username="admin", password="pass"),
    timeout=10,
    use_ssl=False,
    verify_ssl=True,
)
```

The device is an async context manager. For Home Assistant, the
device instance will be created in the coordinator and managed
across the integration lifecycle (not as a context manager per
request).

#### Authentication Modes

| AuthMethod | Credentials Required | Use Case |
| ---------- | -------------------- | -------- |
| NONE | No | Device with no auth configured |
| ALLOWLIST | No | IP-based allowlist on device |
| BASIC | username + password | HTTP Basic Auth |
| DIGEST | username + password | HTTP Digest Auth |

#### Relay Control (Lock Operations)

- `trigger_relay(num=1)` — Unlock relay 1 (auto-close mode)
- `get_relay_status()` — Returns dict with relay states

#### Device Information

- `get_info()` → `DeviceInfo` (model, mac_address, firmware_version,
  hardware_version)
- `get_status()` → `DeviceStatus` (unix_time, uptime)

### Exception Handling

All exceptions inherit from `AkuvoxError`:

| Exception | HTTP Code | HA Mapping |
| --------- | --------- | ---------- |
| AkuvoxConnectionError | N/A (network) | Mark entity unavailable |
| AkuvoxAuthenticationError | 401 | Config entry auth error |
| AkuvoxRequestError | 400 | Log warning, retry |
| AkuvoxDeviceError | 500 | Log error, mark unavailable |
| AkuvoxParseError | N/A | Log error, retry |
| AkuvoxUnsupportedError | N/A | Log warning |
| AkuvoxValidationError | N/A | Raise to caller |

## Home Assistant Integration Patterns

### DataUpdateCoordinator

The integration will use `DataUpdateCoordinator` for polling:

- `_async_update_data()` calls `await get_relay_status()` and
  `await get_info()` on each poll cycle
- `update_interval = timedelta(seconds=30)`
- Raises `UpdateFailed` on `AkuvoxConnectionError` or
  `AkuvoxDeviceError` — HA marks entities unavailable automatically
- Raises `ConfigEntryAuthFailed` on `AkuvoxAuthenticationError` —
  HA triggers re-auth flow

### Config Flow Steps

1. **Step: User** — IP address, Use SSL toggle
2. **Step: SSL** (conditional) — Verify SSL checkbox (only if SSL
   enabled)
3. **Step: Auth** — Authentication mode selection
4. **Step: Credentials** (conditional) — Username/password (only if
   Basic or Digest selected)

After the UI steps are complete, the integration tests the
connection with the provided parameters before creating the config
entry.

### Entity Registration

- One `LockEntity` per relay discovered on the device
- `unique_id` format: `{mac_address}_relay_{relay_number}`
- Device registry: one device per physical Akuvox unit using
  `mac_address` as identifier

### Reconfiguration (FR-010)

Options flow allows changing IP, auth mode, credentials, and SSL
settings without removing the integration entry.

## Resolved Clarifications

All NEEDS CLARIFICATION items from the spec have been resolved:

1. **Auth modes**: Four library enum values (None, AllowList,
   Basic, Digest); spec groups None/AllowList as one mode
   for three user-facing choices (resolved during spec creation)
2. **SSL handling**: Explicit user selection, no auto-detect
   (resolved during spec iteration)
3. **Library**: pylocal-akuvox confirmed as the communication library
   (user directive)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| ---- | ---------- | ------ | ---------- |
| Inconsistent relay status | Low | Medium | Parse defensively |
| Firmware API changes | Low | High | Pin library version |
| Self-signed cert rotation | Low | Low | verify_ssl=False |
| Concurrent unlock requests | Medium | Low | asyncio.Lock in lib |
