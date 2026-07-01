# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Tests for unsupported capability error paths."""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_component import EntityComponent
from pylocal_akuvox import (
    AkuvoxUnsupportedError,
    Capability,
    CapabilityStatus,
    DeviceCapabilities,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.local_akuvox.const import (
    CONF_ATTEMPT_UNKNOWN_CAPABILITY,
    DOMAIN,
)
from custom_components.local_akuvox.coordinator import (
    AkuvoxCoordinatorData,
    AkuvoxDataUpdateCoordinator,
)
from custom_components.local_akuvox.lock import AkuvoxLockEntity
from custom_components.local_akuvox.relay_config import RelayConfig
from tests.conftest import MOCK_MAC


def _unsupported(capability: Capability) -> AkuvoxUnsupportedError:
    """Return a structured unsupported capability error."""
    return AkuvoxUnsupportedError(
        "blocked",
        reason="capability_missing",
        capability=capability,
        device_class="E21V",
    )


async def _setup_lock_entity(
    hass: HomeAssistant,
    entry_data: dict[str, Any],
) -> Any:
    """Set up the integration and return the front-gate lock entity."""
    entry = MockConfigEntry(domain=DOMAIN, data=entry_data, unique_id=MOCK_MAC)
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    comp: EntityComponent[Any] = hass.data["lock"]
    entity = comp.get_entity("lock.testlab_intercom_front_gate")
    assert entity is not None
    return entity


async def test_lock_precheck_reports_unsupported_capability(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test lock actions report unsupported capability prechecks."""
    entity = await _setup_lock_entity(hass, mock_config_entry_data_none)
    entity.coordinator.data.capabilities = DeviceCapabilities(
        device_class="E21V",
        firmware_version="1.0.0",
        capabilities={
            capability: CapabilityStatus.SUPPORTED for capability in Capability
        }
        | {Capability.RELAY_TRIGGER_API: CapabilityStatus.UNSUPPORTED},
        field_aliases={},
        schema_shapes={},
    )

    with pytest.raises(HomeAssistantError):
        await entity.async_unlock()

    mock_akuvox_device.trigger_relay.assert_not_awaited()
    assert len(hass.data[DOMAIN]["unsupported_capability_issue_ids"]) == 1


async def test_relay_status_unsupported_skips_entity_creation(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    unsupported_relay_status_capabilities: DeviceCapabilities,
) -> None:
    """Test relay status unsupported prevents lock entity creation."""

    async def _enter() -> Any:
        """Enter a mock device with unsupported relay status."""
        mock_akuvox_device.capabilities = unsupported_relay_status_capabilities
        return mock_akuvox_device

    mock_akuvox_device.__aenter__ = AsyncMock(side_effect=_enter)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("lock.testlab_intercom_front_gate") is None
    assert len(hass.data[DOMAIN]["unsupported_capability_issue_ids"]) == 1


async def test_unrecognized_relay_status_reports_device_unrecognized(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    unrecognized_capabilities: DeviceCapabilities,
) -> None:
    """Test unrecognized relay status creates device-unrecognized repairs."""

    async def _enter() -> Any:
        """Enter a mock device with unrecognized capabilities."""
        mock_akuvox_device.capabilities = unrecognized_capabilities
        return mock_akuvox_device

    mock_akuvox_device.__aenter__ = AsyncMock(side_effect=_enter)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    issue_id = next(iter(hass.data[DOMAIN]["unsupported_capability_issue_ids"]))
    assert "device_unrecognized" in issue_id


def test_attempt_unknown_defaults_false_without_config_entry(
    hass: HomeAssistant,
    mock_device_info: Any,
    supported_capabilities: DeviceCapabilities,
) -> None:
    """Test entity opt-in helper is false without a config entry."""
    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=AsyncMock())
    coordinator.data = AkuvoxCoordinatorData(
        device_info=mock_device_info,
        relay_status={"RelayA": 0},
        capabilities=supported_capabilities,
    )
    entity = AkuvoxLockEntity(coordinator, "RelayA")

    assert entity._attempt_unknown() is False


async def test_unknown_relay_api_opt_in_passes_adapter(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test opted-in unknown API relay support passes the API adapter."""
    entry_data = {
        **mock_config_entry_data_none,
        CONF_ATTEMPT_UNKNOWN_CAPABILITY: True,
    }
    entity = await _setup_lock_entity(hass, entry_data)
    entity.coordinator.data.capabilities = DeviceCapabilities(
        device_class="E21V",
        firmware_version="1.0.0",
        capabilities={
            capability: CapabilityStatus.SUPPORTED for capability in Capability
        }
        | {Capability.RELAY_TRIGGER_API: CapabilityStatus.UNKNOWN},
        field_aliases={},
        schema_shapes={},
    )

    assert entity._relay_adapter() is Capability.RELAY_TRIGGER_API


async def test_lock_trigger_unsupported_paths(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test lock and unlock trigger paths report upstream unsupported errors."""
    entity = await _setup_lock_entity(hass, mock_config_entry_data_none)

    mock_akuvox_device.trigger_relay = AsyncMock(
        side_effect=_unsupported(Capability.RELAY_TRIGGER_API)
    )
    with pytest.raises(HomeAssistantError):
        await entity.async_unlock()

    mock_akuvox_device.get_relay_status = AsyncMock(return_value={"RelayA": 0})
    entity.coordinator.data.relay_configs["A"] = RelayConfig(relay_mode=1)
    with pytest.raises(HomeAssistantError):
        await entity.async_unlock()

    mock_akuvox_device.get_relay_status = AsyncMock(return_value={"RelayA": 1})
    with pytest.raises(HomeAssistantError):
        await entity.async_lock()


async def test_entity_service_methods_report_unsupported(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_schedule_list: list[Any],
    mock_user_list: list[Any],
) -> None:
    """Test entity service methods convert unsupported errors to HA errors."""
    entity = await _setup_lock_entity(hass, mock_config_entry_data_none)

    mock_akuvox_device.list_schedules = AsyncMock(
        side_effect=_unsupported(Capability.SCHEDULE_LIST)
    )
    with pytest.raises(HomeAssistantError):
        await entity.list_schedules()

    mock_akuvox_device.list_users = AsyncMock(
        side_effect=_unsupported(Capability.USER_LIST)
    )
    with pytest.raises(HomeAssistantError):
        await entity.list_users()

    mock_akuvox_device.add_schedule = AsyncMock(
        side_effect=_unsupported(Capability.SCHEDULE_ADD)
    )
    with pytest.raises(HomeAssistantError):
        await entity.add_schedule(
            schedule_type="2",
            time_start=dt.time(8, 0),
            time_end=dt.time(17, 0),
        )

    with pytest.raises(HomeAssistantError):
        await entity.modify_schedule(id="1")

    mock_akuvox_device.list_schedules = AsyncMock(return_value=mock_schedule_list[:1])
    mock_akuvox_device.modify_schedule = AsyncMock(
        side_effect=_unsupported(Capability.SCHEDULE_MODIFY)
    )
    with pytest.raises(HomeAssistantError):
        await entity.modify_schedule(id="1")

    mock_akuvox_device.delete_schedule = AsyncMock(
        side_effect=_unsupported(Capability.SCHEDULE_DELETE)
    )
    with pytest.raises(HomeAssistantError):
        await entity.delete_schedule(id="1")

    mock_akuvox_device.list_users = AsyncMock(
        side_effect=_unsupported(Capability.USER_LIST)
    )
    with pytest.raises(HomeAssistantError):
        await entity.delete_user(id="42")

    mock_akuvox_device.list_schedules = AsyncMock(
        side_effect=_unsupported(Capability.SCHEDULE_LIST)
    )
    with pytest.raises(HomeAssistantError):
        await entity.add_user(
            name="Jane",
            schedules=["10"],
            lift_floor_num="1",
            private_pin="1234",
        )

    mock_akuvox_device.list_schedules = AsyncMock(return_value=mock_schedule_list[:1])
    mock_akuvox_device.add_user = AsyncMock(
        side_effect=_unsupported(Capability.USER_ADD)
    )
    with pytest.raises(HomeAssistantError):
        await entity.add_user(
            name="Jane",
            schedules=["10"],
            lift_floor_num="1",
            private_pin="1234",
        )

    mock_akuvox_device.list_users = AsyncMock(return_value=mock_user_list[:1])
    mock_akuvox_device.modify_user = AsyncMock(
        side_effect=_unsupported(Capability.USER_MODIFY)
    )
    with pytest.raises(HomeAssistantError):
        await entity.modify_user(id="42")

    mock_akuvox_device.delete_user = AsyncMock(
        side_effect=_unsupported(Capability.USER_DELETE)
    )
    with pytest.raises(HomeAssistantError):
        await entity.delete_user(id="42")

    with pytest.raises(HomeAssistantError):
        await entity.add_user_schedule_relay(
            id="42",
            schedule_id="10",
            relay_id="2",
        )

    user_with_two_relays = replace(mock_user_list[0], schedule_relay="10-1,10-2")
    mock_akuvox_device.list_users = AsyncMock(return_value=[user_with_two_relays])
    with pytest.raises(HomeAssistantError):
        await entity.remove_user_schedule_relay(
            id="42",
            schedule_id="10",
            relay_id="1",
        )


async def test_contact_and_group_services_report_unsupported(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test contact and group services report unsupported errors."""
    entity = await _setup_lock_entity(hass, mock_config_entry_data_none)

    service_calls: list[tuple[str, Capability, dict[str, Any]]] = [
        ("list_contacts", Capability.CONTACT_LIST, {}),
        ("list_groups", Capability.GROUP_LIST, {}),
        ("add_contact", Capability.CONTACT_ADD, {"name": "Jane"}),
        ("add_group", Capability.GROUP_ADD, {"name": "Visitors"}),
        ("modify_contact", Capability.CONTACT_MODIFY, {"id": ["1"], "name": "Jane"}),
        ("modify_group", Capability.GROUP_MODIFY, {"id": "1", "name": "Visitors"}),
        ("delete_contact", Capability.CONTACT_DELETE, {"id": ["1"]}),
        ("delete_group", Capability.GROUP_DELETE, {"id": "1"}),
    ]
    for method_name, capability, kwargs in service_calls:
        setattr(
            mock_akuvox_device,
            method_name,
            AsyncMock(side_effect=_unsupported(capability)),
        )
        if method_name == "delete_group":
            mock_akuvox_device.list_groups = AsyncMock(return_value=[])
        with pytest.raises(HomeAssistantError):
            await getattr(entity, method_name)(**kwargs)
