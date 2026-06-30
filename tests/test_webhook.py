# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Akuvox webhook handler."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlencode

from aiohttp import web
from aiohttp.test_utils import make_mocked_request
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.local_akuvox.const import (
    CONF_WEBHOOK_ID,
    DOMAIN,
    EVENT_WEBHOOK_RECEIVED,
)
from custom_components.local_akuvox.webhook import (
    _refresh_in_flight,
    _refresh_user_cache,
    async_handle_webhook,
    async_register_webhook,
    build_action_urls,
)
from tests.conftest import MOCK_WEBHOOK_ID


def _make_request(query: dict[str, str]) -> web.Request:
    """Build a mocked aiohttp GET request with query parameters."""
    path = f"/api/webhook/{MOCK_WEBHOOK_ID}"
    if query:
        path = f"{path}?{urlencode(query)}"
    return make_mocked_request("GET", path)


# ── Registry lookup tests ────────────────────────────────────


async def test_webhook_id_not_in_registry(
    hass: HomeAssistant,
) -> None:
    """Test handler returns 200 empty when webhook_id not in registry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["webhook_registry"] = {}
    request = _make_request({"event": "relay_a_triggered"})

    response = await async_handle_webhook(hass, MOCK_WEBHOOK_ID, request)

    assert response is not None
    assert response.status == 200
    assert response.body == b""


async def test_coordinator_missing_returns_200(
    hass: HomeAssistant,
) -> None:
    """Test handler returns 200 when coordinator not in hass.data."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["webhook_registry"] = {
        MOCK_WEBHOOK_ID: "test_entry_id",
    }
    # No coordinator at hass.data[DOMAIN]["test_entry_id"]
    request = _make_request({"event": "relay_a_triggered"})

    response = await async_handle_webhook(hass, MOCK_WEBHOOK_ID, request)

    assert response is not None
    assert response.status == 200


# ── Missing event parameter ──────────────────────────────────


async def test_missing_event_returns_400(
    hass: HomeAssistant,
) -> None:
    """Test handler returns 400 when event param missing."""
    coordinator = MagicMock()
    coordinator.async_refresh = AsyncMock()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["webhook_registry"] = {
        MOCK_WEBHOOK_ID: "test_entry_id",
    }
    hass.data[DOMAIN]["test_entry_id"] = coordinator
    request = _make_request({"status": "1"})

    response = await async_handle_webhook(hass, MOCK_WEBHOOK_ID, request)

    assert response is not None
    assert response.status == 400


# ── Known relay event ────────────────────────────────────────


async def test_relay_event_fires_ha_event(
    hass: HomeAssistant,
) -> None:
    """Test relay event fires correct HA event and triggers refresh."""
    coordinator = MagicMock()
    coordinator.async_refresh = AsyncMock()
    coordinator.get_user_by_pin = MagicMock(return_value=None)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["webhook_registry"] = {
        MOCK_WEBHOOK_ID: "test_entry_id",
    }
    hass.data[DOMAIN]["test_entry_id"] = coordinator

    # Mock device registry
    with patch(
        "custom_components.local_akuvox.webhook.dr.async_entries_for_config_entry",
        return_value=[MagicMock(id="device_123")],
    ):
        events: list[Any] = []
        hass.bus.async_listen(
            EVENT_WEBHOOK_RECEIVED,
            lambda event: events.append(event),
        )

        request = _make_request(
            {
                "event": "relay_a_triggered",
                "status": "1",
            }
        )
        response = await async_handle_webhook(
            hass,
            MOCK_WEBHOOK_ID,
            request,
        )
        await hass.async_block_till_done()

    assert response is not None
    assert response.status == 200
    assert len(events) == 1
    data = events[0].data
    assert data["event_type"] == "relay_a_triggered"
    assert data["config_entry_id"] == "test_entry_id"
    assert data["device_id"] == "device_123"
    assert data["payload"]["status"] == "1"


# ── Valid code event with cache hit ──────────────────────────


async def test_valid_code_cache_hit(
    hass: HomeAssistant,
    mock_user_list_with_pins: list[Any],
) -> None:
    """Test valid_code_entered resolves user from cache."""
    coordinator = MagicMock()
    coordinator.async_refresh = AsyncMock()
    user = mock_user_list_with_pins[0]
    coordinator.get_user_by_pin = MagicMock(return_value=user)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["webhook_registry"] = {
        MOCK_WEBHOOK_ID: "test_entry_id",
    }
    hass.data[DOMAIN]["test_entry_id"] = coordinator

    with patch(
        "custom_components.local_akuvox.webhook.dr.async_entries_for_config_entry",
        return_value=[MagicMock(id="device_123")],
    ):
        events: list[Any] = []
        hass.bus.async_listen(
            EVENT_WEBHOOK_RECEIVED,
            lambda event: events.append(event),
        )

        request = _make_request(
            {
                "event": "valid_code_entered",
                "code": "1234",
            }
        )
        response = await async_handle_webhook(
            hass,
            MOCK_WEBHOOK_ID,
            request,
        )
        await hass.async_block_till_done()

    assert response is not None
    assert response.status == 200
    assert len(events) == 1
    payload = events[0].data["payload"]
    assert payload["device_user_id"] == "42"
    assert payload["user_id"] == "john.doe"
    assert payload["username"] == "John Doe"
    # Raw PIN must NOT be in payload
    assert "1234" not in str(events[0].data)


# ── Valid code event with cache miss and fallback ────────────


async def test_valid_code_cache_miss_schedules_refresh(
    hass: HomeAssistant,
    mock_user_list_with_pins: list[Any],
) -> None:
    """Test cache miss returns None and schedules background refresh."""
    coordinator = MagicMock()
    coordinator.async_refresh = AsyncMock()
    coordinator.get_user_by_pin = MagicMock(return_value=None)
    coordinator.device = MagicMock()
    coordinator.device.list_users = AsyncMock(
        return_value=mock_user_list_with_pins,
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["webhook_registry"] = {
        MOCK_WEBHOOK_ID: "test_entry_id",
    }
    hass.data[DOMAIN]["test_entry_id"] = coordinator

    with patch(
        "custom_components.local_akuvox.webhook.dr.async_entries_for_config_entry",
        return_value=[MagicMock(id="device_123")],
    ):
        events: list[Any] = []
        hass.bus.async_listen(
            EVENT_WEBHOOK_RECEIVED,
            lambda event: events.append(event),
        )

        request = _make_request(
            {
                "event": "valid_code_entered",
                "code": "1234",
            }
        )
        response = await async_handle_webhook(
            hass,
            MOCK_WEBHOOK_ID,
            request,
        )
        await hass.async_block_till_done()

    assert response is not None
    assert response.status == 200
    assert len(events) == 1
    # Cache miss: user fields are None (refresh is background)
    payload = events[0].data["payload"]
    assert payload["device_user_id"] is None
    assert payload["username"] is None
    # Background task updated the cache
    coordinator.update_user_cache.assert_called_once()
    # Guard set was cleared after refresh
    assert "test_entry_id" not in _refresh_in_flight


# ── Valid code event with no match ───────────────────────────


async def test_valid_code_no_match(
    hass: HomeAssistant,
) -> None:
    """Test valid_code_entered with no matching user."""
    coordinator = MagicMock()
    coordinator.async_refresh = AsyncMock()
    coordinator.get_user_by_pin = MagicMock(return_value=None)
    coordinator.device = MagicMock()
    coordinator.device.list_users = AsyncMock(return_value=[])

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["webhook_registry"] = {
        MOCK_WEBHOOK_ID: "test_entry_id",
    }
    hass.data[DOMAIN]["test_entry_id"] = coordinator

    with patch(
        "custom_components.local_akuvox.webhook.dr.async_entries_for_config_entry",
        return_value=[MagicMock(id="device_123")],
    ):
        events: list[Any] = []
        hass.bus.async_listen(
            EVENT_WEBHOOK_RECEIVED,
            lambda event: events.append(event),
        )

        request = _make_request(
            {
                "event": "valid_code_entered",
                "code": "9999",
            }
        )
        response = await async_handle_webhook(
            hass,
            MOCK_WEBHOOK_ID,
            request,
        )
        await hass.async_block_till_done()

    assert response is not None
    assert len(events) == 1
    payload = events[0].data["payload"]
    assert payload["device_user_id"] is None
    assert payload["user_id"] is None
    assert payload["username"] is None


# ── Invalid code event ───────────────────────────────────────


async def test_invalid_code_event(
    hass: HomeAssistant,
) -> None:
    """Test invalid_code_entered has None identity, no refresh."""
    coordinator = MagicMock()
    coordinator.async_refresh = AsyncMock()
    coordinator.get_user_by_pin = MagicMock(return_value=None)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["webhook_registry"] = {
        MOCK_WEBHOOK_ID: "test_entry_id",
    }
    hass.data[DOMAIN]["test_entry_id"] = coordinator

    with patch(
        "custom_components.local_akuvox.webhook.dr.async_entries_for_config_entry",
        return_value=[MagicMock(id="device_123")],
    ):
        events: list[Any] = []
        hass.bus.async_listen(
            EVENT_WEBHOOK_RECEIVED,
            lambda event: events.append(event),
        )

        request = _make_request({"event": "invalid_code_entered"})
        response = await async_handle_webhook(
            hass,
            MOCK_WEBHOOK_ID,
            request,
        )
        await hass.async_block_till_done()

    assert response is not None
    assert response.status == 200
    assert len(events) == 1
    payload = events[0].data["payload"]
    assert payload["device_user_id"] is None
    # No refresh for invalid code
    coordinator.async_refresh.assert_not_awaited()


# ── Unknown event ────────────────────────────────────────────


async def test_unknown_event_sanitized(
    hass: HomeAssistant,
) -> None:
    """Test unknown event fires with sanitized raw query params."""
    coordinator = MagicMock()
    coordinator.async_refresh = AsyncMock()
    coordinator.get_user_by_pin = MagicMock(return_value=None)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["webhook_registry"] = {
        MOCK_WEBHOOK_ID: "test_entry_id",
    }
    hass.data[DOMAIN]["test_entry_id"] = coordinator

    with patch(
        "custom_components.local_akuvox.webhook.dr.async_entries_for_config_entry",
        return_value=[MagicMock(id="device_123")],
    ):
        events: list[Any] = []
        hass.bus.async_listen(
            EVENT_WEBHOOK_RECEIVED,
            lambda event: events.append(event),
        )

        request = _make_request(
            {
                "event": "SomeNewEvent",
                "extra": "data",
            }
        )
        response = await async_handle_webhook(
            hass,
            MOCK_WEBHOOK_ID,
            request,
        )
        await hass.async_block_till_done()

    assert response is not None
    assert response.status == 200
    assert len(events) == 1
    data = events[0].data
    assert data["event_type"].startswith("unknown_")
    # No refresh for unknown events
    coordinator.async_refresh.assert_not_awaited()


# ── Input event — no refresh ─────────────────────────────────


async def test_input_event_no_refresh(
    hass: HomeAssistant,
) -> None:
    """Test input events do NOT trigger coordinator refresh."""
    coordinator = MagicMock()
    coordinator.async_refresh = AsyncMock()
    coordinator.get_user_by_pin = MagicMock(return_value=None)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["webhook_registry"] = {
        MOCK_WEBHOOK_ID: "test_entry_id",
    }
    hass.data[DOMAIN]["test_entry_id"] = coordinator

    with patch(
        "custom_components.local_akuvox.webhook.dr.async_entries_for_config_entry",
        return_value=[MagicMock(id="device_123")],
    ):
        request = _make_request(
            {
                "event": "input_a_triggered",
                "status": "0",
            }
        )
        response = await async_handle_webhook(
            hass,
            MOCK_WEBHOOK_ID,
            request,
        )
        await hass.async_block_till_done()

    assert response is not None
    assert response.status == 200
    coordinator.async_refresh.assert_not_awaited()


# ── Concurrent deliveries (FR-014) ──────────────────────────


async def test_concurrent_webhooks_no_event_loss(
    hass: HomeAssistant,
) -> None:
    """Test multiple simultaneous webhooks are processed independently."""
    coordinator = MagicMock()
    coordinator.async_refresh = AsyncMock()
    coordinator.get_user_by_pin = MagicMock(return_value=None)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["webhook_registry"] = {
        MOCK_WEBHOOK_ID: "test_entry_id",
    }
    hass.data[DOMAIN]["test_entry_id"] = coordinator

    with patch(
        "custom_components.local_akuvox.webhook.dr.async_entries_for_config_entry",
        return_value=[MagicMock(id="device_123")],
    ):
        events: list[Any] = []
        hass.bus.async_listen(
            EVENT_WEBHOOK_RECEIVED,
            lambda event: events.append(event),
        )

        requests = [
            _make_request({"event": "relay_a_triggered", "status": "1"}),
            _make_request({"event": "relay_b_triggered", "status": "0"}),
            _make_request({"event": "input_a_triggered", "status": "1"}),
        ]

        responses = await asyncio.gather(
            *[async_handle_webhook(hass, MOCK_WEBHOOK_ID, req) for req in requests]
        )
        await hass.async_block_till_done()

    assert all(r is not None and r.status == 200 for r in responses)
    assert len(events) == 3
    event_types = {e.data["event_type"] for e in events}
    assert event_types == {
        "relay_a_triggered",
        "relay_b_triggered",
        "input_a_triggered",
    }


# ── PIN never in event payload ───────────────────────────────


async def test_raw_pin_never_in_payload(
    hass: HomeAssistant,
    mock_user_list_with_pins: list[Any],
) -> None:
    """Test raw PIN code is never present in event data."""
    coordinator = MagicMock()
    coordinator.async_refresh = AsyncMock()
    user = mock_user_list_with_pins[0]
    coordinator.get_user_by_pin = MagicMock(return_value=user)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["webhook_registry"] = {
        MOCK_WEBHOOK_ID: "test_entry_id",
    }
    hass.data[DOMAIN]["test_entry_id"] = coordinator

    with patch(
        "custom_components.local_akuvox.webhook.dr.async_entries_for_config_entry",
        return_value=[MagicMock(id="device_123")],
    ):
        events: list[Any] = []
        hass.bus.async_listen(
            EVENT_WEBHOOK_RECEIVED,
            lambda event: events.append(event),
        )

        request = _make_request(
            {
                "event": "valid_code_entered",
                "code": "1234",
            }
        )
        await async_handle_webhook(hass, MOCK_WEBHOOK_ID, request)
        await hass.async_block_till_done()

    assert len(events) == 1
    event_str = str(events[0].data)
    assert "1234" not in event_str


async def test_relay_event_without_device_registry_entry(
    hass: HomeAssistant,
) -> None:
    """Test webhook events use None device_id when registry has no device."""
    coordinator = MagicMock()
    coordinator.async_refresh = AsyncMock()
    coordinator.get_user_by_pin = MagicMock(return_value=None)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["webhook_registry"] = {
        MOCK_WEBHOOK_ID: "test_entry_id",
    }
    hass.data[DOMAIN]["test_entry_id"] = coordinator

    with patch(
        "custom_components.local_akuvox.webhook.dr.async_entries_for_config_entry",
        return_value=[],
    ):
        events: list[Any] = []
        hass.bus.async_listen(
            EVENT_WEBHOOK_RECEIVED,
            lambda event: events.append(event),
        )
        response = await async_handle_webhook(
            hass,
            MOCK_WEBHOOK_ID,
            _make_request({"event": "relay_a_triggered"}),
        )
        await hass.async_block_till_done()

    assert response is not None
    assert response.status == 200
    assert len(events) == 1
    assert events[0].data["device_id"] is None


async def test_refresh_user_cache_timeout_clears_guard() -> None:
    """Test user cache refresh timeout clears in-flight state."""
    coordinator = MagicMock()
    coordinator.device.list_users = AsyncMock(side_effect=TimeoutError)
    coordinator.update_user_cache = MagicMock()
    _refresh_in_flight.add("entry_timeout")

    await _refresh_user_cache(coordinator, "entry_timeout")

    assert "entry_timeout" not in _refresh_in_flight
    coordinator.update_user_cache.assert_not_called()


async def test_refresh_user_cache_error_clears_guard() -> None:
    """Test user cache refresh errors clear in-flight state."""
    coordinator = MagicMock()
    coordinator.device.list_users = AsyncMock(side_effect=RuntimeError("boom"))
    coordinator.update_user_cache = MagicMock()
    _refresh_in_flight.add("entry_error")

    await _refresh_user_cache(coordinator, "entry_error")

    assert "entry_error" not in _refresh_in_flight
    coordinator.update_user_cache.assert_not_called()


async def test_unknown_event_truncates_long_event_name(
    hass: HomeAssistant,
) -> None:
    """Test very long unknown events are accepted and normalized."""
    coordinator = MagicMock()
    coordinator.async_refresh = AsyncMock()
    coordinator.get_user_by_pin = MagicMock(return_value=None)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["webhook_registry"] = {
        MOCK_WEBHOOK_ID: "test_entry_id",
    }
    hass.data[DOMAIN]["test_entry_id"] = coordinator

    with patch(
        "custom_components.local_akuvox.webhook.dr.async_entries_for_config_entry",
        return_value=[],
    ):
        events: list[Any] = []
        hass.bus.async_listen(
            EVENT_WEBHOOK_RECEIVED,
            lambda event: events.append(event),
        )
        response = await async_handle_webhook(
            hass,
            MOCK_WEBHOOK_ID,
            _make_request({"event": "X" * 100}),
        )
        await hass.async_block_till_done()

    assert response is not None
    assert response.status == 200
    assert len(events) == 1
    assert events[0].data["event_type"] == f"unknown_{'x' * 32}"


def test_register_webhook_without_id_returns(
    hass: HomeAssistant,
) -> None:
    """Test webhook registration is skipped when no id exists."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, unique_id="entry")
    hass.data.setdefault(DOMAIN, {})

    with patch("custom_components.local_akuvox.webhook.async_register") as register:
        async_register_webhook(hass, entry)

    register.assert_not_called()


def test_register_webhook_reregisters_duplicate(
    hass: HomeAssistant,
) -> None:
    """Test duplicate webhook registration unregisters then retries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_WEBHOOK_ID: MOCK_WEBHOOK_ID},
        unique_id="entry",
    )
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})

    with (
        patch(
            "custom_components.local_akuvox.webhook.async_register",
            side_effect=[ValueError, None],
        ) as register,
        patch("custom_components.local_akuvox.webhook.async_unregister") as unregister,
    ):
        async_register_webhook(hass, entry, device_name="Front Door")

    assert register.call_count == 2
    unregister.assert_called_once_with(hass, MOCK_WEBHOOK_ID)
    assert hass.data[DOMAIN]["webhook_registry"][MOCK_WEBHOOK_ID] == entry.entry_id


def test_build_action_urls_reraises_generation_error(
    hass: HomeAssistant,
) -> None:
    """Test URL generation failures are re-raised."""
    with patch(
        "custom_components.local_akuvox.webhook.async_generate_url",
        side_effect=RuntimeError("no url"),
    ):
        try:
            build_action_urls(hass, MOCK_WEBHOOK_ID)
        except RuntimeError as err:
            assert str(err) == "no url"
        else:
            msg = "Expected webhook URL generation to fail"
            raise AssertionError(msg)
