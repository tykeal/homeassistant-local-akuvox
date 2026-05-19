# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Tests for _create_device request_delay handling."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pylocal_akuvox import DeviceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.local_akuvox.const import (
    AUTH_NONE,
    CONF_AUTH_METHOD,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_REQUEST_DELAY,
    CONF_USE_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    CONF_WEBHOOK_ENABLED,
    DEFAULT_REQUEST_DELAY,
    DOMAIN,
)
from tests.conftest import MOCK_MAC


def _make_entry(
    data: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> MockConfigEntry:
    """Create a MockConfigEntry with given data/options."""
    return MockConfigEntry(
        domain=DOMAIN,
        data=data,
        options=options or {},
        unique_id="AA:BB:CC:DD:EE:FF",
    )


def test_create_device_uses_default_request_delay() -> None:
    """Test _create_device uses DEFAULT_REQUEST_DELAY when not set."""
    from custom_components.local_akuvox import _create_device

    entry = _make_entry(
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USE_SSL: False,
            CONF_VERIFY_SSL: True,
        },
    )

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        _create_device(entry)
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["request_delay"] == DEFAULT_REQUEST_DELAY


def test_create_device_uses_configured_request_delay() -> None:
    """Test _create_device passes custom request_delay from options."""
    from custom_components.local_akuvox import _create_device

    entry = _make_entry(
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USE_SSL: False,
            CONF_VERIFY_SSL: True,
        },
        options={
            CONF_REQUEST_DELAY: 1.5,
        },
    )

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        _create_device(entry)
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["request_delay"] == 1.5


def test_create_device_request_delay_from_data_fallback() -> None:
    """Test _create_device falls back to data when options missing."""
    from custom_components.local_akuvox import _create_device

    entry = _make_entry(
        data={
            CONF_HOST: "192.168.1.100",
            CONF_USE_SSL: False,
            CONF_VERIFY_SSL: True,
            CONF_REQUEST_DELAY: 2.0,
        },
    )

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        _create_device(entry)
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["request_delay"] == 2.0


def test_options_schema_rejects_request_delay_above_max() -> None:
    """Test options schema rejects request_delay > 5.0."""
    from custom_components.local_akuvox.config_flow import (
        AkuvoxOptionsFlow,
    )

    flow = AkuvoxOptionsFlow.__new__(AkuvoxOptionsFlow)
    schema = flow._build_schema({CONF_HOST: "192.168.1.100"})

    with pytest.raises(vol.MultipleInvalid):
        schema(
            {
                CONF_HOST: "192.168.1.100",
                CONF_USE_SSL: False,
                CONF_VERIFY_SSL: True,
                CONF_AUTH_METHOD: AUTH_NONE,
                CONF_WEBHOOK_ENABLED: False,
                CONF_REQUEST_DELAY: 6.0,
            }
        )


def test_options_schema_rejects_request_delay_below_min() -> None:
    """Test options schema rejects request_delay < 0.0."""
    from custom_components.local_akuvox.config_flow import (
        AkuvoxOptionsFlow,
    )

    flow = AkuvoxOptionsFlow.__new__(AkuvoxOptionsFlow)
    schema = flow._build_schema({CONF_HOST: "192.168.1.100"})

    with pytest.raises(vol.MultipleInvalid):
        schema(
            {
                CONF_HOST: "192.168.1.100",
                CONF_USE_SSL: False,
                CONF_VERIFY_SSL: True,
                CONF_AUTH_METHOD: AUTH_NONE,
                CONF_WEBHOOK_ENABLED: False,
                CONF_REQUEST_DELAY: -0.1,
            }
        )


def test_options_schema_accepts_valid_request_delay() -> None:
    """Test options schema accepts request_delay in range."""
    from custom_components.local_akuvox.config_flow import (
        AkuvoxOptionsFlow,
    )

    flow = AkuvoxOptionsFlow.__new__(AkuvoxOptionsFlow)
    schema = flow._build_schema({CONF_HOST: "192.168.1.100"})

    result = schema(
        {
            CONF_HOST: "192.168.1.100",
            CONF_USE_SSL: False,
            CONF_VERIFY_SSL: True,
            CONF_AUTH_METHOD: AUTH_NONE,
            CONF_WEBHOOK_ENABLED: False,
            CONF_REQUEST_DELAY: 3.0,
        }
    )
    assert result[CONF_REQUEST_DELAY] == 3.0


async def test_options_flow_saves_request_delay(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test options flow persists request_delay to entry options."""
    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        device = mock_cls.return_value
        device.get_info = AsyncMock(
            return_value=DeviceInfo(
                model="E21V",
                mac_address=MOCK_MAC,
                firmware_version="1.0.0",
                hardware_version="2.0.0",
            ),
        )
        device.get_relay_status = AsyncMock(
            return_value={"RelayA": 0},
        )
        device.trigger_relay = AsyncMock(return_value=None)
        device.get_device_config = AsyncMock(
            return_value=mock_device_config,
        )
        device.__aenter__ = AsyncMock(return_value=device)
        device.__aexit__ = AsyncMock(return_value=None)

        entry = MockConfigEntry(
            domain=DOMAIN,
            data=mock_config_entry_data_none,
            unique_id=MOCK_MAC.lower().replace(":", ""),
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "192.168.1.100",
                CONF_USE_SSL: False,
                CONF_VERIFY_SSL: True,
                CONF_AUTH_METHOD: AUTH_NONE,
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
                CONF_REQUEST_DELAY: 1.0,
                CONF_WEBHOOK_ENABLED: False,
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert entry.options[CONF_REQUEST_DELAY] == 1.0
