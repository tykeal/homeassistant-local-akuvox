<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Quickstart: Capability Report Service

**Feature**: 012-capability-report-service **Date**: 2026-07-02

## Prerequisites

- Local Akuvox integration is configured and has at least one `lock` entity.
- The implementation stage has bumped `pylocal-akuvox` to `>=1.3.0`.
- For unrecognized devices, enable **Attempt unknown capabilities** only if you
  intentionally accept trying upstream `UNKNOWN` capability gates. Confirmed
  `UNSUPPORTED` capabilities remain blocked.
- For write-mode or OpenDoor testing, be physically present and authorized.
  `write=True` can run the upstream relay-trigger check, and OpenDoor can
  actuate a relay or door through the credentialed OpenDoor HTTP endpoint.

## Invoke from Home Assistant

Open **Developer Tools** → **Services** (called **Actions** in newer Home
Assistant UI versions), choose `local_akuvox.run_capability_report`, and select
a Local Akuvox lock entity. The service returns response data because it is
registered with `SupportsResponse.ONLY`.

### Read-only report

Read-only mode is the default and does not create, modify, delete, or open
anything on the device.

```yaml
service: local_akuvox.run_capability_report
target:
  entity_id: lock.front_door
```

Expected response shape:

```json
{
  "report": {
    "device": {"host": "<redacted>"},
    "auth": {"method": "digest", "ssl": false, "verify_ssl": true},
    "observed_schemas": {},
    "tests": []
  }
}
```

### Write-mode evidence

Write mode runs the upstream write suite. It can create, modify, verify, and
delete throwaway users, schedules, groups, and contacts, and can run additional
relay-trigger or device-config write checks. The relay-trigger check can actuate
a relay even when OpenDoor is not enabled. OpenDoor remains skipped unless it is
separately enabled with credentials.

```yaml
service: local_akuvox.run_capability_report
target:
  entity_id: lock.front_door
data:
  write: true
```

### Hard-gated OpenDoor evidence

OpenDoor can physically actuate a relay, unlock a door, or affect access. It is
valid only when all fields below are supplied in the same service call.
`pylocal-akuvox` v1.3.0 redacts the OpenDoor password in its debug logging but
can include the OpenDoor username; do not enable debug logging around OpenDoor
runs if that username is sensitive unless Stage 5 has consumed an upstream
redaction fix.

```yaml
service: local_akuvox.run_capability_report
target:
  entity_id: lock.front_door
data:
  write: true
  open_door: true
  open_door_user: relay-user
  open_door_password: relay-password
```

Invalid examples rejected before device entry:

```yaml
# Rejected: OpenDoor requires write mode.
open_door: true
open_door_user: relay-user
open_door_password: relay-password
```

```yaml
# Rejected: OpenDoor requires both relay credentials.
write: true
open_door: true
open_door_user: relay-user
```

### Save the redacted report to a file

```yaml
service: local_akuvox.run_capability_report
target:
  entity_id: lock.front_door
data:
  save_to_file: true
```

With a caller-provided relative name:

```yaml
service: local_akuvox.run_capability_report
target:
  entity_id: lock.front_door
data:
  write: true
  save_to_file: true
  file_name: front-door-write-report.json
```

The file is written below
`<config>/local_akuvox/capability_reports/`, is never overwritten, and contains
the same redacted `report` object returned by the service. The response includes
the config-relative path in `file.path`.

## Use output for upstream `new_device`

Copy the `report` object from the response, or the JSON file contents when
`save_to_file` is enabled, into the `pylocal-akuvox` `new_device` issue template.
The upstream report redacts host, credentials, PINs, card codes, phone numbers,
MAC addresses, IP addresses, and user identifiers; still review the artifact
before posting it publicly.

## Developer verification for Stage 5

Run the smallest targeted commands first, then the full local gate before commit:

```bash
uv run pytest tests/test_services.py tests/test_lock.py tests/test_diagnostics.py -q
uv run pytest tests/ --cov=custom_components.local_akuvox --cov-report=term-missing
uv run ruff check custom_components/ tests/
uv run ruff format --check custom_components/ tests/
uv run mypy custom_components tests
uv run interrogate custom_components tests -vv --fail-under=100
npx --yes aislop@0.12.0 ci --staged
```

If dependency metadata changes, refresh the lock file with `uv lock` and include
pin coverage in tests. Hassfest is required through the repository's GitHub
Actions validation workflow; if Stage 5 adds a supported local hassfest command,
run that command as well. Pre-commit remains the final local gate and must not be
bypassed.

<!-- markdownlint-enable MD013 -->
