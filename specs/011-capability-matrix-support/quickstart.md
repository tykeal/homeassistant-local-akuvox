<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Quickstart: Capability Matrix Support

## Automated validation

Run from the repository root after Stage 5 implementation changes:

```bash
uv run pytest --cov=custom_components.local_akuvox --cov-report=term-missing tests/
uv run ruff check custom_components/ tests/
uv run ruff format --check custom_components/ tests/
uv run mypy custom_components tests
uv run interrogate -vv --fail-under=100 custom_components tests
npx --yes aislop@0.12.0 ci
uv run pre-commit run --all-files
```

Expected results:

- pytest passes with 100% coverage;
- ruff reports no lint or format findings;
- mypy reports no type errors;
- interrogate reports 100% docstring coverage;
- aislop reports no findings below failBelow 100;
- pre-commit, including reuse, markdownlint, gitlint, and the mypy hook, passes.

## Dependency verification

Confirm all dependency surfaces require v1.0.0 or newer:

```bash
grep -R "pylocal-akuvox>=1.0.0" \
  custom_components/local_akuvox/manifest.json \
  pyproject.toml \
  .pre-commit-config.yaml
uv lock --check
```

`uv.lock` should resolve `pylocal-akuvox` consistently with the new minimum.

## Manual supported-device path

1. Install the implementation build in Home Assistant.
2. Configure a curated device whose relay, config, schedule, user, contact, and
   group capabilities are `SUPPORTED` for the operations being tested.
3. Leave **Attempt unknown capabilities** disabled.
4. Complete setup, including optional webhook configuration.
5. Confirm setup succeeds, lock entities are available, relay state refreshes,
   lock/unlock actions work, and existing schedule/user/contact/group services
   behave as they did before the dependency upgrade.
6. Download diagnostics and confirm the current capability snapshot is present
   without credentials, PINs, card codes, or raw webhook ids.

## Manual unrecognized-device path

1. Mock or use a device/firmware combination that v1.0.0 maps to the conservative
   empty profile with `device_not_in_matrix` and `UNKNOWN` capability statuses.
2. Complete setup with **Attempt unknown capabilities** disabled.
3. Trigger a gated operation such as webhook config push, relay action, or a
   registered entity service.
4. Confirm Home Assistant shows a deduplicated repairs issue with
   `reason="device_unrecognized"`, explains the breaking change, and tells the
   user how to enable the opt-in.
5. Enable **Attempt unknown capabilities** in options and reload.
6. Confirm `device.attempt_unknown_capability` is set after context entry and
   `UNKNOWN` operations are attempted while real network/auth/parse/device errors
   still surface normally.
7. Trigger a webhook PIN lookup cache miss and confirm the background
   `USER_LIST` refresh reports unsupported capability details without blocking
   the webhook response.

## Manual unsupported-capability path

1. Mock a curated profile where a capability is `UNSUPPORTED`, such as
   `RELAY_STATUS`, `RELAY_TRIGGER_API` for lock actions, or
   `CONTACT_ADD`.
2. Confirm entity setup/availability follows the capability rules: unsupported
   relay status does not expose usable relay locks, and unsupported API trigger
   support prevents lock/unlock actions even if FCGI evidence exists without
   credentialed Open Relay Via HTTP support.
3. Invoke the corresponding service path.
4. Confirm the integration logs `.reason` and `.capability`, creates or updates a
   repairs issue, and returns a controlled Home Assistant error instead of an
   uncaught `AkuvoxUnsupportedError`.
5. Enable **Attempt unknown capabilities** and repeat to verify confirmed
   `UNSUPPORTED` capabilities still do not dispatch.

## Diagnostics probe path

1. Open Home Assistant diagnostics for the config entry.
2. Confirm diagnostics include the current capability snapshot.
3. Confirm the user-triggered diagnostics probe calls
   `device.probe_capabilities(timeout=5.0)` or the selected bounded timeout.
4. Confirm successful probe data is sanitized and merged into diagnostics.
5. Simulate probe auth, connection, parse, or unsupported failures and confirm
   diagnostics record safe error context without breaking the integration.

## Release-note verification

The implementation PR must be categorized as a breaking change in release
drafter and include release text covering:

- `pylocal-akuvox>=1.0.0` requirement;
- the new `/api/system/info` context-entry request;
- unrecognized devices failing gated calls by default;
- the **Attempt unknown capabilities** mitigation;
- confirmed `UNSUPPORTED` capabilities remaining blocked;
- diagnostics/probe guidance for upstream matrix updates.

<!-- markdownlint-enable MD013 -->
