<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Data Model: Akuvox Lock Integration

**Feature**: 001-akuvox-lock-integration
**Date**: 2026-02-23

## Config Entry Data

Stored in Home Assistant's config entry system (`.storage/`).

### Entry Data (set during config flow)

Connection parameters are stored in `entry.data` during initial
setup. When the user reconfigures the integration via the options
flow, updated values are stored in `entry.options`. At runtime,
the integration reads connection parameters from `entry.options`
first, falling back to `entry.data` for fields not yet overridden.

```python
{
    "host": str,  # Device IP address or hostname
    "use_ssl": bool,  # Whether to use HTTPS
    "verify_ssl": bool,  # Whether to verify SSL certs
    "auth_method": str,  # "none"|"allowlist"|"basic"|"digest"
    "username": str | None,  # Basic/Digest only
    "password": str | None,  # Basic/Digest only
}
```

### Options Flow

The options flow presents the same fields as entry data,
pre-filled with current values. On save, the integration
reloads the coordinator with updated connection parameters.

## Coordinator Data

The `DataUpdateCoordinator` stores this data structure, refreshed
every 30 seconds:

```python
@dataclass
class AkuvoxCoordinatorData:
    device_info: DeviceInfo  # Library's DeviceInfo from get_info()
    relay_status: dict[str, Any]  # From get_relay_status()
```

Note: The library's `DeviceInfo` dataclass is distinct from Home
Assistant's `DeviceInfo` helper. The entity's `device_info` property
MUST convert the library type into an HA `DeviceInfo` mapping.

## Entity Model

### Lock Entity

| Attribute | Source | Description |
| --------- | ------ | ----------- |
| `unique_id` | `{mac}_relay_{num}` | Stable across IP changes |
| `name` | `Relay {num}` | Default entity name |
| `is_locked` | `relay_status` | Parsed from relay data |
| `available` | Coordinator | Auto-managed |

### Device Registry Entry

| Field | Source | Description |
| ----- | ------ | ----------- |
| `identifiers` | `{(DOMAIN, mac_address)}` | Unique device ID |
| `name` | `Akuvox {model}` | Device display name |
| `manufacturer` | `"Akuvox"` | Static |
| `model` | `DeviceInfo.model` | From device query |
| `sw_version` | `DeviceInfo.firmware_version` | Firmware version |
| `hw_version` | `DeviceInfo.hardware_version` | Hardware version |

## State Mapping

### Relay State → Lock State

The `get_relay_status()` response is parsed to determine lock state:

| Relay State | Lock Entity State | Notes |
| ----------- | ----------------- | ----- |
| Relay closed/inactive | `STATE_LOCKED` | Normal state for doors |
| Relay open/active | `STATE_UNLOCKED` | After trigger_relay |
| Device unreachable | `STATE_UNAVAILABLE` | Coordinator update failed |

## Relationship Diagram

```text
ConfigEntry (1)
  │
  ├── AkuvoxDevice (1) ─── pylocal-akuvox client instance
  │
  ├── DataUpdateCoordinator (1)
  │     │
  │     └── AkuvoxCoordinatorData
  │           ├── DeviceInfo
  │           └── relay_status dict
  │
  └── LockEntity (1..N) ─── one per relay
        ├── unique_id: {mac}_relay_{num}
        └── state derived from coordinator data
```
