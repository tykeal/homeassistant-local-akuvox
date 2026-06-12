# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Akuvox config flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pylocal_akuvox import (
    AkuvoxAuthenticationError,
    AkuvoxConnectionError,
    AkuvoxError,
    DeviceInfo,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.local_akuvox.const import (
    AUTH_BASIC,
    AUTH_DIGEST,
    AUTH_NONE,
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
from tests.conftest import MOCK_HOST, MOCK_MAC


async def test_user_step_shows_form(
    hass: HomeAssistant,
) -> None:
    """Test user step shows the host form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_user_step_rejects_empty_host(
    hass: HomeAssistant,
) -> None:
    """Test user step rejects empty host with invalid_host error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "   ", CONF_USE_SSL: False},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] is not None
    assert result["errors"]["base"] == "invalid_host"


async def test_ssl_step_appears_when_use_ssl_true(
    hass: HomeAssistant,
) -> None:
    """Test SSL step appears when use_ssl is True."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: MOCK_HOST, CONF_USE_SSL: True},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "ssl"


async def test_ssl_step_skipped_when_use_ssl_false(
    hass: HomeAssistant,
) -> None:
    """Test SSL step is skipped when use_ssl is False."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: MOCK_HOST, CONF_USE_SSL: False},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "auth"


async def test_auth_step_shows_three_options(
    hass: HomeAssistant,
) -> None:
    """Test auth step shows 3 user-facing auth options."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: MOCK_HOST, CONF_USE_SSL: False},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "auth"


async def test_credentials_step_appears_for_basic(
    hass: HomeAssistant,
) -> None:
    """Test credentials step appears for basic auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: MOCK_HOST, CONF_USE_SSL: False},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_AUTH_METHOD: AUTH_BASIC},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"


async def test_credentials_step_appears_for_digest(
    hass: HomeAssistant,
) -> None:
    """Test credentials step appears for digest auth."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: MOCK_HOST, CONF_USE_SSL: False},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_AUTH_METHOD: AUTH_DIGEST},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "credentials"


async def test_credentials_step_skipped_for_none(
    hass: HomeAssistant,
) -> None:
    """Test credentials step skipped for none/allowlist."""
    with (
        patch(
            "custom_components.local_akuvox.config_flow.AkuvoxDevice",
        ) as mock_cls,
        patch(
            "custom_components.local_akuvox._create_device",
        ) as mock_create,
    ):
        device = mock_cls.return_value
        device.get_info = AsyncMock(
            return_value=DeviceInfo(
                model="E21V",
                mac_address=MOCK_MAC,
                firmware_version="1.0.0",
                hardware_version="2.0.0",
            ),
        )

        setup_device = AsyncMock()
        setup_device.__aenter__ = AsyncMock(return_value=setup_device)
        setup_device.__aexit__ = AsyncMock(return_value=None)
        setup_device.get_info = AsyncMock(
            return_value=DeviceInfo(
                model="E21V",
                mac_address=MOCK_MAC,
                firmware_version="1.0.0",
                hardware_version="2.0.0",
            ),
        )
        setup_device.get_relay_status = AsyncMock(
            return_value={"RelayA": "closed"},
        )
        setup_device.get_device_config = AsyncMock(return_value={})
        mock_create.return_value = setup_device

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: MOCK_HOST, CONF_USE_SSL: False},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_AUTH_METHOD: AUTH_NONE},
        )
        # Now at webhook step
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "webhook"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_WEBHOOK_ENABLED: False},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_successful_connection_creates_entry(
    hass: HomeAssistant,
) -> None:
    """Test successful connection creates config entry."""
    with (
        patch(
            "custom_components.local_akuvox.config_flow.AkuvoxDevice",
        ) as mock_cls,
        patch(
            "custom_components.local_akuvox._create_device",
        ) as mock_create,
    ):
        device = mock_cls.return_value
        device.get_info = AsyncMock(
            return_value=DeviceInfo(
                model="E21V",
                mac_address=MOCK_MAC,
                firmware_version="1.0.0",
                hardware_version="2.0.0",
            ),
        )

        setup_device = AsyncMock()
        setup_device.__aenter__ = AsyncMock(return_value=setup_device)
        setup_device.__aexit__ = AsyncMock(return_value=None)
        setup_device.get_info = AsyncMock(
            return_value=DeviceInfo(
                model="E21V",
                mac_address=MOCK_MAC,
                firmware_version="1.0.0",
                hardware_version="2.0.0",
            ),
        )
        setup_device.get_relay_status = AsyncMock(
            return_value={"RelayA": "closed"},
        )
        setup_device.get_device_config = AsyncMock(return_value={})
        mock_create.return_value = setup_device

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: MOCK_HOST, CONF_USE_SSL: False},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_AUTH_METHOD: AUTH_BASIC},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "admin", CONF_PASSWORD: "password"},
        )
        # Now at webhook step
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "webhook"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_WEBHOOK_ENABLED: False},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["title"] == "Akuvox E21V"
        assert result["data"][CONF_HOST] == MOCK_HOST
        assert result["data"][CONF_AUTH_METHOD] == AUTH_BASIC


async def test_cannot_connect_error(
    hass: HomeAssistant,
) -> None:
    """Test cannot_connect error on AkuvoxConnectionError."""
    with patch(
        "custom_components.local_akuvox.config_flow.AkuvoxDevice",
    ) as mock_cls:
        device = mock_cls.return_value
        device.get_info = AsyncMock(
            side_effect=AkuvoxConnectionError("Cannot connect"),
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: MOCK_HOST, CONF_USE_SSL: False},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_AUTH_METHOD: AUTH_NONE},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] is not None
        assert result["errors"]["base"] == "cannot_connect"


async def test_invalid_auth_error(
    hass: HomeAssistant,
) -> None:
    """Test invalid_auth error on AkuvoxAuthenticationError."""
    with patch(
        "custom_components.local_akuvox.config_flow.AkuvoxDevice",
    ) as mock_cls:
        device = mock_cls.return_value
        device.get_info = AsyncMock(
            side_effect=AkuvoxAuthenticationError("Bad auth"),
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: MOCK_HOST, CONF_USE_SSL: False},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_AUTH_METHOD: AUTH_BASIC},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: "admin", CONF_PASSWORD: "wrong"},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] is not None
        assert result["errors"]["base"] == "invalid_auth"


async def test_already_configured_aborts(
    hass: HomeAssistant,
) -> None:
    """Test already_configured aborts on duplicate MAC."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.200"},
        unique_id=MOCK_MAC.lower().replace(":", ""),
    )
    existing.add_to_hass(hass)

    with patch(
        "custom_components.local_akuvox.config_flow.AkuvoxDevice",
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

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: MOCK_HOST, CONF_USE_SSL: False},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_AUTH_METHOD: AUTH_NONE},
        )
        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


async def test_unknown_error(
    hass: HomeAssistant,
) -> None:
    """Test unknown error on generic AkuvoxError."""
    with patch(
        "custom_components.local_akuvox.config_flow.AkuvoxDevice",
    ) as mock_cls:
        device = mock_cls.return_value
        device.get_info = AsyncMock(
            side_effect=AkuvoxError("Something went wrong"),
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: MOCK_HOST, CONF_USE_SSL: False},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_AUTH_METHOD: AUTH_NONE},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] is not None
        assert result["errors"]["base"] == "unknown"


# --- Options Flow Tests ---


async def test_options_flow_shows_current_values(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test options flow init step shows form with current values."""
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
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

        schema = result["data_schema"]
        assert schema is not None
        validated = schema({})
        assert validated[CONF_HOST] == mock_config_entry_data_none[CONF_HOST]
        assert validated[CONF_USE_SSL] == mock_config_entry_data_none[CONF_USE_SSL]
        assert (
            validated[CONF_VERIFY_SSL] == mock_config_entry_data_none[CONF_VERIFY_SSL]
        )
        assert (
            validated[CONF_AUTH_METHOD] == mock_config_entry_data_none[CONF_AUTH_METHOD]
        )


async def test_options_flow_updates_entry(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test options flow saves updated values to entry.options."""
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
                CONF_HOST: "192.168.1.200",
                CONF_USE_SSL: True,
                CONF_VERIFY_SSL: False,
                CONF_AUTH_METHOD: AUTH_NONE,
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
            },
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert entry.options[CONF_HOST] == "192.168.1.200"
        assert entry.options[CONF_USE_SSL] is True
        assert entry.options[CONF_VERIFY_SSL] is False


async def test_options_flow_triggers_reload(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test integration reloads after options change."""
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

        with patch.object(
            hass.config_entries,
            "async_reload",
        ) as mock_reload:
            result = await hass.config_entries.options.async_init(
                entry.entry_id,
            )
            result = await hass.config_entries.options.async_configure(
                result["flow_id"],
                user_input={
                    CONF_HOST: MOCK_HOST,
                    CONF_USE_SSL: False,
                    CONF_VERIFY_SSL: True,
                    CONF_AUTH_METHOD: AUTH_NONE,
                    CONF_USERNAME: "",
                    CONF_PASSWORD: "",
                },
            )
            await hass.async_block_till_done()
            mock_reload.assert_awaited_once_with(entry.entry_id)


async def test_options_flow_rejects_empty_host(
    hass: HomeAssistant,
    mock_relay_status: dict[str, Any],
    mock_device_info: DeviceInfo,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test options flow rejects empty host with invalid_host error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.local_akuvox.AkuvoxDevice",
            autospec=True,
        ) as mock_cls,
    ):
        instance = mock_cls.return_value
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.get_relay_status = AsyncMock(return_value=mock_relay_status)
        instance.get_info = AsyncMock(return_value=mock_device_info)
        instance.get_device_config = AsyncMock(
            return_value=mock_device_config,
        )
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(
        entry.entry_id,
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "",
            CONF_USE_SSL: False,
            CONF_VERIFY_SSL: True,
            CONF_AUTH_METHOD: AUTH_NONE,
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_host"}


async def test_options_flow_rejects_whitespace_host(
    hass: HomeAssistant,
    mock_relay_status: dict[str, Any],
    mock_device_info: DeviceInfo,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test options flow rejects whitespace-only host."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.local_akuvox.AkuvoxDevice",
            autospec=True,
        ) as mock_cls,
    ):
        instance = mock_cls.return_value
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.get_relay_status = AsyncMock(return_value=mock_relay_status)
        instance.get_info = AsyncMock(return_value=mock_device_info)
        instance.get_device_config = AsyncMock(
            return_value=mock_device_config,
        )
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(
        entry.entry_id,
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "   ",
            CONF_USE_SSL: False,
            CONF_VERIFY_SSL: True,
            CONF_AUTH_METHOD: AUTH_NONE,
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_host"}


async def test_options_flow_rejects_missing_credentials(
    hass: HomeAssistant,
    mock_relay_status: dict[str, Any],
    mock_device_info: DeviceInfo,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test options flow rejects auth methods without credentials."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.local_akuvox.AkuvoxDevice",
            autospec=True,
        ) as mock_cls,
    ):
        instance = mock_cls.return_value
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.get_relay_status = AsyncMock(return_value=mock_relay_status)
        instance.get_info = AsyncMock(return_value=mock_device_info)
        instance.get_device_config = AsyncMock(
            return_value=mock_device_config,
        )
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(
        entry.entry_id,
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: MOCK_HOST,
            CONF_USE_SSL: False,
            CONF_VERIFY_SSL: True,
            CONF_AUTH_METHOD: AUTH_BASIC,
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_options_flow_host_error_takes_precedence(
    hass: HomeAssistant,
    mock_relay_status: dict[str, Any],
    mock_device_info: DeviceInfo,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test invalid_host error is not overwritten by invalid_auth."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.local_akuvox.AkuvoxDevice",
            autospec=True,
        ) as mock_cls,
    ):
        instance = mock_cls.return_value
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.get_relay_status = AsyncMock(return_value=mock_relay_status)
        instance.get_info = AsyncMock(return_value=mock_device_info)
        instance.get_device_config = AsyncMock(
            return_value=mock_device_config,
        )
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(
        entry.entry_id,
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: "   ",
            CONF_USE_SSL: False,
            CONF_VERIFY_SSL: True,
            CONF_AUTH_METHOD: AUTH_BASIC,
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_host"}


# --- Config Flow Webhook Step Tests ---


async def test_webhook_step_shows_form(
    hass: HomeAssistant,
) -> None:
    """Test webhook step shows form after connection test."""
    with patch(
        "custom_components.local_akuvox.config_flow.AkuvoxDevice",
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

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: MOCK_HOST, CONF_USE_SSL: False},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_AUTH_METHOD: AUTH_NONE},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "webhook"


async def test_webhook_disabled_creates_entry(
    hass: HomeAssistant,
) -> None:
    """Test disabling webhook creates entry with no webhook config."""
    with (
        patch(
            "custom_components.local_akuvox.config_flow.AkuvoxDevice",
        ) as mock_cls,
        patch(
            "custom_components.local_akuvox._create_device",
        ) as mock_create,
    ):
        device = mock_cls.return_value
        device.get_info = AsyncMock(
            return_value=DeviceInfo(
                model="E21V",
                mac_address=MOCK_MAC,
                firmware_version="1.0.0",
                hardware_version="2.0.0",
            ),
        )

        setup_device = AsyncMock()
        setup_device.__aenter__ = AsyncMock(return_value=setup_device)
        setup_device.__aexit__ = AsyncMock(return_value=None)
        setup_device.get_info = AsyncMock(
            return_value=DeviceInfo(
                model="E21V",
                mac_address=MOCK_MAC,
                firmware_version="1.0.0",
                hardware_version="2.0.0",
            ),
        )
        setup_device.get_relay_status = AsyncMock(
            return_value={"RelayA": "closed"},
        )
        setup_device.get_device_config = AsyncMock(return_value={})
        mock_create.return_value = setup_device

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: MOCK_HOST, CONF_USE_SSL: False},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_AUTH_METHOD: AUTH_NONE},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_WEBHOOK_ENABLED: False},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_WEBHOOK_ID] is None
    assert result["data"][CONF_WEBHOOK_ENABLED] is False


async def test_webhook_enabled_pushes_config(
    hass: HomeAssistant,
) -> None:
    """Test enabling webhook pushes action URLs to device."""
    with (
        patch(
            "custom_components.local_akuvox.config_flow.AkuvoxDevice",
        ) as mock_cls,
        patch(
            "custom_components.local_akuvox._create_device",
        ) as mock_create,
    ):
        device = mock_cls.return_value
        device.get_info = AsyncMock(
            return_value=DeviceInfo(
                model="E21V",
                mac_address=MOCK_MAC,
                firmware_version="1.0.0",
                hardware_version="2.0.0",
            ),
        )
        device.set_device_config = AsyncMock(return_value=None)
        device.__aenter__ = AsyncMock(return_value=device)
        device.__aexit__ = AsyncMock(return_value=None)

        setup_device = AsyncMock()
        setup_device.__aenter__ = AsyncMock(return_value=setup_device)
        setup_device.__aexit__ = AsyncMock(return_value=None)
        setup_device.get_info = AsyncMock(
            return_value=DeviceInfo(
                model="E21V",
                mac_address=MOCK_MAC,
                firmware_version="1.0.0",
                hardware_version="2.0.0",
            ),
        )
        setup_device.get_relay_status = AsyncMock(
            return_value={"RelayA": "closed"},
        )
        setup_device.get_device_config = AsyncMock(return_value={})
        mock_create.return_value = setup_device

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: MOCK_HOST, CONF_USE_SSL: False},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_AUTH_METHOD: AUTH_NONE},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_WEBHOOK_ENABLED: True},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_WEBHOOK_ENABLED] is True
    assert result["data"][CONF_WEBHOOK_ID] is not None
    assert len(result["data"][CONF_WEBHOOK_ID]) == 64
    device.set_device_config.assert_awaited_once()


async def test_webhook_push_fails_shows_error(
    hass: HomeAssistant,
) -> None:
    """Test failed webhook push shows error and allows retry."""
    with patch(
        "custom_components.local_akuvox.config_flow.AkuvoxDevice",
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
        device.set_device_config = AsyncMock(
            side_effect=AkuvoxError("Push failed"),
        )
        device.__aenter__ = AsyncMock(return_value=device)
        device.__aexit__ = AsyncMock(return_value=None)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: MOCK_HOST, CONF_USE_SSL: False},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_AUTH_METHOD: AUTH_NONE},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_WEBHOOK_ENABLED: True},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "webhook"
    assert result["errors"] == {"base": "webhook_push_failed"}


async def test_webhook_push_fails_then_skip(
    hass: HomeAssistant,
) -> None:
    """Test user can skip webhook after push failure."""
    with (
        patch(
            "custom_components.local_akuvox.config_flow.AkuvoxDevice",
        ) as mock_cls,
        patch(
            "custom_components.local_akuvox._create_device",
        ) as mock_create,
    ):
        device = mock_cls.return_value
        device.get_info = AsyncMock(
            return_value=DeviceInfo(
                model="E21V",
                mac_address=MOCK_MAC,
                firmware_version="1.0.0",
                hardware_version="2.0.0",
            ),
        )
        device.set_device_config = AsyncMock(
            side_effect=AkuvoxError("Push failed"),
        )
        device.__aenter__ = AsyncMock(return_value=device)
        device.__aexit__ = AsyncMock(return_value=None)

        setup_device = AsyncMock()
        setup_device.__aenter__ = AsyncMock(return_value=setup_device)
        setup_device.__aexit__ = AsyncMock(return_value=None)
        setup_device.get_info = AsyncMock(
            return_value=DeviceInfo(
                model="E21V",
                mac_address=MOCK_MAC,
                firmware_version="1.0.0",
                hardware_version="2.0.0",
            ),
        )
        setup_device.get_relay_status = AsyncMock(
            return_value={"RelayA": "closed"},
        )
        setup_device.get_device_config = AsyncMock(return_value={})
        mock_create.return_value = setup_device

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: MOCK_HOST, CONF_USE_SSL: False},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_AUTH_METHOD: AUTH_NONE},
        )
        # First attempt fails
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_WEBHOOK_ENABLED: True},
        )
        assert result["errors"] == {"base": "webhook_push_failed"}

        # User skips
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_WEBHOOK_ENABLED: False},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_WEBHOOK_ENABLED] is False
    assert result["data"][CONF_WEBHOOK_ID] is None


# --- Options Flow Webhook Tests ---


async def test_options_webhook_enable(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test options flow enables webhook and pushes config."""
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
        device.set_device_config = AsyncMock(return_value=None)
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

    with (
        patch(
            "custom_components.local_akuvox.options_flow.AkuvoxDevice",
        ) as mock_flow_cls,
        patch(
            "custom_components.local_akuvox._create_device",
        ) as mock_create,
    ):
        flow_dev = mock_flow_cls.return_value
        flow_dev.set_device_config = AsyncMock(return_value=None)
        flow_dev.__aenter__ = AsyncMock(return_value=flow_dev)
        flow_dev.__aexit__ = AsyncMock(return_value=None)

        setup_device = AsyncMock()
        setup_device.__aenter__ = AsyncMock(return_value=setup_device)
        setup_device.__aexit__ = AsyncMock(return_value=None)
        setup_device.get_info = AsyncMock(
            return_value=DeviceInfo(
                model="E21V",
                mac_address=MOCK_MAC,
                firmware_version="1.0.0",
                hardware_version="2.0.0",
            ),
        )
        setup_device.get_relay_status = AsyncMock(
            return_value={"RelayA": "closed"},
        )
        setup_device.get_device_config = AsyncMock(return_value={})
        mock_create.return_value = setup_device

        result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )
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

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_WEBHOOK_ENABLED] is True
    assert entry.options[CONF_WEBHOOK_ID] is not None


async def test_options_webhook_disable(
    hass: HomeAssistant,
    mock_config_entry_data_webhook: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test options flow disables webhook and pushes clear config."""
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
        device.set_device_config = AsyncMock(return_value=None)
        device.__aenter__ = AsyncMock(return_value=device)
        device.__aexit__ = AsyncMock(return_value=None)

        entry = MockConfigEntry(
            domain=DOMAIN,
            data=mock_config_entry_data_webhook,
            unique_id=MOCK_MAC.lower().replace(":", ""),
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    with (
        patch(
            "custom_components.local_akuvox.options_flow.AkuvoxDevice",
        ) as mock_flow_cls,
        patch(
            "custom_components.local_akuvox._create_device",
        ) as mock_create,
    ):
        flow_dev = mock_flow_cls.return_value
        flow_dev.set_device_config = AsyncMock(return_value=None)
        flow_dev.__aenter__ = AsyncMock(return_value=flow_dev)
        flow_dev.__aexit__ = AsyncMock(return_value=None)

        setup_device = AsyncMock()
        setup_device.__aenter__ = AsyncMock(return_value=setup_device)
        setup_device.__aexit__ = AsyncMock(return_value=None)
        setup_device.get_info = AsyncMock(
            return_value=DeviceInfo(
                model="E21V",
                mac_address=MOCK_MAC,
                firmware_version="1.0.0",
                hardware_version="2.0.0",
            ),
        )
        setup_device.get_relay_status = AsyncMock(
            return_value={"RelayA": "closed"},
        )
        setup_device.get_device_config = AsyncMock(return_value={})
        mock_create.return_value = setup_device

        result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )
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


async def test_options_webhook_push_fails(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test options flow shows error on webhook push failure."""
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

    with patch(
        "custom_components.local_akuvox.options_flow.AkuvoxDevice",
    ) as mock_flow_cls:
        flow_dev = mock_flow_cls.return_value
        flow_dev.set_device_config = AsyncMock(
            side_effect=AkuvoxError("Push failed"),
        )
        flow_dev.__aenter__ = AsyncMock(return_value=flow_dev)
        flow_dev.__aexit__ = AsyncMock(return_value=None)

        result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )
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
