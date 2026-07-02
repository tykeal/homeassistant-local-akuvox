# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Capability report service schema for the Akuvox integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# aislop-ignore-next-line ai-slop/hallucinated-import -- provided by homeassistant
import voluptuous as vol  # provided by homeassistant
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_REPORT_FILE_NAME,
    CONF_REPORT_OPEN_DOOR,
    CONF_REPORT_OPEN_DOOR_PASSWORD,
    CONF_REPORT_OPEN_DOOR_USER,
    CONF_REPORT_SAVE_TO_FILE,
    CONF_REPORT_WRITE,
)

SERVICE_RUN_CAPABILITY_REPORT_SCHEMA = vol.All(
    cv.make_entity_service_schema(
        {
            vol.Optional(CONF_REPORT_WRITE, default=False): cv.boolean,
            vol.Optional(CONF_REPORT_OPEN_DOOR, default=False): cv.boolean,
            vol.Optional(CONF_REPORT_OPEN_DOOR_USER): vol.All(
                cv.string,
                vol.Length(min=1),
            ),
            vol.Optional(CONF_REPORT_OPEN_DOOR_PASSWORD): vol.All(
                cv.string,
                vol.Length(min=1),
            ),
            vol.Optional(CONF_REPORT_SAVE_TO_FILE, default=False): cv.boolean,
            vol.Optional(CONF_REPORT_FILE_NAME): vol.All(cv.string, vol.Length(min=1)),
        },
    ),
    lambda value: _validate_report_service_data(value),
)


def _validate_report_service_data(value: dict[str, Any]) -> dict[str, Any]:
    """Validate cross-field capability report service requirements."""
    save_to_file = bool(value[CONF_REPORT_SAVE_TO_FILE])

    if open_door_error := report_open_door_validation_error(value):
        path, message = open_door_error
        raise vol.Invalid(message, path=[path])
    if not save_to_file and CONF_REPORT_FILE_NAME in value:
        raise vol.Invalid(
            "file_name requires save_to_file=True",
            path=[CONF_REPORT_FILE_NAME],
        )
    return value


def report_open_door_validation_error(
    value: Mapping[str, Any],
) -> tuple[str, str] | None:
    """Return the first unsafe OpenDoor option error, if any."""
    write = bool(value.get(CONF_REPORT_WRITE, False))
    open_door = bool(value.get(CONF_REPORT_OPEN_DOOR, False))
    open_door_user = value.get(CONF_REPORT_OPEN_DOOR_USER)
    open_door_password = value.get(CONF_REPORT_OPEN_DOOR_PASSWORD)

    if open_door and not write:
        return CONF_REPORT_OPEN_DOOR, "open_door requires write=True"
    if open_door and open_door_user is None:
        return (
            CONF_REPORT_OPEN_DOOR_USER,
            "open_door_user is required when open_door=True",
        )
    if open_door and open_door_password is None:
        return (
            CONF_REPORT_OPEN_DOOR_PASSWORD,
            "open_door_password is required when open_door=True",
        )
    if not open_door and (open_door_user is not None or open_door_password is not None):
        return CONF_REPORT_OPEN_DOOR, "OpenDoor credentials require open_door=True"
    return None
