# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Diagnostics support for the Local Akuvox integration."""

from __future__ import annotations

from typing import Any, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pylocal_akuvox import AkuvoxError, AkuvoxUnsupportedError

from . import _create_device
from .capability_support import (
    apply_capability_options,
    async_report_unsupported_capability,
    get_effective_attempt_unknown,
    sanitize_value,
    serialize_capabilities,
)
from .const import (
    CONF_AUTH_METHOD,
    CONF_HOST,
    CONF_USE_SSL,
    CONF_VERIFY_SSL,
    DOMAIN,
)
from .coordinator import AkuvoxDataUpdateCoordinator

_PROBE_TIMEOUT = 5.0


def _safe_entry_data(entry: ConfigEntry) -> dict[str, Any]:
    """Return non-sensitive config entry metadata for diagnostics."""
    merged = {**entry.data, **entry.options}
    return {
        "entry_id": entry.entry_id,
        "title": entry.title,
        "host": merged.get(CONF_HOST),
        "use_ssl": bool(merged.get(CONF_USE_SSL, False)),
        "verify_ssl": bool(merged.get(CONF_VERIFY_SSL, True)),
        "auth_method": merged.get(CONF_AUTH_METHOD),
    }


def _safe_device_info(
    coordinator: AkuvoxDataUpdateCoordinator | None,
) -> dict[str, Any]:
    """Return non-sensitive cached device information for diagnostics."""
    if coordinator is None or coordinator.data is None:
        return {}
    device_info = coordinator.data.device_info
    return cast(
        dict[str, Any],
        sanitize_value(
            {
                "model": device_info.model,
                "firmware_version": device_info.firmware_version,
                "hardware_version": device_info.hardware_version,
            }
        ),
    )


def _safe_error(err: Exception) -> dict[str, str]:
    """Return a sanitized error summary for diagnostics."""
    data = {
        "type": type(err).__name__,
        "message": str(err),
    }
    if isinstance(err, AkuvoxUnsupportedError):
        data["reason"] = str(err.reason or "unknown")
        data["capability"] = err.capability.value if err.capability else "unknown"
        data["device_class"] = str(err.device_class or "unknown")
    return cast(dict[str, str], sanitize_value(data))


async def _async_probe_capabilities(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Run the bounded diagnostics capability probe."""
    device = _create_device(entry)
    try:
        async with device:
            apply_capability_options(
                device,
                attempt_unknown=get_effective_attempt_unknown(entry),
            )
            profile = await device.probe_capabilities(timeout=_PROBE_TIMEOUT)
    except AkuvoxUnsupportedError as err:
        await async_report_unsupported_capability(
            hass,
            entry,
            err,
            context="diagnostics capability probe",
        )
        return {"error": _safe_error(err)}
    except AkuvoxError as err:
        return {"error": _safe_error(err)}
    return {"capabilities": serialize_capabilities(profile)}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return sanitized capability diagnostics for one config entry."""
    domain_data = hass.data.get(DOMAIN)
    coordinator: AkuvoxDataUpdateCoordinator | None = None
    if isinstance(domain_data, dict):
        coordinator = domain_data.get(entry.entry_id)
    current = (
        serialize_capabilities(coordinator.data.capabilities)
        if coordinator is not None and coordinator.data is not None
        else {}
    )
    return {
        "entry": _safe_entry_data(entry),
        "device_info": _safe_device_info(coordinator),
        "current_capabilities": current,
        "probe": await _async_probe_capabilities(hass, entry),
    }
