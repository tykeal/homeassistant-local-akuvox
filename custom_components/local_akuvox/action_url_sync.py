# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Detect and reconcile optional (call) Action URLs on Akuvox devices."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Collection
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pylocal_akuvox import AkuvoxUnsupportedError

from .capability_support import async_report_unsupported_capability
from .const import OPTIONAL_ACTIONURL_KEYS
from .sanitize import mask_webhook_id
from .webhook import build_action_urls

_LOGGER = logging.getLogger(__name__)


def supported_optional_action_url_keys(device_config: object) -> frozenset[str]:
    """Return the optional Action URL keys present in a device config.

    A key is supported when its config key is present; its value is
    irrelevant (devices report empty strings for unset URLs).

    Args:
        device_config: A ``DeviceConfig`` or mapping of config keys.

    Returns:
        Logical names from ``OPTIONAL_ACTIONURL_KEYS`` that are present,
        or an empty set for unexpected inputs.

    """
    if isinstance(device_config, (str, bytes)):
        return frozenset()
    try:
        return frozenset(
            name
            for name, config_key in OPTIONAL_ACTIONURL_KEYS.items()
            if config_key in device_config  # type: ignore[operator]
        )
    except TypeError:
        return frozenset()


async def async_detect_optional_action_url_keys(device: Any) -> frozenset[str]:
    """Detect optional Action URL keys supported by an entered device.

    Any failure falls back to no optional keys so callers push the
    base payload unchanged.

    Args:
        device: An entered ``AkuvoxDevice`` session.

    Returns:
        Supported logical optional key names (possibly empty).

    """
    get_device_config = getattr(device, "get_device_config", None)
    if not callable(get_device_config):
        _LOGGER.debug("Device cannot read config; skipping optional action URLs")
        return frozenset()
    try:
        device_config = await get_device_config()
    except Exception as err:
        _LOGGER.debug(
            "Could not read device config for optional action URLs (%s)",
            type(err).__name__,
        )
        return frozenset()
    return supported_optional_action_url_keys(device_config)


def _optional_action_url_updates(
    device_config: Any,
    supported: Collection[str],
    enable_payload: dict[str, str],
) -> dict[str, str]:
    """Return optional Action URL keys whose device values differ.

    Args:
        device_config: The device config read from the device.
        supported: Supported logical optional key names.
        enable_payload: The expected enable payload.

    Returns:
        Mapping of config key to expected URL for differing keys only.

    """
    updates: dict[str, str] = {}
    for name, config_key in OPTIONAL_ACTIONURL_KEYS.items():
        if name not in supported:
            continue
        expected = enable_payload[config_key]
        if device_config.get(config_key) != expected:
            updates[config_key] = expected
    return updates


async def async_reconcile_optional_action_urls(
    hass: HomeAssistant,
    entry: ConfigEntry,
    device: Any,
    webhook_id: str,
) -> None:
    """Write missing or stale optional Action URLs at entry load.

    Only optional keys the device exposes are considered, and only
    those whose current values differ from the expected URLs are
    written. ``Enable``, ``Method`` and base keys are never touched.
    Never raises except for task cancellation.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry being set up.
        device: The entered ``AkuvoxDevice`` session for the entry.
        webhook_id: The registered webhook ID.

    """
    masked_id = mask_webhook_id(webhook_id)
    get_device_config = getattr(device, "get_device_config", None)
    if not callable(get_device_config):
        _LOGGER.debug("Device cannot read config; skipping call URL reconcile")
        return
    try:
        device_config = await get_device_config()
        supported = supported_optional_action_url_keys(device_config)
        if not supported:
            _LOGGER.debug("%s exposes no call action URL keys", entry.title)
            return
        enable_payload, _ = build_action_urls(
            hass,
            webhook_id,
            warn_http=False,
            optional_keys=supported,
        )
        updates = _optional_action_url_updates(
            device_config,
            supported,
            enable_payload,
        )
        if not updates:
            _LOGGER.debug("Call action URLs already current for %s", entry.title)
            return
        await device.set_device_config(updates)
    except AkuvoxUnsupportedError as err:
        await async_report_unsupported_capability(
            hass,
            entry,
            err,
            context="webhook call action URL reconciliation",
        )
        return
    except Exception as err:
        _LOGGER.warning(
            "Failed to reconcile call action URLs for %s (webhook %s): %s",
            entry.title,
            masked_id,
            type(err).__name__,
        )
        return
    _LOGGER.info(
        "Updated %d call action URL(s) for %s (webhook %s)",
        len(updates),
        entry.title,
        masked_id,
    )


async def async_cancel_reconcile_task(coordinator: Any) -> None:
    """Cancel and await in-flight call action URL reconciliation.

    Must run before the device session closes or another Action URL
    write is pushed, because Home Assistant only cancels entry
    background tasks after unload returns.

    Args:
        coordinator: The coordinator owning the reconcile task, if any.

    """
    task = getattr(coordinator, "action_url_reconcile_task", None)
    if isinstance(task, asyncio.Task) and not task.done():
        task.cancel()
        await asyncio.wait({task})
