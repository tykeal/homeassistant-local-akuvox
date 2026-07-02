<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Data Model: Capability Report Service

**Feature**: 012-capability-report-service **Date**: 2026-07-02

## Service input model

`local_akuvox.run_capability_report` is a lock entity service. Home Assistant
adds the standard entity target through `cv.make_entity_service_schema()`; fields
below are the service-specific data.

| Field | Type | Default | Required | Validation and notes |
| ----- | ---- | ------- | -------- | -------------------- |
| `write` | boolean | `False` | No | Passed unchanged to `pylocal_akuvox.run_capability_report()`. When false, the upstream report probes capabilities and runs read tests only. |
| `open_door` | boolean | `False` | No | Passed unchanged only after validation. If true, Home Assistant must also require `write=True`, `open_door_user`, and `open_door_password` before device entry. |
| `open_door_user` | non-empty string | `None` | Required when `open_door=True` | Relay/OpenDoor HTTP username, separate from integration credentials. Never log from integration code, store, return, save, or include in repairs placeholders. Upstream v1.1.0 debug logs can include this username unless an upstream redaction fix is consumed. |
| `open_door_password` | non-empty string | `None` | Required when `open_door=True` | Relay/OpenDoor HTTP password. Use a password selector in `services.yaml`; never log, store, return, save, or include in repairs placeholders. |
| `save_to_file` | boolean | `False` | No | When true, write the same redacted report dictionary returned in the response to a config-dir JSON file. |
| `file_name` | relative path string ending in `.json` | generated | No | Used only when `save_to_file=True`. Must not be absolute, contain `..`, escape the report directory after resolution, or target an existing file. |

## Validation rules

1. Default call data is safe: `write=False`, `open_door=False`, no relay
   credentials, no file output.
2. `open_door=True` with `write=False` is rejected before device entry.
3. `open_door=True` without both `open_door_user` and `open_door_password` is
   rejected before device entry.
4. `open_door_user` or `open_door_password` with `open_door=False` is rejected
   before device entry so unused relay credentials are not passed to upstream.
5. `open_door_user` and `open_door_password` may be omitted when
   `open_door=False`, including write-mode reports that intentionally skip
   OpenDoor.
6. `file_name` is rejected when `save_to_file=False` so callers cannot believe a
   path was used when no artifact was written.
7. File output paths are always resolved under
   `<config>/local_akuvox/capability_reports/` and returned to users as
   config-relative paths only.

## Upstream call model

```python
await run_capability_report(
    device,
    write=write,
    open_door=open_door,
    open_door_user=open_door_user,
    open_door_password=open_door_password,
    timeout=None,
    redact_stdout=True,
    emit=noop_emit,
)
```

`device` is a fresh `_create_device(entry)` instance entered with `async with`
and updated with `apply_capability_options()` before the call. The service does
not pass a timeout field to users in this feature; `timeout=None` preserves the
upstream default behavior.

## Response output model

Successful calls return a `ServiceResponse` dictionary:

| Key | Type | Present | Meaning |
| --- | ---- | ------- | ------- |
| `report` | object | Always | The exact redacted dictionary returned by `pylocal_akuvox.run_capability_report()`. |
| `file` | object | Only when `save_to_file=True` | Metadata about the saved report artifact. |
| `file.path` | string | With `file` | Config-relative path such as `local_akuvox/capability_reports/<entry>-20260702T140000000000Z.json`. |

## Report dictionary shape

The upstream v1.1.0 `DiagnosticReport.to_json()` contract currently returns:

```json
{
  "device": {
    "class": "<model-or-null>",
    "model": "<model-or-null>",
    "firmware": "<firmware-or-null>",
    "host": "<redacted>"
  },
  "auth": {
    "method": "none|basic|digest|...",
    "ssl": false,
    "verify_ssl": true
  },
  "observed_schemas": {
    "/api/endpoint": ["FieldA", "FieldB"]
  },
  "tests": [
    {
      "name": "list_users",
      "label": "list_users",
      "status": "passed|failed|skipped|inconclusive",
      "capability_status": "supported|unsupported|inconclusive",
      "reason": "<skip-or-failure-reason>",
      "endpoint": "/api/endpoint",
      "request_fields": ["FieldA"],
      "observed_fields": ["FieldB"],
      "failure_shape": {
        "method": "GET",
        "endpoint": "/api/endpoint",
        "http": 404,
        "retcode": -1,
        "retmsg": "<redacted-or-summary>",
        "body_snippet": "<redacted-or-omitted>",
        "request_fields": [],
        "observed_fields": [],
        "exception_class": "AkuvoxRequestError",
        "exception_message": "<redacted-or-summary>"
      },
      "http_events": [
        {
          "method": "GET",
          "endpoint": "/api/endpoint",
          "http": 200,
          "retcode": 0,
          "retmsg": "OK",
          "body_snippet": "<redacted-or-omitted>",
          "request_fields": [],
          "observed_fields": [],
          "exception_class": "AkuvoxParseError",
          "exception_message": "<redacted-or-summary>"
        }
      ]
    }
  ]
}
```

Optional keys inside each test/event are omitted by upstream when values are
`None`. The Home Assistant service must not reshape or manually de-redact the
report. If Stage 5 adds response metadata, it must stay outside the `report`
object.

## File artifact model

| Attribute | Value |
| --------- | ----- |
| Base directory | `<Home Assistant config>/local_akuvox/capability_reports/` |
| Default name | `<entry_id>-<YYYYMMDDTHHMMSSffffffZ>.json` |
| Caller name | Optional relative `.json` path under the base directory |
| Encoding | UTF-8 |
| Format | `json.dumps(report, indent=2, sort_keys=True) + "\n"` |
| Overwrite | Never overwrite existing files |
| Response path | Config-relative, for example `local_akuvox/capability_reports/abc-20260702T140000000000Z.json` |
| Secrets | Same redacted report as response; no OpenDoor password or raw integration credentials |

<!-- markdownlint-enable MD013 -->
