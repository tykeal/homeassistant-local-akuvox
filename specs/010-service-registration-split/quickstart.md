<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Quickstart: Service Registration Split

**Feature**: 010-service-registration-split **Date**: 2026-06-18

## Overview

The implementation stage splits
`custom_components/local_akuvox/services.py:async_register_services` into four
private helpers for schedule, user, contact, and group registrations. This is a
pure refactor: no service names, schemas, handlers, responses, or caller
contracts change.

## Development Notes

1. Keep `async_register_services(hass: HomeAssistant) -> None` as `async def`.
1. Add synchronous private helpers named `_register_schedule_services`,
   `_register_user_services`, `_register_contact_services`, and
   `_register_group_services`.
1. Move each `service.async_register_platform_entity_service(...)` block
   mechanically into the matching domain helper.
1. Preserve `SupportsResponse.ONLY` on only these services:
   `SERVICE_LIST_SCHEDULES`, `SERVICE_LIST_USERS`, `SERVICE_LIST_CONTACTS`, and
   `SERVICE_LIST_GROUPS`.
1. Do not change `custom_components/local_akuvox/__init__.py`, schemas,
   constants, tests, or public service behavior.

## How to Verify

```bash
uv run pytest tests/
uv run ruff check custom_components/ tests/
uv run mypy custom_components/local_akuvox/
uv run interrogate custom_components/ tests/
uv run aislop ci --staged
python -c "import ast, pathlib; p=pathlib.Path('custom_components/local_akuvox/services.py'); m=ast.parse(p.read_text()); print([n.end_lineno - n.lineno + 1 for n in m.body if isinstance(n, ast.AsyncFunctionDef) and n.name == 'async_register_services'][0])"
```

Expected results:

- All existing tests pass.
- Ruff, mypy, interrogate, and aislop complete successfully.
- Interrogate remains at 100% docstring coverage for the new helpers.
- `async_register_services` is 80 lines or fewer.
- All 18 Local Akuvox services still register through Home Assistant setup.

## Common Pitfalls

- Do not make the helper functions async; the registration calls are synchronous.
- Do not drop `SupportsResponse.ONLY` from any `list_*` service.
- Do not add a new module for service registration.
- Do not rewrite schemas or handlers while moving registration blocks.
- Do not write `tasks.md` or implementation code during this planning stage.

<!-- markdownlint-enable MD013 -->
