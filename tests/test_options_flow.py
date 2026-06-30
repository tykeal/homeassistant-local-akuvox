# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Akuvox options flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

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

    with patch(
        "custom_components.local_akuvox.options_flow.build_action_urls",
        side_effect=RuntimeError("no url"),
    ):
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
