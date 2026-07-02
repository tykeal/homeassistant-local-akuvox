# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Tests for Local Akuvox diagnostics."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from pylocal_akuvox import (
    AkuvoxAuthenticationError,
    AkuvoxUnsupportedError,
    Capability,
    DeviceCapabilities,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.local_akuvox.const import (
    CONF_AUTH_METHOD,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USE_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    CONF_WEBHOOK_ID,
    DOMAIN,
)
from custom_components.local_akuvox.coordinator import (
    AkuvoxCoordinatorData,
    AkuvoxDataUpdateCoordinator,
)
from custom_components.local_akuvox.diagnostics import (
    _safe_device_info,
    async_get_config_entry_diagnostics,
)
from tests.conftest import (
    MOCK_FW_VERSION,
    MOCK_HOST,
    MOCK_HW_VERSION,
    MOCK_MAC,
    MOCK_MODEL,
    MOCK_WEBHOOK_ID,
)


def test_diagnostics_do_not_import_report_service() -> None:
    """Test diagnostics stay passive and do not call capability reports."""
    import custom_components.local_akuvox.diagnostics as diagnostics

    assert not hasattr(diagnostics, "run_capability_report")
    assert not hasattr(diagnostics, "_run_capability_report")


async def test_diagnostics_sanitizes_entry_and_current_capabilities(
    hass: HomeAssistant,
    mock_device_info: Any,
    supported_capabilities: DeviceCapabilities,
) -> None:
    """Test diagnostics include safe entry and current capability data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: MOCK_HOST,
            CONF_USE_SSL: False,
            CONF_VERIFY_SSL: True,
            CONF_AUTH_METHOD: "basic",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "secret",
            CONF_WEBHOOK_ID: MOCK_WEBHOOK_ID,
        },
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)
    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=AsyncMock())
    coordinator.data = AkuvoxCoordinatorData(
        device_info=mock_device_info,
        relay_status={"RelayA": 0},
        capabilities=supported_capabilities,
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    device = AsyncMock()
    device.__aenter__ = AsyncMock(return_value=device)
    device.__aexit__ = AsyncMock(return_value=None)
    device.probe_capabilities = AsyncMock(return_value=supported_capabilities)
    with patch(
        "custom_components.local_akuvox.diagnostics._create_device",
        return_value=device,
    ):
        result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["entry"]["host"] == MOCK_HOST
    assert CONF_PASSWORD not in str(result)
    assert MOCK_WEBHOOK_ID not in str(result)
    assert result["device_info"] == {
        "model": MOCK_MODEL,
        "firmware_version": MOCK_FW_VERSION,
        "hardware_version": MOCK_HW_VERSION,
    }
    assert "mac_address" not in result["device_info"]
    assert MOCK_MAC not in str(result["device_info"])
    assert "user.list" in result["current_capabilities"]["capabilities"]
    device.probe_capabilities.assert_awaited_once_with(timeout=5.0)


def test_safe_device_info_handles_missing_coordinator_data(
    hass: HomeAssistant,
) -> None:
    """Test safe device info handles missing coordinator data."""
    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=AsyncMock())

    assert _safe_device_info(None) == {}
    assert _safe_device_info(coordinator) == {}


async def test_diagnostics_records_safe_probe_error(
    hass: HomeAssistant,
    mock_device_info: Any,
    supported_capabilities: DeviceCapabilities,
) -> None:
    """Test diagnostics records safe probe errors without raising."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: MOCK_HOST})
    entry.add_to_hass(hass)
    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=AsyncMock())
    coordinator.data = AkuvoxCoordinatorData(
        device_info=mock_device_info,
        relay_status={},
        capabilities=supported_capabilities,
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    device = AsyncMock()
    device.__aenter__ = AsyncMock(return_value=device)
    device.__aexit__ = AsyncMock(return_value=None)
    device.probe_capabilities = AsyncMock(
        side_effect=AkuvoxAuthenticationError("bad password")
    )

    with patch(
        "custom_components.local_akuvox.diagnostics._create_device",
        return_value=device,
    ):
        result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["probe"]["error"]["type"] == "AkuvoxAuthenticationError"
    assert Capability.USER_LIST.value in result["current_capabilities"]["capabilities"]


async def test_diagnostics_reports_unsupported_probe_error(
    hass: HomeAssistant,
    mock_device_info: Any,
    supported_capabilities: DeviceCapabilities,
) -> None:
    """Test diagnostics reports structured unsupported probe errors."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: MOCK_HOST})
    entry.add_to_hass(hass)
    coordinator = AkuvoxDataUpdateCoordinator(hass=hass, device=AsyncMock())
    coordinator.data = AkuvoxCoordinatorData(
        device_info=mock_device_info,
        relay_status={},
        capabilities=supported_capabilities,
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    device = AsyncMock()
    device.__aenter__ = AsyncMock(return_value=device)
    device.__aexit__ = AsyncMock(return_value=None)
    device.probe_capabilities = AsyncMock(
        side_effect=AkuvoxUnsupportedError(
            "blocked",
            reason="device_unrecognized",
            capability=Capability.USER_LIST,
            device_class="unknown",
        )
    )

    with patch(
        "custom_components.local_akuvox.diagnostics._create_device",
        return_value=device,
    ):
        result = await async_get_config_entry_diagnostics(hass, entry)

    assert result["probe"]["error"]["reason"] == "device_unrecognized"
    assert result["probe"]["error"]["capability"] == "user.list"
    assert len(hass.data[DOMAIN]["unsupported_capability_issue_ids"]) == 1
