# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Akuvox coordinator."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from pylocal_akuvox import (
    AkuvoxAuthenticationError,
    AkuvoxConnectionError,
    AkuvoxDeviceError,
    AkuvoxParseError,
    DeviceInfo,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.local_akuvox.const import (
    CONFIG_KEY_LOCATION,
    CONFIG_KEY_RELAY_HOLD_DELAY,
    CONFIG_KEY_RELAY_MODE_SUFFIX,
    CONFIG_KEY_RELAY_NAME,
    CONFIG_KEY_RELAY_PREFIX,
    CONFIG_KEY_RELAY_TYPE_SUFFIX,
    DEFAULT_HOLD_DELAY_SECONDS,
    DEFAULT_RELAY_MODE,
    DEFAULT_RELAY_TYPE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from custom_components.local_akuvox.coordinator import (
    AkuvoxCoordinatorData,
    AkuvoxDataUpdateCoordinator,
)
from custom_components.local_akuvox.relay_config import (
    RelayConfig,
    _build_relay_config,
    _parse_config_int,
)
from tests.conftest import MOCK_MAC


async def test_coordinator_fetches_data(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test coordinator fetches device info and relay status."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(return_value=mock_device_config)

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)
    data = await coordinator._async_update_data()

    assert isinstance(data, AkuvoxCoordinatorData)
    assert data.device_info == mock_device_info
    assert data.relay_status == mock_relay_status
    device.get_relay_status.assert_awaited_once()
    device.get_info.assert_awaited_once()


async def test_coordinator_update_failed_on_connection_error(
    hass: HomeAssistant,
) -> None:
    """Test coordinator raises UpdateFailed on AkuvoxConnectionError."""
    device = AsyncMock()
    device.get_relay_status = AsyncMock(
        side_effect=AkuvoxConnectionError("Connection failed"),
    )

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_update_failed_on_device_error(
    hass: HomeAssistant,
) -> None:
    """Test coordinator raises UpdateFailed on AkuvoxDeviceError."""
    device = AsyncMock()
    device.get_relay_status = AsyncMock(
        side_effect=AkuvoxDeviceError("Device error"),
    )

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_update_failed_on_parse_error(
    hass: HomeAssistant,
) -> None:
    """Test coordinator raises UpdateFailed on AkuvoxParseError."""
    device = AsyncMock()
    device.get_relay_status = AsyncMock(
        side_effect=AkuvoxParseError("Parse error"),
    )

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_auth_failed_on_auth_error(
    hass: HomeAssistant,
) -> None:
    """Test coordinator raises ConfigEntryAuthFailed on auth error."""
    device = AsyncMock()
    device.get_relay_status = AsyncMock(
        side_effect=AkuvoxAuthenticationError("Auth failed"),
    )

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_coordinator_caches_device_info(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test coordinator caches device_info after first call."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(return_value=mock_device_config)

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)

    # First call should fetch device info
    await coordinator._async_update_data()
    assert device.get_info.await_count == 1

    # Second call should use cached device info
    await coordinator._async_update_data()
    assert device.get_info.await_count == 1


async def test_coordinator_update_interval(
    hass: HomeAssistant,
) -> None:
    """Test coordinator uses 30s update interval."""
    device = AsyncMock()
    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)
    assert coordinator.update_interval == timedelta(
        seconds=DEFAULT_SCAN_INTERVAL,
    )


async def test_coordinator_user_cache_lookup(
    hass: HomeAssistant,
    mock_user_list: list[Any],
) -> None:
    """Test updating the user cache enables PIN lookups."""
    device = AsyncMock()
    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)

    coordinator.update_user_cache(mock_user_list)

    assert coordinator.get_user_by_pin("1234") == mock_user_list[0]
    assert coordinator.get_user_by_pin("0000") is None


async def test_coordinator_defaults_when_config_api_missing(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
) -> None:
    """Test missing get_device_config applies default relay config."""
    device = MagicMock(spec=["get_info", "get_relay_status", "list_users"])
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.list_users = AsyncMock(return_value=[])
    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)

    data = await coordinator._async_update_data()

    assert data.device_name == "Akuvox E21V"
    assert data.relay_configs == {"A": RelayConfig()}


async def test_coordinator_config_auth_error_raises_auth_failed(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
) -> None:
    """Test auth failure during config fetch raises auth failed."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(
        side_effect=AkuvoxAuthenticationError("bad credentials"),
    )
    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)

    with pytest.raises(ConfigEntryAuthFailed, match="config fetch"):
        await coordinator._async_update_data()


async def test_coordinator_logs_unexpected_user_fetch_error(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test unexpected user fetch errors keep an empty cache."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(return_value=mock_device_config)
    device.list_users = AsyncMock(side_effect=RuntimeError("boom"))
    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)

    data = await coordinator._async_update_data()

    assert data.users == []


@pytest.mark.parametrize(
    ("lib_exc", "ha_exc", "message"),
    [
        (AkuvoxAuthenticationError, ConfigEntryAuthFailed, "Authentication failed"),
        (AkuvoxConnectionError, UpdateFailed, "Failed to get device info"),
        (AkuvoxDeviceError, UpdateFailed, "Failed to get device info"),
        (AkuvoxParseError, UpdateFailed, "Failed to get device info"),
    ],
    ids=["auth", "connection", "device", "parse"],
)
async def test_coordinator_device_info_errors(
    hass: HomeAssistant,
    mock_relay_status: dict[str, Any],
    lib_exc: type[Exception],
    ha_exc: type[Exception],
    message: str,
) -> None:
    """Test device info fetch errors map to HA exceptions."""
    device = AsyncMock()
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_info = AsyncMock(side_effect=lib_exc("fail"))
    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)

    with pytest.raises(ha_exc, match=message):
        await coordinator._async_update_data()


async def test_state_reflects_relay_change_after_update(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test entity state changes when coordinator data changes.

    After a coordinator refresh with a new relay state, the lock
    entity must reflect the updated value.
    """
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value={"RelayA": 0})
    device.trigger_relay = AsyncMock(return_value=None)
    device.get_device_config = AsyncMock(return_value=mock_device_config)
    device.__aenter__ = AsyncMock(return_value=device)
    device.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        mock_cls.return_value = device

        entry = MockConfigEntry(
            domain=DOMAIN,
            data=mock_config_entry_data_none,
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "locked"

        # Change relay state to unlocked
        device.get_relay_status.return_value = {"RelayA": 1}

        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "unlocked"


async def test_entity_recovers_after_coordinator_failure(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test entity recovers to correct state after device comes back.

    After the coordinator fails (making entity unavailable), a
    subsequent successful update must restore the entity to the
    correct state within 2 coordinator update cycles (SC-004).
    """
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value={"RelayA": 0})
    device.trigger_relay = AsyncMock(return_value=None)
    device.get_device_config = AsyncMock(return_value=mock_device_config)
    device.__aenter__ = AsyncMock(return_value=device)
    device.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        mock_cls.return_value = device

        entry = MockConfigEntry(
            domain=DOMAIN,
            data=mock_config_entry_data_none,
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "locked"

        # Coordinator fails
        device.get_relay_status.side_effect = AkuvoxConnectionError(
            "Connection lost",
        )

        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "unavailable"

        # Device comes back online
        device.get_relay_status.side_effect = None
        device.get_relay_status.return_value = {"RelayA": 0}

        await coordinator.async_refresh()
        await hass.async_block_till_done()

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "locked"


async def test_coordinator_data_includes_multiple_relays(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_device_config: Any,
) -> None:
    """Test coordinator data includes status for all relays."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0, "RelayB": 1},
    )
    device.get_device_config = AsyncMock(return_value=mock_device_config)

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)
    data = await coordinator._async_update_data()

    assert "RelayA" in data.relay_status
    assert "RelayB" in data.relay_status
    assert data.relay_status["RelayA"] == 0
    assert data.relay_status["RelayB"] == 1


async def test_coordinator_multi_relay_state_change(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test coordinator updates propagate to correct relay entities.

    When only one relay changes state, only that entity should
    update while the other remains unchanged.
    """
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0, "RelayB": 0},
    )
    device.trigger_relay = AsyncMock(return_value=None)
    device.get_device_config = AsyncMock(return_value=mock_device_config)
    device.__aenter__ = AsyncMock(return_value=device)
    device.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        mock_cls.return_value = device

        entry = MockConfigEntry(
            domain=DOMAIN,
            data=mock_config_entry_data_none,
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Both locked
        state_a = hass.states.get("lock.testlab_intercom_front_gate")
        state_b = hass.states.get("lock.testlab_intercom_side_gate")
        assert state_a is not None
        assert state_b is not None
        assert state_a.state == "locked"
        assert state_b.state == "locked"

        # Only RelayB changes
        device.get_relay_status.return_value = {"RelayA": 0, "RelayB": 1}

        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        state_a = hass.states.get("lock.testlab_intercom_front_gate")
        state_b = hass.states.get("lock.testlab_intercom_side_gate")
        assert state_a is not None
        assert state_b is not None
        assert state_a.state == "locked"
        assert state_b.state == "unlocked"


def test_relay_config_defaults() -> None:
    """Test RelayConfig uses correct default values."""
    config = RelayConfig()
    assert config.name == ""
    assert config.hold_delay == DEFAULT_HOLD_DELAY_SECONDS
    assert config.relay_type == DEFAULT_RELAY_TYPE
    assert config.relay_mode == DEFAULT_RELAY_MODE


def test_relay_config_custom_values() -> None:
    """Test RelayConfig stores custom field values."""
    config = RelayConfig(
        name="Front Gate",
        hold_delay=10,
        relay_type=1,
        relay_mode=1,
    )
    assert config.name == "Front Gate"
    assert config.hold_delay == 10
    assert config.relay_type == 1
    assert config.relay_mode == 1


def test_relay_config_frozen() -> None:
    """Test RelayConfig is immutable (frozen)."""
    config = RelayConfig()
    with pytest.raises(AttributeError):
        config.name = "changed"  # type: ignore[misc]


def test_parse_config_int_valid() -> None:
    """Test _parse_config_int returns int for valid string."""
    assert _parse_config_int("42", default=0) == 42


def test_parse_config_int_non_numeric() -> None:
    """Test _parse_config_int returns default for non-numeric."""
    assert _parse_config_int("abc", default=5) == 5


def test_parse_config_int_empty() -> None:
    """Test _parse_config_int returns default for empty string."""
    assert _parse_config_int("", default=5) == 5


def test_parse_config_int_negative() -> None:
    """Test _parse_config_int returns default for negative value."""
    assert _parse_config_int("-1", default=5, min_val=0) == 5


def test_parse_config_int_above_max() -> None:
    """Test _parse_config_int returns default for value above max."""
    assert _parse_config_int("999", default=5, max_val=100) == 5


def test_parse_config_int_at_boundary() -> None:
    """Test _parse_config_int accepts boundary values."""
    assert _parse_config_int("0", default=5, min_val=0, max_val=10) == 0
    assert _parse_config_int("10", default=5, min_val=0, max_val=10) == 10


def test_parse_config_int_allowed_values() -> None:
    """Test _parse_config_int validates against allowed values."""
    assert _parse_config_int("1", default=0, allowed={0, 1}, key="AllowTest") == 1
    assert _parse_config_int("2", default=0, allowed={0, 1}, key="AllowTest") == 0


def test_parse_config_int_warns_on_invalid(caplog: Any) -> None:
    """Test _parse_config_int logs warning for invalid values."""
    _parse_config_int("bad", default=0, key="TestKey")
    assert "TestKey" in caplog.text


def test_build_relay_config_full(mock_device_config: Any) -> None:
    """Test _build_relay_config returns populated RelayConfig."""
    config = _build_relay_config(mock_device_config, "A")
    assert config.name == "Front Gate"
    assert config.hold_delay == 5
    assert config.relay_type == 0
    assert config.relay_mode == 0


def test_build_relay_config_empty() -> None:
    """Test _build_relay_config returns defaults for empty config."""
    from pylocal_akuvox import (
        DeviceConfig,
    )

    empty = DeviceConfig(data={})
    config = _build_relay_config(empty, "A")
    assert config.name == ""
    assert config.hold_delay == DEFAULT_HOLD_DELAY_SECONDS
    assert config.relay_type == DEFAULT_RELAY_TYPE
    assert config.relay_mode == DEFAULT_RELAY_MODE


def test_build_relay_config_partial(
    mock_device_config_factory: Any,
) -> None:
    """Test _build_relay_config fills defaults for missing keys."""
    partial = mock_device_config_factory(
        **{f"{CONFIG_KEY_RELAY_NAME}A": "Lobby Door"},
    )
    config = _build_relay_config(partial, "A")
    assert config.name == "Lobby Door"
    assert config.hold_delay == DEFAULT_HOLD_DELAY_SECONDS


# --- T010: Updated AkuvoxCoordinatorData tests ---


async def test_coordinator_data_includes_device_name(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test coordinator data includes device_name field."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(return_value=mock_device_config)

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)
    data = await coordinator._async_update_data()

    assert hasattr(data, "device_name")
    assert isinstance(data.device_name, str)


async def test_coordinator_data_includes_relay_configs(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_device_config: Any,
) -> None:
    """Test coordinator data includes relay_configs dict."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0, "RelayB": 1},
    )
    device.get_device_config = AsyncMock(return_value=mock_device_config)

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)
    data = await coordinator._async_update_data()

    assert hasattr(data, "relay_configs")
    assert isinstance(data.relay_configs, dict)
    assert "A" in data.relay_configs
    assert "B" in data.relay_configs
    assert isinstance(data.relay_configs["A"], RelayConfig)


# --- T011: DeviceConfig fetch on first poll ---


async def test_coordinator_fetches_config_on_first_poll(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test get_device_config called on first successful poll."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(return_value=mock_device_config)

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)
    data = await coordinator._async_update_data()

    device.get_device_config.assert_awaited_once()
    assert data.device_name == "TestLab Intercom"
    assert data.relay_configs["A"].name == "Front Gate"


async def test_coordinator_caches_device_config(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test config NOT re-fetched on normal successive polls."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(return_value=mock_device_config)

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)
    await coordinator._async_update_data()
    await coordinator._async_update_data()

    assert device.get_device_config.await_count == 1


# --- T012: Config fetch failure graceful degradation ---


async def test_coordinator_config_failure_first_time_uses_defaults(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
) -> None:
    """Test first config failure yields defaults."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(
        side_effect=AkuvoxConnectionError("Config fetch failed"),
    )

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)
    data = await coordinator._async_update_data()

    assert data.device_name == f"Akuvox {mock_device_info.model}"
    for letter in data.relay_configs:
        assert data.relay_configs[letter].name == ""
        assert data.relay_configs[letter].hold_delay == DEFAULT_HOLD_DELAY_SECONDS


async def test_coordinator_config_failure_subsequent_keeps_cached(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test subsequent config failure preserves cached values."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(return_value=mock_device_config)

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)

    # First poll succeeds
    data1 = await coordinator._async_update_data()
    assert data1.device_name == "TestLab Intercom"

    # Force reconnection to re-fetch config
    coordinator._was_unavailable = True
    device.get_device_config.side_effect = AkuvoxConnectionError(
        "Config fetch failed",
    )

    data2 = await coordinator._async_update_data()
    # Should retain cached values
    assert data2.device_name == "TestLab Intercom"
    assert data2.relay_configs["A"].name == "Front Gate"


# --- T013: _was_unavailable reconnection config refresh ---


async def test_coordinator_refetches_config_after_unavailable(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_device_config: Any,
) -> None:
    """Test config re-fetched after device recovers from failure."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value={"RelayA": 0})
    device.get_device_config = AsyncMock(return_value=mock_device_config)

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)

    # First successful poll
    await coordinator._async_update_data()
    assert device.get_device_config.await_count == 1

    # Simulate failure (sets _was_unavailable)
    device.get_relay_status.side_effect = AkuvoxConnectionError(
        "Lost connection",
    )
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    # Recovery — config should be re-fetched
    device.get_relay_status.side_effect = None
    device.get_relay_status.return_value = {"RelayA": 0}
    await coordinator._async_update_data()
    assert device.get_device_config.await_count == 2


async def test_coordinator_no_refetch_on_normal_polls(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test config NOT re-fetched on successive normal polls."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(return_value=mock_device_config)

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)

    await coordinator._async_update_data()
    await coordinator._async_update_data()
    await coordinator._async_update_data()

    assert device.get_device_config.await_count == 1


# ── T020: Name update on reconnection ───────────────────────────


async def test_device_name_updates_on_reconnection(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_device_config_factory: Any,
) -> None:
    """Test device_name updates when config changes after reconnect."""
    config_v1 = mock_device_config_factory(
        **{CONFIG_KEY_LOCATION: "Lobby"},
    )
    config_v2 = mock_device_config_factory(
        **{CONFIG_KEY_LOCATION: "Entrance"},
    )

    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value={"RelayA": 0})
    device.get_device_config = AsyncMock(return_value=config_v1)

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)

    # First poll — fetch config v1
    data = await coordinator._async_update_data()
    assert data.device_name == "Lobby"

    # Simulate unavailable
    device.get_relay_status.side_effect = AkuvoxConnectionError("down")
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    # Recovery with new config
    device.get_relay_status.side_effect = None
    device.get_relay_status.return_value = {"RelayA": 0}
    device.get_device_config = AsyncMock(return_value=config_v2)

    data = await coordinator._async_update_data()
    assert data.device_name == "Entrance"


# ── T036: Edge case tests for non-numeric/out-of-range config ────


def test_build_relay_config_hold_delay_non_numeric(
    mock_device_config_factory: Any,
    caplog: Any,
) -> None:
    """Test _build_relay_config falls back when HoldDelay is non-numeric."""
    cfg = mock_device_config_factory(
        **{f"{CONFIG_KEY_RELAY_HOLD_DELAY}A": "abc"},
    )
    result = _build_relay_config(cfg, "A")
    assert result.hold_delay == DEFAULT_HOLD_DELAY_SECONDS
    assert "abc" in caplog.text
    assert "HoldDelayA" in caplog.text
    assert f"default {DEFAULT_HOLD_DELAY_SECONDS}" in caplog.text


def test_build_relay_config_relay_type_out_of_range(
    mock_device_config_factory: Any,
    caplog: Any,
) -> None:
    """Test _build_relay_config falls back when RelayType is 99."""
    cfg = mock_device_config_factory(
        **{f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_TYPE_SUFFIX}": "99"},
    )
    result = _build_relay_config(cfg, "A")
    assert result.relay_type == DEFAULT_RELAY_TYPE
    assert "99" in caplog.text
    assert "RelayAType" in caplog.text
    assert f"default {DEFAULT_RELAY_TYPE}" in caplog.text


def test_build_relay_config_relay_mode_negative(
    mock_device_config_factory: Any,
    caplog: Any,
) -> None:
    """Test _build_relay_config falls back when RelayMode is -1."""
    cfg = mock_device_config_factory(
        **{f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "-1"},
    )
    result = _build_relay_config(cfg, "A")
    assert result.relay_mode == DEFAULT_RELAY_MODE
    assert "-1" in caplog.text
    assert "RelayAMode" in caplog.text
    assert f"default {DEFAULT_RELAY_MODE}" in caplog.text


# ── User cache tests (T003) ─────────────────────────────────


async def test_coordinator_populates_user_cache(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
    mock_device_config: Any,
    mock_user_list: list[Any],
) -> None:
    """Test coordinator populates users from list_users."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(return_value=mock_device_config)
    device.list_users = AsyncMock(return_value=mock_user_list)

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)
    data = await coordinator._async_update_data()

    assert data.users == mock_user_list
    device.list_users.assert_awaited_once_with(page=None)


async def test_coordinator_user_cache_empty_on_no_users(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test coordinator returns empty users when device has none."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(return_value=mock_device_config)
    device.list_users = AsyncMock(return_value=[])

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)
    data = await coordinator._async_update_data()

    assert data.users == []


async def test_coordinator_user_cache_survives_fetch_failure(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
    mock_device_config: Any,
    mock_user_list: list[Any],
) -> None:
    """Test user cache is preserved when fetch fails."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(return_value=mock_device_config)
    device.list_users = AsyncMock(return_value=mock_user_list)

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)
    data1 = await coordinator._async_update_data()
    assert len(data1.users) == 2

    # Second fetch fails — reset TTL to force re-fetch
    coordinator._last_user_fetch = None
    device.list_users = AsyncMock(
        side_effect=AkuvoxConnectionError("timeout"),
    )
    data2 = await coordinator._async_update_data()

    # Cache preserved
    assert len(data2.users) == 2


async def test_get_user_by_pin_cache_hit(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
    mock_device_config: Any,
    mock_user_list: list[Any],
) -> None:
    """Test get_user_by_pin returns matching user."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(return_value=mock_device_config)
    device.list_users = AsyncMock(return_value=mock_user_list)

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)
    await coordinator._async_update_data()

    user = coordinator.get_user_by_pin("1234")
    assert user is not None
    assert user.name == "John Doe"
    assert user.id == "42"


async def test_get_user_by_pin_cache_miss(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
    mock_device_config: Any,
    mock_user_list: list[Any],
) -> None:
    """Test get_user_by_pin returns None for unknown PIN."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(return_value=mock_device_config)
    device.list_users = AsyncMock(return_value=mock_user_list)

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)
    await coordinator._async_update_data()

    user = coordinator.get_user_by_pin("9999")
    assert user is None


async def test_get_user_by_pin_empty_cache(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test get_user_by_pin returns None with empty cache."""
    device = AsyncMock()
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(return_value=mock_device_config)
    device.list_users = AsyncMock(return_value=[])

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)
    await coordinator._async_update_data()

    assert coordinator.get_user_by_pin("1234") is None


async def test_coordinator_user_cache_returns_none_when_list_users_absent(
    hass: HomeAssistant,
    mock_device_info: DeviceInfo,
    mock_relay_status: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test user cache is empty when device lacks list_users."""
    device = AsyncMock(spec=[])
    device.get_info = AsyncMock(return_value=mock_device_info)
    device.get_relay_status = AsyncMock(return_value=mock_relay_status)
    device.get_device_config = AsyncMock(return_value=mock_device_config)
    # Explicitly remove list_users
    if hasattr(device, "list_users"):
        delattr(device, "list_users")

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=device)
    data = await coordinator._async_update_data()

    assert data.users == []
