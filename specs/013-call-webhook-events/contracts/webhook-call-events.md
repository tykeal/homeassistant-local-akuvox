<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Contract: Webhook Call Events

**Module**: `custom_components.local_akuvox.webhook.async_handle_webhook`
**Consumers**: Akuvox devices (HTTP GET), Home Assistant automations.

## Requests

| Request | Result |
| ------- | ------ |
| `GET ?event=call_made&remote=1001` | 200, fire `event_type=call_made`, `payload.remote="1001"` |
| `GET ?event=call_ended&remote=1001` | 200, fire `event_type=call_ended`, `payload.remote="1001"` |
| `GET ?event=call_made` | 200, fire with `payload.remote=None` |
| `GET ?event=relay_a_triggered&status=1` | unchanged except `payload.remote=None` |
| `GET ?remote=1001` (no event) | 400; warning log with `remote` redacted |
| `GET ?event=foo&remote=1001` | unchanged unknown handling; sanitized payload keeps `remote` |

## Guarantees

- Call events do not schedule `coordinator.async_refresh()`.
- Call events do not resolve users (no `_resolve_user` call).
- `remote` is never logged at info or above by the handler.
