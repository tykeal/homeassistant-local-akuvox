<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Contract: Capability Report File Output

**Module**: `custom_components.local_akuvox.lock` or a shared helper if Stage 5
extracts file handling **Type**: Optional service artifact contract **Consumers**:
`local_akuvox.run_capability_report`, Home Assistant users, tests, and upstream
support workflow.

## Inputs

| Input | Source | Contract |
| ----- | ------ | -------- |
| `report` | Upstream `run_capability_report()` return value | Already redacted dictionary; write exactly this value. |
| `save_to_file` | Service data | File output occurs only when true. |
| `file_name` | Service data | Optional relative `.json` path under the report directory. |
| `entry_id` | Target config entry | Used only to generate a default file name; not exposed as a host path. |
| `hass.config.path()` | Home Assistant | Defines the config directory root. |

## Directory and naming

- Base directory: `<config>/local_akuvox/capability_reports/`.
- Response path prefix: `local_akuvox/capability_reports/`.
- Generated name format: `<entry_id>-<YYYYMMDDTHHMMSSffffffZ>.json`.
- Caller-supplied names are resolved relative to the base directory.
- Caller-supplied names may include subdirectories only if the resolved path
  remains under the base directory.
- File names must end with `.json`.
- All validation, parent-directory creation, and existing-target checks complete
  before `_create_device()` or device entry/report execution, so predictable path
  errors cannot happen after network/auth work, write-mode side effects, or
  OpenDoor side effects.

## Path validation

The implementation must reject:

- absolute paths;
- empty paths;
- paths containing `..` segments;
- paths that resolve outside `<config>/local_akuvox/capability_reports/`;
- paths that do not end in `.json`;
- targets that already exist.

Validation errors raise `ServiceValidationError` and must not create a file.
Error messages should mention the invalid field and corrective action without
including raw host paths beyond the config-relative report directory.

## Write behavior

- Create the report directory and any validated subdirectories as needed.
- Serialize with `json.dumps(report, indent=2, sort_keys=True) + "\n"` using
  UTF-8.
- Do not overwrite existing files. Use exclusive file creation
  (`Path.open("x")` or equivalent `O_EXCL`) for the final write, and map a late
  `FileExistsError` from concurrent same-name calls to the same controlled
  no-overwrite service failure.
- Avoid blocking the event loop for file writes; Stage 5 should use Home
  Assistant's executor helper if the implementation performs synchronous path or
  write operations.
- The saved JSON must contain the same `report` value returned in the service
  response, not the response wrapper.

## Response metadata

When writing succeeds, the service response includes:

```json
{
  "file": {
    "path": "local_akuvox/capability_reports/<name>.json"
  }
}
```

The path is config-relative and must not expose absolute host filesystem paths.

## Security and privacy

- Do not write `open_door_password`, integration passwords, PINs, card codes, or
  raw device/user identifiers outside the upstream-redacted report.
- Do not log the report body on success or failure.
- Do not include a raw host path in repairs placeholders or user-facing errors.
- If a write fails after report generation, raise a controlled
  `HomeAssistantError`; do not retry with a broader path or fallback outside the
  config directory.

## Test contract

Stage 5 tests must cover:

- default generated file name and config-relative response path;
- caller-provided relative file name;
- nested relative file name that remains inside the report directory;
- rejection of absolute paths, traversal, non-JSON suffix, empty names, and
  existing targets;
- saved file content equals the returned `report` object;
- write failures do not leak raw host paths or secrets.

<!-- markdownlint-enable MD013 -->
