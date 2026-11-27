# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Akuvox options flow."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.local_akuvox.const import (
    AUTH_BASIC,
    AUTH_NONE,
    CONF_ATTEMPT_UNKNOWN_CAPABILITY,
    CONF_AUTH_METHOD,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USE_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    CONF_WEBHOOK_ENABLED,
    CONF_WEBHOOK_ID,
    DOMAIN,
)
from tests.conftest import MOCK_HOST, MOCK_MAC, MOCK_WEBHOOK_ID


async def test_options_disable_without_webhook_id_saves_options(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
) -> None:
    """Test disabling with no stored webhook id does not push config."""
    data = {
        **mock_config_entry_data_none,
        CONF_WEBHOOK_ENABLED: True,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: MOCK_HOST,
            CONF_USE_SSL: False,
            CONF_VERIFY_SSL: True,
            CONF_AUTH_METHOD: AUTH_NONE,
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
            CONF_WEBHOOK_ENABLED: False,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_WEBHOOK_ENABLED] is False
    assert CONF_WEBHOOK_ID not in entry.options


async def test_options_webhook_url_build_failure_shows_error(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
) -> None:
    """Test webhook URL generation failures surface as form errors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.local_akuvox.options_flow.build_action_urls",
            side_effect=RuntimeError("no url"),
        ),
        patch(
            "custom_components.local_akuvox.options_flow.AkuvoxDevice",
        ) as mock_cls,
    ):
        device = mock_cls.return_value
        device.__aenter__ = AsyncMock(return_value=device)
        device.__aexit__ = AsyncMock(return_value=None)
        device.get_device_config = AsyncMock(return_value={})
        device.set_device_config = AsyncMock(return_value=None)
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: MOCK_HOST,
                CONF_USE_SSL: False,
                CONF_VERIFY_SSL: True,
                CONF_AUTH_METHOD: AUTH_NONE,
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
                CONF_WEBHOOK_ENABLED: True,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "webhook_push_failed"}
    device.set_device_config.assert_not_awaited()


async def test_options_webhook_enable_uses_basic_auth(
    hass: HomeAssistant,
    mock_config_entry_data_basic: dict[str, Any],
) -> None:
    """Test enabling webhooks builds basic auth credentials."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            **mock_config_entry_data_basic,
            CONF_WEBHOOK_ENABLED: False,
            CONF_WEBHOOK_ID: MOCK_WEBHOOK_ID,
        },
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.local_akuvox.options_flow.build_action_urls",
            return_value=({"enable": "1"}, {"enable": "0"}),
        ),
        patch(
            "custom_components.local_akuvox.options_flow.AkuvoxDevice",
        ) as mock_cls,
    ):
        device = mock_cls.return_value
        device.set_device_config = AsyncMock(return_value=None)
        device.__aenter__ = AsyncMock(return_value=device)
        device.__aexit__ = AsyncMock(return_value=None)

        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: MOCK_HOST,
                CONF_USE_SSL: False,
                CONF_VERIFY_SSL: True,
                CONF_AUTH_METHOD: AUTH_BASIC,
                CONF_USERNAME: "admin",
                CONF_PASSWORD: "password",
                CONF_WEBHOOK_ENABLED: True,
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    auth = mock_cls.call_args.kwargs["auth"]
    assert auth.username == "admin"
    assert auth.password == mock_config_entry_data_basic[CONF_PASSWORD]


async def test_options_flow_prefills_and_saves_attempt_unknown(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
) -> None:
    """Test options flow preserves and saves the unknown-capability opt-in."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            **mock_config_entry_data_none,
            CONF_ATTEMPT_UNKNOWN_CAPABILITY: True,
        },
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    schema = result["data_schema"]
    assert schema is not None
    assert schema({})[CONF_ATTEMPT_UNKNOWN_CAPABILITY] is True
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: MOCK_HOST,
            CONF_USE_SSL: False,
            CONF_VERIFY_SSL: True,
            CONF_AUTH_METHOD: AUTH_NONE,
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
            CONF_ATTEMPT_UNKNOWN_CAPABILITY: False,
            CONF_WEBHOOK_ENABLED: False,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_ATTEMPT_UNKNOWN_CAPABILITY] is False


# ── Call action URL gating (issue #330) ──────────────────────

_MAKE_CALL_KEY = "Config.Features.ACTIONURL.MakeCall"
_HANG_UP_KEY = "Config.Features.ACTIONURL.HangUp"


async def _options_toggle_webhook(
    hass: HomeAssistant,
    entry_data: dict[str, Any],
    *,
    enable: bool,
    device_config: Any,
) -> dict[str, str]:
    """Toggle webhooks via options and return the pushed payload."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            **entry_data,
            CONF_WEBHOOK_ENABLED: not enable,
            CONF_WEBHOOK_ID: MOCK_WEBHOOK_ID,
        },
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.local_akuvox.options_flow.AkuvoxDevice",
    ) as mock_cls:
        device = mock_cls.return_value
        device.__aenter__ = AsyncMock(return_value=device)
        device.__aexit__ = AsyncMock(return_value=None)
        if isinstance(device_config, Exception):
            device.get_device_config = AsyncMock(side_effect=device_config)
        else:
            device.get_device_config = AsyncMock(return_value=device_config)
        device.set_device_config = AsyncMock(return_value=None)

        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: MOCK_HOST,
                CONF_USE_SSL: False,
                CONF_VERIFY_SSL: True,
                CONF_AUTH_METHOD: AUTH_NONE,
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
                CONF_WEBHOOK_ENABLED: enable,
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    device.set_device_config.assert_awaited_once()
    payload: dict[str, str] = device.set_device_config.await_args.args[0]
    return payload


@pytest.mark.parametrize("enable", [True, False])
async def test_options_webhook_change_includes_exposed_call_keys(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config_factory: Any,
    enable: bool,
) -> None:
    """Test options pushes call keys only when the device exposes them."""
    payload = await _options_toggle_webhook(
        hass,
        mock_config_entry_data_none,
        enable=enable,
        device_config=mock_device_config_factory(**{_MAKE_CALL_KEY: ""}),
    )

    assert _HANG_UP_KEY not in payload
    if enable:
        assert payload[_MAKE_CALL_KEY].endswith(
            "?event=call_made&remote=$remote",
        )
    else:
        assert payload[_MAKE_CALL_KEY] == ""


@pytest.mark.parametrize("use_error", [False, True])
async def test_options_webhook_enable_base_payload_without_call_keys(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
    use_error: bool,
) -> None:
    """Test options falls back to the base payload without call keys."""
    payload = await _options_toggle_webhook(
        hass,
        mock_config_entry_data_none,
        enable=True,
        device_config=RuntimeError("read failed") if use_error else mock_device_config,
    )

    assert _MAKE_CALL_KEY not in payload
    assert _HANG_UP_KEY not in payload
    assert payload["Config.Features.ACTIONURL.Enable"] == "1"


@pytest.mark.parametrize("push", ["succeeds", "fails", "fails_after_unload"])
async def test_options_webhook_change_cancels_reconcile_first(
    hass: HomeAssistant,
    mock_config_entry_data_webhook: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
    push: str,
) -> None:
    """Test webhook changes cancel reconciliation, resuming it if still loaded."""
    started = asyncio.Event()
    never = asyncio.Event()

    async def _blocking_set(_payload: dict[str, str]) -> None:
        """Block the reconciliation write until cancelled."""
        started.set()
        await never.wait()

    mock_akuvox_device.get_device_config = AsyncMock(
        return_value=mock_device_config_factory(**{_MAKE_CALL_KEY: ""}),
    )
    mock_akuvox_device.set_device_config = AsyncMock(side_effect=_blocking_set)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_webhook,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await asyncio.wait_for(started.wait(), timeout=1)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    task = coordinator.action_url_reconcile_task
    observed: dict[str, bool] = {}

    async def _record_push(_payload: dict[str, str]) -> None:
        """Record whether reconciliation finished before the push."""
        observed["done"] = task.done()
        if push == "fails_after_unload":
            assert await hass.config_entries.async_unload(entry.entry_id)
        if push != "succeeds":
            raise RuntimeError("device offline")

    mock_akuvox_device.set_device_config = AsyncMock(return_value=None)
    with patch(
        "custom_components.local_akuvox.options_flow.AkuvoxDevice",
    ) as mock_cls:
        device = mock_cls.return_value
        device.__aenter__ = AsyncMock(return_value=device)
        device.__aexit__ = AsyncMock(return_value=None)
        device.get_device_config = AsyncMock(return_value={})
        device.set_device_config = AsyncMock(side_effect=_record_push)

        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: MOCK_HOST,
                CONF_USE_SSL: False,
                CONF_VERIFY_SSL: True,
                CONF_AUTH_METHOD: AUTH_NONE,
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
                CONF_WEBHOOK_ENABLED: False,
            },
        )
        await hass.async_block_till_done(wait_background_tasks=True)

    assert observed == {"done": True}
    assert task.cancelled()
    if push == "succeeds":
        assert result["type"] is FlowResultType.CREATE_ENTRY
        return
    assert result["errors"] == {"base": "webhook_push_failed"}
    if push == "fails_after_unload":
        assert coordinator.action_url_reconcile_task is task
        mock_akuvox_device.set_device_config.assert_not_awaited()
        return
    restarted = coordinator.action_url_reconcile_task
    assert restarted is not task
    assert restarted.done()
    mock_akuvox_device.set_device_config.assert_awaited_once()
