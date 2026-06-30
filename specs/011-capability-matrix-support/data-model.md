<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Data Model: Capability Matrix Support

## Upstream capability vocabulary

### Capability

`pylocal_akuvox.Capability` is the canonical enum used by v1.0.0 capability
gates. The integration must import and compare enum members, not string literals,
for runtime decisions.

| Domain | Members relevant to Local Akuvox |
| ------ | --------------------------------- |
| Users | `USER_LIST`, `USER_ADD`, `USER_MODIFY`, `USER_DELETE` |
| Schedules | `SCHEDULE_LIST`, `SCHEDULE_ADD`, `SCHEDULE_MODIFY`, `SCHEDULE_DELETE` |
| Groups | `GROUP_LIST`, `GROUP_ADD`, `GROUP_MODIFY`, `GROUP_DELETE` |
| Contacts | `CONTACT_LIST`, `CONTACT_ADD`, `CONTACT_MODIFY`, `CONTACT_DELETE` |
| Relays | `RELAY_TRIGGER_API`, `RELAY_TRIGGER_FCGI`, `RELAY_STATUS` |
| Device config | `DEVICE_CONFIG_GET`, `DEVICE_CONFIG_SET` |
| Logs/diagnostics | `LOG_DOOR`, `LOG_CALL`, `KEY_DISCOVERY` |

### CapabilityStatus

`pylocal_akuvox.CapabilityStatus` has three values:

- `SUPPORTED`: the integration may expose entities and dispatch calls.
- `UNSUPPORTED`: the integration must not attempt the operation except to handle
  an upstream-raised `AkuvoxUnsupportedError`; the opt-in never bypasses this.
- `UNKNOWN`: the integration behaves conservatively when
  `attempt_unknown_capability` is false and may dispatch when the opt-in is true.

### DeviceCapabilities

`pylocal_akuvox.DeviceCapabilities` is a frozen profile populated after
`AkuvoxDevice.__aenter__()` succeeds.

| Field | Type/meaning |
| ----- | ------------ |
| `device_class` | Detected upstream device class string, such as a model family |
| `firmware_version` | Firmware version associated with the matrix/probe result |
| `capabilities` | Read-only mapping of `Capability` to `CapabilityStatus` |
| `field_aliases` | Read-only mapping of logical fields to `FieldAliases` |
| `schema_shapes` | Read-only mapping of resource names to `SchemaShape` |
| `notes` | Read-only mapping of diagnostic notes; unrecognized profiles include `device_not_in_matrix` |
| `provenance` | Curated matrix metadata or `None` for probe-derived profiles |

Important methods/properties:

- `status_of(capability) -> CapabilityStatus`: returns `UNKNOWN` for absent
  capabilities.
- `require(capability, allow_unknown=False) -> None`: raises
  `AkuvoxUnsupportedError` for `UNSUPPORTED` and disallowed `UNKNOWN`.
- `supported_set -> frozenset[Capability]`: all explicitly supported members.

## Config option model

### `attempt_unknown_capability`

| Attribute | Value |
| --------- | ----- |
| Constant | `CONF_ATTEMPT_UNKNOWN_CAPABILITY` |
| Stored key | `"attempt_unknown_capability"` |
| Default | `False` via `DEFAULT_ATTEMPT_UNKNOWN_CAPABILITY` |
| Stored in setup | Config entry `data` |
| Stored in options | Config entry `options` |
| Missing existing value | Treated as `False` |
| Device application | `device.attempt_unknown_capability = True` only when the stored/effective value is enabled, after context entry succeeds |

The option affects only `UNKNOWN` capability gates. It does not bypass
`UNSUPPORTED`, relay adapter validation, adapter-missing failures, or real
network/authentication/parse/device errors.

## Repairs issue model

Unsupported capability events are surfaced as Home Assistant repairs issues.

| Attribute | Model |
| --------- | ----- |
| Domain | `local_akuvox` |
| Issue id | Deterministic per entry or setup-flow scope, reason, and capability; e.g. `unsupported_<entry_id>_<reason>_<capability>` or `unsupported_flow_<scope>_<reason>_<capability>` |
| Severity | Warning for unsupported/unknown capability conditions |
| Translation key | `unsupported_capability` with reason-specific placeholders |
| Placeholders | Entry title/id, context path, reason, capability value/name, device class, and safe mitigation text |
| Created | When `AkuvoxUnsupportedError` is caught or when coordinator detects a known unsupported required capability |
| Updated | Re-created with the same id and new placeholders when the context changes |
| Cleared | After a later successful operation for the same capability/reason, after capabilities show the condition no longer applies, after a setup flow succeeds for a flow-scoped issue, or on permanent config-entry removal |

Known reason meanings:

| Reason | User meaning |
| ------ | ------------ |
| `device_unrecognized` | Device/firmware is not in the upstream matrix; enable the opt-in only if willing to attempt unknown operations and share diagnostics upstream. |
| `capability_unknown` | Device is recognized, but this specific capability lacks matrix evidence. |
| `capability_missing` | Matrix confirms the device does not support the capability. |
| `adapter_missing` | The library has no usable adapter for the selected capability variant. |
| `envelope_unsupported` | The device returned an unsupported-operation response envelope. |
| `None` | Legacy/message-only unsupported error; show the message plus generic guidance. |

## Coordinator data model

Extend `AkuvoxCoordinatorData` with capability state:

```python
@dataclass
class AkuvoxCoordinatorData:
    """Data class for coordinator update results."""

    device_info: DeviceInfo
    relay_status: dict[str, Any]
    capabilities: DeviceCapabilities
    device_name: str = ""
    relay_configs: dict[str, RelayConfig] = field(default_factory=dict)
    users: list[User] = field(default_factory=list)
```

Rules:

- `capabilities` is read from `device.capabilities` only after context entry.
- If `device.capabilities is None` during update, raise a controlled
  `UpdateFailed` because using service methods outside context is invalid.
- Entity setup and availability must consume `coordinator.data.capabilities`.
- Diagnostics serialize a sanitized copy of the same snapshot rather than the
  raw dataclass object.

## Capability-derived lock model

A lock entity remains tied to one relay key (`RelayA`, `RelayB`, ...), but its
availability also depends on the capability snapshot.

| Field/derived value | Source |
| ------------------- | ------ |
| Relay number | Existing `_relay_key_to_number(relay_key)` |
| Relay state | `coordinator.data.relay_status[relay_key]` when `RELAY_STATUS` is usable |
| Relay config | `coordinator.data.relay_configs[letter]` when `DEVICE_CONFIG_GET` succeeds |
| State availability | `Capability.RELAY_STATUS` plus opt-in handling for `UNKNOWN` |
| Action availability | Usable `Capability.RELAY_TRIGGER_API`; `Capability.RELAY_TRIGGER_FCGI` is diagnostic only for current lock actions because upstream requires separate Open Relay Via HTTP credentials |

If relay status is unsupported, the coordinator returns no usable relay state and
creates a repairs issue. If API relay trigger is unsupported while status is
supported, the entity may show known state but should be unavailable for
lock/unlock actions to avoid exposing a control that cannot work. If API relay
trigger is `UNKNOWN` and the opt-in is enabled, the implementation may pass
`adapter=Capability.RELAY_TRIGGER_API` to intentionally attempt the legacy API
path.

## Diagnostics model

Diagnostics output contains only non-sensitive data:

- integration version and dependency requirement;
- config-entry safe metadata (entry id/title, SSL booleans, auth method, but no
  username/password/webhook id);
- current capability snapshot: `device_class`, `firmware_version`, statuses,
  schema shapes, non-sensitive notes, and provenance summary;
- optional probe result with the same sanitized shape;
- recent unsupported reason/capability summary without raw credentials, PINs,
  card codes, or unsanitized response bodies.

<!-- markdownlint-enable MD013 -->
