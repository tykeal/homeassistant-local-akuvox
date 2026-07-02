# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""The Akuvox integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from pylocal_akuvox import (
    AkuvoxAuthenticationError,
    AkuvoxDevice,
    AkuvoxError,
    AkuvoxUnsupportedError,
    AuthConfig,
    AuthMethod,
)

from .capability_support import (
    apply_capability_options,
    async_clear_unsupported_capability_issue,
    async_report_unsupported_capability,
    get_effective_attempt_unknown,
)
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
    DATA_CAPABILITY_REPORT_LOCK,
    DEFAULT_REQUEST_DELAY,
    DOMAIN,
    PLATFORMS,
    get_auth_method_map,
)
from .coordinator import AkuvoxDataUpdateCoordinator
from .services import async_register_services
from .webhook import (
    async_register_webhook,
    async_unregister_webhook,
    build_action_urls,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register platform entity services for Akuvox.

    Args:
        hass: The Home Assistant instance.
        config: The configuration.

    Returns:
        True after all services are registered.

    """
    await async_register_services(hass)
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


def _cleanup_domain_runtime_data(hass: HomeAssistant) -> None:
    """Remove reserved runtime data when no coordinators remain."""
    domain_data = hass.data.get(DOMAIN)
    if not isinstance(domain_data, dict):
        return
    has_coordinator = any(
        isinstance(value, AkuvoxDataUpdateCoordinator) for value in domain_data.values()
    )
    if not has_coordinator:
        domain_data.pop(DATA_CAPABILITY_REPORT_LOCK, None)
    if not domain_data:
        hass.data.pop(DOMAIN, None)


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
    try:
        await device.__aenter__()
    except AkuvoxAuthenticationError as err:
        raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
    except AkuvoxUnsupportedError as err:
        await async_report_unsupported_capability(
            hass,
            entry,
            err,
            context="setup",
        )
        raise ConfigEntryNotReady(
            f"Unsupported capability during setup: {err}"
        ) from err
    except AkuvoxError as err:
        raise ConfigEntryNotReady(f"Unable to connect to Akuvox device: {err}") from err

    apply_capability_options(
        device,
        attempt_unknown=get_effective_attempt_unknown(entry),
    )
    await async_clear_unsupported_capability_issue(
        hass,
        entry,
        reason=None,
        capability=None,
    )
    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)
    coordinator.config_entry = entry

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
        _cleanup_domain_runtime_data(hass)
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

        _cleanup_domain_runtime_data(hass)

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
            apply_capability_options(
                device,
                attempt_unknown=get_effective_attempt_unknown(entry),
            )
            await device.set_device_config(disable_payload)  # type: ignore[attr-defined]
    except AkuvoxUnsupportedError as err:
        await async_report_unsupported_capability(
            hass,
            entry,
            err,
            context="entry removal webhook disable",
        )
        _LOGGER.warning(
            "Webhook disable config is unsupported for %s; "
            "device may retain stale URLs",
            entry.title,
        )
    except Exception:
        _LOGGER.warning(
            "Failed to push webhook disable config to %s "
            "during removal; device may retain stale URLs",
            entry.title,
            exc_info=True,
        )
    finally:
        await async_clear_unsupported_capability_issue(
            hass,
            entry,
            reason=None,
            capability=None,
        )
