<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

<!-- markdownlint-disable MD013 -->

# Data Model: Call Webhook Events

**Feature**: 013-call-webhook-events **Date**: 2026-11-27

## Optional Action URL keys (`const.OPTIONAL_ACTIONURL_KEYS`)

| Logical name | Device config key | URL template (`webhook._URL_TEMPLATES`) | Event type |
| ------------ | ----------------- | --------------------------------------- | ---------- |
| `MakeCall` | `Config.Features.ACTIONURL.MakeCall` | `?event=call_made&remote=$remote` | `call_made` |
| `HangUp` | `Config.Features.ACTIONURL.HangUp` | `?event=call_ended&remote=$remote` | `call_ended` |

Ordering is stable (`MakeCall`, then `HangUp`) and follows the base keys in
generated payloads.

## Event type sets

| Set | Change |
| --- | ------ |
| `KNOWN_EVENT_TYPES` | add `call_made`, `call_ended` |
| `REFRESH_EVENT_TYPES` | unchanged |

## Supported optional keys

`frozenset[str]` of logical names (subset of `OPTIONAL_ACTIONURL_KEYS`) whose
device config key is present in the device's `DeviceConfig`. Empty when
detection fails or the input is not a container.

## Action URL payloads

Given `url = async_generate_url(hass, webhook_id, allow_external=True, allow_internal=True)`
and `S = optional_keys ∩ OPTIONAL_ACTIONURL_KEYS`:

| Payload | Keys |
| ------- | ---- |
| enable | `Enable="1"`, `Method=""`, 10 base keys → `url+template`, each `k∈S` → `url+template` |
| disable | `Enable="0"`, `Method=""`, 10 base keys → `""`, each `k∈S` → `""` |

With `S = ∅` both payloads are identical to the pre-feature payloads.

## Reconciliation write set

For each logical name `k ∈ supported(device_config)`:
`expected[k] = enable_payload[config_key(k)]`; include `config_key(k) →
expected[k]` in the write set iff `device_config.get(config_key(k)) !=
expected[k]`. If the write set is empty, no write occurs.

## Fired event data (`local_akuvox_webhook_received`)

Known events (including call events):

```json
{
  "device_id": "ha_device_registry_id",
  "config_entry_id": "ha_config_entry_id",
  "event_type": "call_made",
  "payload": {
    "event": "call_made",
    "status": null,
    "remote": "1001",
    "device_user_id": null,
    "user_id": null,
    "username": null
  }
}
```

| Field | Change |
| ----- | ------ |
| `payload.remote` | **new**; `remote` query parameter or `null`. Present on all known events. |
| other fields | unchanged |

Unknown events: unchanged (sanitized query parameters, which naturally
preserve `remote`).

## State transitions

| Trigger | Webhook enabled | Device exposes keys | Action |
| ------- | --------------- | ------------------- | ------ |
| Config flow enable | → true | yes / no / read fails | push base + exposed / base / base |
| Options toggle on | false → true | same as above | push enable payload |
| Options toggle off | true → false | yes / no / read fails | push disable incl. exposed / base / base |
| Entry load | true + id | yes, values differ | write differing call keys only |
| Entry load | true + id | yes, values match / no | no write |
| Entry load | false or no id | — | nothing |
| Entry removal | true + id | yes / no / read fails | disable incl. exposed / base / base |

<!-- markdownlint-enable MD013 -->
