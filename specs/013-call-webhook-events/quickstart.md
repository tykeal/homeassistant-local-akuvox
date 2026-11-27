<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Quickstart: Call Webhook Events

**Feature**: 013-call-webhook-events

## Developer validation

```bash
uv run pytest tests/ -x -q
uv run ruff check custom_components/ tests/
uv run ruff format --check
uv run pre-commit run --all-files
```

Focused suites:

```bash
uv run pytest tests/test_webhook.py tests/test_config_flow.py \
  tests/test_options_flow.py tests/test_init.py -q
```

## Simulating a call event

With a webhook-enabled entry, send (replace the ID):

```bash
curl "http://<ha>:8123/api/webhook/<webhook_id>?event=call_made&remote=1001"
```

In **Developer Tools → Events**, listen to `local_akuvox_webhook_received`
and confirm `event_type: call_made` and `payload.remote: "1001"`.

## Automation example

```yaml
automation:
  - alias: "Intercom placed a call"
    trigger:
      - platform: event
        event_type: local_akuvox_webhook_received
        event_data:
          event_type: call_made
    action:
      - service: persistent_notification.create
        data:
          message: "Intercom called {{ trigger.event.data.payload.remote }}"
```

## Owner hardware verification (before release; CI must be green first)

1. Upgrade the integration on an instance with a webhook-enabled entry for a
   device exposing `Config.Features.ACTIONURL.MakeCall`/`HangUp`.
2. After load, confirm (debug logs or device web UI) that only the call
   Action URLs were written, then restart and confirm no second write
   (read-back equality).
3. Place an outgoing call from the device; confirm `call_made` with the
   called number in `payload.remote`.
4. Hang up; confirm `call_ended`. Optionally test an incoming call's hang-up.
5. On a device without the keys, confirm no write occurs and existing
   relay/input/code events still arrive.
