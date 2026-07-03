<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Contract: Capability Report Service

**Module**: `custom_components.local_akuvox.services` and
`custom_components.local_akuvox.lock` **Type**: Home Assistant platform entity
service with response data **Consumers**: Home Assistant service registry,
Developer Tools Actions, automations, tests, and upstream `new_device` support
workflow.

## Public service

### `local_akuvox.run_capability_report`

```python
SERVICE_RUN_CAPABILITY_REPORT: Final = "run_capability_report"
```

**Registration contract**:

- Registered by `async_register_services(hass)` through a private helper in
  `services.py`.
- Uses `service.async_register_platform_entity_service()` with `DOMAIN` and
  `entity_domain=Platform.LOCK`.
- Uses `cv.make_entity_service_schema()` for entity-targeted call data.
- Sets `supports_response=SupportsResponse.ONLY`.
- Dispatches to the lock entity method named `run_capability_report`.
- Does not change existing schedule, user, contact, or group service names,
  schemas, response settings, or behavior.

## Service schema

| Field | Schema | Default | Contract |
| ----- | ------ | ------- | -------- |
| `write` | optional boolean | `False` | Passed to upstream as `write`. False keeps read-only behavior. True opts into upstream write tests and warnings. |
| `open_door` | optional boolean | `False` | Passed to upstream as `open_door` only after hard-gate validation. |
| `open_door_user` | optional non-empty string | `None` | Required when `open_door=True`; passed as `open_door_user`; never logged by integration code, persisted, returned, saved, or placed in repairs/errors. Upstream v1.1.1 debug logs can include it unless an upstream fix is consumed. |
| `open_door_password` | optional non-empty string | `None` | Required when `open_door=True`; passed as `open_door_password`; password selector in service metadata; never logged, persisted, returned, saved, or placed in repairs/errors. |
| `save_to_file` | optional boolean | `False` | Enables file-output contract without changing report content. |
| `file_name` | optional relative `.json` path | generated | Valid only with `save_to_file=True`; rejected otherwise. The file-output contract performs path validation. |

## Safety and gating rules

- Default service calls are read-only and must not run upstream write tests.
- `open_door=True` is rejected before device entry unless `write=True` is also
  supplied.
- `open_door=True` is rejected before device entry unless both
  `open_door_user` and `open_door_password` are non-empty.
- `open_door_user` or `open_door_password` with `open_door=False` is rejected
  before device entry so unused relay credentials are not handled or passed to
  upstream.
- OpenDoor field labels and descriptions in `services.yaml`, `strings.json`, and
  `translations/en.json` must warn that OpenDoor can actuate a relay, unlock a
  door, or affect building access, and that callers must be authorized and
  physically present.
- Write-mode descriptions must warn that upstream write tests create, modify,
  verify, and delete throwaway device data and may perform relay-trigger or
  device-config write checks.
- The service reads the existing `attempt_unknown_capability` config-entry option
  through `get_effective_attempt_unknown(entry)` and never adds a service field
  that bypasses confirmed `UNSUPPORTED` capabilities.

## Execution contract

```python
async def run_capability_report(self, **kwargs: Any) -> ServiceResponse:
    """Run and return the redacted upstream capability report."""
```

The entity method must:

1. Validate OpenDoor and file-output combinations before opening a device.
2. Obtain the config entry from the entity coordinator.
3. Resolve and validate any requested file target, create validated parent
   directories, and check the no-overwrite condition before `_create_device()` or
   device entry so network/auth work, write mode, or OpenDoor side effects cannot
   precede a predictable path failure.
4. Build a fresh device with `_create_device(entry)`.
5. Enter it with `async with device:`.
6. Apply capability options with
   `apply_capability_options(device, attempt_unknown=get_effective_attempt_unknown(entry))`.
7. Acquire one Home Assistant instance-wide capability-report lock stored under a
   reserved `hass.data[DOMAIN]` key, shared by all Local Akuvox config entries,
   before calling upstream because the verified v1.1.1 source redirects
   process-wide stdout/stderr for no-op/custom emitters. The reserved key must be
   ignored as a coordinator entry and removed on final unload when no config
   entries remain.
8. Call the public upstream `pylocal_akuvox.run_capability_report()` with explicit
   kwargs for `write`, `open_door`, `open_door_user`, `open_door_password`,
   `timeout=None`, `redact_stdout=True`, and a no-op `emit` sink.
9. Return the upstream redacted dictionary under `response["report"]`.
10. If requested, write the exact same report value through the file-output
   contract and include `response["file"]["path"]`.

## Response contract

Successful response:

```json
{
  "report": {
    "device": {},
    "auth": {},
    "observed_schemas": {},
    "tests": []
  },
  "file": {
    "path": "local_akuvox/capability_reports/example.json"
  }
}
```

- `report` is always present on success.
- `file` is present only when a file was written.
- `report` must be the upstream redacted dict without manual de-redaction.
- No raw OpenDoor password, integration password, PIN, card code, phone number,
  MAC address, IP address, or user identifier may be added by the integration.

## Error contract

| Failure | Home Assistant surface |
| ------- | ---------------------- |
| Invalid OpenDoor combination | `ServiceValidationError` before device entry |
| Invalid file path or existing file target | `ServiceValidationError` before `_create_device()` or device entry/report execution; late exclusive-create collisions map to the same controlled no-overwrite failure |
| `AkuvoxValidationError` | `ServiceValidationError` preserving the existing lock service pattern |
| `AkuvoxUnsupportedError` | Call `async_report_unsupported_capability()` with context `capability report service`, then raise controlled `HomeAssistantError` |
| Other `AkuvoxError` subclasses | Raise sanitized actionable `HomeAssistantError` |
| Unexpected file write failure | Raise `HomeAssistantError` without leaking host paths outside config-relative context |

No failure path may return a partial report as success.

## Test contract

Stage 5 tests must cover:

- Service is registered for lock entities with `SupportsResponse.ONLY`.
- Default call passes `write=False`, `open_door=False`, credentials `None`,
  `redact_stdout=True`, and a no-op `emit` to upstream.
- `write=True` passes through without requiring OpenDoor credentials.
- Invalid OpenDoor combinations fail before `_create_device()` or upstream report
  invocation.
- Valid OpenDoor passes user/password to upstream, does not log either field from
  integration code, and documents the upstream v1.1.1 username debug-log caveat.
- `attempt_unknown_capability` is applied after context entry and before report
  invocation.
- Concurrent report calls from different config entries are serialized around the
  upstream call so custom/no-op emit stdout redirection cannot overlap.
- Final unload removes any reserved report-lock runtime key and preserves the
  existing behavior that `hass.data[DOMAIN]` disappears when no coordinators or
  non-empty runtime issue data remain.
- Unsupported and generic `AkuvoxError` paths use existing repairs/error surfaces.
- Existing diagnostics remain read-only and do not call the new report API.
- `manifest.json`, `pyproject.toml`, and lock metadata resolve
  `pylocal-akuvox>=1.1.1`.

<!-- markdownlint-enable MD013 -->
