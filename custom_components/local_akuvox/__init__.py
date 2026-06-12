# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""The Akuvox integration."""

from __future__ import annotations

import logging
from typing import Any

# aislop-ignore-next-line ai-slop/hallucinated-import -- provided by homeassistant
import voluptuous as vol  # provided by homeassistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import service
from homeassistant.helpers.typing import ConfigType
from pylocal_akuvox import AkuvoxDevice, AuthConfig, AuthMethod

from .const import (
    CONF_AUTH_METHOD,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_REQUEST_DELAY,
    CONF_USE_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    CONF_WEBHOOK_ENABLED,
    CONF_WEBHOOK_ID,
    DEFAULT_REQUEST_DELAY,
    DOMAIN,
    PLATFORMS,
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
    get_auth_method_map,
)
from .coordinator import AkuvoxDataUpdateCoordinator
from .webhook import (
    async_register_webhook,
    async_unregister_webhook,
    build_action_urls,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def _csv_to_list(value: Any) -> list[str]:
    """Split a comma-separated string into a list of trimmed strings.

    Also flattens lists that contain comma-separated items.
    Coerces other iterables via ``cv.ensure_list``.

    """
    if isinstance(value, str):
        return [s.strip() for s in value.split(",") if s.strip()]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, str):
                for part in item.split(","):
                    stripped = part.strip()
                    if stripped:
                        result.append(stripped)
            else:
                result.append(str(item))
        return result
    return cv.ensure_list(value)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register platform entity services for Akuvox.

    Args:
        hass: The Home Assistant instance.
        config: The configuration.

    Returns:
        True after all services are registered.

    """
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_LIST_SCHEDULES,
        entity_domain=Platform.LOCK,
        schema={
            vol.Optional("page"): cv.positive_int,
        },
        func=SERVICE_LIST_SCHEDULES,
        supports_response=SupportsResponse.ONLY,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_LIST_USERS,
        entity_domain=Platform.LOCK,
        schema={
            vol.Optional("page"): cv.positive_int,
        },
        func=SERVICE_LIST_USERS,
        supports_response=SupportsResponse.ONLY,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_ADD_SCHEDULE,
        entity_domain=Platform.LOCK,
        schema={
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
        },
        func=SERVICE_ADD_SCHEDULE,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_MODIFY_SCHEDULE,
        entity_domain=Platform.LOCK,
        schema={
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
        },
        func=SERVICE_MODIFY_SCHEDULE,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_DELETE_SCHEDULE,
        entity_domain=Platform.LOCK,
        schema={
            vol.Required("id"): cv.string,
        },
        func=SERVICE_DELETE_SCHEDULE,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_ADD_USER,
        entity_domain=Platform.LOCK,
        schema={
            vol.Required("name"): cv.string,
            vol.Required("schedules"): vol.All(
                _csv_to_list,
                vol.Length(min=1),
                [vol.All(cv.string, vol.Length(min=1), vol.Match(r"^\d+$"))],
                vol.Unique(),
            ),
            vol.Required("lift_floor_num"): cv.string,
            vol.Optional("user_id"): cv.string,
            vol.Optional("web_relay"): cv.string,
            vol.Optional("private_pin"): cv.string,
            vol.Optional("card_code"): cv.string,
        },
        func=SERVICE_ADD_USER,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_MODIFY_USER,
        entity_domain=Platform.LOCK,
        schema={
            vol.Required("id"): cv.string,
            vol.Optional("name"): cv.string,
            vol.Optional("user_id"): cv.string,
            vol.Optional("schedule_relay"): cv.string,
            vol.Optional("lift_floor_num"): cv.string,
            vol.Optional("web_relay"): cv.string,
            vol.Optional("private_pin"): cv.string,
            vol.Optional("card_code"): cv.string,
        },
        func=SERVICE_MODIFY_USER,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_DELETE_USER,
        entity_domain=Platform.LOCK,
        schema={
            vol.Required("id"): cv.string,
        },
        func=SERVICE_DELETE_USER,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_ADD_USER_SCHEDULE_RELAY,
        entity_domain=Platform.LOCK,
        schema={
            vol.Required("id"): cv.string,
            vol.Required("schedule_id"): cv.string,
            vol.Required("relay_id"): cv.string,
        },
        func=SERVICE_ADD_USER_SCHEDULE_RELAY,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_REMOVE_USER_SCHEDULE_RELAY,
        entity_domain=Platform.LOCK,
        schema={
            vol.Required("id"): cv.string,
            vol.Required("schedule_id"): cv.string,
            vol.Required("relay_id"): cv.string,
        },
        func=SERVICE_REMOVE_USER_SCHEDULE_RELAY,
    )

    # ── Contact services ─────────────────────────────────────

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_LIST_CONTACTS,
        entity_domain=Platform.LOCK,
        schema={
            vol.Optional("page"): cv.positive_int,
        },
        func=SERVICE_LIST_CONTACTS,
        supports_response=SupportsResponse.ONLY,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_ADD_CONTACT,
        entity_domain=Platform.LOCK,
        schema={
            vol.Required("name"): vol.All(cv.string, vol.Length(min=1)),
            vol.Optional("phone"): cv.string,
            vol.Optional("group"): cv.string,
        },
        func=SERVICE_ADD_CONTACT,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_MODIFY_CONTACT,
        entity_domain=Platform.LOCK,
        schema={
            vol.Required("id"): cv.string,
            vol.Optional("name"): vol.All(cv.string, vol.Length(min=1)),
            vol.Optional("phone"): cv.string,
            vol.Optional("group"): cv.string,
        },
        func=SERVICE_MODIFY_CONTACT,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_DELETE_CONTACT,
        entity_domain=Platform.LOCK,
        schema={
            vol.Required("id"): vol.All(_csv_to_list, vol.Length(min=1), [cv.string]),
        },
        func=SERVICE_DELETE_CONTACT,
    )

    # ── Group services ───────────────────────────────────────

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_LIST_GROUPS,
        entity_domain=Platform.LOCK,
        schema={
            vol.Optional("page"): cv.positive_int,
        },
        func=SERVICE_LIST_GROUPS,
        supports_response=SupportsResponse.ONLY,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_ADD_GROUP,
        entity_domain=Platform.LOCK,
        schema={
            vol.Required("name"): vol.All(cv.string, vol.Length(min=1)),
        },
        func=SERVICE_ADD_GROUP,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_MODIFY_GROUP,
        entity_domain=Platform.LOCK,
        schema={
            vol.Required("id"): cv.string,
            vol.Required("name"): vol.All(cv.string, vol.Length(min=1)),
        },
        func=SERVICE_MODIFY_GROUP,
    )

    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_DELETE_GROUP,
        entity_domain=Platform.LOCK,
        schema={
            vol.Required("id"): cv.string,
        },
        func=SERVICE_DELETE_GROUP,
    )

    return True


def _get_config_value(entry: ConfigEntry, key: str, default: object = None) -> object:
    """Get config value from options first, then data.

    Args:
        entry: The config entry.
        key: The configuration key.
        default: Default value if not found.

    Returns:
        The configuration value.

    """
    return entry.options.get(key, entry.data.get(key, default))


def _create_device(entry: ConfigEntry) -> AkuvoxDevice:
    """Create an AkuvoxDevice from a config entry.

    Args:
        entry: The config entry.

    Returns:
        Configured AkuvoxDevice instance.

    """
    host = str(_get_config_value(entry, CONF_HOST, ""))
    use_ssl = bool(_get_config_value(entry, CONF_USE_SSL, False))
    verify_ssl = bool(_get_config_value(entry, CONF_VERIFY_SSL, True))
    auth_method_str = str(_get_config_value(entry, CONF_AUTH_METHOD, "none"))
    auth_method = get_auth_method_map().get(auth_method_str, AuthMethod.NONE)

    auth_config: AuthConfig | None = None
    if auth_method in (AuthMethod.BASIC, AuthMethod.DIGEST):
        auth_config = AuthConfig(
            method=auth_method,
            username=str(_get_config_value(entry, CONF_USERNAME, "")),
            password=str(_get_config_value(entry, CONF_PASSWORD, "")),
        )
    else:
        auth_config = AuthConfig(method=auth_method)

    request_delay = float(
        _get_config_value(  # type: ignore[arg-type]
            entry, CONF_REQUEST_DELAY, DEFAULT_REQUEST_DELAY
        )
    )

    return AkuvoxDevice(
        host=host,
        auth=auth_config,
        use_ssl=use_ssl,
        verify_ssl=verify_ssl,
        request_delay=request_delay,  # type: ignore[call-arg]
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Akuvox from a config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.

    Returns:
        True if setup was successful.

    """
    device = _create_device(entry)
    await device.__aenter__()
    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await device.__aexit__(None, None, None)
        raise

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register webhook if enabled
    webhook_enabled = bool(_get_config_value(entry, CONF_WEBHOOK_ENABLED, False))
    webhook_id = _get_config_value(entry, CONF_WEBHOOK_ID)
    if webhook_enabled and webhook_id is not None:
        device_name = ""
        if coordinator.data:
            device_name = coordinator.data.device_name
        async_register_webhook(hass, entry, device_name=device_name)

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        async_unregister_webhook(hass, entry)
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)
        await device.__aexit__(None, None, None)
        raise

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload integration when options change.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry that was updated.

    """
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload an Akuvox config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.

    Returns:
        True if unload was successful.

    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Unregister webhook (also cleans registry)
        async_unregister_webhook(hass, entry)

        coordinator: AkuvoxDataUpdateCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.device.__aexit__(None, None, None)
        _LOGGER.debug("Closed device session for %s", entry.title)

        if not hass.data.get(DOMAIN):
            hass.data.pop(DOMAIN, None)

    return unload_ok


async def async_remove_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Clean up device webhook config on permanent entry removal.

    Called after async_unload_entry during deletion. Pushes the
    disable payload to the device on a best-effort basis.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry being removed.

    """
    webhook_enabled = bool(
        _get_config_value(entry, CONF_WEBHOOK_ENABLED, False),
    )
    webhook_id = _get_config_value(entry, CONF_WEBHOOK_ID)

    if not webhook_enabled or webhook_id is None:
        return

    try:
        _, disable_payload = build_action_urls(
            hass,
            str(webhook_id),
            warn_http=False,
        )
        device = _create_device(entry)
        async with device:
            await device.set_device_config(disable_payload)  # type: ignore[attr-defined]
    except Exception:
        _LOGGER.warning(
            "Failed to push webhook disable config to %s "
            "during removal; device may retain stale URLs",
            entry.title,
            exc_info=True,
        )
