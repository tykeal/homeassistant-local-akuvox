# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Service schemas and registration for the Akuvox integration."""

from __future__ import annotations

# aislop-ignore-next-line ai-slop/hallucinated-import -- provided by homeassistant
import voluptuous as vol  # provided by homeassistant
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import service

from .const import (
    DOMAIN,
    SERVICE_ADD_CONTACT,
    SERVICE_ADD_GROUP,
    SERVICE_ADD_SCHEDULE,
    SERVICE_ADD_USER,
    SERVICE_ADD_USER_SCHEDULE_RELAY,
    SERVICE_DELETE_CONTACT,
    SERVICE_DELETE_GROUP,
    SERVICE_DELETE_SCHEDULE,
    SERVICE_DELETE_USER,
    SERVICE_LIST_CONTACTS,
    SERVICE_LIST_GROUPS,
    SERVICE_LIST_SCHEDULES,
    SERVICE_LIST_USERS,
    SERVICE_MODIFY_CONTACT,
    SERVICE_MODIFY_GROUP,
    SERVICE_MODIFY_SCHEDULE,
    SERVICE_MODIFY_USER,
    SERVICE_REMOVE_USER_SCHEDULE_RELAY,
    VALID_DAYS,
)
from .validation import csv_to_list

SERVICE_LIST_SCHEDULES_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Optional("page"): cv.positive_int,
    }
)
SERVICE_LIST_USERS_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Optional("page"): cv.positive_int,
    }
)
SERVICE_ADD_SCHEDULE_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("schedule_type"): vol.In(["0", "1", "2"]),
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional("week"): vol.All(
            cv.ensure_list,
            vol.Length(min=1),
            [vol.In(VALID_DAYS)],
            vol.Unique(),
        ),
        vol.Optional("date_start"): cv.date,
        vol.Optional("date_end"): cv.date,
        vol.Required("time_start"): cv.time,
        vol.Required("time_end"): cv.time,
    }
)
SERVICE_MODIFY_SCHEDULE_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("id"): cv.string,
        vol.Optional("schedule_type"): vol.In(["0", "1", "2"]),
        vol.Optional("name"): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional("week"): vol.All(
            cv.ensure_list,
            vol.Length(min=1),
            [vol.In(VALID_DAYS)],
            vol.Unique(),
        ),
        vol.Optional("date_start"): cv.date,
        vol.Optional("date_end"): cv.date,
        vol.Optional("time_start"): cv.time,
        vol.Optional("time_end"): cv.time,
    }
)
SERVICE_DELETE_SCHEDULE_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("id"): cv.string,
    }
)
SERVICE_ADD_USER_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("name"): cv.string,
        vol.Required("schedules"): vol.All(
            csv_to_list,
            vol.Length(min=1),
            [vol.All(cv.string, vol.Length(min=1), vol.Match(r"^\d+$"))],
            vol.Unique(),
        ),
        vol.Required("lift_floor_num"): cv.string,
        vol.Optional("user_id"): cv.string,
        vol.Optional("web_relay"): cv.string,
        vol.Optional("private_pin"): cv.string,
        vol.Optional("card_code"): cv.string,
    }
)
SERVICE_MODIFY_USER_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("id"): cv.string,
        vol.Optional("name"): cv.string,
        vol.Optional("user_id"): cv.string,
        vol.Optional("schedule_relay"): cv.string,
        vol.Optional("lift_floor_num"): cv.string,
        vol.Optional("web_relay"): cv.string,
        vol.Optional("private_pin"): cv.string,
        vol.Optional("card_code"): cv.string,
    }
)
SERVICE_DELETE_USER_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("id"): cv.string,
    }
)
SERVICE_ADD_USER_SCHEDULE_RELAY_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("id"): cv.string,
        vol.Required("schedule_id"): cv.string,
        vol.Required("relay_id"): cv.string,
    }
)
SERVICE_REMOVE_USER_SCHEDULE_RELAY_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("id"): cv.string,
        vol.Required("schedule_id"): cv.string,
        vol.Required("relay_id"): cv.string,
    }
)
SERVICE_LIST_CONTACTS_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Optional("page"): cv.positive_int,
    }
)
SERVICE_ADD_CONTACT_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional("phone"): cv.string,
        vol.Optional("group"): cv.string,
    }
)
SERVICE_MODIFY_CONTACT_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("id"): cv.string,
        vol.Optional("name"): vol.All(cv.string, vol.Length(min=1)),
        vol.Optional("phone"): cv.string,
        vol.Optional("group"): cv.string,
    }
)
SERVICE_DELETE_CONTACT_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("id"): vol.All(csv_to_list, vol.Length(min=1), [cv.string]),
    }
)
SERVICE_LIST_GROUPS_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Optional("page"): cv.positive_int,
    }
)
SERVICE_ADD_GROUP_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1)),
    }
)
SERVICE_MODIFY_GROUP_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("id"): cv.string,
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1)),
    }
)
SERVICE_DELETE_GROUP_SCHEMA = cv.make_entity_service_schema(
    {
        vol.Required("id"): cv.string,
    }
)


async def async_register_services(hass: HomeAssistant) -> None:
    """Register all Akuvox lock entity services."""
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_LIST_SCHEDULES,
        entity_domain=Platform.LOCK,
        schema=SERVICE_LIST_SCHEDULES_SCHEMA,
        func=SERVICE_LIST_SCHEDULES,
        supports_response=SupportsResponse.ONLY,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_LIST_USERS,
        entity_domain=Platform.LOCK,
        schema=SERVICE_LIST_USERS_SCHEMA,
        func=SERVICE_LIST_USERS,
        supports_response=SupportsResponse.ONLY,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_ADD_SCHEDULE,
        entity_domain=Platform.LOCK,
        schema=SERVICE_ADD_SCHEDULE_SCHEMA,
        func=SERVICE_ADD_SCHEDULE,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_MODIFY_SCHEDULE,
        entity_domain=Platform.LOCK,
        schema=SERVICE_MODIFY_SCHEDULE_SCHEMA,
        func=SERVICE_MODIFY_SCHEDULE,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_DELETE_SCHEDULE,
        entity_domain=Platform.LOCK,
        schema=SERVICE_DELETE_SCHEDULE_SCHEMA,
        func=SERVICE_DELETE_SCHEDULE,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_ADD_USER,
        entity_domain=Platform.LOCK,
        schema=SERVICE_ADD_USER_SCHEMA,
        func=SERVICE_ADD_USER,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_MODIFY_USER,
        entity_domain=Platform.LOCK,
        schema=SERVICE_MODIFY_USER_SCHEMA,
        func=SERVICE_MODIFY_USER,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_DELETE_USER,
        entity_domain=Platform.LOCK,
        schema=SERVICE_DELETE_USER_SCHEMA,
        func=SERVICE_DELETE_USER,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_ADD_USER_SCHEDULE_RELAY,
        entity_domain=Platform.LOCK,
        schema=SERVICE_ADD_USER_SCHEDULE_RELAY_SCHEMA,
        func=SERVICE_ADD_USER_SCHEDULE_RELAY,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_REMOVE_USER_SCHEDULE_RELAY,
        entity_domain=Platform.LOCK,
        schema=SERVICE_REMOVE_USER_SCHEDULE_RELAY_SCHEMA,
        func=SERVICE_REMOVE_USER_SCHEDULE_RELAY,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_LIST_CONTACTS,
        entity_domain=Platform.LOCK,
        schema=SERVICE_LIST_CONTACTS_SCHEMA,
        func=SERVICE_LIST_CONTACTS,
        supports_response=SupportsResponse.ONLY,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_ADD_CONTACT,
        entity_domain=Platform.LOCK,
        schema=SERVICE_ADD_CONTACT_SCHEMA,
        func=SERVICE_ADD_CONTACT,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_MODIFY_CONTACT,
        entity_domain=Platform.LOCK,
        schema=SERVICE_MODIFY_CONTACT_SCHEMA,
        func=SERVICE_MODIFY_CONTACT,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_DELETE_CONTACT,
        entity_domain=Platform.LOCK,
        schema=SERVICE_DELETE_CONTACT_SCHEMA,
        func=SERVICE_DELETE_CONTACT,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_LIST_GROUPS,
        entity_domain=Platform.LOCK,
        schema=SERVICE_LIST_GROUPS_SCHEMA,
        func=SERVICE_LIST_GROUPS,
        supports_response=SupportsResponse.ONLY,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_ADD_GROUP,
        entity_domain=Platform.LOCK,
        schema=SERVICE_ADD_GROUP_SCHEMA,
        func=SERVICE_ADD_GROUP,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_MODIFY_GROUP,
        entity_domain=Platform.LOCK,
        schema=SERVICE_MODIFY_GROUP_SCHEMA,
        func=SERVICE_MODIFY_GROUP,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_DELETE_GROUP,
        entity_domain=Platform.LOCK,
        schema=SERVICE_DELETE_GROUP_SCHEMA,
        func=SERVICE_DELETE_GROUP,
    )
