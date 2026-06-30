# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Constants for the Akuvox integration."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pylocal_akuvox import AuthMethod

DOMAIN: Final = "local_akuvox"
PLATFORMS: Final = ["lock"]

# Webhook config keys
CONF_WEBHOOK_ID: Final = "webhook_id"
CONF_WEBHOOK_ENABLED: Final = "webhook_enabled"

# Webhook event name
EVENT_WEBHOOK_RECEIVED: Final = "local_akuvox_webhook_received"

# Action URL config key prefix
ACTIONURL_PREFIX: Final = "Config.Features.ACTIONURL"

# Action URL keys — maps logical name to device config key
ACTIONURL_KEYS: Final[dict[str, str]] = {
    "RelayATriggered": f"{ACTIONURL_PREFIX}.RelayATriggered",
    "RelayAClosed": f"{ACTIONURL_PREFIX}.RelayAClosed",
    "RelayBTriggered": f"{ACTIONURL_PREFIX}.RelayBTriggered",
    "RelayBClosed": f"{ACTIONURL_PREFIX}.RelayBClosed",
    "InputATriggered": f"{ACTIONURL_PREFIX}.InputATriggered",
    "InputAClosed": f"{ACTIONURL_PREFIX}.InputAClosed",
    "InputBTriggered": f"{ACTIONURL_PREFIX}.InputBTriggered",
    "InputBClosed": f"{ACTIONURL_PREFIX}.InputBClosed",
    "ValidCodeEntered": f"{ACTIONURL_PREFIX}.ValidCodeEntered",
    "InvalidCodeEntered": f"{ACTIONURL_PREFIX}.InvalidCodeEntered",
}

# Action URL enable/method keys
ACTIONURL_ENABLE_KEY: Final = f"{ACTIONURL_PREFIX}.Enable"
ACTIONURL_METHOD_KEY: Final = f"{ACTIONURL_PREFIX}.Method"

# Known event types (from device action URL names)
KNOWN_EVENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "relay_a_triggered",
        "relay_a_closed",
        "relay_b_triggered",
        "relay_b_closed",
        "input_a_triggered",
        "input_a_closed",
        "input_b_triggered",
        "input_b_closed",
        "valid_code_entered",
        "invalid_code_entered",
    }
)

# Event types that trigger coordinator refresh
REFRESH_EVENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "relay_a_triggered",
        "relay_a_closed",
        "relay_b_triggered",
        "relay_b_closed",
        "valid_code_entered",
    }
)

# Service names
SERVICE_LIST_SCHEDULES: Final = "list_schedules"
SERVICE_ADD_SCHEDULE: Final = "add_schedule"
SERVICE_MODIFY_SCHEDULE: Final = "modify_schedule"
SERVICE_DELETE_SCHEDULE: Final = "delete_schedule"
SERVICE_LIST_USERS: Final = "list_users"
SERVICE_ADD_USER: Final = "add_user"
SERVICE_MODIFY_USER: Final = "modify_user"
SERVICE_DELETE_USER: Final = "delete_user"
SERVICE_ADD_USER_SCHEDULE_RELAY: Final = "add_user_schedule_relay"
SERVICE_REMOVE_USER_SCHEDULE_RELAY: Final = "remove_user_schedule_relay"
SERVICE_LIST_CONTACTS: Final = "list_contacts"
SERVICE_ADD_CONTACT: Final = "add_contact"
SERVICE_MODIFY_CONTACT: Final = "modify_contact"
SERVICE_DELETE_CONTACT: Final = "delete_contact"
SERVICE_LIST_GROUPS: Final = "list_groups"
SERVICE_ADD_GROUP: Final = "add_group"
SERVICE_MODIFY_GROUP: Final = "modify_group"
SERVICE_DELETE_GROUP: Final = "delete_group"

# Event names
EVENT_SCHEDULE_CHANGED: Final = "local_akuvox_schedule_changed"
EVENT_USER_CHANGED: Final = "local_akuvox_user_changed"
EVENT_CONTACT_CHANGED: Final = "local_akuvox_contact_changed"
EVENT_GROUP_CHANGED: Final = "local_akuvox_group_changed"

# Config keys
CONF_HOST: Final = "host"
CONF_USE_SSL: Final = "use_ssl"
CONF_VERIFY_SSL: Final = "verify_ssl"
CONF_AUTH_METHOD: Final = "auth_method"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"  # noqa: S105
CONF_REQUEST_DELAY: Final = "request_delay"
DEFAULT_REQUEST_DELAY: Final = 0.25
CONF_ATTEMPT_UNKNOWN_CAPABILITY: Final = "attempt_unknown_capability"
DEFAULT_ATTEMPT_UNKNOWN_CAPABILITY: Final = False

# Repairs issue identifiers
REPAIR_UNSUPPORTED_CAPABILITY_PREFIX: Final = "unsupported"
REPAIR_UNSUPPORTED_CAPABILITY_TRANSLATION_KEY: Final = "unsupported_capability"

# Auth mode constants
AUTH_NONE: Final = "none"
AUTH_BASIC: Final = "basic"
AUTH_DIGEST: Final = "digest"

# Defaults
DEFAULT_SCAN_INTERVAL: Final = 30

# Device config key prefix
CONFIG_KEY_PREFIX: Final = "Config.DoorSetting"

# Device config keys (full dot-separated paths)
CONFIG_KEY_LOCATION: Final = f"{CONFIG_KEY_PREFIX}.DEVICENODE.Location"

# Relay config key patterns — use with relay letter suffix (A, B, etc.)
# Name/HoldDelay: PREFIX.RELAY.{Property}{Letter} (e.g., NameA, HoldDelayA)
CONFIG_KEY_RELAY_NAME: Final = f"{CONFIG_KEY_PREFIX}.RELAY.Name"
CONFIG_KEY_RELAY_HOLD_DELAY: Final = f"{CONFIG_KEY_PREFIX}.RELAY.HoldDelay"
# Type/Mode: PREFIX.RELAY.Relay{Letter}{Property} (e.g., RelayAType, RelayAMode)
CONFIG_KEY_RELAY_PREFIX: Final = f"{CONFIG_KEY_PREFIX}.RELAY.Relay"
CONFIG_KEY_RELAY_TYPE_SUFFIX: Final = "Type"
CONFIG_KEY_RELAY_MODE_SUFFIX: Final = "Mode"

# Relay key pattern — matches "RelayA", "RelayB", etc.
RELAY_KEY_RE: Final = re.compile(r"Relay([A-Z])")

# Device config defaults
DEFAULT_HOLD_DELAY_SECONDS: Final = 5
DEFAULT_RELAY_TYPE: Final = 0
DEFAULT_RELAY_MODE: Final = 0

# Day-of-week name → digit mapping (single source of truth)
DAY_NAME_TO_DIGIT: Final[dict[str, str]] = {
    "sun": "0",
    "mon": "1",
    "tue": "2",
    "wed": "3",
    "thu": "4",
    "fri": "5",
    "sat": "6",
}
VALID_DAYS: Final = list(DAY_NAME_TO_DIGIT.keys())

# Lazy import: AuthMethod lives in pylocal_akuvox and is imported at
# runtime to avoid a top-level heavy dependency in const.py.  The map
# is built once on first call and cached.
_AUTH_METHOD_MAP: dict[str, AuthMethod] | None = None


def get_auth_method_map() -> dict[str, AuthMethod]:
    """Return the AUTH_METHOD_MAP, importing AuthMethod on first use.

    Returns:
        Mapping from string auth constants to AuthMethod enum values.

    """
    global _AUTH_METHOD_MAP  # noqa: PLW0603
    if _AUTH_METHOD_MAP is None:
        from pylocal_akuvox import AuthMethod as _AuthMethod

        _AUTH_METHOD_MAP = {
            AUTH_NONE: _AuthMethod.NONE,
            AUTH_BASIC: _AuthMethod.BASIC,
            AUTH_DIGEST: _AuthMethod.DIGEST,
        }
    return _AUTH_METHOD_MAP
