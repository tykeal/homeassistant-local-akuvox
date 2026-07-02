# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Akuvox integration setup."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from pylocal_akuvox import (
    AkuvoxAuthenticationError,
    AkuvoxConnectionError,
    AkuvoxUnsupportedError,
    Capability,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.local_akuvox import async_setup_entry
from custom_components.local_akuvox.const import (
    CONF_PASSWORD,
    CONFIG_KEY_LOCATION,
    DATA_CAPABILITY_REPORT_LOCK,
    DOMAIN,
)
from tests.conftest import MOCK_MAC


async def test_setup_entry_creates_coordinator(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_info: Any,
    mock_relay_status: dict[str, Any],
) -> None:
    """Test async_setup_entry creates coordinator in hass.data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert DOMAIN in hass.data
    assert entry.entry_id in hass.data[DOMAIN]


async def test_setup_entry_forwards_to_lock(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_info: Any,
    mock_relay_status: dict[str, Any],
) -> None:
    """Test async_setup_entry forwards to lock platform."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    # Verify lock entity was created (platform was forwarded)
    state = hass.states.get("lock.testlab_intercom_front_gate")
    assert state is not None


async def test_unload_entry_cleans_up(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_info: Any,
    mock_relay_status: dict[str, Any],
) -> None:
    """Test async_unload_entry cleans up hass.data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.NOT_LOADED  # type: ignore[comparison-overlap]
    assert entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_setup_fails_on_connection_error(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
) -> None:
    """Test setup fails gracefully on initial connection error."""
    from pylocal_akuvox import AkuvoxConnectionError

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        device = mock_cls.return_value
        device.get_relay_status = AsyncMock(
            side_effect=AkuvoxConnectionError("Cannot connect"),
        )
        device.__aenter__ = AsyncMock(return_value=device)
        device.__aexit__ = AsyncMock(return_value=None)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_entry_maps_entry_auth_failure(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
) -> None:
    """Test setup maps context-entry authentication failures to reauth."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        device = mock_cls.return_value
        device.__aenter__ = AsyncMock(
            side_effect=AkuvoxAuthenticationError("bad credentials")
        )

        with pytest.raises(ConfigEntryAuthFailed):
            await async_setup_entry(hass, entry)


async def test_setup_entry_reports_entry_unsupported(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
) -> None:
    """Test setup reports context-entry unsupported capability failures."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)
    err = AkuvoxUnsupportedError(
        "blocked",
        reason="device_unrecognized",
        capability=Capability.DEVICE_CONFIG_GET,
    )

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        device = mock_cls.return_value
        device.__aenter__ = AsyncMock(side_effect=err)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
    issue_id = next(iter(hass.data[DOMAIN]["unsupported_capability_issue_ids"]))
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None


async def test_setup_entry_maps_entry_connection_failure(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
) -> None:
    """Test setup maps other context-entry Akuvox failures to retry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        device = mock_cls.return_value
        device.__aenter__ = AsyncMock(side_effect=AkuvoxConnectionError("offline"))

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


def test_create_device_uses_basic_auth_credentials(
    mock_config_entry_data_basic: dict[str, Any],
) -> None:
    """Test device creation passes basic auth credentials to library."""
    from custom_components.local_akuvox import _create_device

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_basic,
        unique_id=MOCK_MAC,
    )

    with patch("custom_components.local_akuvox.AkuvoxDevice") as mock_cls:
        _create_device(entry)

    auth = mock_cls.call_args.kwargs["auth"]
    assert auth.username == "admin"
    assert auth.password == mock_config_entry_data_basic[CONF_PASSWORD]


async def test_setup_entry_cleans_up_when_forwarding_fails(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test setup failure during platform forwarding unloads resources."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    with patch.object(
        hass.config_entries,
        "async_forward_entry_setups",
        side_effect=RuntimeError("platform failed"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert DOMAIN not in hass.data
    mock_akuvox_device.__aexit__.assert_awaited_once_with(None, None, None)


# ── T018: Device name from config location ──────────────────────


async def test_device_name_from_config_location(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test HA device name matches DeviceConfig location."""
    cfg = mock_device_config_factory(
        **{CONFIG_KEY_LOCATION: "Front Door"},
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

    dev_reg = dr.async_get(hass)
    mac_clean = MOCK_MAC.lower().replace(":", "")
    device = dev_reg.async_get_device(identifiers={(DOMAIN, mac_clean)})
    assert device is not None
    assert device.name == "Front Door"


async def test_device_name_fallback_when_location_empty(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
    mock_device_config_factory: Any,
) -> None:
    """Test fallback to 'Akuvox {model}' when location is empty."""
    cfg = mock_device_config_factory(
        **{CONFIG_KEY_LOCATION: ""},
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

    dev_reg = dr.async_get(hass)
    mac_clean = MOCK_MAC.lower().replace(":", "")
    device = dev_reg.async_get_device(identifiers={(DOMAIN, mac_clean)})
    assert device is not None
    assert device.name == "Akuvox E21V"


# ── T038: Config fetch during integration reload ─────────────────


async def test_config_fetched_on_reload(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test get_device_config is called after unload and reload."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC,
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    # Record how many times config was fetched during initial setup
    initial_config_calls = mock_akuvox_device.get_device_config.await_count

    # Unload
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED  # type: ignore[comparison-overlap]

    # Reload
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    # get_device_config should have been awaited again on reload
    assert mock_akuvox_device.get_device_config.await_count > initial_config_calls


# ── Webhook lifecycle tests (T009) ──────────────────────────


async def test_webhook_registered_when_enabled(
    hass: HomeAssistant,
    mock_config_entry_data_webhook: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test webhook endpoint registered during setup when enabled."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_webhook,
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.local_akuvox.webhook.async_register",
    ) as mock_register:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.LOADED
        mock_register.assert_called_once()
        # Verify webhook_registry populated
        registry = hass.data[DOMAIN].get("webhook_registry", {})
        from tests.conftest import MOCK_WEBHOOK_ID

        assert MOCK_WEBHOOK_ID in registry
        assert registry[MOCK_WEBHOOK_ID] == entry.entry_id


async def test_webhook_not_registered_when_disabled(
    hass: HomeAssistant,
    mock_config_entry_data_webhook_disabled: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test webhook not registered when webhook_enabled=False."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_webhook_disabled,
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.local_akuvox.webhook.async_register",
    ) as mock_register:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.LOADED
        mock_register.assert_not_called()


async def test_webhook_not_registered_when_no_webhook_fields(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test webhook not registered for entries without webhook fields."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.local_akuvox.webhook.async_register",
    ) as mock_register:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.LOADED
        mock_register.assert_not_called()


async def test_webhook_unregistered_on_unload(
    hass: HomeAssistant,
    mock_config_entry_data_webhook: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test webhook unregistered during unload when in registry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_webhook,
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.local_akuvox.webhook.async_register",
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED

    with patch(
        "custom_components.local_akuvox.webhook.async_unregister",
    ) as mock_unregister:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.NOT_LOADED  # type: ignore[comparison-overlap]
        mock_unregister.assert_called_once()

    # Registry entry cleaned up
    registry = hass.data.get(DOMAIN, {}).get("webhook_registry", {})
    from tests.conftest import MOCK_WEBHOOK_ID

    assert MOCK_WEBHOOK_ID not in registry


async def test_webhook_unload_safe_noop_when_not_in_registry(
    hass: HomeAssistant,
    mock_config_entry_data_webhook_disabled: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test unload with webhook_id but not in registry is safe."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_webhook_disabled,
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    with patch(
        "custom_components.local_akuvox.webhook.async_unregister",
    ) as mock_unregister:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

        # Not called since webhook was never registered
        mock_unregister.assert_not_called()


async def test_unload_cleans_up_empty_registry(
    hass: HomeAssistant,
    mock_config_entry_data_webhook: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test unload removes empty webhook_registry and DOMAIN keys."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_webhook,
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.local_akuvox.webhook.async_register",
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    with patch(
        "custom_components.local_akuvox.webhook.async_unregister",
    ):
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

    # DOMAIN key should be cleaned up when last entry unloads
    assert DOMAIN not in hass.data


async def test_unload_cleans_reserved_report_lock(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test final unload removes reserved capability report lock data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    hass.data[DOMAIN][DATA_CAPABILITY_REPORT_LOCK] = object()

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert DOMAIN not in hass.data


async def test_unload_preserves_other_runtime_data(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_akuvox_device: AsyncMock,
) -> None:
    """Test final unload removes only the report lock when data remains."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    hass.data[DOMAIN][DATA_CAPABILITY_REPORT_LOCK] = object()
    hass.data[DOMAIN]["other_runtime_data"] = {"kept": True}

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert DATA_CAPABILITY_REPORT_LOCK not in hass.data[DOMAIN]
    assert hass.data[DOMAIN]["other_runtime_data"] == {"kept": True}


def test_cleanup_domain_runtime_data_ignores_non_dict(
    hass: HomeAssistant,
) -> None:
    """Test domain cleanup tolerates unexpected non-dict runtime data."""
    from custom_components.local_akuvox import _cleanup_domain_runtime_data

    hass.data[DOMAIN] = object()
    _cleanup_domain_runtime_data(hass)

    assert DOMAIN in hass.data


# --- async_remove_entry tests ---


async def test_remove_entry_pushes_disable_when_enabled(
    hass: HomeAssistant,
    mock_config_entry_data_webhook: dict[str, Any],
    mock_relay_status: dict[str, Any],
    mock_device_info: Any,
    mock_device_config: Any,
) -> None:
    """Test removal pushes disable payload when webhook was enabled."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_webhook,
        unique_id=MOCK_MAC.lower().replace(":", ""),
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        device = mock_cls.return_value
        device.__aenter__ = AsyncMock(return_value=device)
        device.__aexit__ = AsyncMock(return_value=None)
        device.get_relay_status = AsyncMock(
            return_value=mock_relay_status,
        )
        device.get_info = AsyncMock(return_value=mock_device_info)
        device.get_device_config = AsyncMock(
            return_value=mock_device_config,
        )
        device.set_device_config = AsyncMock(return_value=None)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_remove_cls:
        remove_dev = mock_remove_cls.return_value
        remove_dev.__aenter__ = AsyncMock(return_value=remove_dev)
        remove_dev.__aexit__ = AsyncMock(return_value=None)
        remove_dev.set_device_config = AsyncMock(return_value=None)

        await hass.config_entries.async_remove(entry.entry_id)
        await hass.async_block_till_done()

    remove_dev.set_device_config.assert_awaited_once()


async def test_remove_entry_skips_when_disabled(
    hass: HomeAssistant,
    mock_config_entry_data_none: dict[str, Any],
    mock_relay_status: dict[str, Any],
    mock_device_info: Any,
    mock_device_config: Any,
) -> None:
    """Test removal does not push when webhook was disabled."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_none,
        unique_id=MOCK_MAC.lower().replace(":", ""),
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        device = mock_cls.return_value
        device.__aenter__ = AsyncMock(return_value=device)
        device.__aexit__ = AsyncMock(return_value=None)
        device.get_relay_status = AsyncMock(
            return_value=mock_relay_status,
        )
        device.get_info = AsyncMock(return_value=mock_device_info)
        device.get_device_config = AsyncMock(
            return_value=mock_device_config,
        )

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_remove_cls:
        remove_dev = mock_remove_cls.return_value
        remove_dev.__aenter__ = AsyncMock(return_value=remove_dev)
        remove_dev.__aexit__ = AsyncMock(return_value=None)
        remove_dev.set_device_config = AsyncMock(return_value=None)

        await hass.config_entries.async_remove(entry.entry_id)
        await hass.async_block_till_done()

    remove_dev.set_device_config.assert_not_awaited()


async def test_remove_entry_handles_push_failure(
    hass: HomeAssistant,
    mock_config_entry_data_webhook: dict[str, Any],
    mock_relay_status: dict[str, Any],
    mock_device_info: Any,
    mock_device_config: Any,
) -> None:
    """Test removal logs warning on push failure, does not block."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_webhook,
        unique_id=MOCK_MAC.lower().replace(":", ""),
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        device = mock_cls.return_value
        device.__aenter__ = AsyncMock(return_value=device)
        device.__aexit__ = AsyncMock(return_value=None)
        device.get_relay_status = AsyncMock(
            return_value=mock_relay_status,
        )
        device.get_info = AsyncMock(return_value=mock_device_info)
        device.get_device_config = AsyncMock(
            return_value=mock_device_config,
        )

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_remove_cls:
        remove_dev = mock_remove_cls.return_value
        remove_dev.__aenter__ = AsyncMock(return_value=remove_dev)
        remove_dev.__aexit__ = AsyncMock(return_value=None)
        remove_dev.set_device_config = AsyncMock(
            side_effect=Exception("Device offline"),
        )

        # Should not raise — best-effort
        await hass.config_entries.async_remove(entry.entry_id)
        await hass.async_block_till_done()


async def test_remove_entry_reports_unsupported_push_failure(
    hass: HomeAssistant,
    mock_config_entry_data_webhook: dict[str, Any],
    mock_relay_status: dict[str, Any],
    mock_device_info: Any,
    mock_device_config: Any,
) -> None:
    """Test removal reports unsupported webhook disable failures."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=mock_config_entry_data_webhook,
        unique_id=MOCK_MAC.lower().replace(":", ""),
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_cls:
        device = mock_cls.return_value
        device.__aenter__ = AsyncMock(return_value=device)
        device.__aexit__ = AsyncMock(return_value=None)
        device.get_relay_status = AsyncMock(return_value=mock_relay_status)
        device.get_info = AsyncMock(return_value=mock_device_info)
        device.get_device_config = AsyncMock(return_value=mock_device_config)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    with patch(
        "custom_components.local_akuvox.AkuvoxDevice",
        autospec=True,
    ) as mock_remove_cls:
        remove_dev = mock_remove_cls.return_value
        remove_dev.__aenter__ = AsyncMock(return_value=remove_dev)
        remove_dev.__aexit__ = AsyncMock(return_value=None)
        remove_dev.set_device_config = AsyncMock(
            side_effect=AkuvoxUnsupportedError(
                "blocked",
                reason="capability_missing",
                capability=Capability.DEVICE_CONFIG_SET,
            )
        )

        await hass.config_entries.async_remove(entry.entry_id)
        await hass.async_block_till_done()

    assert DOMAIN not in hass.data
