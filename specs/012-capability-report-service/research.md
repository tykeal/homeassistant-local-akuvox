<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Research: Capability Report Service

**Feature**: 012-capability-report-service **Date**: 2026-07-02
**Status**: Complete

## Verified upstream facts

The adjacent `pylocal-akuvox` source checkout was used as the load-bearing
reference for this plan. Stage 5 should re-check the exact installed v1.3.0
package before implementation.

- `pylocal_akuvox.run_capability_report` is exported from
  `src/pylocal_akuvox/_capability_report.py` with this public signature:

  ```python
  async def run_capability_report(
      device: AkuvoxDevice,
      *,
      write: bool = False,
      open_door: bool = False,
      open_door_user: str | None = None,
      open_door_password: str | None = None,
      timeout: float | None = None,
      redact_stdout: bool = False,
      emit: Callable[[str], None] | None = None,
  ) -> dict[str, object]:
      ...
  ```

- The public function wraps `_run_capability_report()` in `_stdout_context(emit)`.
  In the verified source, both `emit=None` and custom emitters redirect
  process-wide stdout/stderr while the run is active; `emit=print` is the only
  no-redirection branch but would write progress to Home Assistant stdout.
- `_run_capability_report()` builds a `DiagnosticReport`, probes capabilities,
  converts UNKNOWN capabilities to SUPPORTED only when
  `device.attempt_unknown_capability` is true, runs write tests only when
  `write=True`, runs read tests, and returns `diagnostics.to_json()`.
- The returned dictionary is already redacted by `DiagnosticReport.to_json()`.
  Top-level keys are `device`, `auth`, `observed_schemas`, and `tests`; each test
  may contain nested `http_events` and `failure_shape` entries with redacted
  request/response evidence.
- OpenDoor is only executed from `_run_write_tests()`. In read-only mode,
  `open_door=True` produces a skipped `open_door_http` test with reason
  `requires write=True to run OpenDoor HTTP`.
- `_run_open_door_write_step()` runs OpenDoor only when all of `open_door`,
  `open_door_user`, and `open_door_password` are present; otherwise it records a
  skipped `open_door_http` step. The Home Assistant service will reject unsafe
  combinations earlier so the device is not entered for invalid calls.
- OpenDoor relay credentials are separate from the integration connection
  credentials. The report API accepts them only as call arguments and does not
  require storing them on `AkuvoxDevice`.
- `redact_stdout` affects display values printed by report steps. The returned
  report dictionary is redacted independently through `DiagnosticReport`.

## Verified integration facts

- `custom_components/local_akuvox/services.py` currently centralizes service
  schemas and uses `service.async_register_platform_entity_service()` with
  `entity_domain=Platform.LOCK`. Read services set
  `supports_response=SupportsResponse.ONLY` and dispatch to methods on
  `AkuvoxLockEntity` by passing the service name as `func`.
- `async_register_services()` is a thin orchestrator that calls four private
  helpers: `_register_schedule_services`, `_register_user_services`,
  `_register_contact_services`, and `_register_group_services`.
- `diagnostics.py` creates a fresh device with `_create_device(entry)`, enters it
  with `async with device:`, applies `apply_capability_options(device,
  attempt_unknown=get_effective_attempt_unknown(entry))`, runs the diagnostic
  capability probe, and maps `AkuvoxUnsupportedError` through
  `async_report_unsupported_capability()`.
- `capability_support.py` already owns `apply_capability_options()`,
  `get_effective_attempt_unknown()`, `sanitize_value()`, and repairs issue
  helpers for unsupported capabilities.
- `lock.py` entity service methods already catch `AkuvoxValidationError`,
  `AkuvoxUnsupportedError`, and other `AkuvoxError` subclasses, converting them
  to Home Assistant `ServiceValidationError` or `HomeAssistantError` surfaces.

## Decisions

### 1. Service registration surface

**Decision**: Register `local_akuvox.run_capability_report` as a platform entity
service on `Platform.LOCK`, not as a domain service. Add
`SERVICE_RUN_CAPABILITY_REPORT = "run_capability_report"` and a
`SERVICE_RUN_CAPABILITY_REPORT_SCHEMA`, then register it from a new private
`_register_report_services(hass)` helper called by `async_register_services()`.
Set `supports_response=SupportsResponse.ONLY`.

**Rationale**: The report targets one configured Akuvox device and needs the lock
entity's coordinator/config-entry context. Platform entity services already give
Home Assistant entity targeting, reuse the current registration style, and avoid
inventing a separate lookup path from config entry IDs or device registry IDs.

**Alternatives considered**:

- Domain service with `config_entry_id` or device selector — rejected because it
  duplicates Home Assistant's entity targeting and would need custom entity or
  config-entry lookup code.
- Diagnostics download only — rejected because the spec requires an explicit
  response-returning service with write and hard-gated OpenDoor modes, while
  diagnostics must stay passive.

### 2. Device-entry approach

**Decision**: The entity service method will create a fresh short-lived device
from the target entity's config entry using `_create_device(entry)`, enter it with
`async with device:`, apply the stored unknown-capability option with
`apply_capability_options()`, then pass that entered template device to
`pylocal_akuvox.run_capability_report()`.

**Rationale**: This mirrors `diagnostics.py`, applies the
`attempt_unknown_capability` opt-in at the required post-entry point, and avoids
using the coordinator's long-lived entered device for a deliberate report run
that internally creates additional device sessions for probing, write tests, and
read tests. It also limits report failures and cleanup to the service call.

**Alternatives considered**:

- Reuse `self.coordinator.device` — rejected because the upstream report uses the
  passed device as a connection template and then opens its own report devices;
  reusing the coordinator object risks coupling a long-running report to normal
  polling and entity actions.
- Create a device without entering it — rejected because the integration's
  capability option contract applies options after successful context entry and
  because entry-time auth/network/device errors should be surfaced consistently.

### 3. Upstream report invocation

**Decision**: Call the public API with explicit keyword arguments:

```python
report = await run_capability_report(
    device,
    write=write,
    open_door=open_door,
    open_door_user=open_door_user,
    open_door_password=open_door_password,
    timeout=None,
    redact_stdout=True,
    emit=lambda _line: None,
)
```

The implementation may define the no-op emitter once as a private helper for
coverage/docstring clarity.

**Rationale**: Explicit kwargs prevent accidental drift if upstream defaults
change. `redact_stdout=True` ensures any progress lines would be redacted, and a
no-op `emit` suppresses progress text because the Home Assistant response carries
the report data. The verified v1.3.0 source still redirects stdout/stderr for
custom emitters, so Stage 5 must serialize report executions with one
Home Assistant instance-wide `asyncio.Lock` shared across all `local_akuvox`
config entries. Store it in `hass.data[DOMAIN]` under a reserved key such as
`capability_report_lock`, access it from the entity method through `self.hass`,
hold it around the upstream call, and cover multi-entry concurrent service calls
in tests instead of allowing overlapping report runs. The reserved key must not
be treated as a config-entry coordinator: final unload cleanup must remove the
lock and then remove `hass.data[DOMAIN]` when only reserved/empty runtime keys
remain, preserving existing domain-data cleanup expectations.

**Alternatives considered**:

- `emit=None` — rejected because it relies on upstream silent mode and still uses
  stdout/stderr redirection; a no-op emitter makes the intended sink explicit.
- `emit=print` — rejected because it avoids upstream redirection only by writing
  progress to Home Assistant stdout, which the service does not need.
- `redact_stdout=False` — rejected because even discarded/emitted progress should
  follow the safest redaction setting.

### 4. Service schema and OpenDoor hard gate

**Decision**: Use voluptuous with `cv.make_entity_service_schema()` and add a
post-validation guard that rejects unsafe combinations before device entry:

| Field | Rule |
| ----- | ---- |
| `write` | Optional boolean, default `False`. |
| `open_door` | Optional boolean, default `False`; allowed only when `write=True`. |
| `open_door_user` | Optional non-empty string; required when `open_door=True`. |
| `open_door_password` | Optional non-empty string/password selector; required when `open_door=True`; never logged, stored, or returned. |
| `save_to_file` | Optional boolean, default `False`; when true, write the same redacted response report to a JSON file under the config directory. |
| `file_name` | Optional relative JSON file name/path used only when `save_to_file=True`; must stay inside the report directory and may not be absolute or contain traversal. |

Invalid OpenDoor calls raise `ServiceValidationError` with actionable messages:
`open_door requires write`, `open_door_user is required`,
`open_door_password is required`, and `OpenDoor credentials require open_door`.
Reject `open_door_user` or `open_door_password` when `open_door=False` before
device entry so unused credentials are not handled or passed through. Treat both
OpenDoor fields as relay
credentials for integration-controlled surfaces: neither `open_door_user` nor
`open_door_password` may appear in integration logs, repairs placeholders,
errors, responses, saved files, or tests. Accuracy caveat: verified upstream
v1.3.0 debug logging redacts the password but includes `UserName` in the
OpenDoor HTTP parameter log, so Stage 5 must not claim end-to-end username log
redaction unless an upstream redaction fix is consumed first.

**Rationale**: Upstream will skip unsafe combinations, but Home Assistant should
fail fast before any network connection for an operation that can physically
actuate a relay. The schema keeps safe defaults while allowing advanced users to
opt in deliberately.

**Alternatives considered**:

- Let upstream record skipped OpenDoor evidence for `open_door=True, write=False`
  — rejected because the spec requires Home Assistant rejection before invoking
  the report API.
- Require OpenDoor credentials whenever `write=True` — rejected because write-mode
  evidence is useful without OpenDoor and the spec keeps OpenDoor separately
  opt-in.

### 5. Response shape

**Decision**: Return a Home Assistant service response wrapper with the exact
upstream report under `report` and optional file metadata under `file`:

```json
{
  "report": {
    "device": {},
    "auth": {},
    "observed_schemas": {},
    "tests": []
  },
  "file": {
    "path": "local_akuvox/capability_reports/<name>.json"
  }
}
```

The `file` key is omitted when `save_to_file` is false.

**Rationale**: Wrapping avoids adding Home Assistant metadata keys to the
upstream report dictionary and satisfies the requirement to identify the saved
config-relative path alongside the report. The `report` value remains suitable
for copy/paste into the upstream `new_device` issue template.

**Alternatives considered**:

- Return the upstream report as the top-level response — rejected because optional
  file metadata would have to collide with upstream keys or be omitted.
- Return only a file path when saved — rejected because `SupportsResponse.ONLY`
  should always return the report data on success.

### 6. Optional config-dir file output

**Decision**: Add `save_to_file` and `file_name` fields. When `save_to_file` is
true, serialize the same redacted `report` value as pretty JSON under
`<config>/local_akuvox/capability_reports/`. If `file_name` is omitted, generate
`<entry_id>-<YYYYMMDDTHHMMSSffffffZ>.json`. If `file_name` is supplied, treat
it as relative to the report directory, require a `.json` suffix, reject absolute
paths and `..`, resolve the path, and verify it remains under the report
directory. Resolve the final target, perform containment/suffix/existing-target
checks, and create any report directories before `_create_device()` or device
entry. Do not overwrite existing files; raise `ServiceValidationError` if the
validated target exists. Use exclusive creation for the final write so concurrent
calls with the same supplied `file_name` cannot race past the preflight check.

**Rationale**: The directory groups support artifacts away from unrelated config
files, the generated name is deterministic from the entry and call time while
being collision-resistant, config-relative paths avoid exposing host filesystem
details, and no-overwrite protects prior evidence.

**Alternatives considered**:

- Caller-supplied absolute path — rejected because the spec requires staying
  inside the Home Assistant config directory.
- Always overwrite — rejected because reports can be used as support evidence and
  should not be replaced accidentally.
- Put files at config root — rejected because a dedicated integration directory is
  clearer and easier to clean up.

### 7. Error handling and repairs

**Decision**: Reuse existing integration error surfaces. Entry/report execution
should catch `AkuvoxValidationError` as `ServiceValidationError`, catch
`AkuvoxUnsupportedError`, call `async_report_unsupported_capability()` with
context `capability report service`, and raise a controlled `HomeAssistantError`.
Other `AkuvoxError` subclasses should become sanitized, actionable
`HomeAssistantError` messages. Schema and file validation failures should become
`ServiceValidationError`. Raw OpenDoor credentials must never appear in
integration-controlled logs, repairs placeholders, exception messages, response
data, or saved JSON. Because upstream v1.3.0 debug logging can include
`open_door_user`, Stage 5 must either document that limitation in service
descriptions or consume an upstream fix before promising username log redaction.

**Rationale**: This matches capability-matrix support behavior and gives users a
repairable upstream-report path for unsupported or unrecognized devices without
leaking secrets.

**Alternatives considered**:

- Return partial reports on error — rejected because the spec says unavailable or
  failed calls must not return partial success.
- Log raw exceptions with service data — rejected because service data may include
  relay credentials.

### 8. Dependency pin bump

**Decision**: Raise the runtime and project metadata floor from
`pylocal-akuvox>=1.0.0` to `pylocal-akuvox>=1.3.0` in `manifest.json` and
`pyproject.toml`, then refresh `uv.lock` in the implementation stage. Update
existing `strings.json` and `translations/en.json` text that names
`pylocal-akuvox 1.0.0` so user-facing capability-safety descriptions reference
the new `1.3.0` dependency floor. Review `.pre-commit-config.yaml` comments and
hook environments for stale references, but no hook currently pins
`pylocal-akuvox` directly.

**Rationale**: `run_capability_report()` is a public API introduced in v1.1.0.
Both Home Assistant runtime installation and local test environments must resolve
a package that exports it.

**Alternatives considered**:

- Optional import with old-library fallback — rejected because the feature cannot
  work without the report API and would complicate tests and user errors.
- Exact `==1.3.0` pin — rejected because the repository uses minimum compatible
  constraints and should accept future compatible fixes.

## Summary of Decisions

| Item | Decision |
| ---- | -------- |
| Service registration | Platform lock entity service registered in `services.py` |
| Response support | `SupportsResponse.ONLY` |
| Device entry | Fresh `_create_device(entry)` + `async with` + `apply_capability_options()` |
| Coordinator device | Not reused for report execution |
| Upstream call | `run_capability_report(..., redact_stdout=True, emit=noop)` |
| Stdout mitigation | Serialize all entries with one HA-instance-wide report lock in `hass.data[DOMAIN]` |
| OpenDoor gate | Reject unless `write=True`, `open_door=True`, user, and password are all supplied |
| Response wrapper | `{"report": <upstream redacted dict>, "file": {"path": ...}}` when saved |
| File directory | `<config>/local_akuvox/capability_reports/` |
| File overwrite | Never overwrite; existing target is validation error |
| Dependency floor | `pylocal-akuvox>=1.3.0` in runtime and project metadata |

<!-- markdownlint-enable MD013 -->
