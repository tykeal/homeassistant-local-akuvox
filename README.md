<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Local Akuvox Integration for Home Assistant

[![HACS][hacs-badge]][hacs-url]
[![GitHub Release][release-badge]][release-url]
[![License][license-badge]][license-url]
[![Build Status][build-badge]][build-url]

A [Home Assistant](https://www.home-assistant.io/) custom integration for
locally controlling [Akuvox](https://www.akuvox.com/) intercoms and access
control devices. All communication happens over your local network — no
cloud services required.

## Features

- **Lock Entities** — One lock entity per relay on your device. Unlock
  doors and gates directly from Home Assistant.
- **Webhook Events** — Receive real-time notifications when relays
  trigger, codes are entered, or inputs change state.
- **User & Schedule Management** — Full CRUD services for managing
  access codes, user PINs, card codes, and time-based schedules.
- **Local Polling** — Device state updates every 30 seconds via direct
  HTTP communication.
- **Flexible Authentication** — Supports no-auth (IP allowlist), HTTP
  Basic, and HTTP Digest authentication.
- **SSL Support** — Optional HTTPS with configurable certificate
  verification.

## Requirements

- Home Assistant 2026.7.0 or later
- An Akuvox intercom or access control device with HTTP API access
  (e.g., E21V, R29, or similar models)
- Network connectivity between Home Assistant and the device

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant.
2. Go to **Integrations** → click the three-dot menu → **Custom
   repositories**.
3. Add `https://github.com/tykeal/homeassistant-local-akuvox` with
   category **Integration**.
4. Search for "Local Akuvox" and install it.
5. Restart Home Assistant.

### Manual

1. Download the latest release from the
   [releases page][release-url].
2. Copy the `custom_components/local_akuvox` directory into your Home
   Assistant `config/custom_components/` directory.
3. Restart Home Assistant.

## Configuration

### Adding the Integration

1. Go to **Settings** → **Devices & Services** → **Add Integration**.
2. Search for **Local Akuvox**.
3. Follow the setup wizard:

| Step                   | Description                                     |
| ---------------------- | ----------------------------------------------- |
| **Device Connection**  | Enter the IP/hostname and whether to use SSL.   |
| **SSL Options**        | Choose whether to verify the SSL certificate.   |
| **Authentication**     | Select: None / AllowList, Basic, or Digest.     |
| **Credentials**        | Enter username and password (if required).      |
| **Webhook Events**     | Optionally enable webhook event delivery.       |

### Reconfiguration

Go to **Settings** → **Devices & Services** → **Local Akuvox** →
**Configure**
to update connection settings, authentication, or webhook configuration
at any time.

## Entities

### Lock

One `lock` entity is created for each relay on the device (e.g., Relay
A, Relay B). Each lock entity supports:

| Action     | Description                                              |
| ---------- | -------------------------------------------------------- |
| **Unlock** | Triggers the relay for the configured hold duration.     |
| **Lock**   | Not supported — relay closure depends on device config.  |

Entity names are derived from the device configuration. If a relay has
a custom name configured on the device, that name is used.

## Webhook Events

When webhooks are enabled, the integration configures your Akuvox device
to send event notifications to Home Assistant. Events are fired on the
Home Assistant event bus as `local_akuvox_webhook_received`.

### Listening for Events

Use **Developer Tools** → **Events** → **Listen to events** and enter
`local_akuvox_webhook_received` to monitor incoming webhooks.

You can also use these events in automations:

```yaml
automation:
  - alias: "Notify on door unlock"
    trigger:
      - platform: event
        event_type: local_akuvox_webhook_received
        event_data:
          event_type: relay_a_triggered
    action:
      - service: notify.mobile_app
        data:
          message: "Front door was unlocked!"
```

### Known Event Types

| Event Type             | Description                              |
| ---------------------- | ---------------------------------------- |
| `relay_a_triggered`    | Relay A was activated (door opened).     |
| `relay_a_closed`       | Relay A returned to closed state.        |
| `relay_b_triggered`    | Relay B was activated.                   |
| `relay_b_closed`       | Relay B returned to closed state.        |
| `input_a_triggered`    | Input A was triggered.                   |
| `input_a_closed`       | Input A returned to closed state.        |
| `input_b_triggered`    | Input B was triggered.                   |
| `input_b_closed`       | Input B returned to closed state.        |
| `valid_code_entered`   | A valid PIN or card code was entered.    |
| `invalid_code_entered` | An invalid PIN or card code was entered. |

Unrecognized events from the device are emitted as
`unknown_<normalized_name>` with sanitized query parameters (sensitive
fields such as `code` are redacted) as the payload.

### Event Payload

```json
{
  "device_id": "ha_device_registry_id",
  "config_entry_id": "ha_config_entry_id",
  "event_type": "relay_a_triggered",
  "payload": {
    "event": "relay_a_triggered",
    "status": "1",
    "device_user_id": "42",
    "user_id": "john.doe",
    "username": "John Doe"
  }
}
```

| Field                    | Description                              |
| ------------------------ | ---------------------------------------- |
| `device_id`              | HA device registry ID (may be null).     |
| `config_entry_id`        | Home Assistant config entry ID.          |
| `event_type`             | Normalized event type string.            |
| `payload.event`          | Event name from webhook query param.     |
| `payload.status`         | Relay status (null for code events).     |
| `payload.device_user_id` | Device-internal user ID (code events).   |
| `payload.user_id`        | External user identifier (code events).  |
| `payload.username`       | Display name of the user (code events).  |

> **Note:** User identity fields (`device_user_id`, `user_id`,
> `username`) are populated from a local cache and may be `null` on
> first use. The cache refreshes automatically.
>
> **Security:** Raw PIN codes are never included in event payloads.
> Only the resolved user identity is emitted.

## Services

All services target lock entities belonging to this integration. Call
them via **Developer Tools** → **Services** or from automations and
scripts.

### Schedule Management

| Service                            | Description                    |
| ---------------------------------- | ------------------------------ |
| `local_akuvox.list_schedules`      | Retrieve all access schedules. |
| `local_akuvox.add_schedule`        | Create a new access schedule.  |
| `local_akuvox.modify_schedule`     | Update an existing schedule.   |
| `local_akuvox.delete_schedule`     | Remove a schedule.             |

**Schedule types** (`schedule_type` must be a string):

- `"0"` — Date Range (specific start/end dates)
- `"1"` — Weekly (selected days of the week)
- `"2"` — Daily (every day)

### User Management

| Service                                   | Description               |
| ----------------------------------------- | ------------------------- |
| `local_akuvox.list_users`                 | Retrieve all user codes.  |
| `local_akuvox.add_user`                   | Create a user (PIN/card). |
| `local_akuvox.modify_user`                | Update an existing user.  |
| `local_akuvox.delete_user`                | Remove a user.            |
| `local_akuvox.add_user_schedule_relay`    | Assign schedule-relay.    |
| `local_akuvox.remove_user_schedule_relay` | Remove schedule-relay.    |

### Example: Add a User with PIN Access

```yaml
service: local_akuvox.add_user
target:
  entity_id: lock.local_akuvox_front_gate
data:
  name: "Jane Doe"
  schedules: "10, 20"
  lift_floor_num: "3"
  private_pin: "5678"
```

## Troubleshooting

### Cannot connect to device

- Verify the device IP address is correct and reachable from your
  Home Assistant host.
- Check that the HTTP API is enabled on the device.
- If using authentication, confirm the credentials are correct.
- If using SSL, try disabling certificate verification to rule out
  certificate issues.

### Webhook events not received

- Ensure your Home Assistant instance is accessible from the device's
  network.
- Check that webhooks are enabled in the integration options.
- Verify the device's action URL configuration points to the correct
  Home Assistant webhook URL.
- Use HTTPS/TLS for webhook URLs. `valid_code_entered` webhooks
  include the entered PIN in the query string; using HTTP transmits
  it in plaintext. Only use HTTP on a trusted network for testing.

### Lock entity shows unknown state

- The device may not have responded to the initial status poll. Wait
  for the next polling interval (30 seconds).
- Check Home Assistant logs for connection errors.

### Cloud-provisioned users or schedules

Users and schedules provisioned via Akuvox cloud services cannot be
modified or deleted through this integration. The integration will
return a clear error message when this is attempted.

## License

This project is licensed under the Apache License 2.0. See the
[LICENSE](LICENSE) file for details. This project follows the
[REUSE specification](https://reuse.software/) for license compliance.

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[hacs-url]: https://hacs.xyz/
[release-badge]: https://img.shields.io/github/v/release/tykeal/homeassistant-local-akuvox
[release-url]: https://github.com/tykeal/homeassistant-local-akuvox/releases
[license-badge]: https://img.shields.io/github/license/tykeal/homeassistant-local-akuvox
[license-url]: https://github.com/tykeal/homeassistant-local-akuvox/blob/main/LICENSE
[build-badge]: https://img.shields.io/github/actions/workflow/status/tykeal/homeassistant-local-akuvox/build-test.yaml?branch=main
[build-url]: https://github.com/tykeal/homeassistant-local-akuvox/actions/workflows/build-test.yaml
