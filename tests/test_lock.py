# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Akuvox lock entity."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import AsyncMock, call, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
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
    DOMAIN,
)
from tests.conftest import MOCK_MAC


async def test_entity_unique_id(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test entity created with correct unique_id {mac}_relay_{num}."""
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

    ent_reg = er.async_get(hass)
    entity_entry = ent_reg.async_get("lock.testlab_intercom_front_gate")
    assert entity_entry is not None
    expected_uid = f"{MOCK_MAC.lower().replace(':', '')}_relay_1"
    assert entity_entry.unique_id == expected_uid


async def test_entity_name(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test entity name uses config-sourced relay name."""
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
    assert state.attributes.get("friendly_name") == "TestLab Intercom Front Gate"


async def test_entity_device_info(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test entity device_info maps library DeviceInfo to HA DeviceInfo."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    dev_reg = dr.async_get(hass)
    mac_clean = MOCK_MAC.lower().replace(":", "")
    device = dev_reg.async_get_device(
        identifiers={(DOMAIN, mac_clean)},
    )
    assert device is not None
    assert device.manufacturer == "Akuvox"
    assert device.model == "E21V"


@pytest.mark.parametrize(
    ("relay_state", "expected_ha_state"),
    [("closed", "locked"), ("inactive", "locked"), (0, "locked")],
)
async def test_is_locked_true(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
    relay_state: str | int,
    expected_ha_state: str,
) -> None:
    """Test is_locked returns True for closed/inactive/0 states."""
    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        from pylocal_akuvox import DeviceInfo

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
            return_value={"RelayA": relay_state},
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
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == expected_ha_state


@pytest.mark.parametrize(
    ("relay_state", "expected_ha_state"),
    [("open", "unlocked"), ("active", "unlocked"), (1, "unlocked")],
)
async def test_is_locked_false(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
    relay_state: str | int,
    expected_ha_state: str,
) -> None:
    """Test is_locked returns False for open/active/1 states."""
    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        from pylocal_akuvox import DeviceInfo

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
            return_value={"RelayA": relay_state},
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
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == expected_ha_state


@pytest.mark.parametrize("relay_state", [2, -1])
async def test_is_locked_unknown_for_unexpected_int(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
    relay_state: int,
) -> None:
    """Test is_locked returns None for unexpected integer states."""
    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        from pylocal_akuvox import DeviceInfo

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
            return_value={"RelayA": relay_state},
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
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "unknown"


@pytest.mark.parametrize("relay_state", ["fault", "unknown", ""])
async def test_is_locked_unknown_for_unexpected_str(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
    relay_state: str,
) -> None:
    """Test is_locked returns None for unrecognized string states."""
    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        from pylocal_akuvox import DeviceInfo

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
            return_value={"RelayA": relay_state},
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
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "unknown"


async def test_is_locked_none_for_missing_relay_key(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test is_locked returns None when relay key missing from status.

    If the relay_status dict does not contain the entity's relay key,
    is_locked must return None so HA reports the entity as unknown.
    """
    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        from pylocal_akuvox import DeviceInfo

        device = mock_cls.return_value
        device.get_info = AsyncMock(
            return_value=DeviceInfo(
                model="E21V",
                mac_address=MOCK_MAC,
                firmware_version="1.0.0",
                hardware_version="2.0.0",
            ),
        )
        # Initially has RelayA
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
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "locked"

        # Now relay key disappears from status
        device.get_relay_status.return_value = {"RelayB": 0}

        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "unknown"


@pytest.mark.parametrize(
    ("relay_state", "expected_ha_state"),
    [({"state": 0}, "locked"), ({"state": 1}, "unlocked")],
)
async def test_is_locked_handles_dict_int_state(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
    relay_state: dict[str, int],
    expected_ha_state: str,
) -> None:
    """Test is_locked handles dict-wrapped integer states."""
    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        from pylocal_akuvox import DeviceInfo

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
            return_value={"RelayA": relay_state},
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
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == expected_ha_state


async def test_entity_unavailable_when_coordinator_fails(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test entity becomes unavailable when coordinator fails."""
    from pylocal_akuvox import AkuvoxConnectionError, DeviceInfo

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
            return_value={"RelayA": "closed"},
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
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "locked"

        # Now make coordinator fail
        device.get_relay_status.side_effect = AkuvoxConnectionError(
            "Connection lost",
        )

        coordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "unavailable"


async def test_multi_relay_entities_created(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test multiple relay entities are created with correct IDs."""
    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        from pylocal_akuvox import DeviceInfo

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
            return_value={"RelayA": "closed", "RelayB": "open"},
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
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state_a = hass.states.get("lock.testlab_intercom_front_gate")
        assert state_a is not None
        assert state_a.state == "locked"

        state_b = hass.states.get("lock.testlab_intercom_side_gate")
        assert state_b is not None
        assert state_b.state == "unlocked"

        ent_reg = er.async_get(hass)
        mac_clean = MOCK_MAC.lower().replace(":", "")
        entry_a = ent_reg.async_get("lock.testlab_intercom_front_gate")
        assert entry_a is not None
        assert entry_a.unique_id == f"{mac_clean}_relay_1"

        entry_b = ent_reg.async_get("lock.testlab_intercom_side_gate")
        assert entry_b is not None
        assert entry_b.unique_id == f"{mac_clean}_relay_2"


async def test_multi_relay_distinct_names(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test multi-relay entities have distinct friendly names."""
    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        from pylocal_akuvox import DeviceInfo

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
            return_value={"RelayA": 0, "RelayB": 0},
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
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state_a = hass.states.get("lock.testlab_intercom_front_gate")
        state_b = hass.states.get("lock.testlab_intercom_side_gate")
        assert state_a is not None
        assert state_b is not None

        name_a = state_a.attributes.get("friendly_name")
        name_b = state_b.attributes.get("friendly_name")
        assert name_a is not None
        assert name_b is not None
        assert name_a != name_b
        assert "Front Gate" in name_a
        assert "Side Gate" in name_b


async def test_unlock_relay_a_does_not_change_relay_b(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test unlocking relay A only affects relay A entity.

    When relay A is unlocked, relay B must remain locked.
    """
    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        from pylocal_akuvox import DeviceInfo

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
            return_value={"RelayA": 0, "RelayB": 0},
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
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Both start locked
        state_a = hass.states.get("lock.testlab_intercom_front_gate")
        state_b = hass.states.get("lock.testlab_intercom_side_gate")
        assert state_a is not None
        assert state_b is not None
        assert state_a.state == "locked"
        assert state_b.state == "locked"

        # Unlock relay A
        await hass.services.async_call(
            "lock",
            "unlock",
            {"entity_id": "lock.testlab_intercom_front_gate"},
            blocking=True,
        )
        await hass.async_block_till_done()

        # Relay A is now unlocked (optimistic)
        state_a = hass.states.get("lock.testlab_intercom_front_gate")
        assert state_a is not None
        assert state_a.state == "unlocked"

        # Relay B remains locked
        state_b = hass.states.get("lock.testlab_intercom_side_gate")
        assert state_b is not None
        assert state_b.state == "locked"

        # Verify trigger_relay was called for relay 1 only
        device.trigger_relay.assert_awaited_once_with(
            num=1,
            delay=5,
            level=0,
            mode=0,
        )


async def test_is_locked_handles_dict_state_format(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test is_locked handles legacy dict state format defensively."""
    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        from pylocal_akuvox import DeviceInfo

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
            return_value={"RelayA": {"state": "closed"}},
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
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "locked"


async def test_unrecognized_relay_keys_skipped(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test that unrecognized relay keys are skipped."""
    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        from pylocal_akuvox import DeviceInfo

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
            return_value={
                "RelayA": "closed",
                "unknown_key": "open",
                "relay_b": "open",
            },
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
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Only RelayA should be created
        state_a = hass.states.get("lock.testlab_intercom_front_gate")
        assert state_a is not None

        ent_reg = er.async_get(hass)
        entities = er.async_entries_for_config_entry(
            ent_reg,
            entry.entry_id,
        )
        assert len(entities) == 1


# ──────────────────────────────────────────────────────
# User Story 2 — Control Door Lock
# ──────────────────────────────────────────────────────


async def test_async_unlock_calls_trigger_relay(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test async_unlock calls trigger_relay with correct params."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    mock_akuvox_device.trigger_relay.assert_called_once_with(
        num=1,
        delay=5,
        level=0,
        mode=0,
    )


async def test_async_unlock_shows_unlocked_optimistically(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test unlock shows unlocked even if device hasn't updated yet.

    After triggering the relay, the device may still report locked
    because it hasn't processed the command yet. The entity must
    optimistically report unlocked immediately after a successful
    trigger.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Relay status is NOT updated — device still reports locked.
    # The entity must still show unlocked via optimistic state.

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    # State must be unlocked optimistically despite device lag
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "unlocked"


async def test_optimistic_state_survives_coordinator_update(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test optimistic unlocked state survives a coordinator poll.

    If the coordinator refreshes during the unlock-delay window, the
    device may still report locked. The optimistic override must not
    be cleared until the delayed refresh fires.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    # Simulate a coordinator poll returning stale locked state
    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # Entity must still report unlocked despite stale coordinator data
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "unlocked"


async def test_rapid_unlock_resets_optimistic_window(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test rapid successive unlocks keep optimistic state active.

    When a second unlock is issued before the first timer fires, the
    earlier timer is cancelled and a new window starts.  The entity
    must remain unlocked until the latest window expires.
    """
    import datetime

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import (
        async_fire_time_changed,
    )

    from custom_components.local_akuvox.lock import _RELAY_REFRESH_BUFFER_SECONDS

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    start = dt_util.utcnow()

    # First unlock
    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    # Advance part-way through the first window
    async_fire_time_changed(
        hass,
        start
        + datetime.timedelta(
            seconds=DEFAULT_HOLD_DELAY_SECONDS - 1,
        ),
    )
    await hass.async_block_till_done()

    # Second unlock — resets the timer
    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    second_unlock = dt_util.utcnow()

    # Advance past the original window but before the new one expires
    async_fire_time_changed(
        hass,
        second_unlock
        + datetime.timedelta(
            seconds=DEFAULT_HOLD_DELAY_SECONDS,
        ),
    )
    await hass.async_block_till_done()

    # Entity must still report unlocked (second timer hasn't fired)
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "unlocked"

    # Now advance past the second window
    mock_akuvox_device.get_relay_status.return_value = {"RelayA": 0}
    async_fire_time_changed(
        hass,
        second_unlock
        + datetime.timedelta(
            seconds=DEFAULT_HOLD_DELAY_SECONDS + _RELAY_REFRESH_BUFFER_SECONDS + 1,
        ),
    )
    await hass.async_block_till_done()

    # Now entity should reflect real device state (locked)
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "locked"


async def test_delayed_refresh_clears_optimistic_state(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test delayed refresh fires, clears optimistic state, re-syncs.

    After the unlock-delay window expires the timer must trigger a
    coordinator refresh and clear the optimistic override so the entity
    reports real device state.
    """
    import datetime

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import (
        async_fire_time_changed,
    )

    from custom_components.local_akuvox.lock import _RELAY_REFRESH_BUFFER_SECONDS

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    start = dt_util.utcnow()

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    # Device now returns locked (relay re-locked after delay)
    mock_akuvox_device.get_relay_status.return_value = {"RelayA": 0}

    # Advance time past the unlock-delay + buffer window
    async_fire_time_changed(
        hass,
        start
        + datetime.timedelta(
            seconds=DEFAULT_HOLD_DELAY_SECONDS + _RELAY_REFRESH_BUFFER_SECONDS + 1,
        ),
    )
    await hass.async_block_till_done()

    # Entity should now reflect real device state (locked)
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "locked"


# ── T003: _schedule_delayed_refresh backward compatibility ───────


async def test_schedule_delayed_refresh_default_callback(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test _schedule_delayed_refresh default calls unlock finish.

    When no finish_callback is provided, the timer must call
    _async_finish_optimistic_unlock (backward compatibility after
    T001 refactor).  A spy on the method proves it was dispatched.
    """
    import datetime

    from homeassistant.helpers.entity_component import EntityComponent
    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import (
        async_fire_time_changed,
    )

    from custom_components.local_akuvox.lock import _RELAY_REFRESH_BUFFER_SECONDS

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    comp: EntityComponent[Any] = hass.data["lock"]
    lock_entity = comp.get_entity("lock.testlab_intercom_front_gate")
    assert lock_entity is not None

    original = lock_entity._async_finish_optimistic_unlock
    spy = AsyncMock(wraps=original)

    with patch.object(lock_entity, "_async_finish_optimistic_unlock", spy):
        # Unlock uses default callback (no finish_callback arg)
        await hass.services.async_call(
            "lock",
            "unlock",
            {"entity_id": "lock.testlab_intercom_front_gate"},
            blocking=True,
        )

        # Capture baseline after the timer is scheduled
        start = dt_util.utcnow()

        # Device returns locked after delay
        mock_akuvox_device.get_relay_status.return_value = {"RelayA": 0}

        # Fire timer past relay_delay + buffer
        async_fire_time_changed(
            hass,
            start
            + datetime.timedelta(
                seconds=DEFAULT_HOLD_DELAY_SECONDS + _RELAY_REFRESH_BUFFER_SECONDS + 1,
            ),
        )
        await hass.async_block_till_done()

    # Default callback was dispatched by the timer
    spy.assert_awaited_once()

    # Optimistic override cleared → real state (locked)
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "locked"


# ── T004: _schedule_delayed_refresh with explicit callback ───────


async def test_schedule_delayed_refresh_explicit_callback(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test _schedule_delayed_refresh invokes explicit callback.

    When a finish_callback is provided, the timer must call that
    callback instead of the default unlock finish callback.
    """
    import datetime

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import (
        async_fire_time_changed,
    )

    from custom_components.local_akuvox.lock import _RELAY_REFRESH_BUFFER_SECONDS

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # AsyncMock as explicit callback; spy on default to prove exclusion
    explicit_cb = AsyncMock()

    # Access the lock entity directly from the platform
    from homeassistant.helpers.entity_component import EntityComponent

    comp: EntityComponent[Any] = hass.data["lock"]
    lock_entity = comp.get_entity("lock.testlab_intercom_front_gate")
    assert lock_entity is not None

    # Instrument default callback to prove it is NOT dispatched
    default_spy = AsyncMock()

    with patch.object(lock_entity, "_async_finish_optimistic_unlock", default_spy):
        lock_entity._schedule_delayed_refresh(0, finish_callback=explicit_cb)

        # Capture baseline after the timer is scheduled
        start = dt_util.utcnow()

        # Timer fires after 0 + buffer seconds
        async_fire_time_changed(
            hass,
            start
            + datetime.timedelta(
                seconds=_RELAY_REFRESH_BUFFER_SECONDS + 1,
            ),
        )
        await hass.async_block_till_done()

    explicit_cb.assert_awaited_once()
    default_spy.assert_not_awaited()


async def test_entity_removal_cancels_delayed_refresh(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test entity removal cancels pending delayed refresh timer.

    When the entity is removed from Home Assistant while a delayed
    refresh timer is pending, the timer must be cancelled to avoid
    refreshing a torn-down coordinator.
    """
    import datetime

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import (
        async_fire_time_changed,
    )

    from custom_components.local_akuvox.lock import _RELAY_REFRESH_BUFFER_SECONDS

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    start = dt_util.utcnow()

    # Trigger unlock to schedule a delayed refresh
    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    # Record call count before removal
    refresh_count = mock_akuvox_device.get_relay_status.call_count

    # Unload the config entry (removes entities)
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # Advance time past the unlock-delay + buffer window
    async_fire_time_changed(
        hass,
        start
        + datetime.timedelta(
            seconds=DEFAULT_HOLD_DELAY_SECONDS + _RELAY_REFRESH_BUFFER_SECONDS + 1,
        ),
    )
    await hass.async_block_till_done()

    # No additional refresh should have been triggered
    assert mock_akuvox_device.get_relay_status.call_count == refresh_count


@pytest.mark.parametrize(
    "exception_cls",
    [
        "AkuvoxConnectionError",
        "AkuvoxAuthenticationError",
        "AkuvoxError",
    ],
)
async def test_async_unlock_raises_on_device_error(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
    exception_cls: str,
) -> None:
    """Test async_unlock raises HomeAssistantError on device errors."""
    import pylocal_akuvox
    from homeassistant.exceptions import HomeAssistantError

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        from pylocal_akuvox import DeviceInfo

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
            return_value={"RelayA": "closed"},
        )
        exc = getattr(pylocal_akuvox, exception_cls)
        device.trigger_relay = AsyncMock(
            side_effect=exc("trigger failed"),
        )
        device.get_device_config = AsyncMock(
            return_value=mock_device_config,
        )
        device.__aenter__ = AsyncMock(return_value=device)
        device.__aexit__ = AsyncMock(return_value=None)

        entry = MockConfigEntry(
            domain=DOMAIN,
            data=mock_config_entry_data_none,
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                "lock",
                "unlock",
                {"entity_id": "lock.testlab_intercom_front_gate"},
                blocking=True,
            )


async def test_async_lock_no_longer_raises_error(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test async_lock no longer raises unconditionally.

    T012: The old stub raised HomeAssistantError for all lock
    calls. Now that async_lock is implemented, calling lock on a
    bistable relay that is confirmed unlocked must succeed without
    error.
    """
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    # Device reports unlocked so lock action proceeds
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Must NOT raise HomeAssistantError
    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )


async def test_async_unlock_completes_within_5s(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_device_config: Any,
) -> None:
    """Test async_unlock completes within 5 seconds (SC-002).

    With a mock device, the unlock action should complete
    near-instantly, well under the 5-second budget.
    """
    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        from pylocal_akuvox import DeviceInfo

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
            unique_id=MOCK_MAC,
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        start = time.monotonic()
        await hass.services.async_call(
            "lock",
            "unlock",
            {"entity_id": "lock.testlab_intercom_front_gate"},
            blocking=True,
        )
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, f"Unlock took {elapsed:.2f}s, exceeds 5s budget"


# ── T005–T011: Bistable relay lock tests (Phase 3) ──────────────


async def test_bistable_lock_sends_trigger_relay(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test bistable lock sends trigger_relay when confirmed unlocked.

    T005: Mock coordinator refresh to return unlocked state, call
    lock.lock, assert trigger_relay called with correct relay params.
    """
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    mock_akuvox_device.trigger_relay.assert_called_once_with(
        num=1,
        delay=DEFAULT_HOLD_DELAY_SECONDS,
        level=DEFAULT_RELAY_TYPE,
        mode=1,
    )


async def test_bistable_lock_sets_optimistic_locked(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test bistable lock sets optimistic locked state.

    T006: After successful trigger_relay, verify _optimistic_locked
    is True and entity reports locked via async_write_ha_state.
    """
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Starts unlocked
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "unlocked"

    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    # Now optimistically locked
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "locked"


async def test_bistable_lock_schedules_delayed_refresh(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test bistable lock delayed refresh clears optimistic state.

    T007: After locking a bistable relay, verify the optimistic
    locked state is cleared once the delayed refresh timer fires
    and the entity reflects the real device state.
    """
    import datetime

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import (
        async_fire_time_changed,
    )

    from custom_components.local_akuvox.lock import _RELAY_REFRESH_BUFFER_SECONDS

    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    start = dt_util.utcnow()

    # Optimistically locked
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "locked"

    # Device now reports locked (confirmed)
    mock_akuvox_device.get_relay_status.return_value = {"RelayA": 0}

    # Timer fires at 0 + buffer seconds
    async_fire_time_changed(
        hass,
        start
        + datetime.timedelta(
            seconds=_RELAY_REFRESH_BUFFER_SECONDS + 1,
        ),
    )
    await hass.async_block_till_done()

    # Optimistic override cleared, real state confirmed locked
    comp = hass.data["lock"]
    entity = comp.get_entity("lock.testlab_intercom_front_gate")
    assert entity._optimistic_locked is None
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "locked"


async def test_bistable_lock_noop_when_already_locked(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test bistable lock is no-op when already locked.

    T008: Mock coordinator refresh to return locked state, call
    lock.lock, assert trigger_relay NOT called, state unchanged.
    """
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0},
    )

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

    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    # trigger_relay should NOT have been called
    mock_akuvox_device.trigger_relay.assert_not_called()

    # State unchanged
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "locked"


async def test_bistable_lock_raises_on_device_error(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test bistable lock raises HomeAssistantError on device error.

    T009: Mock trigger_relay to raise AkuvoxError, verify
    HomeAssistantError raised, state unchanged.
    """
    from homeassistant.exceptions import HomeAssistantError
    from pylocal_akuvox import AkuvoxError

    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    # Device reports unlocked so lock action proceeds
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )
    mock_akuvox_device.trigger_relay = AsyncMock(
        side_effect=AkuvoxError("device error"),
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "lock",
            "lock",
            {"entity_id": "lock.testlab_intercom_front_gate"},
            blocking=True,
        )

    # State unchanged (still unlocked)
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "unlocked"


async def test_bistable_lock_refreshes_coordinator_first(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test bistable lock refreshes coordinator before state check.

    T010: Device starts unlocked so setup sees unlocked state.
    Before the lock call, switch mock to return locked. If
    async_lock refreshes before checking is_locked, it sees
    locked and skips trigger_relay. If it checked stale state
    first, it would incorrectly send the command.
    """
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    # Device starts unlocked during setup
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Confirm entity sees unlocked
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "unlocked"

    # Before lock call, device transitions to locked externally
    mock_akuvox_device.get_relay_status.return_value = {"RelayA": 0}

    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    # Because async_lock refreshes BEFORE checking is_locked,
    # it sees locked and skips trigger_relay (no-op path).
    mock_akuvox_device.trigger_relay.assert_not_called()


async def test_bistable_lock_cancels_pending_unlock_refresh(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test bistable lock cancels pending unlock refresh.

    T011: Set up pending unlock timer, call lock.lock, verify the
    old unlock callback never fires by spying on it after advancing
    time past its scheduled deadline.
    """
    import datetime
    from unittest.mock import patch as mock_patch

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import (
        async_fire_time_changed,
    )

    from custom_components.local_akuvox.lock import _RELAY_REFRESH_BUFFER_SECONDS

    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    # Start locked
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Install spy BEFORE unlock so the timer captures the wrapped method
    comp = hass.data["lock"]
    entity = comp.get_entity("lock.testlab_intercom_front_gate")

    with mock_patch.object(
        entity,
        "_async_finish_optimistic_unlock",
        wraps=entity._async_finish_optimistic_unlock,
    ) as unlock_spy:
        # Unlock to set up pending timer
        await hass.services.async_call(
            "lock",
            "unlock",
            {"entity_id": "lock.testlab_intercom_front_gate"},
            blocking=True,
        )

        # Entity is optimistically unlocked
        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "unlocked"

        # Now device reports unlocked (bistable: stays unlocked)
        mock_akuvox_device.get_relay_status.return_value = {"RelayA": 1}

        # Call lock — should cancel pending unlock refresh
        await hass.services.async_call(
            "lock",
            "lock",
            {"entity_id": "lock.testlab_intercom_front_gate"},
            blocking=True,
        )

        # Entity is now optimistically locked
        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "locked"

        start = dt_util.utcnow()

        # Advance past old unlock timer deadline
        async_fire_time_changed(
            hass,
            start
            + datetime.timedelta(
                seconds=DEFAULT_HOLD_DELAY_SECONDS + _RELAY_REFRESH_BUFFER_SECONDS + 1,
            ),
        )
        await hass.async_block_till_done()

        # Unlock callback was never invoked (timer was cancelled)
        unlock_spy.assert_not_called()


# ── T014–T018: Auto-close relay lock tests (Phase 4) ────────────


async def test_autoclose_lock_no_trigger_relay(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test auto-close relay lock does NOT send trigger_relay.

    T014: Mock coordinator refresh, call lock.lock on auto-close relay,
    assert trigger_relay NOT called.
    """
    cfg = mock_device_config_factory()
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )

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
    assert state.state == "unlocked"

    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    mock_akuvox_device.trigger_relay.assert_not_called()


async def test_autoclose_lock_performs_coordinator_refresh(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test auto-close relay lock performs coordinator refresh.

    T015: Verify coordinator.async_refresh() called during lock
    by checking get_relay_status call count increases.
    """
    cfg = mock_device_config_factory()
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    calls_before = mock_akuvox_device.get_relay_status.call_count

    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    assert mock_akuvox_device.get_relay_status.call_count > calls_before


async def test_autoclose_lock_preserves_pending_unlock_timer(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test auto-close relay lock does NOT cancel pending unlock refresh.

    T016: Set up pending unlock timer, call lock.lock, verify the
    unlock callback still fires after advancing time.
    """
    import datetime
    from unittest.mock import patch as mock_patch

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import (
        async_fire_time_changed,
    )

    from custom_components.local_akuvox.lock import _RELAY_REFRESH_BUFFER_SECONDS

    cfg = mock_device_config_factory()
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    comp = hass.data["lock"]
    entity = comp.get_entity("lock.testlab_intercom_front_gate")

    with mock_patch.object(
        entity,
        "_async_finish_optimistic_unlock",
        wraps=entity._async_finish_optimistic_unlock,
    ) as unlock_spy:
        # Unlock to set up pending timer
        await hass.services.async_call(
            "lock",
            "unlock",
            {"entity_id": "lock.testlab_intercom_front_gate"},
            blocking=True,
        )

        # Now call lock on auto-close relay — should preserve timer
        await hass.services.async_call(
            "lock",
            "lock",
            {"entity_id": "lock.testlab_intercom_front_gate"},
            blocking=True,
        )

        start = dt_util.utcnow()

        # Advance past the unlock timer deadline
        async_fire_time_changed(
            hass,
            start
            + datetime.timedelta(
                seconds=DEFAULT_HOLD_DELAY_SECONDS + _RELAY_REFRESH_BUFFER_SECONDS + 1,
            ),
        )
        await hass.async_block_till_done()

        # Unlock callback DID fire (timer was preserved)
        unlock_spy.assert_called_once()


async def test_autoclose_lock_noop_when_already_locked(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test auto-close relay lock when already locked is a no-op.

    T017: Mock coordinator refresh returning locked state, assert no
    command sent, no state change.
    """
    cfg = mock_device_config_factory()
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0},
    )

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

    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    mock_akuvox_device.trigger_relay.assert_not_called()

    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "locked"


async def test_autoclose_lock_no_optimistic_state(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test auto-close relay lock does NOT set optimistic state.

    T018: Verify _optimistic_locked remains None after lock call
    (no optimistic override for auto-close).
    """
    cfg = mock_device_config_factory()
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    comp = hass.data["lock"]
    entity = comp.get_entity("lock.testlab_intercom_front_gate")

    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    assert entity._optimistic_locked is None


# ── T020–T021: Service-call integration tests (Phase 5) ─────────


async def test_service_call_lock_bistable(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test lock.lock service call succeeds on bistable relay.

    T020: Use hass.services.async_call("lock", "lock", ...) with
    blocking=True, verify no exception and state updated to locked.
    """
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )

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
    assert state.state == "unlocked"

    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "locked"


async def test_service_call_lock_autoclose(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test lock.lock service call succeeds on auto-close relay.

    T021: Use hass.services.async_call("lock", "lock", ...) with
    blocking=True, verify no exception. State reflects device state
    from coordinator refresh.
    """
    cfg = mock_device_config_factory()
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )

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
    assert state.state == "unlocked"

    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    # No exception raised; state reflects device state from refresh
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "unlocked"


# ── T022–T026: Polish & edge-case tests (Phase 6) ───────────────


async def test_lock_during_active_unlock_window_bistable(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test lock during active unlock window on bistable relay.

    T022: Unlock, then immediately lock before hold_delay expires.
    Verify pending unlock refresh cancelled, lock command sent,
    and new lock refresh scheduled.
    """
    import datetime
    from unittest.mock import patch as mock_patch

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import (
        async_fire_time_changed,
    )

    from custom_components.local_akuvox.lock import _RELAY_REFRESH_BUFFER_SECONDS

    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    comp = hass.data["lock"]
    entity = comp.get_entity("lock.testlab_intercom_front_gate")
    assert entity is not None, (
        "Expected lock.testlab_intercom_front_gate entity to exist"
    )

    with (
        mock_patch.object(
            entity,
            "_async_finish_optimistic_unlock",
            wraps=entity._async_finish_optimistic_unlock,
        ) as unlock_spy,
        mock_patch.object(
            entity,
            "_async_finish_optimistic_lock",
            wraps=entity._async_finish_optimistic_lock,
        ) as lock_spy,
    ):
        # Unlock first
        await hass.services.async_call(
            "lock",
            "unlock",
            {"entity_id": "lock.testlab_intercom_front_gate"},
            blocking=True,
        )

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "unlocked"

        # Device still reports unlocked after unlock command
        mock_akuvox_device.get_relay_status.return_value = {"RelayA": 1}
        mock_akuvox_device.trigger_relay.reset_mock()

        # Lock immediately (within hold_delay window)
        await hass.services.async_call(
            "lock",
            "lock",
            {"entity_id": "lock.testlab_intercom_front_gate"},
            blocking=True,
        )

        # Lock command was sent
        mock_akuvox_device.trigger_relay.assert_called_once()

        # Entity is optimistically locked
        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "locked"

        start = dt_util.utcnow()

        # Advance past both old unlock and new lock timer deadlines
        async_fire_time_changed(
            hass,
            start
            + datetime.timedelta(
                seconds=DEFAULT_HOLD_DELAY_SECONDS + _RELAY_REFRESH_BUFFER_SECONDS + 1,
            ),
        )
        await hass.async_block_till_done()

        # Old unlock callback was cancelled
        unlock_spy.assert_not_called()

        # New lock callback fired
        lock_spy.assert_called_once()


async def test_rapid_lock_lock_idempotent_bistable(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test rapid lock-lock is idempotent on bistable relay.

    T023: Call lock twice in succession on bistable relay, verify
    only one trigger_relay command sent (second is no-op because a
    status refresh confirms the relay is already locked after the first
    command).
    """
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )

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
    assert state.state == "unlocked"

    # First lock — triggers relay
    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    assert mock_akuvox_device.trigger_relay.call_count == 1

    # Device reports locked after first command
    mock_akuvox_device.get_relay_status.return_value = {"RelayA": 0}

    # Second lock — no-op (already locked after refresh)
    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    # Still only one trigger_relay call total
    assert mock_akuvox_device.trigger_relay.call_count == 1


async def test_async_lock_completes_within_5s(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test async_lock completes within 5 seconds (SC-002).

    T024: With a mock device in bistable mode, the lock action
    should complete near-instantly, well under the 5-second budget.
    """
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    start = time.monotonic()
    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )
    elapsed = time.monotonic() - start
    assert elapsed < 5.0, f"Lock took {elapsed:.2f}s, exceeds 5s budget"

    # Verify bistable path was exercised
    mock_akuvox_device.trigger_relay.assert_called_once()


async def test_existing_unlock_behavior_unchanged(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test existing unlock behavior unchanged after refactoring (SC-005).

    T025: Re-verify existing unlock with refactored
    _schedule_delayed_refresh: unlock sends trigger_relay, sets
    optimistic unlocked state, and schedules delayed refresh with
    default callback.
    """
    import datetime
    from unittest.mock import patch as mock_patch

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import (
        async_fire_time_changed,
    )

    from custom_components.local_akuvox.lock import _RELAY_REFRESH_BUFFER_SECONDS

    cfg = mock_device_config_factory()
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0},
    )

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

    comp = hass.data["lock"]
    entity = comp.get_entity("lock.testlab_intercom_front_gate")
    assert entity is not None

    with mock_patch.object(
        entity,
        "_async_finish_optimistic_unlock",
        wraps=entity._async_finish_optimistic_unlock,
    ) as unlock_spy:
        await hass.services.async_call(
            "lock",
            "unlock",
            {"entity_id": "lock.testlab_intercom_front_gate"},
            blocking=True,
        )

        # trigger_relay called
        mock_akuvox_device.trigger_relay.assert_called_once()

        # Optimistically unlocked
        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "unlocked"

        start = dt_util.utcnow()

        # Advance past hold_delay + buffer
        async_fire_time_changed(
            hass,
            start
            + datetime.timedelta(
                seconds=DEFAULT_HOLD_DELAY_SECONDS + _RELAY_REFRESH_BUFFER_SECONDS + 1,
            ),
        )
        await hass.async_block_till_done()

        # Default callback fired
        unlock_spy.assert_called_once()

        # Optimistic state cleared — falls through to coordinator
        assert entity._optimistic_locked is None


async def test_bistable_lock_proceeds_on_unknown_state(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test bistable lock proceeds when state is unknown (None).

    T026: Mock coordinator refresh to return state where is_locked
    is None (relay key missing from status), verify trigger_relay
    is called (treats unknown as unlocked per R-001).
    """
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    # Start with relay present so entity gets created
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0},
    )

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

    # Now make relay status return empty so is_locked returns None
    mock_akuvox_device.get_relay_status.return_value = {}

    # Lock should proceed (R-001: None treated as unlocked)
    await hass.services.async_call(
        "lock",
        "lock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    # trigger_relay was called despite unknown state
    mock_akuvox_device.trigger_relay.assert_called_once()

    # Optimistically locked now
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "locked"


async def test_relay_entity_name_from_config(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test relay entity name uses NameA from DeviceConfig."""
    cfg = mock_device_config_factory(
        **{
            CONFIG_KEY_LOCATION: "Front Door",
            f"{CONFIG_KEY_RELAY_NAME}A": "Main Gate",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("lock.front_door_main_gate")
    assert state is not None
    assert state.attributes.get("friendly_name") == "Front Door Main Gate"


async def test_relay_entity_name_fallback_when_empty(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test relay entity falls back to 'Relay A' when config name empty."""
    cfg = mock_device_config_factory(
        **{
            CONFIG_KEY_LOCATION: "Front Door",
            f"{CONFIG_KEY_RELAY_NAME}A": "",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("lock.front_door_relay_a")
    assert state is not None
    assert state.attributes.get("friendly_name") == "Front Door Relay A"


# ── T024: Per-relay hold_delay in trigger_relay ──────────────────


async def test_unlock_uses_config_hold_delay(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test async_unlock passes per-relay hold_delay to trigger_relay."""
    cfg = mock_device_config_factory(
        **{f"{CONFIG_KEY_RELAY_HOLD_DELAY}A": "7"},
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    mock_akuvox_device.trigger_relay.assert_called_once_with(
        num=1,
        delay=7,
        level=0,
        mode=0,
    )


async def test_unlock_each_relay_uses_own_hold_delay(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_relay_status_multi: dict[str, Any],
    mock_device_config_factory: Any,
) -> None:
    """Test different relays use their own config hold_delay values."""
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_HOLD_DELAY}A": "3",
            f"{CONFIG_KEY_RELAY_HOLD_DELAY}B": "10",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value=mock_relay_status_multi,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_side_gate"},
        blocking=True,
    )

    assert mock_akuvox_device.trigger_relay.call_count == 2
    mock_akuvox_device.trigger_relay.assert_has_calls(
        [
            call(num=1, delay=3, level=0, mode=0),
            call(num=2, delay=10, level=0, mode=0),
        ],
    )


# ── T025: Refresh timer uses config hold_delay + buffer ──────────


async def test_refresh_timer_uses_config_hold_delay(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test refresh timer fires at hold_delay + buffer from config.

    With hold_delay=7 the async_call_later should schedule at 8s
    (7 + 1s buffer).  At 7s the entity must still be unlocked
    (optimistic), at 9s it must reflect real device state.
    """
    import datetime

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import (
        async_fire_time_changed,
    )

    from custom_components.local_akuvox.lock import _RELAY_REFRESH_BUFFER_SECONDS

    cfg = mock_device_config_factory(
        **{f"{CONFIG_KEY_RELAY_HOLD_DELAY}A": "7"},
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    start = dt_util.utcnow()

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    # At 7s the timer (8s) hasn't fired — still unlocked
    async_fire_time_changed(
        hass,
        start + datetime.timedelta(seconds=7),
    )
    await hass.async_block_till_done()

    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "unlocked"

    # Past the full window (8s) — locked
    mock_akuvox_device.get_relay_status.return_value = {"RelayA": 0}
    async_fire_time_changed(
        hass,
        start
        + datetime.timedelta(
            seconds=7 + _RELAY_REFRESH_BUFFER_SECONDS + 1,
        ),
    )
    await hass.async_block_till_done()

    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "locked"


# ── T026: hold_delay fallback to default ─────────────────────────


async def test_unlock_fallback_delay_when_relay_not_in_configs(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test unlock uses DEFAULT_HOLD_DELAY when relay absent from configs.

    When relay_configs does not contain the relay letter, the unlock
    must fall back to DEFAULT_HOLD_DELAY_SECONDS for both trigger_relay
    and the refresh timer.
    """
    import datetime

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import (
        async_fire_time_changed,
    )

    from custom_components.local_akuvox.coordinator import AkuvoxCoordinatorData
    from custom_components.local_akuvox.lock import _RELAY_REFRESH_BUFFER_SECONDS

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Clear relay_configs to simulate missing config entry
    coordinator = hass.data[DOMAIN][entry.entry_id]
    original = coordinator.data
    coordinator.data = AkuvoxCoordinatorData(
        device_info=original.device_info,
        relay_status=original.relay_status,
        device_name=original.device_name,
        relay_configs={},
    )

    start = dt_util.utcnow()

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    mock_akuvox_device.trigger_relay.assert_called_once_with(
        num=1,
        delay=DEFAULT_HOLD_DELAY_SECONDS,
        level=DEFAULT_RELAY_TYPE,
        mode=DEFAULT_RELAY_MODE,
    )

    # Refresh timer: DEFAULT_HOLD_DELAY + buffer + 1
    mock_akuvox_device.get_relay_status.return_value = {"RelayA": 0}
    async_fire_time_changed(
        hass,
        start
        + datetime.timedelta(
            seconds=DEFAULT_HOLD_DELAY_SECONDS + _RELAY_REFRESH_BUFFER_SECONDS + 1,
        ),
    )
    await hass.async_block_till_done()

    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "locked"


# ── T026b: hold_delay updates after reconnection ────────────────


async def test_hold_delay_updates_after_reconnection(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test unlock uses updated hold_delay after device reconnection.

    Initial config uses default HoldDelayA=5.  Device goes offline
    then comes back with HoldDelayA=10.  The next unlock must use
    delay=10.
    """
    from pylocal_akuvox import AkuvoxConnectionError

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Device goes offline
    mock_akuvox_device.get_relay_status.side_effect = AkuvoxConnectionError("offline")
    coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # Device comes back with new config: HoldDelayA=10
    mock_akuvox_device.get_relay_status.side_effect = None
    mock_akuvox_device.get_relay_status.return_value = {"RelayA": 0}
    cfg_new = mock_device_config_factory(
        **{f"{CONFIG_KEY_RELAY_HOLD_DELAY}A": "10"},
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg_new)

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    mock_akuvox_device.trigger_relay.reset_mock()

    # Unlock should use updated delay=10
    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )
    mock_akuvox_device.trigger_relay.assert_called_once_with(
        num=1,
        delay=10,
        level=0,
        mode=0,
    )


# ── T029: NO relay state interpretation (regression) ─────────────


async def test_no_relay_state_0_is_locked(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test NO relay (type=0): state 0 → locked."""
    cfg = mock_device_config_factory(
        **{f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_TYPE_SUFFIX}": "0"},
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0},
    )

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


async def test_no_relay_state_1_is_unlocked(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test NO relay (type=0): state 1 → unlocked."""
    cfg = mock_device_config_factory(
        **{f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_TYPE_SUFFIX}": "0"},
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )

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
    assert state.state == "unlocked"


# ── T030: NC relay state interpretation (inverted) ───────────────


async def test_nc_relay_state_0_is_unlocked(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test NC relay (type=1): state 0 → unlocked (inverted)."""
    cfg = mock_device_config_factory(
        **{f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_TYPE_SUFFIX}": "1"},
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0},
    )

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
    assert state.state == "unlocked"


async def test_nc_relay_state_1_is_locked(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test NC relay (type=1): state 1 → locked (inverted)."""
    cfg = mock_device_config_factory(
        **{f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_TYPE_SUFFIX}": "1"},
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )

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


# ── T031: trigger_relay level and mode parameters ────────────────


async def test_unlock_no_relay_sends_level_0_mode_0(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test NO relay (type=0, mode=0): trigger_relay level=0, mode=0."""
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_TYPE_SUFFIX}": "0",
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "0",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    mock_akuvox_device.trigger_relay.assert_called_once_with(
        num=1,
        delay=DEFAULT_HOLD_DELAY_SECONDS,
        level=DEFAULT_RELAY_TYPE,
        mode=DEFAULT_RELAY_MODE,
    )


async def test_unlock_nc_relay_sends_level_1(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test NC relay (type=1): trigger_relay called with level=1."""
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_TYPE_SUFFIX}": "1",
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "0",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    mock_akuvox_device.trigger_relay.assert_called_once_with(
        num=1,
        delay=DEFAULT_HOLD_DELAY_SECONDS,
        level=1,
        mode=0,
    )


async def test_unlock_manual_mode_sends_mode_0(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test manual mode relay (mode=1): unlock sends API mode=0.

    The API mode parameter controls command direction (0=open/toggle,
    1=close-only). Bistable unlock must send mode=0 with delay=0.
    """
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_TYPE_SUFFIX}": "0",
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    mock_akuvox_device.trigger_relay.assert_called_once_with(
        num=1,
        delay=0,
        level=0,
        mode=0,
    )


# ── T032: Fallback to NO when relay_type missing ────────────────


async def test_state_fallback_no_when_relay_not_in_configs(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test NO interpretation when relay_configs is empty.

    When relay_configs does not have the relay letter, state parsing
    must fall back to NO (0=locked, 1=unlocked).
    """
    from custom_components.local_akuvox.coordinator import AkuvoxCoordinatorData

    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Clear relay_configs to simulate missing config
    coordinator = hass.data[DOMAIN][entry.entry_id]
    original = coordinator.data
    coordinator.data = AkuvoxCoordinatorData(
        device_info=original.device_info,
        relay_status={"RelayA": 0},
        device_name=original.device_name,
        relay_configs={},
    )

    state = hass.states.get("lock.testlab_intercom_front_gate")
    # Force entity to re-evaluate state
    coordinator.async_set_updated_data(coordinator.data)
    await hass.async_block_till_done()

    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "locked"


async def test_unlock_fallback_level_0_when_relay_not_in_configs(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test trigger_relay uses level=0 when relay_configs is empty."""
    from custom_components.local_akuvox.coordinator import AkuvoxCoordinatorData

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Clear relay_configs to simulate missing config
    coordinator = hass.data[DOMAIN][entry.entry_id]
    original = coordinator.data
    coordinator.data = AkuvoxCoordinatorData(
        device_info=original.device_info,
        relay_status=original.relay_status,
        device_name=original.device_name,
        relay_configs={},
    )

    mock_akuvox_device.trigger_relay.reset_mock()

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    mock_akuvox_device.trigger_relay.assert_called_once_with(
        num=1,
        delay=DEFAULT_HOLD_DELAY_SECONDS,
        level=DEFAULT_RELAY_TYPE,
        mode=DEFAULT_RELAY_MODE,
    )


# ── T037: Relay without matching config entry ────────────────────


async def test_relay_defaults_when_no_config_entry(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test relay uses default delay/state/level when config missing.

    When relay_configs has entries for other relays but NOT this one,
    the entity should fall back to default hold delay, NO state
    interpretation, and default level/mode in trigger_relay.
    """
    from custom_components.local_akuvox.coordinator import AkuvoxCoordinatorData
    from custom_components.local_akuvox.relay_config import RelayConfig

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Set relay_configs with only B (not A) to simulate missing entry
    coordinator = hass.data[DOMAIN][entry.entry_id]
    original = coordinator.data
    coordinator.data = AkuvoxCoordinatorData(
        device_info=original.device_info,
        relay_status={"RelayA": 0},
        device_name=original.device_name,
        relay_configs={"B": RelayConfig(name="Side Gate")},
    )
    coordinator.async_set_updated_data(coordinator.data)
    await hass.async_block_till_done()

    # Entity should show locked (NO: 0=locked)
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "locked"

    # Unlock should use default delay/level/mode
    mock_akuvox_device.trigger_relay.reset_mock()
    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )
    mock_akuvox_device.trigger_relay.assert_called_once_with(
        num=1,
        delay=DEFAULT_HOLD_DELAY_SECONDS,
        level=DEFAULT_RELAY_TYPE,
        mode=DEFAULT_RELAY_MODE,
    )


# ── T029–T036: Bistable unlock fix tests (Phase 7) ──────────────


async def test_bistable_unlock_sends_mode_0(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test bistable unlock sends trigger_relay with mode=0 and delay=0.

    T029: The API mode parameter controls direction (0=open/toggle,
    1=close-only). Bistable unlock must send mode=0 to open the
    relay, with delay=0 since bistable toggles take effect instantly.
    """
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    mock_akuvox_device.trigger_relay.assert_called_once_with(
        num=1,
        delay=0,
        level=DEFAULT_RELAY_TYPE,
        mode=0,
    )


async def test_bistable_unlock_refreshes_coordinator_first(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test bistable unlock refreshes coordinator before state check.

    T030: Verify coordinator.async_refresh() is called before the
    is_locked evaluation to avoid acting on stale state.
    """
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)

    call_order: list[str] = []
    original_get_relay = mock_akuvox_device.get_relay_status

    async def tracking_get_relay() -> dict[str, int]:
        """Track relay status calls for ordering."""
        call_order.append("refresh")
        result: dict[str, int] = await original_get_relay()
        return result

    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0},
        side_effect=tracking_get_relay,
    )

    async def tracking_trigger(**kwargs: Any) -> None:
        """Track trigger_relay calls for ordering."""
        call_order.append("trigger")

    mock_akuvox_device.trigger_relay = AsyncMock(
        side_effect=tracking_trigger,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Clear call_order from setup refreshes
    call_order.clear()

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    # Refresh must come before trigger
    assert "refresh" in call_order
    assert "trigger" in call_order
    assert call_order.index("refresh") < call_order.index("trigger")


async def test_bistable_unlock_noop_when_already_unlocked(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test bistable unlock is no-op when relay is already unlocked.

    T031: mode=0 is a toggle on bistable relays, so sending it on
    an already-unlocked relay would re-lock it. Must check state
    first and return early if already unlocked.
    """
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )

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
    assert state.state == "unlocked"

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    mock_akuvox_device.trigger_relay.assert_not_called()

    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "unlocked"


async def test_bistable_unlock_cancels_pending_lock_timer(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test bistable unlock cancels pending lock refresh timer.

    T032: Lock sets a pending refresh timer. If unlock is called
    before that timer fires, the lock callback must not execute.
    """
    import datetime
    from unittest.mock import patch as mock_patch

    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import (
        async_fire_time_changed,
    )

    from custom_components.local_akuvox.lock import _RELAY_REFRESH_BUFFER_SECONDS

    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    # Start unlocked so lock will fire
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 1},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    comp = hass.data["lock"]
    entity = comp.get_entity("lock.testlab_intercom_front_gate")
    assert entity is not None

    with mock_patch.object(
        entity,
        "_async_finish_optimistic_lock",
        wraps=entity._async_finish_optimistic_lock,
    ) as lock_spy:
        # Lock first to create a pending lock timer
        await hass.services.async_call(
            "lock",
            "lock",
            {"entity_id": "lock.testlab_intercom_front_gate"},
            blocking=True,
        )

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "locked"

        # Device now reports locked (lock command took effect)
        mock_akuvox_device.get_relay_status.return_value = {
            "RelayA": 0,
        }
        mock_akuvox_device.trigger_relay.reset_mock()

        # Unlock — should cancel pending lock timer
        await hass.services.async_call(
            "lock",
            "unlock",
            {"entity_id": "lock.testlab_intercom_front_gate"},
            blocking=True,
        )

        state = hass.states.get("lock.testlab_intercom_front_gate")
        assert state is not None
        assert state.state == "unlocked"

        start = dt_util.utcnow()

        # Advance past where lock timer would have fired
        async_fire_time_changed(
            hass,
            start
            + datetime.timedelta(
                seconds=_RELAY_REFRESH_BUFFER_SECONDS + 2,
            ),
        )
        await hass.async_block_till_done()

        # Lock callback never fired (timer was cancelled)
        lock_spy.assert_not_called()


async def test_bistable_unlock_schedules_refresh_delay_0(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test bistable unlock schedules delayed refresh with delay=0.

    T033: Bistable toggles take effect instantly, so the refresh
    should use delay=0 (plus buffer), not hold_delay.
    """
    from unittest.mock import patch as mock_patch

    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    comp = hass.data["lock"]
    entity = comp.get_entity("lock.testlab_intercom_front_gate")
    assert entity is not None

    with mock_patch.object(
        entity,
        "_schedule_delayed_refresh",
        wraps=entity._schedule_delayed_refresh,
    ) as refresh_spy:
        await hass.services.async_call(
            "lock",
            "unlock",
            {"entity_id": "lock.testlab_intercom_front_gate"},
            blocking=True,
        )

        refresh_spy.assert_called_once_with(0)


async def test_bistable_unlock_proceeds_on_unknown_state(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test bistable unlock proceeds when state is unknown (None).

    T034: When is_locked returns None after coordinator refresh,
    treat as locked and proceed with trigger_relay.
    """
    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0},
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Switch relay status to empty so is_locked returns None
    mock_akuvox_device.get_relay_status.return_value = {}
    mock_akuvox_device.trigger_relay.reset_mock()

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    mock_akuvox_device.trigger_relay.assert_called_once()


async def test_bistable_unlock_raises_on_device_error(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test bistable unlock raises HomeAssistantError on device error.

    T035: Mock trigger_relay to raise AkuvoxError, verify
    HomeAssistantError raised, state unchanged.
    """
    from homeassistant.exceptions import HomeAssistantError
    from pylocal_akuvox import AkuvoxError

    cfg = mock_device_config_factory(
        **{
            f"{CONFIG_KEY_RELAY_PREFIX}A{CONFIG_KEY_RELAY_MODE_SUFFIX}": "1",
        },
    )
    mock_akuvox_device.get_device_config = AsyncMock(return_value=cfg)
    mock_akuvox_device.get_relay_status = AsyncMock(
        return_value={"RelayA": 0},
    )

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

    mock_akuvox_device.trigger_relay = AsyncMock(
        side_effect=AkuvoxError("device unreachable"),
    )

    with pytest.raises(HomeAssistantError, match="Failed to unlock"):
        await hass.services.async_call(
            "lock",
            "unlock",
            {"entity_id": "lock.testlab_intercom_front_gate"},
            blocking=True,
        )

    # State unchanged after error
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None
    assert state.state == "locked"


async def test_autoclose_unlock_mode_unchanged(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config: Any,
) -> None:
    """Test auto-close unlock behavior unchanged (regression).

    T036: Auto-close unlock must still send trigger_relay with
    mode=0 and delay=hold_delay. Verifies the bistable fix does
    not alter auto-close behavior.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.services.async_call(
        "lock",
        "unlock",
        {"entity_id": "lock.testlab_intercom_front_gate"},
        blocking=True,
    )

    mock_akuvox_device.trigger_relay.assert_called_once_with(
        num=1,
        delay=DEFAULT_HOLD_DELAY_SECONDS,
        level=DEFAULT_RELAY_TYPE,
        mode=0,
    )


def test_unexpected_relay_key_uses_raw_label() -> None:
    """Test malformed relay keys fall back to the raw label."""
    from custom_components.local_akuvox.lock import _relay_key_to_label

    assert _relay_key_to_label("DoorOne") == "DoorOne"


@pytest.mark.parametrize(
    "state",
    [{"value": "closed"}, object()],
    ids=["dict-without-state", "unexpected-type"],
)
def test_parse_relay_state_rejects_unrecognized_values(state: object) -> None:
    """Test unrecognized relay state shapes return None."""
    from custom_components.local_akuvox.lock import _parse_relay_state

    assert _parse_relay_state("RelayA", state) is None


async def test_lock_setup_returns_when_coordinator_has_no_data(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
) -> None:
    """Test lock platform setup skips entity creation without data."""
    from custom_components.local_akuvox.lock import async_setup_entry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)
    coordinator = AsyncMock()
    coordinator.data = None
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    add_entities = AsyncMock()

    await async_setup_entry(hass, entry, add_entities)

    add_entities.assert_not_called()


async def test_lock_entity_rejects_invalid_relay_key(
    hass: HomeAssistant,
    mock_device_info: Any,
) -> None:
    """Test lock entity initialization rejects malformed relay keys."""
    from custom_components.local_akuvox.coordinator import (
        AkuvoxCoordinatorData,
        AkuvoxDataUpdateCoordinator,
    )
    from custom_components.local_akuvox.lock import AkuvoxLockEntity

    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=AsyncMock())
    coordinator.data = AkuvoxCoordinatorData(
        device_info=mock_device_info,
        relay_status={"DoorOne": 0},
        device_name="Test",
        relay_configs={},
    )

    with pytest.raises(ValueError, match="Invalid relay key"):
        AkuvoxLockEntity(coordinator, "DoorOne")


@pytest.mark.parametrize(
    ("method_name", "optimistic_value"),
    [
        ("_async_finish_optimistic_unlock", False),
        ("_async_finish_optimistic_lock", True),
    ],
    ids=["unlock", "lock"],
)
async def test_finish_optimistic_state_clears_after_refresh_error(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    method_name: str,
    optimistic_value: bool,
) -> None:
    """Test optimistic cleanup still runs when refresh fails."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity = hass.data["lock"].get_entity("lock.testlab_intercom_front_gate")
    assert entity is not None
    entity._optimistic_locked = optimistic_value

    with patch.object(
        entity.coordinator,
        "async_refresh",
        AsyncMock(side_effect=RuntimeError("refresh failed")),
    ):
        await getattr(entity, method_name)()

    assert entity._optimistic_locked is None
