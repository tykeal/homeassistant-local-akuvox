<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Tasks: Call Webhook Events

**Input**: Design documents from `/specs/013-call-webhook-events/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
quickstart.md, and contracts/

**Tests**: Required. The constitution mandates code-level TDD, so each
behavior change is preceded by a failing test in the named test file.
Coverage must remain at 100% (`fail_under = 100`).

**Organization**: Tasks are dependency-ordered and grouped by user story.
The MVP is US1 (call events dispatched by the webhook handler); US2 gates
the device payload on detected keys; US3 upgrades existing devices at
load. Polish covers docs, the release note, and full validation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel after prerequisites (different files or
  independent checks).
- **[Story]**: User story from `spec.md` (US1, US2, US3) or cross-cutting
  work (no label).
- Each task names exact paths and maps to functional requirements (FR) and
  success criteria (SC).

## Path Conventions

- **Integration**: `custom_components/local_akuvox/`
- **Tests**: `tests/`
- **Spec docs**: `specs/013-call-webhook-events/`

______________________________________________________________________

## Phase 1: Foundation (constants, templates, payload builder)

**Purpose**: Define the optional keys and make `build_action_urls()`
capable of including them without changing the default payload.

### Tests (Phase 1)

- [X] T001 [P] Add failing tests in `tests/test_webhook.py` asserting
  `OPTIONAL_ACTIONURL_KEYS` maps `MakeCall`/`HangUp` to
  `Config.Features.ACTIONURL.MakeCall`/`.HangUp`, that `call_made` and
  `call_ended` are in `KNOWN_EVENT_TYPES` and not in
  `REFRESH_EVENT_TYPES`, and that the templates are
  `?event=call_made&remote=$remote` and
  `?event=call_ended&remote=$remote`. Covers FR-001 through FR-003.
- [X] T002 Add failing tests in `tests/test_webhook.py` for
  `build_action_urls(..., optional_keys=...)`: default/empty → payloads
  identical to today's (10 base keys + `Enable`/`Method`); both keys →
  12 URLs in enable and 12 blanks in disable; one key → only that key;
  unrecognized names ignored. Covers FR-006, SC-001, SC-002.

### Implementation (Phase 1)

- [X] T003 Add `OPTIONAL_ACTIONURL_KEYS` and the two event types to
  `custom_components/local_akuvox/const.py` (not to
  `REFRESH_EVENT_TYPES`). Covers FR-001, FR-003.
- [X] T004 Add `MakeCall`/`HangUp` entries to `_URL_TEMPLATES` and the
  keyword-only `optional_keys: Collection[str] = ()` parameter to
  `build_action_urls()` in `custom_components/local_akuvox/webhook.py`,
  appending supported optional keys in `OPTIONAL_ACTIONURL_KEYS` order.
  Covers FR-002, FR-006.

**Checkpoint**: `uv run pytest tests/test_webhook.py -q` green; no other
test changes required.

______________________________________________________________________

## Phase 2: User Story 1 — Receive Call Events (P1, MVP)

**Goal**: Handler fires `call_made`/`call_ended` with `payload.remote`.

### Tests (Phase 2)

- [X] T005 [P] [US1] Add failing handler tests in `tests/test_webhook.py`:
  `?event=call_made&remote=1001` and `?event=call_ended&remote=1001` fire
  `local_akuvox_webhook_received` with the right `event_type` and
  `payload.remote == "1001"`; missing `remote` → `None`; no
  `coordinator.async_refresh` scheduled and no user lookup; existing
  relay event payload now includes `remote: None` with other fields
  unchanged. Covers FR-003, FR-004, US1 scenarios 1–4.
- [X] T006 [US1] Add a failing test in `tests/test_webhook.py` that a
  request with `remote` but no `event` returns 400 and the warning log
  does not contain the `remote` value. Covers FR-005.

### Implementation (Phase 2)

- [X] T007 [US1] In `async_handle_webhook`
  (`custom_components/local_akuvox/webhook.py`) add
  `"remote": query_params.get("remote")` to the known-event payload and
  redact `remote` (e.g. `"[REDACTED]"`) in the sanitized parameters
  logged by the missing-`event` warning. Covers FR-004, FR-005.

**Checkpoint**: US1 tests green; full `tests/test_webhook.py` green.

______________________________________________________________________

## Phase 3: User Story 2 — Capability-Gated Configuration (P1)

**Goal**: Flows and removal include call keys only when the device
exposes them; any detection failure falls back to the base payload.

### Tests (Phase 3)

- [X] T008 [P] [US2] Add failing unit tests in `tests/test_webhook.py` for
  `supported_optional_action_url_keys()` (both, one, none, `DeviceConfig`
  and plain `dict` inputs, `None`/non-container → empty) and
  `async_detect_optional_action_url_keys()` (missing/non-callable
  `get_device_config`, `AkuvoxUnsupportedError`, generic exception,
  success). Covers FR-007, FR-008.
- [X] T009 [P] [US2] Add failing tests in `tests/test_config_flow.py`:
  webhook enable with a device config containing both call keys pushes a
  payload including both call URLs; without the keys pushes exactly the
  base payload; `get_device_config` raising still pushes the base payload
  and creates the entry. Covers FR-009, US2 scenarios 1–4.
- [X] T010 [P] [US2] Add failing tests in `tests/test_options_flow.py`:
  toggling webhook on with keys present includes call URLs; toggling off
  with keys present blanks them; keys absent or read failure → base
  enable/disable payload; build failure still returns
  `webhook_push_failed`. Covers FR-010, US2 scenarios 1–5.
- [X] T011 [P] [US2] Add failing tests in `tests/test_init.py` for
  `async_remove_entry`: keys present → disable payload blanks call keys;
  keys absent or read failure → base disable payload. Covers FR-011,
  US2 scenario 5.

### Implementation (Phase 3)

- [X] T012 [US2] Add `supported_optional_action_url_keys()` and
  `async_detect_optional_action_url_keys()` to
  `custom_components/local_akuvox/webhook.py` per
  `contracts/action-url-payload.md` (debug logs only, no URLs or config
  values). Covers FR-007, FR-008, FR-016.
- [X] T013 [US2] Update `ConfigFlow._async_push_webhook_config` in
  `custom_components/local_akuvox/config_flow.py` to detect on the
  entered session after `apply_capability_options()` and pass
  `optional_keys` to `build_action_urls()`. Covers FR-009.
- [X] T014 [US2] Update `_async_handle_webhook_change` in
  `custom_components/local_akuvox/options_flow.py` the same way, keeping
  every failure mapped to `webhook_push_failed`. Covers FR-010.
- [X] T015 [US2] Update `async_remove_entry` in
  `custom_components/local_akuvox/__init__.py` to detect before building
  the disable payload (`warn_http=False`). Covers FR-011.
- [X] T016 [US2] Adjust existing tests in `tests/test_config_flow.py`,
  `tests/test_options_flow.py`, and `tests/test_init.py` where the
  build-inside-session ordering changes call expectations. In particular,
  `test_options_webhook_url_build_failure_shows_error` in
  `tests/test_options_flow.py` must also patch `options_flow.AkuvoxDevice`
  so it still exercises the URL-build failure (not a network failure), and
  the config-flow and removal build-failure cases must likewise use a
  mocked device session.

**Checkpoint**: Focused suites green; payloads for devices without keys
unchanged (SC-002).

______________________________________________________________________

## Phase 4: User Story 3 — Automatic Upgrade of Existing Devices (P2)

**Goal**: Webhook-enabled entries write differing call URLs at load
without ever blocking setup.

### Tests (Phase 4)

- [X] T017 [US3] Add failing unit tests in `tests/test_webhook.py` for
  `async_reconcile_optional_action_urls()`: values differ → one
  `set_device_config` call containing only differing call keys (no
  `Enable`/`Method`/base keys); values match → no write; keys missing →
  no write; `get_device_config` not callable → no write;
  `AkuvoxUnsupportedError` on read and on write → reported via
  `async_report_unsupported_capability`, no raise; generic exception on
  read, URL generation, or write → warning without URL, no raise; HTTP
  warning not emitted; info log contains masked webhook ID only.
  Covers FR-013 through FR-016, SC-003.
- [X] T018 [P] [US3] Add failing setup tests in `tests/test_init.py`:
  webhook enabled + ID → reconciliation scheduled after platform setup
  and writes differing keys (use
  `hass.async_block_till_done(wait_background_tasks=True)`); webhook
  disabled or ID missing → no reconciliation read/write; reconciliation
  error → entry state `LOADED`; unload while reconciliation is blocked
  cancels the task before `device.__aexit__`; `async_forward_entry_setups`
  raising → no reconciliation scheduled. Covers FR-012, FR-015,
  SC-004, US3 scenarios 1–5.

### Implementation (Phase 4)

- [X] T019 [US3] Add `async_reconcile_optional_action_urls()` to
  `custom_components/local_akuvox/webhook.py` per
  `contracts/reconciliation.md`, splitting the diff computation into a
  pure helper if needed for C901. Covers FR-013 through FR-016.
- [X] T020 [US3] Add `action_url_reconcile_task: asyncio.Task[None] |
  None = None` to `AkuvoxDataUpdateCoordinator` in
  `custom_components/local_akuvox/coordinator.py`. Covers FR-012.
- [X] T021 [US3] In `async_setup_entry`
  (`custom_components/local_akuvox/__init__.py`), after
  `async_forward_entry_setups()` succeeds and only when webhook is
  enabled with an ID, schedule the task via
  `entry.async_create_background_task()` and store it on the
  coordinator; in `async_unload_entry`, cancel an unfinished task and
  `await asyncio.wait({task})` before closing the device. Covers FR-012,
  FR-015.

**Checkpoint**: Full `uv run pytest tests/ -x -q` green at 100% coverage.

______________________________________________________________________

## Phase 5: Polish & Cross-Cutting

- [X] T022 [P] Update `README.md` "Webhook Events" and
  `wiki/Webhook-Events.md`: add `call_made`/`call_ended` rows (note
  `call_ended` may also fire for incoming calls), `payload.remote` in the
  payload example/field table, a call automation example, and a note that
  call events are configured only on devices exposing the keys and that
  existing webhook-enabled devices are upgraded automatically at load.
  Covers FR-017.
- [X] T023 [P] Add a Reno release note under `releasenotes/notes/`
  (`uv run reno new call-webhook-events` or equivalent) with a
  `features` entry describing the events, capability gating, and
  automatic upgrade, and an `upgrade` entry about the one-time call URL
  write on load. Covers FR-018.
- [X] T024 Run `uv run pytest tests/ -x -q`,
  `uv run ruff check custom_components/ tests/`,
  `uv run ruff format --check`, and
  `uv run pre-commit run --all-files`; fix any findings. Covers SC-005.
- [X] T025 Mark tasks complete in this file in a separate
  `Docs(tasks): Mark 013 task list complete` commit.

______________________________________________________________________

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5.
- Within each phase, tests (T001–T002, T005–T006, T008–T011, T017–T018)
  precede their implementation tasks.
- T012 precedes T013–T015 and T019. T020 precedes T021.
- T022 and T023 may run in parallel with each other after Phase 4.

## Commit Plan (implementation PR)

1. `Feat(webhook): Add capability-gated call events` — code and tests
   (T001–T021), body `Closes #330`.
2. `Docs(webhook): Document call webhook events` — README, wiki, release
   note (T022–T023).
3. `Docs(tasks): Mark 013 task list complete` — this file only (T025).
