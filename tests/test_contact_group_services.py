# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Tests for Akuvox contact and group CRUD services."""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import AsyncMock

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pylocal_akuvox import (
    AkuvoxConnectionError,
    AkuvoxDeviceError,
    AkuvoxValidationError,
    Contact,
    Group,
)
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
)

from custom_components.local_akuvox.const import (
    DOMAIN,
    EVENT_CONTACT_CHANGED,
    EVENT_GROUP_CHANGED,
)
from tests.conftest import setup_entry

ENTITY_ID = "lock.testlab_intercom_front_gate"


# ── US1: List Contacts ───────────────────────────────────────


async def test_list_contacts_returns_all_contacts(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_contact_list: list[Contact],
) -> None:
    """Test list_contacts returns contact dicts."""
    mock_akuvox_device.list_contacts.return_value = mock_contact_list
    await setup_entry(hass, mock_config_entry_data_none)

    result = await hass.services.async_call(
        DOMAIN,
        "list_contacts",
        service_data={"entity_id": ENTITY_ID},
        blocking=True,
        return_response=True,
    )

    assert result is not None
    entity_result = result[ENTITY_ID]
    assert isinstance(entity_result, dict)
    assert "contacts" in entity_result
    contacts = entity_result["contacts"]
    assert isinstance(contacts, list)
    assert len(contacts) == 2
    first = contacts[0]
    assert isinstance(first, dict)
    assert first["id"] == "1"
    assert first["name"] == "John Doe"
    assert first["phone"] == "555-1234"
    assert first["group"] == "Family"
    second = contacts[1]
    assert isinstance(second, dict)
    assert second["id"] == "2"
    assert second["name"] == "Jane Smith"
    assert second["phone"] is None
    assert second["group"] is None


async def test_list_contacts_empty(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test list_contacts with no contacts returns empty list."""
    mock_akuvox_device.list_contacts.return_value = []
    await setup_entry(hass, mock_config_entry_data_none)

    result = await hass.services.async_call(
        DOMAIN,
        "list_contacts",
        service_data={"entity_id": ENTITY_ID},
        blocking=True,
        return_response=True,
    )

    assert result is not None
    assert result[ENTITY_ID] == {"contacts": []}


async def test_list_contacts_with_page(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test page parameter is forwarded to device."""
    mock_akuvox_device.list_contacts.return_value = []
    await setup_entry(hass, mock_config_entry_data_none)

    await hass.services.async_call(
        DOMAIN,
        "list_contacts",
        service_data={"entity_id": ENTITY_ID, "page": 2},
        blocking=True,
        return_response=True,
    )

    mock_akuvox_device.list_contacts.assert_called_once_with(page=2)


async def test_list_contacts_device_offline(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test device offline raises HomeAssistantError."""
    mock_akuvox_device.list_contacts.side_effect = AkuvoxConnectionError("offline")
    await setup_entry(hass, mock_config_entry_data_none)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "list_contacts",
            service_data={"entity_id": ENTITY_ID},
            blocking=True,
            return_response=True,
        )


# ── US2: List Groups ─────────────────────────────────────────


async def test_list_groups_returns_all_groups(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_group_list: list[Group],
) -> None:
    """Test list_groups returns group dicts."""
    mock_akuvox_device.list_groups.return_value = mock_group_list
    await setup_entry(hass, mock_config_entry_data_none)

    result = await hass.services.async_call(
        DOMAIN,
        "list_groups",
        service_data={"entity_id": ENTITY_ID},
        blocking=True,
        return_response=True,
    )

    assert result is not None
    entity_result = result[ENTITY_ID]
    assert isinstance(entity_result, dict)
    assert "groups" in entity_result
    groups = entity_result["groups"]
    assert isinstance(groups, list)
    assert len(groups) == 2
    first = groups[0]
    assert isinstance(first, dict)
    assert first["id"] == "1"
    assert first["name"] == "Family"
    second = groups[1]
    assert isinstance(second, dict)
    assert second["id"] == "2"
    assert second["name"] == "Maintenance"


async def test_list_groups_empty(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test list_groups with no groups returns empty list."""
    mock_akuvox_device.list_groups.return_value = []
    await setup_entry(hass, mock_config_entry_data_none)

    result = await hass.services.async_call(
        DOMAIN,
        "list_groups",
        service_data={"entity_id": ENTITY_ID},
        blocking=True,
        return_response=True,
    )

    assert result is not None
    assert result[ENTITY_ID] == {"groups": []}


async def test_list_groups_with_page(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test page parameter is forwarded to device."""
    mock_akuvox_device.list_groups.return_value = []
    await setup_entry(hass, mock_config_entry_data_none)

    await hass.services.async_call(
        DOMAIN,
        "list_groups",
        service_data={"entity_id": ENTITY_ID, "page": 3},
        blocking=True,
        return_response=True,
    )

    mock_akuvox_device.list_groups.assert_called_once_with(page=3)


async def test_list_groups_device_offline(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test device offline raises HomeAssistantError."""
    mock_akuvox_device.list_groups.side_effect = AkuvoxConnectionError("offline")
    await setup_entry(hass, mock_config_entry_data_none)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "list_groups",
            service_data={"entity_id": ENTITY_ID},
            blocking=True,
            return_response=True,
        )


# ── US3: Add Contact ─────────────────────────────────────────


async def test_add_contact_with_all_fields(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test add_contact with all fields calls device and fires event."""
    entry = await setup_entry(hass, mock_config_entry_data_none)
    events = async_capture_events(hass, EVENT_CONTACT_CHANGED)

    await hass.services.async_call(
        DOMAIN,
        "add_contact",
        service_data={
            "entity_id": ENTITY_ID,
            "name": "John Doe",
            "phone": "555-1234",
            "group": "Family",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_akuvox_device.add_contact.assert_called_once_with(
        name="John Doe",
        phone="555-1234",
        group="Family",
    )
    assert len(events) == 1
    assert events[0].data["action"] == "add"
    assert events[0].data["config_entry_id"] == entry.entry_id


async def test_add_contact_name_only(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test add_contact with name only passes None for optional fields."""
    await setup_entry(hass, mock_config_entry_data_none)

    await hass.services.async_call(
        DOMAIN,
        "add_contact",
        service_data={
            "entity_id": ENTITY_ID,
            "name": "Jane Smith",
        },
        blocking=True,
    )

    mock_akuvox_device.add_contact.assert_called_once_with(
        name="Jane Smith",
        phone=None,
        group=None,
    )


async def test_add_contact_missing_name(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test add_contact without name raises vol.Invalid."""
    await setup_entry(hass, mock_config_entry_data_none)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            "add_contact",
            service_data={
                "entity_id": ENTITY_ID,
                "phone": "555-1234",
            },
            blocking=True,
        )


async def test_add_contact_device_error(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test device error raises HomeAssistantError and no event fired."""
    mock_akuvox_device.add_contact.side_effect = AkuvoxDeviceError("fail")
    await setup_entry(hass, mock_config_entry_data_none)
    events = async_capture_events(hass, EVENT_CONTACT_CHANGED)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "add_contact",
            service_data={
                "entity_id": ENTITY_ID,
                "name": "John Doe",
            },
            blocking=True,
        )
    await hass.async_block_till_done()

    assert len(events) == 0


# ── US4: Add Group ────────────────────────────────────────────


async def test_add_group_success(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test add_group calls device and fires event."""
    entry = await setup_entry(hass, mock_config_entry_data_none)
    events = async_capture_events(hass, EVENT_GROUP_CHANGED)

    await hass.services.async_call(
        DOMAIN,
        "add_group",
        service_data={
            "entity_id": ENTITY_ID,
            "name": "Family",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_akuvox_device.add_group.assert_called_once_with(name="Family")
    assert len(events) == 1
    assert events[0].data["action"] == "add"
    assert events[0].data["config_entry_id"] == entry.entry_id


async def test_add_group_missing_name(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test add_group without name raises vol.Invalid."""
    await setup_entry(hass, mock_config_entry_data_none)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            "add_group",
            service_data={
                "entity_id": ENTITY_ID,
            },
            blocking=True,
        )


async def test_add_group_device_error(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test device error raises HomeAssistantError and no event fired."""
    mock_akuvox_device.add_group.side_effect = AkuvoxDeviceError("fail")
    await setup_entry(hass, mock_config_entry_data_none)
    events = async_capture_events(hass, EVENT_GROUP_CHANGED)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "add_group",
            service_data={
                "entity_id": ENTITY_ID,
                "name": "Family",
            },
            blocking=True,
        )
    await hass.async_block_till_done()

    assert len(events) == 0


# ── US5: Modify Contact ──────────────────────────────────────


async def test_modify_contact_success(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test modify_contact calls device and fires event."""
    entry = await setup_entry(hass, mock_config_entry_data_none)
    events = async_capture_events(hass, EVENT_CONTACT_CHANGED)

    await hass.services.async_call(
        DOMAIN,
        "modify_contact",
        service_data={
            "entity_id": ENTITY_ID,
            "id": "42",
            "phone": "555-9999",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_akuvox_device.modify_contact.assert_called_once_with(
        id="42",
        name=None,
        phone="555-9999",
        group=None,
    )
    assert len(events) == 1
    assert events[0].data["action"] == "modify"
    assert events[0].data["contact_id"] == "42"
    assert events[0].data["config_entry_id"] == entry.entry_id


async def test_modify_contact_not_found(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test device error (not found) raises HomeAssistantError."""
    mock_akuvox_device.modify_contact.side_effect = AkuvoxDeviceError("not found")
    await setup_entry(hass, mock_config_entry_data_none)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "modify_contact",
            service_data={
                "entity_id": ENTITY_ID,
                "id": "999",
                "name": "Updated",
            },
            blocking=True,
        )


async def test_modify_contact_no_fields(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test library validation error maps to ServiceValidationError."""
    mock_akuvox_device.modify_contact.side_effect = AkuvoxValidationError("no fields")
    await setup_entry(hass, mock_config_entry_data_none)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "modify_contact",
            service_data={
                "entity_id": ENTITY_ID,
                "id": "42",
            },
            blocking=True,
        )


async def test_modify_contact_missing_id(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test modify_contact without id raises vol.Invalid."""
    await setup_entry(hass, mock_config_entry_data_none)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            "modify_contact",
            service_data={
                "entity_id": ENTITY_ID,
                "name": "Updated",
            },
            blocking=True,
        )


# ── US6: Modify Group ────────────────────────────────────────


async def test_modify_group_success(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test modify_group calls device and fires event."""
    entry = await setup_entry(hass, mock_config_entry_data_none)
    events = async_capture_events(hass, EVENT_GROUP_CHANGED)

    await hass.services.async_call(
        DOMAIN,
        "modify_group",
        service_data={
            "entity_id": ENTITY_ID,
            "id": "5",
            "name": "Friends",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_akuvox_device.modify_group.assert_called_once_with(
        id="5",
        name="Friends",
    )
    assert len(events) == 1
    assert events[0].data["action"] == "modify"
    assert events[0].data["group_id"] == "5"
    assert events[0].data["config_entry_id"] == entry.entry_id


async def test_modify_group_not_found(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test device error (not found) raises HomeAssistantError."""
    mock_akuvox_device.modify_group.side_effect = AkuvoxDeviceError("not found")
    await setup_entry(hass, mock_config_entry_data_none)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "modify_group",
            service_data={
                "entity_id": ENTITY_ID,
                "id": "999",
                "name": "Updated",
            },
            blocking=True,
        )


async def test_modify_group_missing_id(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test modify_group without id raises vol.Invalid."""
    await setup_entry(hass, mock_config_entry_data_none)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            "modify_group",
            service_data={
                "entity_id": ENTITY_ID,
                "name": "Updated",
            },
            blocking=True,
        )


async def test_modify_group_missing_name(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test modify_group without name raises vol.Invalid."""
    await setup_entry(hass, mock_config_entry_data_none)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            "modify_group",
            service_data={
                "entity_id": ENTITY_ID,
                "id": "5",
            },
            blocking=True,
        )


# ── US7: Delete Contact ──────────────────────────────────────


async def test_delete_contact_single(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test delete_contact with single id calls device and fires event."""
    entry = await setup_entry(hass, mock_config_entry_data_none)
    events = async_capture_events(hass, EVENT_CONTACT_CHANGED)

    await hass.services.async_call(
        DOMAIN,
        "delete_contact",
        service_data={
            "entity_id": ENTITY_ID,
            "id": "42",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_akuvox_device.delete_contact.assert_called_once_with(id=["42"])
    assert len(events) == 1
    assert events[0].data["action"] == "delete"
    assert events[0].data["contact_ids"] == ["42"]
    assert events[0].data["config_entry_id"] == entry.entry_id


async def test_delete_contact_batch(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test delete_contact with list of ids calls device and fires event."""
    entry = await setup_entry(hass, mock_config_entry_data_none)
    events = async_capture_events(hass, EVENT_CONTACT_CHANGED)

    await hass.services.async_call(
        DOMAIN,
        "delete_contact",
        service_data={
            "entity_id": ENTITY_ID,
            "id": ["42", "43", "44"],
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_akuvox_device.delete_contact.assert_called_once_with(
        id=["42", "43", "44"],
    )
    assert len(events) == 1
    assert events[0].data["action"] == "delete"
    assert events[0].data["contact_ids"] == ["42", "43", "44"]
    assert events[0].data["config_entry_id"] == entry.entry_id


async def test_delete_contact_csv(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test delete_contact with CSV string parses into list."""
    await setup_entry(hass, mock_config_entry_data_none)
    events = async_capture_events(hass, EVENT_CONTACT_CHANGED)

    await hass.services.async_call(
        DOMAIN,
        "delete_contact",
        service_data={
            "entity_id": ENTITY_ID,
            "id": "42, 43",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_akuvox_device.delete_contact.assert_called_once_with(
        id=["42", "43"],
    )
    assert len(events) == 1
    assert events[0].data["contact_ids"] == ["42", "43"]


async def test_delete_contact_not_found(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test device error raises HomeAssistantError."""
    mock_akuvox_device.delete_contact.side_effect = AkuvoxDeviceError("not found")
    await setup_entry(hass, mock_config_entry_data_none)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "delete_contact",
            service_data={
                "entity_id": ENTITY_ID,
                "id": "999",
            },
            blocking=True,
        )


async def test_delete_contact_missing_id(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test delete_contact without id raises vol.Invalid."""
    await setup_entry(hass, mock_config_entry_data_none)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            "delete_contact",
            service_data={
                "entity_id": ENTITY_ID,
            },
            blocking=True,
        )


# ── US8: Delete Group ────────────────────────────────────────


async def test_delete_group_success(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test delete_group calls device and fires event."""
    entry = await setup_entry(hass, mock_config_entry_data_none)
    events = async_capture_events(hass, EVENT_GROUP_CHANGED)

    await hass.services.async_call(
        DOMAIN,
        "delete_group",
        service_data={
            "entity_id": ENTITY_ID,
            "id": "5",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_akuvox_device.delete_group.assert_called_once_with(id="5")
    assert len(events) == 1
    assert events[0].data["action"] == "delete"
    assert events[0].data["group_id"] == "5"
    assert events[0].data["config_entry_id"] == entry.entry_id


async def test_delete_group_orphan_warning(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test delete_group logs warning for orphaned contacts."""
    mock_akuvox_device.list_groups.return_value = [
        Group(name="Family", id="5"),
    ]
    mock_akuvox_device.list_contacts.return_value = [
        Contact(name="John Doe", id="1", phone="555-1234", group="Family"),
        Contact(name="Jane Smith", id="2", phone=None, group="other"),
    ]
    await setup_entry(hass, mock_config_entry_data_none)

    with caplog.at_level(logging.WARNING, logger="custom_components.local_akuvox"):
        await hass.services.async_call(
            DOMAIN,
            "delete_group",
            service_data={
                "entity_id": ENTITY_ID,
                "id": "5",
            },
            blocking=True,
        )

    assert "John Doe" in caplog.text
    assert "orphan" in caplog.text.lower() or "still references" in caplog.text.lower()


async def test_delete_group_not_found(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test device error raises HomeAssistantError."""
    mock_akuvox_device.delete_group.side_effect = AkuvoxDeviceError("not found")
    await setup_entry(hass, mock_config_entry_data_none)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "delete_group",
            service_data={
                "entity_id": ENTITY_ID,
                "id": "999",
            },
            blocking=True,
        )


async def test_delete_group_missing_id(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test delete_group without id raises vol.Invalid."""
    await setup_entry(hass, mock_config_entry_data_none)

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            "delete_group",
            service_data={
                "entity_id": ENTITY_ID,
            },
            blocking=True,
        )


@pytest.mark.parametrize(
    ("service", "device_method", "service_data", "return_response"),
    [
        ("list_contacts", "list_contacts", {}, True),
        ("list_groups", "list_groups", {}, True),
        ("add_contact", "add_contact", {"name": "Bad Contact"}, False),
        ("add_group", "add_group", {"name": "Bad Group"}, False),
        ("modify_group", "modify_group", {"id": "5", "name": "Bad"}, False),
        ("delete_contact", "delete_contact", {"id": "5"}, False),
        ("delete_group", "delete_group", {"id": "5"}, False),
    ],
    ids=[
        "list-contacts",
        "list-groups",
        "add-contact",
        "add-group",
        "modify-group",
        "delete-contact",
        "delete-group",
    ],
)
async def test_contact_group_validation_errors(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    service: str,
    device_method: str,
    service_data: dict[str, Any],
    return_response: bool,
) -> None:
    """Test contact and group validation errors map to HA validation."""
    getattr(mock_akuvox_device, device_method).side_effect = AkuvoxValidationError(
        "invalid",
    )
    await setup_entry(hass, mock_config_entry_data_none)

    with pytest.raises(ServiceValidationError, match="invalid"):
        await hass.services.async_call(
            DOMAIN,
            service,
            service_data={"entity_id": ENTITY_ID, **service_data},
            blocking=True,
            return_response=return_response,
        )


async def test_delete_group_logs_contact_orphan_check_failure(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test delete_group tolerates failures during orphan checking."""
    mock_akuvox_device.list_groups.return_value = [Group(name="Family", id="5")]
    mock_akuvox_device.list_contacts.side_effect = AkuvoxDeviceError("offline")
    await setup_entry(hass, mock_config_entry_data_none)

    with caplog.at_level(logging.DEBUG, logger="custom_components.local_akuvox"):
        await hass.services.async_call(
            DOMAIN,
            "delete_group",
            service_data={"entity_id": ENTITY_ID, "id": "5"},
            blocking=True,
        )

    assert "Could not check for orphaned contacts" in caplog.text
    mock_akuvox_device.delete_group.assert_called_once_with(id="5")


async def test_delete_group_logs_group_name_lookup_failure(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test delete_group proceeds when resolving group name fails."""
    mock_akuvox_device.list_groups.side_effect = AkuvoxDeviceError("offline")
    await setup_entry(hass, mock_config_entry_data_none)

    with caplog.at_level(logging.DEBUG, logger="custom_components.local_akuvox"):
        await hass.services.async_call(
            DOMAIN,
            "delete_group",
            service_data={"entity_id": ENTITY_ID, "id": "5"},
            blocking=True,
        )

    assert "Could not resolve group name" in caplog.text
    mock_akuvox_device.delete_group.assert_called_once_with(id="5")
