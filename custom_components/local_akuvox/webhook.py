# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Webhook handler and registration helpers for Akuvox."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING, Final

# aislop-ignore-next-line ai-slop/hallucinated-import -- provided by homeassistant
from aiohttp import web  # provided by homeassistant
from homeassistant.components.webhook import (
    async_generate_url,
    async_register,
    async_unregister,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pylocal_akuvox import AkuvoxUnsupportedError

from .capability_support import async_report_unsupported_capability
from .const import (
    ACTIONURL_ENABLE_KEY,
    ACTIONURL_KEYS,
    ACTIONURL_METHOD_KEY,
    CONF_WEBHOOK_ID,
    DOMAIN,
    EVENT_WEBHOOK_RECEIVED,
    KNOWN_EVENT_TYPES,
    REFRESH_EVENT_TYPES,
)
from .sanitize import mask_webhook_id, sanitize_payload

if TYPE_CHECKING:
    from .coordinator import AkuvoxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Unknown event normalization pattern
_NORMALIZE_RE: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9_]")
_COLLAPSE_RE: Final[re.Pattern[str]] = re.compile(r"_+")
_MAX_NORMALIZED_LENGTH: Final = 32

# URL templates for each action URL key
_URL_TEMPLATES: Final[dict[str, str]] = {
    "RelayATriggered": "?event=relay_a_triggered&status=$relay1status",
    "RelayAClosed": "?event=relay_a_closed&status=$relay1status",
    "RelayBTriggered": "?event=relay_b_triggered&status=$relay2status",
    "RelayBClosed": "?event=relay_b_closed&status=$relay2status",
    "InputATriggered": "?event=input_a_triggered&status=$relay1status",
    "InputAClosed": "?event=input_a_closed&status=$relay1status",
    "InputBTriggered": "?event=input_b_triggered&status=$relay2status",
    "InputBClosed": "?event=input_b_closed&status=$relay2status",
    "ValidCodeEntered": "?event=valid_code_entered&code=$code",
    "InvalidCodeEntered": "?event=invalid_code_entered",
}


def _normalize_event_type(raw_event: str) -> str:
    """Normalize an unknown event type to a safe identifier.

    Args:
        raw_event: The raw event parameter value.

    Returns:
        Normalized string suitable for ``unknown_{result}``.

    """
    normalized = raw_event.lower()
    normalized = _NORMALIZE_RE.sub("_", normalized)
    normalized = _COLLAPSE_RE.sub("_", normalized)
    normalized = normalized.strip("_")
    normalized = normalized[:_MAX_NORMALIZED_LENGTH]
    return normalized or "event"


def _get_device_id(
    hass: HomeAssistant,
    config_entry_id: str,
) -> str | None:
    """Look up the HA device ID for a config entry.

    Args:
        hass: The Home Assistant instance.
        config_entry_id: The config entry ID.

    Returns:
        The device ID or None.

    """
    dev_reg = dr.async_get(hass)
    for dev in dr.async_entries_for_config_entry(dev_reg, config_entry_id):
        return dev.id
    return None


_refresh_in_flight: set[str] = set()


async def _refresh_user_cache(
    coordinator: AkuvoxDataUpdateCoordinator,
    entry_id: str,
) -> None:
    """Background task to refresh the user cache from the device.

    Must not be awaited in the webhook handler path.
    Uses _refresh_in_flight to deduplicate concurrent calls.

    """
    try:
        users = await asyncio.wait_for(
            coordinator.device.list_users(page=None),
            timeout=5.0,
        )
    except TimeoutError:
        _LOGGER.debug("User cache refresh timed out")
        return
    except AkuvoxUnsupportedError as exc:
        await async_report_unsupported_capability(
            coordinator.hass,
            getattr(coordinator, "config_entry", None),
            exc,
            context="webhook user cache refresh",
            issue_scope=entry_id,
        )
        return
    except Exception as exc:
        _LOGGER.debug("Failed to refresh user cache: %s", exc, exc_info=True)
        return
    finally:
        _refresh_in_flight.discard(entry_id)

    if users is not None:
        coordinator.update_user_cache(users)


async def _resolve_user(
    hass: HomeAssistant,
    coordinator: AkuvoxDataUpdateCoordinator,
    code: str,
    entry_id: str,
) -> object | None:
    """Resolve a user by PIN from cache only.

    On cache miss, schedules a background refresh (guarded against
    duplicate in-flight requests) so future lookups succeed without
    blocking the webhook response.

    Args:
        hass: The Home Assistant instance.
        coordinator: The data update coordinator.
        code: The PIN code to match.
        entry_id: The config entry ID for deduplication.

    Returns:
        Matching User object or None.

    """
    user = coordinator.get_user_by_pin(code)
    if user is not None:
        return user

    # Schedule background cache refresh (non-blocking, deduplicated)
    if entry_id not in _refresh_in_flight:
        _refresh_in_flight.add(entry_id)
        hass.async_create_task(_refresh_user_cache(coordinator, entry_id))

    return None


async def async_handle_webhook(
    hass: HomeAssistant,
    webhook_id: str,
    request: web.Request,
) -> web.Response | None:
    """Handle incoming webhook request from Akuvox device.

    Args:
        hass: The Home Assistant instance.
        webhook_id: The webhook ID from the URL.
        request: The aiohttp request.

    Returns:
        HTTP response (200 or 400).

    """
    domain_data = hass.data.get(DOMAIN)
    registry: dict[str, str] = (
        domain_data.get("webhook_registry", {}) if domain_data else {}
    )
    config_entry_id = registry.get(webhook_id)
    if config_entry_id is None:
        _LOGGER.warning(
            "Webhook %s not in registry; ignoring",
            mask_webhook_id(webhook_id),
        )
        return web.Response(status=200, body=b"")

    try:
        coordinator: AkuvoxDataUpdateCoordinator = hass.data[DOMAIN][config_entry_id]
    except KeyError:
        _LOGGER.warning(
            "Coordinator missing for entry %s; ignoring webhook",
            config_entry_id,
        )
        return web.Response(status=200, body=b"")

    query_params = dict(request.query)

    raw_event = query_params.get("event")
    if raw_event is None:
        sanitized = sanitize_payload(query_params, webhook_id=webhook_id)
        _LOGGER.warning(
            "Webhook missing 'event' parameter: %s",
            sanitized,
        )
        return web.Response(status=400, text="Bad Request")

    device_id = _get_device_id(hass, config_entry_id)

    if raw_event not in KNOWN_EVENT_TYPES:
        normalized = _normalize_event_type(raw_event)
        event_type = f"unknown_{normalized}"
        sanitized = sanitize_payload(query_params, webhook_id=webhook_id)
        safe_event = repr(raw_event)
        if len(safe_event) > 80:
            safe_event = safe_event[:77] + "..."
        _LOGGER.warning("Unknown webhook event type: %s", safe_event)
        hass.bus.async_fire(
            EVENT_WEBHOOK_RECEIVED,
            {
                "device_id": device_id,
                "config_entry_id": config_entry_id,
                "event_type": event_type,
                "payload": sanitized,
            },
        )
        return web.Response(status=200, body=b"")

    event_type = raw_event

    user = None
    code_value = query_params.get("code")
    if event_type == "valid_code_entered" and code_value:
        user = await _resolve_user(hass, coordinator, code_value, config_entry_id)

    hass.bus.async_fire(
        EVENT_WEBHOOK_RECEIVED,
        {
            "device_id": device_id,
            "config_entry_id": config_entry_id,
            "event_type": event_type,
            "payload": {
                "event": raw_event,
                "status": query_params.get("status"),
                "device_user_id": (getattr(user, "id", None) if user else None),
                "user_id": (getattr(user, "user_id", None) if user else None),
                "username": (getattr(user, "name", None) if user else None),
            },
        },
    )

    # Schedule coordinator refresh for relay/code events
    if event_type in REFRESH_EVENT_TYPES:
        hass.async_create_task(coordinator.async_refresh())

    return web.Response(status=200, body=b"")


def async_register_webhook(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device_name: str = "",
) -> None:
    """Register a webhook endpoint for an Akuvox device.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry with webhook_id.
        device_name: Human-readable device name.

    """
    webhook_id = entry.options.get(
        CONF_WEBHOOK_ID,
        entry.data.get(CONF_WEBHOOK_ID),
    )
    if webhook_id is None:
        return

    name = f"Akuvox {device_name}" if device_name else "Akuvox Webhook"
    try:
        async_register(
            hass,
            domain=DOMAIN,
            name=name,
            webhook_id=webhook_id,
            handler=async_handle_webhook,
            allowed_methods=["GET"],
        )
    except ValueError:
        _LOGGER.warning(
            "Webhook %s already registered; re-registering",
            mask_webhook_id(webhook_id),
        )
        async_unregister(hass, webhook_id)
        async_register(
            hass,
            domain=DOMAIN,
            name=name,
            webhook_id=webhook_id,
            handler=async_handle_webhook,
            allowed_methods=["GET"],
        )

    # Add to registry after successful registration
    hass.data[DOMAIN].setdefault("webhook_registry", {})
    hass.data[DOMAIN]["webhook_registry"][webhook_id] = entry.entry_id

    _LOGGER.debug(
        "Registered webhook %s for %s",
        mask_webhook_id(webhook_id),
        entry.title,
    )


def async_unregister_webhook(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Unregister a webhook endpoint for an Akuvox device.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry with webhook_id.

    """
    webhook_id = entry.options.get(
        CONF_WEBHOOK_ID,
        entry.data.get(CONF_WEBHOOK_ID),
    )
    if webhook_id is None:
        return

    domain_data = hass.data.get(DOMAIN)
    registry: dict[str, str] = (
        domain_data.get("webhook_registry", {}) if domain_data else {}
    )
    if webhook_id not in registry:
        return

    async_unregister(hass, webhook_id)

    registry.pop(webhook_id, None)

    if domain_data and "webhook_registry" in domain_data and not registry:
        domain_data.pop("webhook_registry", None)

    _LOGGER.debug(
        "Unregistered webhook %s for %s",
        mask_webhook_id(webhook_id),
        entry.title,
    )


def build_action_urls(
    hass: HomeAssistant,
    webhook_id: str,
    *,
    warn_http: bool = True,
) -> tuple[dict[str, str], dict[str, str]]:
    """Build enable and disable payloads for device action URLs.

    Args:
        hass: The Home Assistant instance.
        webhook_id: The webhook ID for URL generation.
        warn_http: Log HTTPS warning (set False for disables).

    Returns:
        Tuple of (enable_payload, disable_payload) dicts.

    """
    try:
        webhook_url = async_generate_url(
            hass,
            webhook_id,
            allow_external=True,
            allow_internal=True,
        )
    except Exception:
        _LOGGER.exception(
            "Failed to generate webhook URL for %s",
            mask_webhook_id(webhook_id),
        )
        raise

    action_urls: dict[str, str] = {}
    for name, config_key in ACTIONURL_KEYS.items():
        template = _URL_TEMPLATES[name]
        action_urls[config_key] = f"{webhook_url}{template}"

    enable_payload: dict[str, str] = {
        ACTIONURL_ENABLE_KEY: "1",
        ACTIONURL_METHOD_KEY: "",
        **action_urls,
    }

    disable_payload: dict[str, str] = {
        ACTIONURL_ENABLE_KEY: "0",
        ACTIONURL_METHOD_KEY: "",
        **{key: "" for key in action_urls},
    }

    if warn_http and not webhook_url.startswith("https://"):
        _LOGGER.warning(
            "Webhook URL uses HTTP (not HTTPS). PINs may be "
            "transmitted in plaintext. Configure an external "
            "URL with TLS for security.",
        )

    return enable_payload, disable_payload
