<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Contract: Capability Matrix Integration

**Modules**: `custom_components/local_akuvox.const`,
`custom_components/local_akuvox.capability_support`, `__init__.py`,
`config_flow.py`, `options_flow.py`, `coordinator.py`, `diagnostics.py`, and
`lock.py` **Type**: Internal integration contract plus user-facing config,
repairs, and diagnostics behavior **Consumers**: Home Assistant config/options
flows, setup/unload, data coordinator, lock platform, service registry,
diagnostics download, tests, and release notes.

## Config option contract

### Constants

```python
CONF_ATTEMPT_UNKNOWN_CAPABILITY: Final = "attempt_unknown_capability"
DEFAULT_ATTEMPT_UNKNOWN_CAPABILITY: Final = False
```

**Contract**:

- The setup flow stores the key in config entry `data`.
- The options flow stores the key in config entry `options`.
- Effective reads use options first, then data, then
  `DEFAULT_ATTEMPT_UNKNOWN_CAPABILITY`.
- The field is absent-safe for existing config entries.
- The default is always `False`.
- Strings and English translations describe the v1.0.0 breaking behavior and the
  safety tradeoff of attempting unknown operations.

### Device application helper

```python
def apply_capability_options(device: AkuvoxDevice, *, attempt_unknown: bool) -> None:
    """Apply capability options after the device context is entered."""
```

**Contract**:

- Must be called after `await device.__aenter__()` or inside `async with device:`
  after entry succeeds.
- Sets `device.attempt_unknown_capability = True` only when the effective option
  is true.
- Leaves the upstream default `False` in place otherwise.
- Must run before any gated method such as `get_relay_status`,
  `get_device_config`, `set_device_config`, `trigger_relay`, or CRUD services.

## Unsupported-error repairs contract

### Reporting helper

```python
async def async_report_unsupported_capability(
    hass: HomeAssistant,
    entry: ConfigEntry | None,
    err: AkuvoxUnsupportedError,
    *,
    context: str,
    issue_scope: str | None = None,
) -> None:
    """Log and surface an unsupported Akuvox capability as a repairs issue."""
```

**Contract**:

- Logs the context path, config entry title/id when present, `err.reason`,
  `err.capability`, `err.device_class`, and `str(err)`.
- Creates or updates a Home Assistant repairs issue with a deterministic id
  scoped by entry id, reason, and capability when `entry` exists.
- For setup-flow failures before an entry exists, creates a flow-scoped issue id
  using `issue_scope` from the unique id or normalized host, and the flow also
  returns a form error.
- Uses `homeassistant.helpers.issue_registry.async_create_issue` with
  translation keys from `strings.json`/`translations/en.json`.
- Does not include credentials, PINs, card codes, webhook ids, or raw response
  bodies in placeholders.
- Is safe to call repeatedly from polling paths without creating duplicate user
  messages.

### Clearing helper

```python
async def async_clear_unsupported_capability_issue(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    reason: str | None,
    capability: Capability | None,
) -> None:
    """Clear a previously reported unsupported-capability repairs issue."""
```

**Contract**:

- Deletes the issue matching the same entry/reason/capability when a later
  successful operation or capability snapshot proves the condition no longer
  applies.
- Deletes flow-scoped setup issues when the same flow path later succeeds or the
  config entry is created.
- Deletes all entry-scoped capability issues during permanent entry removal.
- Does not clear confirmed unsupported capability issues merely because an entity
  is hidden or unavailable.

## Coordinator capability snapshot contract

### Data shape

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

**Contract**:

- `capabilities` is copied from `device.capabilities` after context entry.
- `capabilities` must not be `None` in successful coordinator data.
- Coordinator fetches catch `AkuvoxUnsupportedError`, call
  `async_report_unsupported_capability`, and return controlled `UpdateFailed` or
  fallback data according to the existing fetch semantics.
- `DEVICE_CONFIG_GET` unsupported falls back to default/cached relay config while
  reporting a repairs issue.
- `USER_LIST` unsupported leaves the user cache unchanged while reporting a
  repairs issue.
- `RELAY_STATUS` unsupported prevents a crashing refresh and produces no usable
  relay state for new entities.

## Entity availability contract

### Capability evaluation helper

```python
def is_capability_usable(
    capabilities: DeviceCapabilities,
    capability: Capability,
    *,
    attempt_unknown: bool,
) -> bool:
    """Return whether a capability should be exposed by the integration."""
```

**Contract**:

- Returns `True` for `SUPPORTED`.
- Returns `False` for `UNSUPPORTED`.
- Returns `attempt_unknown` for `UNKNOWN`.
- Uses `DeviceCapabilities.status_of()` so absent enum members are treated as
  `UNKNOWN`.

### Relay lock rules

| Required behavior | Capability rule |
| ----------------- | --------------- |
| Relay state polling | Requires usable `Capability.RELAY_STATUS` |
| Relay actions | Require usable `Capability.RELAY_TRIGGER_API` for current lock/unlock actions |
| API relay dispatch | Prefer/allow `Capability.RELAY_TRIGGER_API` when supported by upstream |
| FCGI relay dispatch | Recognize `Capability.RELAY_TRIGGER_FCGI` as a separate diagnostic variant; do not treat it as usable by current lock actions without separate Open Relay Via HTTP credentials |
| Unknown with opt-in off | Unavailable and repairs guidance instead of dispatch |
| API unknown with opt-in on | Available by explicitly passing `adapter=Capability.RELAY_TRIGGER_API`; upstream errors are still handled |
| Confirmed unsupported | Unavailable regardless of opt-in |

## Service capability contract

Service methods should precheck when the mapping is direct and must catch
`AkuvoxUnsupportedError` in all cases.

| Service/action | Required and prerequisite capabilities |
| -------------- | ------------------------------------- |
| `list_schedules` | `SCHEDULE_LIST` |
| `add_schedule` | `SCHEDULE_ADD` |
| `modify_schedule` | `SCHEDULE_LIST`, then `SCHEDULE_MODIFY` |
| `delete_schedule` | `SCHEDULE_LIST`, then `SCHEDULE_DELETE`, then best-effort `USER_LIST` orphan check |
| `list_users` | `USER_LIST` |
| `add_user` | `SCHEDULE_LIST`, then `USER_ADD` |
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
| Webhook user-cache refresh | Best-effort `USER_LIST`; leave cache unchanged and do not block webhook response |
| `async_lock` / `async_unlock` | `RELAY_TRIGGER_API` for current lock actions |

**Error contract**:

- `AkuvoxValidationError` remains `ServiceValidationError`.
- `AkuvoxUnsupportedError` becomes a controlled `HomeAssistantError` or
  `ServiceValidationError` with repairs issue reporting.
- Other `AkuvoxError` handling keeps existing user-visible semantics.
- Best-effort orphan checks still report unsupported capabilities but must not
  undo an already successful mutation.

## Diagnostics/probe contract

### Diagnostics platform

```python
async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return sanitized capability diagnostics for one config entry."""
```

**Contract**:

- Returns sanitized current coordinator capability data.
- Runs `device.probe_capabilities(timeout=5.0)` only from this user-triggered
  diagnostics path, not automatically at setup.
- Includes probe result when successful and safe error context when it fails.
- Sanitizes credentials, usernames where needed, PINs, card codes, webhook ids,
  and raw response bodies.
- May update the device capability profile through upstream merge semantics, but
  must not make normal setup depend on probe success.

## Test fixture contract

`tests/conftest.py` and direct `AkuvoxDevice` patches must model the v1.0.0
lifecycle:

- `device.capabilities` is `None` before entry and a `DeviceCapabilities` object
  after mocked entry succeeds.
- `device.attempt_unknown_capability` defaults to `False` and records option
  application after entry.
- `device.__aenter__` can raise auth, connection, parse, and generic
  `AkuvoxError` failures before the block body executes.
- `device.probe_capabilities` is an `AsyncMock` returning a merged
  `DeviceCapabilities` or raising controlled errors.
- Tests include supported, unsupported, unknown recognized, and unrecognized
  conservative-empty profiles.

<!-- markdownlint-enable MD013 -->
