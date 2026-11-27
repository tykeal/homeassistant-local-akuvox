<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Webhook Events

When webhooks are enabled during [Configuration](Configuration),
the integration configures your Akuvox device to send real-time
event notifications to Home Assistant. Events are fired on the
Home Assistant event bus as `local_akuvox_webhook_received`.

## Enabling Webhooks

Webhooks are configured during the setup wizard or through
reconfiguration. The integration automatically registers a
webhook URL with the device. See [Device Setup](Device-Setup)
for prerequisite HTTP API configuration.

## Listening for Events

Open **Developer Tools** → **Events** → **Listen to events** and
enter `local_akuvox_webhook_received` to monitor incoming events.

### Automation Example

```yaml
automation:
  - alias: "Notify on door unlock"
    trigger:
      - platform: event
        event_type: local_akuvox_webhook_received
        event_data:
          event_type: relay_a_triggered
    action:
      - service: persistent_notification.create
        data:
          title: "Door unlocked"
          message: "Front door relay was triggered!"
```

## Known Event Types

| Event Type             | Description                                |
| ---------------------- | ------------------------------------------ |
| `relay_a_triggered`    | Relay A activated (unlock requested).      |
| `relay_a_closed`       | Relay A returned to closed state.          |
| `relay_b_triggered`    | Relay B was activated.                     |
| `relay_b_closed`       | Relay B returned to closed state.          |
| `input_a_triggered`    | Input A was triggered.                     |
| `input_a_closed`       | Input A returned to closed state.          |
| `input_b_triggered`    | Input B was triggered.                     |
| `input_b_closed`       | Input B returned to closed state.          |
| `valid_code_entered`   | A valid PIN or card code was entered.      |
| `invalid_code_entered` | An invalid PIN or card code was entered.   |
| `call_made`            | The device placed an outgoing call.¹       |
| `call_ended`           | The device hung up a call.¹                |

¹ Call events are only configured on devices whose configuration
exposes the `MakeCall`/`HangUp` Action URL keys; other devices keep
the relay, input and code events only. `call_ended` may also fire for
incoming calls. `payload.remote` holds the other party's SIP or IP
number. When Home Assistant loads the integration with webhooks
enabled, any missing or outdated call URLs are written to the device
automatically; up-to-date devices are not rewritten.

Example — notify when the intercom places a call:

```yaml
automation:
  - alias: "Intercom call placed"
    trigger:
      - platform: event
        event_type: local_akuvox_webhook_received
        event_data:
          event_type: call_made
    action:
      - service: persistent_notification.create
        data:
          title: "Intercom call"
          message: "Calling {{ trigger.event.data.payload.remote }}"
```

Unrecognized events from the device are emitted as
`unknown_<normalized_name>` with sanitized query parameters
(sensitive fields such as `code` are redacted) as the payload.

## Event Payload

```json
{
  "device_id": "ha_device_registry_id",
  "config_entry_id": "ha_config_entry_id",
  "event_type": "relay_a_triggered",
  "payload": {
    "event": "relay_a_triggered",
    "status": "1",
    "remote": null,
    "device_user_id": "42",
    "user_id": "john.doe",
    "username": "John Doe"
  }
}
```

### Payload Fields

| Field                    | Description                              |
| ------------------------ | ---------------------------------------- |
| `device_id`              | HA device registry ID (may be null).     |
| `config_entry_id`        | Home Assistant config entry ID.          |
| `event_type`             | Normalized event type string.            |
| `payload.event`          | Event name from webhook query param.     |
| `payload.status`         | Relay status (null for code events).     |
| `payload.remote`         | Remote party number (call events).       |
| `payload.device_user_id` | Device-internal user ID (code events).   |
| `payload.user_id`        | External user identifier (code events).  |
| `payload.username`       | Display name of the user (code events).  |

> **Note:** User identity fields (`device_user_id`, `user_id`,
> `username`) are populated from a local cache and may be `null`
> on first use. The cache refreshes automatically.
>
> **Security:** Raw PIN codes are never included in event
> payloads. Only the resolved user identity is emitted.

## Integration Events

In addition to device webhook events, the integration fires
events on the Home Assistant event bus when contacts or groups
are modified through services.

### `local_akuvox_contact_changed`

Fired when contacts are added, modified, or deleted via
services.

**Event data payloads:**

Add:

```json
{
  "action": "add",
  "config_entry_id": "ha_config_entry_id"
}
```

Modify:

```json
{
  "action": "modify",
  "contact_id": "42",
  "config_entry_id": "ha_config_entry_id"
}
```

Delete:

```json
{
  "action": "delete",
  "contact_ids": ["42", "43"],
  "config_entry_id": "ha_config_entry_id"
}
```

### `local_akuvox_group_changed`

Fired when groups are added, modified, or deleted via
services.

**Event data payloads:**

Add:

```json
{
  "action": "add",
  "config_entry_id": "ha_config_entry_id"
}
```

Modify:

```json
{
  "action": "modify",
  "group_id": "5",
  "config_entry_id": "ha_config_entry_id"
}
```

Delete:

```json
{
  "action": "delete",
  "group_id": "5",
  "config_entry_id": "ha_config_entry_id"
}
```

### Integration Event Automation Example

```yaml
automation:
  - alias: "Refresh contacts panel on change"
    trigger:
      - platform: event
        event_type: local_akuvox_contact_changed
    action:
      - service: persistent_notification.create
        data:
          title: "Contact list updated"
          message: >
            Action: {{ trigger.event.data.action }}
```
