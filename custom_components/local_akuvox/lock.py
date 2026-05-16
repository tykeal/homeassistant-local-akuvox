# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Lock platform for the Akuvox integration."""

from __future__ import annotations

import datetime as dt
import logging
import re
import time
from collections.abc import Callable, Coroutine
from typing import Any, ClassVar, cast

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, ServiceResponse, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later
from pylocal_akuvox import (
    AccessSchedule,
    AkuvoxError,
    AkuvoxValidationError,
    User,
)

from .const import (
    DAY_NAME_TO_DIGIT,
    DEFAULT_HOLD_DELAY_SECONDS,
    DEFAULT_RELAY_MODE,
    DEFAULT_RELAY_TYPE,
    DOMAIN,
    EVENT_CONTACT_CHANGED,
    EVENT_GROUP_CHANGED,
    EVENT_SCHEDULE_CHANGED,
    EVENT_USER_CHANGED,
    RELAY_KEY_RE,
)
from .coordinator import AkuvoxDataUpdateCoordinator
from .entity import AkuvoxEntity

_LOGGER = logging.getLogger(__name__)

# Extra seconds added to the unlock delay before polling the device,
# giving the relay time to re-lock after the window expires.
_RELAY_REFRESH_BUFFER_SECONDS = 1

# Required fields per schedule_type (0=date-range, 1=weekly, 2=daily)
_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "0": ("week", "date_start", "date_end"),
    "1": ("week",),
    "2": (),
}

# Akuvox devices expose relays as "RelayA", "RelayB", etc.
# with a single uppercase letter A-Z suffix.


def _relay_key_to_number(relay_key: str) -> int | None:
    """Convert a relay key like 'RelayA' to a relay number (1-based).

    Args:
        relay_key: The relay key from the device (e.g., "RelayA").

    Returns:
        The 1-based relay number, or None if format is unrecognized.

    """
    match = RELAY_KEY_RE.fullmatch(relay_key)
    if match:
        return ord(match.group(1)) - ord("A") + 1
    _LOGGER.warning(
        "Unexpected relay key format '%s'; skipping",
        relay_key,
    )
    return None


def _relay_key_to_label(relay_key: str) -> str:
    """Convert a relay key like 'RelayA' to a display label.

    Args:
        relay_key: The relay key from the device.

    Returns:
        A human-readable label (e.g., "Relay A").

    """
    match = RELAY_KEY_RE.fullmatch(relay_key)
    if match:
        return f"Relay {match.group(1)}"
    _LOGGER.warning(
        "Unexpected relay key format '%s'; using raw key as label",
        relay_key,
    )
    return relay_key


def _parse_relay_state(
    relay_key: str,
    state: object,
    relay_type: int = DEFAULT_RELAY_TYPE,
) -> bool | None:
    """Parse a relay state value into a locked boolean.

    Args:
        relay_key: The relay key for logging context.
        state: The raw state value from the device.
        relay_type: 0 for NO (normal-open), 1 for NC (normal-closed).

    Returns:
        True if locked, False if unlocked, None if unknown.

    """
    if isinstance(state, int):
        return _parse_int_state(relay_key, state, relay_type)

    if isinstance(state, str):
        return _parse_str_state(relay_key, state)

    if isinstance(state, dict):
        inner = state.get("state")
        if isinstance(inner, int):
            return _parse_int_state(relay_key, inner, relay_type)
        if isinstance(inner, str):
            return _parse_str_state(relay_key, inner)
        _LOGGER.debug(
            "Unrecognized dict relay state for %s: %r",
            relay_key,
            state,
        )
        return None

    _LOGGER.debug(
        "Unexpected relay state type for %s: %r (type=%s)",
        relay_key,
        state,
        type(state).__name__,
    )
    return None


def _parse_int_state(
    relay_key: str,
    state: int,
    relay_type: int = DEFAULT_RELAY_TYPE,
) -> bool | None:
    """Parse an integer relay state value.

    Args:
        relay_key: The relay key for logging context.
        state: The integer state value.
        relay_type: 0 for NO (0=locked, 1=unlocked),
                    1 for NC (0=unlocked, 1=locked).

    Returns:
        True if locked, False if unlocked, None if unknown.

    """
    if state == 0:
        return relay_type != 1
    if state == 1:
        return relay_type == 1
    _LOGGER.debug(
        "Unexpected integer relay state %d for %s",
        state,
        relay_key,
    )
    return None


def _parse_str_state(relay_key: str, state: str) -> bool | None:
    """Parse a string relay state value.

    Args:
        relay_key: The relay key for logging context.
        state: The string state value.

    Returns:
        True if locked, False if unlocked, None if unknown.

    """
    if state in ("closed", "inactive"):
        return True
    if state in ("open", "active"):
        return False
    _LOGGER.debug(
        "Unrecognized relay state '%s' for %s",
        state,
        relay_key,
    )
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Akuvox lock entities from a config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry.
        async_add_entities: Callback to add entities.

    """
    coordinator: AkuvoxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    if coordinator.data is None:
        _LOGGER.warning("No data available for %s", entry.title)
        return

    relay_status = coordinator.data.relay_status
    entities: list[AkuvoxLockEntity] = []

    for relay_key in relay_status:
        if _relay_key_to_number(relay_key) is None:
            continue
        entities.append(
            AkuvoxLockEntity(
                coordinator=coordinator,
                relay_key=relay_key,
            ),
        )

    async_add_entities(entities)


class AkuvoxLockEntity(AkuvoxEntity, LockEntity):
    """Represents an Akuvox relay as a lock entity."""

    def __init__(
        self,
        coordinator: AkuvoxDataUpdateCoordinator,
        relay_key: str,
    ) -> None:
        """Initialize the lock entity.

        Args:
            coordinator: The data update coordinator.
            relay_key: The relay key from the device (e.g., "RelayA").

        """
        super().__init__(coordinator)
        self._relay_key = relay_key
        relay_number = _relay_key_to_number(relay_key)
        if relay_number is None:
            msg = f"Invalid relay key: {relay_key}"
            raise ValueError(msg)
        self._relay_number = relay_number
        mac_clean = coordinator.data.device_info.mac_address.lower().replace(
            ":",
            "",
        )
        self._attr_unique_id = f"{mac_clean}_relay_{self._relay_number}"
        self._attr_has_entity_name = True
        # Use config-sourced name if available, fallback to label
        letter = chr(ord("A") + self._relay_number - 1)
        relay_cfg = coordinator.data.relay_configs.get(letter)
        config_name = (relay_cfg.name if relay_cfg else "").strip()
        self._attr_name = config_name if config_name else _relay_key_to_label(relay_key)
        self._optimistic_locked: bool | None = None
        self._delayed_refresh_cancel: CALLBACK_TYPE | None = None

    @property
    def is_locked(self) -> bool | None:
        """Return true if the relay is closed/inactive/0 (locked).

        Returns:
            True if locked (closed/inactive/0), False if unlocked
            (open/active/1), None if unknown.

        """
        if self._optimistic_locked is not None:
            return self._optimistic_locked

        relay_status = self.coordinator.data.relay_status
        state = relay_status.get(self._relay_key)

        if state is None:
            return None

        letter = chr(ord("A") + self._relay_number - 1)
        relay_cfg = self.coordinator.data.relay_configs.get(letter)
        relay_type = relay_cfg.relay_type if relay_cfg else DEFAULT_RELAY_TYPE

        return _parse_relay_state(self._relay_key, state, relay_type)

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the relay using mode-aware logic.

        Clears optimistic state before proceeding with mode-specific
        logic.

        For **bistable** relays (relay_mode=1): cancels any pending
        unlock timer (FR-005), refreshes coordinator state, then sends
        a ``trigger_relay`` command if the relay is confirmed unlocked.
        Sets optimistic locked state and schedules a delayed refresh.

        For **auto-close** relays (relay_mode=0): performs a coordinator
        refresh and writes the updated state (no command sent).  Any
        pending unlock timer is preserved so it can re-sync state after
        the relay hold-delay window.

        Args:
            **kwargs: Service call keyword arguments (unused).

        Raises:
            HomeAssistantError: If device communication fails.

        """
        letter = chr(ord("A") + self._relay_number - 1)
        relay_cfg = self.coordinator.data.relay_configs.get(letter)
        relay_mode = relay_cfg.relay_mode if relay_cfg else DEFAULT_RELAY_MODE

        # Clear optimistic state so coordinator data drives is_locked
        self._optimistic_locked = None

        if relay_mode == 0:
            # Auto-close: refresh only, no command.
            # Any pending unlock refresh timer is preserved so it can
            # re-sync state after the relay hold-delay window.
            await self.coordinator.async_refresh()
            self.async_write_ha_state()
            return

        # Bistable: cancel any pending unlock timer (FR-005)
        if self._delayed_refresh_cancel is not None:
            self._delayed_refresh_cancel()
            self._delayed_refresh_cancel = None

        # Refresh coordinator to get current state
        await self.coordinator.async_refresh()

        # R-001: None (unknown after refresh) treated as unlocked — proceed
        if self.is_locked:
            self.async_write_ha_state()
            return

        hold_delay = relay_cfg.hold_delay if relay_cfg else DEFAULT_HOLD_DELAY_SECONDS
        relay_type = relay_cfg.relay_type if relay_cfg else DEFAULT_RELAY_TYPE
        try:
            await self.coordinator.device.trigger_relay(
                num=self._relay_number,
                delay=hold_delay,
                level=relay_type,
                mode=relay_mode,
            )
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"Failed to lock relay {self._relay_number}: {err}"
            ) from err
        self._optimistic_locked = True
        self.async_write_ha_state()
        self._schedule_delayed_refresh(
            0,
            finish_callback=self._async_finish_optimistic_lock,
        )

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the door using mode-aware relay logic.

        Clears optimistic state before proceeding with mode-specific
        logic.

        For **bistable** relays (relay_mode=1): cancels any pending
        lock timer, refreshes coordinator state, then sends a
        ``trigger_relay`` command with ``mode=0`` (toggle) and
        ``delay=0`` if the relay is confirmed locked.  The API
        ``mode`` parameter controls command direction: ``0`` means
        open/toggle, ``1`` means close-only.

        For **auto-close** relays (relay_mode=0): sends
        ``trigger_relay`` with ``mode=0`` and the configured hold
        delay, then sets optimistic unlocked state and schedules a
        delayed refresh.

        Args:
            **kwargs: Service call keyword arguments (unused).

        Raises:
            HomeAssistantError: If the device communication fails.

        """
        letter = chr(ord("A") + self._relay_number - 1)
        relay_cfg = self.coordinator.data.relay_configs.get(letter)
        relay_mode = relay_cfg.relay_mode if relay_cfg else DEFAULT_RELAY_MODE

        # Clear optimistic state so coordinator data drives is_locked
        self._optimistic_locked = None

        if relay_mode == 1:
            # Bistable: cancel any pending lock timer
            if self._delayed_refresh_cancel is not None:
                self._delayed_refresh_cancel()
                self._delayed_refresh_cancel = None

            # Refresh coordinator to get current state
            await self.coordinator.async_refresh()

            # mode=0 is a toggle — skip if already unlocked
            if self.is_locked is False:
                self.async_write_ha_state()
                return

            relay_type = relay_cfg.relay_type if relay_cfg else DEFAULT_RELAY_TYPE
            try:
                await self.coordinator.device.trigger_relay(
                    num=self._relay_number,
                    delay=0,
                    level=relay_type,
                    mode=0,
                )
            except AkuvoxError as err:
                raise HomeAssistantError(
                    f"Failed to unlock relay {self._relay_number}: {err}"
                ) from err
            self._optimistic_locked = False
            self.async_write_ha_state()
            self._schedule_delayed_refresh(0)
            return

        # Auto-close: trigger with configured hold delay
        hold_delay = relay_cfg.hold_delay if relay_cfg else DEFAULT_HOLD_DELAY_SECONDS
        relay_type = relay_cfg.relay_type if relay_cfg else DEFAULT_RELAY_TYPE
        try:
            await self.coordinator.device.trigger_relay(
                num=self._relay_number,
                delay=hold_delay,
                level=relay_type,
                mode=0,
            )
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"Failed to unlock relay {self._relay_number}: {err}"
            ) from err
        self._optimistic_locked = False
        self.async_write_ha_state()
        self._schedule_delayed_refresh(hold_delay)

    def _schedule_delayed_refresh(
        self,
        relay_delay: int,
        finish_callback: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        """Schedule a coordinator refresh after the relay delay expires.

        If called while a previous timer is pending (e.g. rapid unlock
        calls), the earlier timer is cancelled and only the latest
        window is tracked.

        Args:
            relay_delay: Seconds to wait before refreshing (typically
                the relay hold delay from device config, or ``0`` for
                immediate refresh after the buffer).
            finish_callback: Async callback invoked when the timer
                fires. Defaults to ``_async_finish_optimistic_unlock``
                for backward compatibility.

        """
        if self._delayed_refresh_cancel is not None:
            self._delayed_refresh_cancel()

        cb = (
            self._async_finish_optimistic_unlock
            if finish_callback is None
            else finish_callback
        )

        @callback
        def _refresh(_now: Any) -> None:
            """Kick off async refresh after relay window expires."""
            self._delayed_refresh_cancel = None
            self.hass.async_create_task(cb())

        self._delayed_refresh_cancel = async_call_later(
            self.hass,
            relay_delay + _RELAY_REFRESH_BUFFER_SECONDS,
            _refresh,
        )

    async def _async_finish_optimistic_unlock(self) -> None:
        """Refresh coordinator then clear optimistic state.

        The optimistic override is kept until the refresh completes so
        that any coordinator update triggered during the refresh does
        not write stale device state to Home Assistant. A finally
        block ensures the override is always cleared even if the
        refresh fails.
        """
        try:
            await self.coordinator.async_refresh()
        except Exception:  # noqa: BLE001
            _LOGGER.exception(
                "Error refreshing coordinator after optimistic unlock for relay %s",
                self._relay_key,
            )
        finally:
            self._optimistic_locked = None
            self.async_write_ha_state()

    async def _async_finish_optimistic_lock(self) -> None:
        """Refresh coordinator then clear optimistic lock state.

        Mirrors ``_async_finish_optimistic_unlock`` but logs a
        lock-specific message. The optimistic override is kept until
        the refresh completes; a finally block ensures cleanup.
        """
        try:
            await self.coordinator.async_refresh()
        except Exception:  # noqa: BLE001
            _LOGGER.exception(
                "Error refreshing coordinator after optimistic lock for relay %s",
                self._relay_key,
            )
        finally:
            self._optimistic_locked = None
            self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """Cancel pending timers on entity removal."""
        if self._delayed_refresh_cancel is not None:
            self._delayed_refresh_cancel()
            self._delayed_refresh_cancel = None
        await super().async_will_remove_from_hass()

    async def list_schedules(self, **kwargs: Any) -> ServiceResponse:
        """Return all access schedules from the device.

        Args:
            **kwargs: Service call data (optional ``page`` key).

        Returns:
            Dict with ``schedules`` list of schedule dicts.

        Raises:
            HomeAssistantError: On device communication errors.
            ServiceValidationError: On validation errors.

        """
        page = kwargs.get("page")
        try:
            schedules = await self.coordinator.device.list_schedules(
                page=page,
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"list_schedules: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"list_schedules failed: {err}",
            ) from err
        return cast(
            ServiceResponse,
            {"schedules": [dict(vars(s)) for s in schedules]},
        )

    async def list_users(self, **kwargs: Any) -> ServiceResponse:
        """Return all users from the device with plain-text credentials.

        Sensitive fields (``private_pin``, ``card_code``) are returned
        in plain text for automation consumption but masked in log
        output.

        Args:
            **kwargs: Service call data (optional ``page`` key).

        Returns:
            Dict with ``users`` list of user dicts.

        Raises:
            HomeAssistantError: On device communication errors.
            ServiceValidationError: On validation errors.

        """
        page = kwargs.get("page")
        try:
            users = await self.coordinator.device.list_users(
                page=page,
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"list_users: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"list_users failed: {err}",
            ) from err

        user_dicts = [dict(vars(u)) for u in users]
        if _LOGGER.isEnabledFor(logging.DEBUG):
            masked = []
            for ud in user_dicts:
                masked_copy = dict(ud)
                if masked_copy.get("private_pin"):
                    masked_copy["private_pin"] = "****"
                if masked_copy.get("card_code"):
                    masked_copy["card_code"] = "****"
                masked.append(masked_copy)
            _LOGGER.debug("list_users result: %s", masked)
        return cast(ServiceResponse, {"users": user_dicts})

    @staticmethod
    def _convert_week(days: list[str]) -> str:
        """Convert day-name list to device digit string.

        Args:
            days: List of day abbreviations (e.g. ["mon", "fri"]).

        Returns:
            Sorted digit string for the device (e.g. "15").

        """
        digits = sorted(DAY_NAME_TO_DIGIT[d] for d in days)
        return "".join(digits)

    @staticmethod
    def _convert_date(value: dt.date) -> str:
        """Convert a date object to YYYYMMDD string.

        Args:
            value: The date to convert.

        Returns:
            Date formatted as YYYYMMDD for the device.

        """
        return value.strftime("%Y%m%d")

    @staticmethod
    def _convert_time(value: dt.time) -> str:
        """Convert a time object to HH:MM string.

        Args:
            value: The time to convert.

        Returns:
            Time formatted as HH:MM for the device.

        """
        return value.strftime("%H:%M")

    def _check_required_schedule_fields(
        self,
        schedule_type: str,
        **kwargs: Any,
    ) -> None:
        """Validate required fields are present for the schedule type.

        Type 0 (date range) requires week, date_start, date_end.
        Type 1 (weekly) requires week.
        Type 2 (daily) has no extra required fields.
        time_start and time_end are enforced by the schema.

        Args:
            schedule_type: The schedule type ("0", "1", "2").
            **kwargs: Service call data.

        Raises:
            ServiceValidationError: If a required field is missing.

        """
        for field in _REQUIRED_FIELDS.get(schedule_type, ()):
            if kwargs.get(field) is None:
                raise ServiceValidationError(
                    f"Field '{field}' is required for schedule type {schedule_type}",
                )

    async def add_schedule(self, **kwargs: Any) -> None:
        """Create a new access schedule on the device.

        Converts user-friendly inputs (day names, date/time
        objects) to the device's expected string formats before
        forwarding the call.

        Args:
            **kwargs: Service call data with schedule fields.

        Raises:
            ServiceValidationError: On input validation errors.
            HomeAssistantError: On device communication errors.

        """
        stype = kwargs["schedule_type"]
        self._check_required_schedule_fields(
            stype, **{k: v for k, v in kwargs.items() if k != "schedule_type"}
        )

        week_list: list[str] | None = kwargs.get("week")
        week_str = self._convert_week(week_list) if week_list else None

        date_start: dt.date | None = kwargs.get("date_start")
        date_end: dt.date | None = kwargs.get("date_end")
        time_start: dt.time = kwargs["time_start"]
        time_end: dt.time = kwargs["time_end"]

        try:
            await self.coordinator.device.add_schedule(
                schedule_type=stype,
                name=kwargs.get("name"),
                week=week_str,
                daily=None,
                date_start=(self._convert_date(date_start) if date_start else None),
                date_end=(self._convert_date(date_end) if date_end else None),
                time_start=self._convert_time(time_start),
                time_end=self._convert_time(time_end),
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"add_schedule: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"add_schedule failed: {err}",
            ) from err
        event_data: dict[str, str] = {"action": "add"}
        config_entry = self.coordinator.config_entry
        if config_entry is not None and hasattr(config_entry, "entry_id"):
            event_data["config_entry_id"] = config_entry.entry_id
        self.hass.bus.async_fire(EVENT_SCHEDULE_CHANGED, event_data)

    async def _fetch_local_schedule(
        self,
        schedule_id: str,
        *,
        action: str = "modify",
    ) -> AccessSchedule:
        """Fetch a schedule by ID and verify it is locally managed.

        Args:
            schedule_id: The ID of the schedule to look up.
            action: Action label for error messages.

        Returns:
            The matching AccessSchedule.

        Raises:
            ServiceValidationError: If schedule is cloud-provisioned.
            HomeAssistantError: If schedule not found or fetch fails.

        """
        try:
            schedules = await self.coordinator.device.list_schedules(
                page=None,
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"{action}_schedule: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"{action}_schedule: failed to fetch schedules: {err}",
            ) from err

        target = None
        for s in schedules:
            if s.id == schedule_id:
                target = s
                break

        if target is None:
            raise HomeAssistantError(
                f"Schedule '{schedule_id}' not found",
            )

        if self._is_cloud_provisioned_schedule(target):
            raise ServiceValidationError(
                f"Cannot {action} cloud-provisioned schedule",
            )

        return target

    async def modify_schedule(self, **kwargs: Any) -> None:
        """Modify an existing access schedule on the device.

        Fetches the current schedule list to verify the schedule
        exists and is not cloud-provisioned before forwarding the
        update.

        Args:
            **kwargs: Service call data (``id`` required, other
                schedule fields optional).

        Raises:
            ServiceValidationError: If schedule is cloud-provisioned
                or input validation fails.
            HomeAssistantError: If schedule not found or device error.

        """
        schedule_id: str = kwargs["id"]
        await self._fetch_local_schedule(schedule_id)

        # Validate type-specific fields when schedule_type changes
        stype: str | None = kwargs.get("schedule_type")
        if stype is not None:
            self._check_required_schedule_fields(
                stype,
                **{k: v for k, v in kwargs.items() if k != "schedule_type"},
            )

        # Convert optional fields
        week_list: list[str] | None = kwargs.get("week")
        week_str = self._convert_week(week_list) if week_list else None

        date_start: dt.date | None = kwargs.get("date_start")
        date_end: dt.date | None = kwargs.get("date_end")
        time_start: dt.time | None = kwargs.get("time_start")
        time_end: dt.time | None = kwargs.get("time_end")

        try:
            await self.coordinator.device.modify_schedule(
                id=schedule_id,
                schedule_type=kwargs.get("schedule_type"),
                name=kwargs.get("name"),
                week=week_str,
                daily=None,
                date_start=(self._convert_date(date_start) if date_start else None),
                date_end=(self._convert_date(date_end) if date_end else None),
                time_start=(self._convert_time(time_start) if time_start else None),
                time_end=(self._convert_time(time_end) if time_end else None),
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"modify_schedule: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"modify_schedule failed: {err}",
            ) from err

        event_data: dict[str, str] = {
            "action": "modify",
            "schedule_id": schedule_id,
        }
        config_entry = self.coordinator.config_entry
        if config_entry is not None and hasattr(config_entry, "entry_id"):
            event_data["config_entry_id"] = config_entry.entry_id
        self.hass.bus.async_fire(EVENT_SCHEDULE_CHANGED, event_data)

    async def delete_schedule(self, **kwargs: Any) -> None:
        """Delete an access schedule from the device.

        Fetches the schedule list to verify the target exists and
        is not cloud-provisioned, deletes it, then checks for
        orphaned user-schedule assignments.

        Args:
            **kwargs: Service call data (``id`` required).

        Raises:
            ServiceValidationError: If schedule is cloud-provisioned.
            HomeAssistantError: If schedule not found or device error.

        """
        schedule_id: str = kwargs["id"]
        schedule = await self._fetch_local_schedule(schedule_id, action="delete")
        display_id = schedule.display_id or schedule_id

        try:
            await self.coordinator.device.delete_schedule(id=schedule_id)
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"delete_schedule: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"delete_schedule failed: {err}",
            ) from err

        # Check for orphaned user-schedule assignments
        try:
            users = await self.coordinator.device.list_users(page=None)
            for user in users:
                relay = getattr(user, "schedule_relay", "") or ""
                for pair in re.split(r"[;,]", relay):
                    pair = pair.strip()
                    if pair and pair.split("-")[0] == display_id:
                        _LOGGER.warning(
                            "Orphaned schedule-relay assignment: "
                            "user '%s' (id=%s) still references "
                            "deleted schedule %s",
                            user.name,
                            user.id,
                            display_id,
                        )
                        break
        except AkuvoxError:
            _LOGGER.debug(
                "Could not check for orphaned assignments after deleting schedule %s",
                schedule_id,
            )

        event_data: dict[str, str] = {
            "action": "delete",
            "schedule_id": schedule_id,
        }
        config_entry = self.coordinator.config_entry
        if config_entry is not None and hasattr(config_entry, "entry_id"):
            event_data["config_entry_id"] = config_entry.entry_id
        self.hass.bus.async_fire(EVENT_SCHEDULE_CHANGED, event_data)

    @staticmethod
    def _is_cloud_provisioned_user(user: User) -> bool:
        """Return True if the user is cloud-provisioned.

        Akuvox firmware varies across models and versions:
          - E18C/A08S may set ``source_type`` to ``"2"`` (cloud)
            or ``source`` to ``"Cloud"``
          - X916 may omit ``source_type`` entirely
          - SDMC-managed users may have ``"SDMC"`` as source

        This checks both fields to handle all known variants.
        """
        if user.source is not None and user.source not in ("Local", ""):
            return True
        return user.source_type is not None and user.source_type not in (
            "1",
            "Local",
            "",
        )

    _FACTORY_SCHEDULE_IDS: ClassVar[frozenset[str]] = frozenset({"1001", "1002"})

    @staticmethod
    def _is_cloud_provisioned_schedule(
        schedule: AccessSchedule,
    ) -> bool:
        """Return True if the schedule is cloud-provisioned.

        Schedule ``source_type`` uses numeric codes:
        ``"1"``=Local, ``"2"``=Cloud, ``"3"``=ACMS, ``"4"``=SDMC.
        Treated as local when absent, empty, or ``"1"``;
        otherwise non-local.

        Factory schedules 1001 ("Always") and 1002 ("Never") are
        always treated as local even when a cloud enrolment sets
        their ``source_type`` to a non-local value.
        """
        if schedule.display_id in AkuvoxLockEntity._FACTORY_SCHEDULE_IDS:
            return False
        return schedule.source_type is not None and schedule.source_type not in (
            "1",
            "",
        )

    def _validate_pin(self, pin: str | None) -> None:
        """Validate private_pin is 4-8 digits if provided.

        Args:
            pin: The PIN string to validate, or None.

        Raises:
            ServiceValidationError: If PIN is not 4-8 decimal digits.

        """
        if pin is not None and (len(pin) < 4 or len(pin) > 8 or not pin.isdigit()):
            raise ServiceValidationError(
                "PIN must be 4-8 digits",
            )

    async def _fetch_local_user(
        self,
        user_id: str,
        *,
        service: str = "modify_user",
    ) -> User:
        """Fetch a user by ID and verify it is locally managed.

        Args:
            user_id: The device-internal ID of the user.
            service: Service name for error message prefixes.

        Returns:
            The matching User.

        Raises:
            ServiceValidationError: If user is cloud-provisioned.
            HomeAssistantError: If user not found or fetch fails.

        """
        try:
            users = await self.coordinator.device.list_users(
                page=None,
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"{service}: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"{service}: failed to fetch users: {err}",
            ) from err

        target = None
        for u in users:
            if u.id == user_id:
                target = u
                break

        if target is None:
            raise HomeAssistantError(
                f"{service}: user '{user_id}' not found",
            )

        if self._is_cloud_provisioned_user(target):
            raise ServiceValidationError(
                f"{service}: user is cloud-provisioned",
            )

        return target

    async def _check_cloud_schedules(
        self,
        display_ids: list[str],
    ) -> None:
        """Verify no referenced schedules are cloud-provisioned.

        Looks up schedules by ``display_id`` (not internal ``id``).

        Args:
            display_ids: Schedule display_ids to validate.

        Raises:
            ServiceValidationError: If any referenced schedule is
                cloud-provisioned or does not exist on the device.
            HomeAssistantError: If schedule list fetch fails.

        """
        try:
            schedules = await self.coordinator.device.list_schedules(
                page=None,
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"Failed to verify schedules: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"Failed to verify schedules: {err}",
            ) from err

        display_map = {s.display_id: s for s in schedules if s.display_id is not None}
        for did in display_ids:
            sched = display_map.get(did)
            if sched is None:
                # ServiceValidationError because the caller supplied
                # an invalid schedule reference (input-validation).
                raise ServiceValidationError(
                    f"Schedule '{did}' not found on device",
                )
            if self._is_cloud_provisioned_schedule(sched):
                raise ServiceValidationError(
                    "Cannot assign cloud-provisioned schedule",
                )

    def _build_schedule_relay(
        self,
        display_ids: list[str],
    ) -> str:
        """Build a schedule_relay string from display_ids.

        Pairs each display_id with the entity's relay number
        using comma separation (device firmware requirement).

        Args:
            display_ids: Schedule display_ids to assign.

        Returns:
            Formatted schedule_relay string (e.g. ``"10-1,20-1"``).

        """
        parts: list[str] = []
        for did in display_ids:
            parts.append(f"{did}-{self._relay_number}")
        return ",".join(parts)

    @staticmethod
    def _parse_schedule_relay_pairs(
        raw: str,
        *,
        allow_empty: bool = False,
    ) -> list[str]:
        """Parse a schedule_relay string into validated pairs.

        Accepts comma or semicolon separators and strips whitespace.
        Each pair must match the ``<digits>-<digits>`` format.

        Args:
            raw: Raw schedule_relay string from user or device.
            allow_empty: If ``True``, return an empty list instead
                of raising when no valid pairs are found.

        Returns:
            List of validated ``"<schedule_id>-<relay_id>"`` pairs.

        Raises:
            ServiceValidationError: If any pair is malformed or
                the result is empty (unless *allow_empty*).

        """
        pairs: list[str] = []
        for raw_pair in re.split(r"[;,]", raw):
            pair = raw_pair.strip()
            if not pair:
                continue
            if not re.fullmatch(r"\d+-\d+", pair):
                raise ServiceValidationError(
                    f"Invalid schedule_relay entry '{pair}'. "
                    "Expected format '<schedule_id>-<relay_id>'.",
                )
            pairs.append(pair)
        if not pairs and not allow_empty:
            raise ServiceValidationError(
                "schedule_relay must contain at least one "
                "'<schedule_id>-<relay_id>' pair.",
            )
        return pairs

    async def add_user(self, **kwargs: Any) -> None:
        """Create a new user on the device.

        Validates input fields, checks that referenced schedules
        are not cloud-provisioned, builds the schedule_relay
        string from display_ids and relay numbers, then forwards
        the call.

        Args:
            **kwargs: Service call data with user fields.

        Raises:
            ServiceValidationError: On input validation errors.
            HomeAssistantError: On device communication errors.

        """
        schedules: list[str] = kwargs["schedules"]
        self._validate_pin(kwargs.get("private_pin"))
        await self._check_cloud_schedules(schedules)

        schedule_relay = self._build_schedule_relay(schedules)

        try:
            await self.coordinator.device.add_user(
                name=kwargs["name"],
                user_id=kwargs.get("user_id") or str(int(time.time())),
                schedule_relay=schedule_relay,
                lift_floor_num=kwargs["lift_floor_num"],
                web_relay=kwargs.get("web_relay"),
                private_pin=kwargs.get("private_pin"),
                card_code=kwargs.get("card_code"),
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"add_user: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"add_user failed: {err}",
            ) from err

        event_data: dict[str, str] = {"action": "add"}
        config_entry = self.coordinator.config_entry
        if config_entry is not None and hasattr(config_entry, "entry_id"):
            event_data["config_entry_id"] = config_entry.entry_id
        self.hass.bus.async_fire(EVENT_USER_CHANGED, event_data)

    async def modify_user(self, **kwargs: Any) -> None:
        """Modify an existing user on the device.

        Fetches the current user list to verify the user exists and
        is not cloud-provisioned, validates fields, checks cloud
        schedules if schedule_relay is updated, then forwards the
        update.

        Args:
            **kwargs: Service call data (``id`` required, other
                user fields optional).

        Raises:
            ServiceValidationError: If user is cloud-provisioned,
                input validation fails, or cloud schedule referenced.
            HomeAssistantError: If user not found or device error.

        """
        device_user_id: str = kwargs["id"]
        await self._fetch_local_user(device_user_id)

        self._validate_pin(kwargs.get("private_pin"))

        schedule_relay: str | None = kwargs.get("schedule_relay")
        if schedule_relay is not None:
            parsed_pairs = self._parse_schedule_relay_pairs(schedule_relay)
            sched_ids = [p.split("-", 1)[0] for p in parsed_pairs]
            await self._check_cloud_schedules(sched_ids)
            # Normalize to comma-separated (device firmware requirement).
            schedule_relay = ",".join(parsed_pairs)

        try:
            await self.coordinator.device.modify_user(
                id=device_user_id,
                name=kwargs.get("name"),
                user_id=kwargs.get("user_id"),
                schedule_relay=schedule_relay,
                lift_floor_num=kwargs.get("lift_floor_num"),
                web_relay=kwargs.get("web_relay"),
                private_pin=kwargs.get("private_pin"),
                card_code=kwargs.get("card_code"),
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"modify_user: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"modify_user failed: {err}",
            ) from err

        event_data: dict[str, str] = {
            "action": "modify",
            "device_user_id": device_user_id,
        }
        config_entry = self.coordinator.config_entry
        if config_entry is not None and hasattr(config_entry, "entry_id"):
            event_data["config_entry_id"] = config_entry.entry_id
        self.hass.bus.async_fire(EVENT_USER_CHANGED, event_data)

    async def delete_user(self, **kwargs: Any) -> None:
        """Delete an existing user from the device.

        Fetches the user list to verify the target exists and
        is not cloud-provisioned, then deletes it.

        Args:
            **kwargs: Service call data (``id`` required).

        Raises:
            ServiceValidationError: If user is cloud-provisioned.
            HomeAssistantError: If user not found or device error.

        """
        device_user_id: str = kwargs["id"]
        await self._fetch_local_user(device_user_id, service="delete_user")

        try:
            await self.coordinator.device.delete_user(id=device_user_id)
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"delete_user: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"delete_user failed: {err}",
            ) from err

        event_data_del: dict[str, str] = {
            "action": "delete",
            "device_user_id": device_user_id,
        }
        config_entry = self.coordinator.config_entry
        if config_entry is not None and hasattr(config_entry, "entry_id"):
            event_data_del["config_entry_id"] = config_entry.entry_id
        self.hass.bus.async_fire(EVENT_USER_CHANGED, event_data_del)

    async def add_user_schedule_relay(self, **kwargs: Any) -> None:
        """Add a schedule-relay pair to an existing user.

        Fetches the user, verifies not cloud-provisioned, checks the
        schedule is not cloud-provisioned, appends the pair, and
        calls ``modify_user`` on the device.

        Args:
            **kwargs: Service call data (``id``, ``schedule_id``,
                ``relay_id`` required).

        Raises:
            ServiceValidationError: If user/schedule is cloud,
                pair is duplicate.
            HomeAssistantError: If user not found or device error.

        """
        device_user_id: str = kwargs["id"]
        schedule_id: str = kwargs["schedule_id"]
        relay_id: str = kwargs["relay_id"]

        if not re.fullmatch(r"\d+", schedule_id):
            raise ServiceValidationError(
                f"Invalid schedule_id '{schedule_id}'. Must be numeric.",
            )
        if not re.fullmatch(r"\d+", relay_id):
            raise ServiceValidationError(
                f"Invalid relay_id '{relay_id}'. Must be numeric.",
            )

        user = await self._fetch_local_user(
            device_user_id, service="add_user_schedule_relay"
        )

        current_relay = getattr(user, "schedule_relay", "") or ""
        pairs = self._parse_schedule_relay_pairs(current_relay, allow_empty=True)

        new_pair = f"{schedule_id}-{relay_id}"
        if new_pair in pairs:
            raise ServiceValidationError(
                f"Pair already assigned: {new_pair}",
            )
        pairs.append(new_pair)

        # Validate all schedule IDs (existing + new) against cloud.
        all_sched_ids = [p.split("-", 1)[0] for p in pairs]
        await self._check_cloud_schedules(all_sched_ids)

        try:
            await self.coordinator.device.modify_user(
                id=device_user_id,
                schedule_relay=",".join(pairs),
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"add_user_schedule_relay: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"add_user_schedule_relay failed: {err}",
            ) from err

        event_data: dict[str, str] = {
            "action": "add_schedule_relay",
            "device_user_id": device_user_id,
            "schedule_id": schedule_id,
            "relay_id": relay_id,
        }
        config_entry = self.coordinator.config_entry
        if config_entry is not None and hasattr(config_entry, "entry_id"):
            event_data["config_entry_id"] = config_entry.entry_id
        self.hass.bus.async_fire(EVENT_USER_CHANGED, event_data)

    async def remove_user_schedule_relay(self, **kwargs: Any) -> None:
        """Remove a schedule-relay pair from an existing user.

        Fetches the user, verifies not cloud-provisioned, removes
        the pair from the schedule_relay string, and calls
        ``modify_user`` on the device.

        Args:
            **kwargs: Service call data (``id``, ``schedule_id``,
                ``relay_id`` required).

        Raises:
            ServiceValidationError: If user is cloud, pair not found,
                or removal would leave zero pairs.
            HomeAssistantError: If user not found or device error.

        """
        device_user_id: str = kwargs["id"]
        schedule_id: str = kwargs["schedule_id"]
        relay_id: str = kwargs["relay_id"]

        if not re.fullmatch(r"\d+", schedule_id):
            raise ServiceValidationError(
                f"Invalid schedule_id '{schedule_id}'. Must be numeric.",
            )
        if not re.fullmatch(r"\d+", relay_id):
            raise ServiceValidationError(
                f"Invalid relay_id '{relay_id}'. Must be numeric.",
            )

        user = await self._fetch_local_user(
            device_user_id, service="remove_user_schedule_relay"
        )

        current_relay = getattr(user, "schedule_relay", "") or ""
        pairs = self._parse_schedule_relay_pairs(current_relay, allow_empty=True)

        target_pair = f"{schedule_id}-{relay_id}"
        if target_pair not in pairs:
            raise ServiceValidationError(
                f"Pair not assigned: {target_pair}",
            )
        if len(pairs) == 1:
            raise ServiceValidationError(
                "Cannot remove last pair",
            )
        pairs.remove(target_pair)

        # Validate remaining schedule IDs against cloud.
        remaining_sched_ids = [p.split("-", 1)[0] for p in pairs]
        await self._check_cloud_schedules(remaining_sched_ids)

        try:
            await self.coordinator.device.modify_user(
                id=device_user_id,
                schedule_relay=",".join(pairs),
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"remove_user_schedule_relay: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"remove_user_schedule_relay failed: {err}",
            ) from err

        event_data: dict[str, str] = {
            "action": "remove_schedule_relay",
            "device_user_id": device_user_id,
            "schedule_id": schedule_id,
            "relay_id": relay_id,
        }
        config_entry = self.coordinator.config_entry
        if config_entry is not None and hasattr(config_entry, "entry_id"):
            event_data["config_entry_id"] = config_entry.entry_id
        self.hass.bus.async_fire(EVENT_USER_CHANGED, event_data)

    # ── Contact & Group Service Methods ──────────────────────

    async def list_contacts(self, **kwargs: Any) -> ServiceResponse:
        """Return all contacts from the device address book.

        Args:
            **kwargs: Service call data (optional ``page`` key).

        Returns:
            Dict with ``contacts`` list of contact dicts.

        Raises:
            HomeAssistantError: On device communication errors.
            ServiceValidationError: On validation errors.

        """
        page = kwargs.get("page")
        try:
            contacts = await self.coordinator.device.list_contacts(
                page=page,
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"list_contacts: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"list_contacts failed: {err}",
            ) from err
        return cast(
            ServiceResponse,
            {"contacts": [dict(vars(c)) for c in contacts]},
        )

    async def list_groups(self, **kwargs: Any) -> ServiceResponse:
        """Return all groups from the device.

        Args:
            **kwargs: Service call data (optional ``page`` key).

        Returns:
            Dict with ``groups`` list of group dicts.

        Raises:
            HomeAssistantError: On device communication errors.
            ServiceValidationError: On validation errors.

        """
        page = kwargs.get("page")
        try:
            groups = await self.coordinator.device.list_groups(
                page=page,
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"list_groups: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"list_groups failed: {err}",
            ) from err
        return cast(
            ServiceResponse,
            {"groups": [dict(vars(g)) for g in groups]},
        )

    async def add_contact(self, **kwargs: Any) -> None:
        """Create a new contact in the device address book.

        Args:
            **kwargs: Service call data (``name`` required,
                ``phone`` and ``group`` optional).

        Raises:
            ServiceValidationError: On input validation errors.
            HomeAssistantError: On device communication errors.

        """
        try:
            await self.coordinator.device.add_contact(
                name=kwargs["name"],
                phone=kwargs.get("phone"),
                group=kwargs.get("group"),
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"add_contact: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"add_contact failed: {err}",
            ) from err
        event_data: dict[str, str] = {"action": "add"}
        config_entry = self.coordinator.config_entry
        if config_entry is not None and hasattr(config_entry, "entry_id"):
            event_data["config_entry_id"] = config_entry.entry_id
        self.hass.bus.async_fire(EVENT_CONTACT_CHANGED, event_data)

    async def add_group(self, **kwargs: Any) -> None:
        """Create a new group on the device.

        Args:
            **kwargs: Service call data (``name`` required).

        Raises:
            ServiceValidationError: On input validation errors.
            HomeAssistantError: On device communication errors.

        """
        try:
            await self.coordinator.device.add_group(
                name=kwargs["name"],
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"add_group: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"add_group failed: {err}",
            ) from err
        event_data: dict[str, str] = {"action": "add"}
        config_entry = self.coordinator.config_entry
        if config_entry is not None and hasattr(config_entry, "entry_id"):
            event_data["config_entry_id"] = config_entry.entry_id
        self.hass.bus.async_fire(EVENT_GROUP_CHANGED, event_data)

    async def modify_contact(self, **kwargs: Any) -> None:
        """Update an existing contact in the device address book.

        Args:
            **kwargs: Service call data (``id`` required,
                ``name``, ``phone``, ``group`` optional).

        Raises:
            ServiceValidationError: On input validation errors.
            HomeAssistantError: On device communication errors.

        """
        contact_id: str = kwargs["id"]
        try:
            await self.coordinator.device.modify_contact(
                id=contact_id,
                name=kwargs.get("name"),
                phone=kwargs.get("phone"),
                group=kwargs.get("group"),
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"modify_contact: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"modify_contact failed: {err}",
            ) from err
        event_data: dict[str, str] = {
            "action": "modify",
            "contact_id": contact_id,
        }
        config_entry = self.coordinator.config_entry
        if config_entry is not None and hasattr(config_entry, "entry_id"):
            event_data["config_entry_id"] = config_entry.entry_id
        self.hass.bus.async_fire(EVENT_CONTACT_CHANGED, event_data)

    async def modify_group(self, **kwargs: Any) -> None:
        """Rename an existing group on the device.

        Args:
            **kwargs: Service call data (``id`` and ``name``
                required).

        Raises:
            ServiceValidationError: On input validation errors.
            HomeAssistantError: On device communication errors.

        """
        group_id: str = kwargs["id"]
        try:
            await self.coordinator.device.modify_group(
                id=group_id,
                name=kwargs["name"],
            )
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"modify_group: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"modify_group failed: {err}",
            ) from err
        event_data: dict[str, str] = {
            "action": "modify",
            "group_id": group_id,
        }
        config_entry = self.coordinator.config_entry
        if config_entry is not None and hasattr(config_entry, "entry_id"):
            event_data["config_entry_id"] = config_entry.entry_id
        self.hass.bus.async_fire(EVENT_GROUP_CHANGED, event_data)

    async def delete_contact(self, **kwargs: Any) -> None:
        """Delete one or more contacts from the device address book.

        Accepts a single ID or comma-separated IDs for batch
        deletion.

        Args:
            **kwargs: Service call data (``id`` required,
                list[str] after CSV parsing).

        Raises:
            ServiceValidationError: On input validation errors.
            HomeAssistantError: On device communication errors.

        """
        id_value: list[str] = kwargs["id"]
        try:
            await self.coordinator.device.delete_contact(id=id_value)
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"delete_contact: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"delete_contact failed: {err}",
            ) from err
        event_data: dict[str, Any] = {
            "action": "delete",
            "contact_ids": id_value,
        }
        config_entry = self.coordinator.config_entry
        if config_entry is not None and hasattr(config_entry, "entry_id"):
            event_data["config_entry_id"] = config_entry.entry_id
        self.hass.bus.async_fire(EVENT_CONTACT_CHANGED, event_data)

    async def _check_group_orphans(
        self,
        group_id: str,
        group_name: str,
    ) -> None:
        """Log warnings for contacts that reference a deleted group.

        Args:
            group_id: The ID of the deleted group.
            group_name: The name of the deleted group.

        """
        try:
            contacts = await self.coordinator.device.list_contacts(
                page=None,
            )
            for contact in contacts:
                if contact.group == group_name:
                    _LOGGER.warning(
                        "Orphaned contact-group assignment: "
                        "contact '%s' (id=%s) still references "
                        "deleted group %s",
                        contact.name,
                        contact.id,
                        group_id,
                    )
        except AkuvoxError:
            _LOGGER.debug(
                "Could not check for orphaned contacts after deleting group %s",
                group_id,
            )

    async def delete_group(self, **kwargs: Any) -> None:
        """Delete a group from the device.

        After deletion, performs a best-effort check for contacts
        that still reference the deleted group and logs a warning
        for each orphaned contact.

        Args:
            **kwargs: Service call data (``id`` required).

        Raises:
            ServiceValidationError: On input validation errors.
            HomeAssistantError: On device communication errors.

        """
        group_id: str = kwargs["id"]

        # Resolve group name before deletion for orphan check
        group_name: str | None = None
        try:
            groups = await self.coordinator.device.list_groups(
                page=None,
            )
            for grp in groups:
                if grp.id == group_id:
                    group_name = grp.name
                    break
        except AkuvoxError:
            _LOGGER.debug(
                "Could not resolve group name for id %s",
                group_id,
            )

        try:
            await self.coordinator.device.delete_group(id=group_id)
        except AkuvoxValidationError as err:
            raise ServiceValidationError(
                f"delete_group: {err}",
            ) from err
        except AkuvoxError as err:
            raise HomeAssistantError(
                f"delete_group failed: {err}",
            ) from err

        if group_name is not None:
            await self._check_group_orphans(group_id, group_name)

        event_data: dict[str, str] = {
            "action": "delete",
            "group_id": group_id,
        }
        config_entry = self.coordinator.config_entry
        if config_entry is not None and hasattr(config_entry, "entry_id"):
            event_data["config_entry_id"] = config_entry.entry_id
        self.hass.bus.async_fire(EVENT_GROUP_CHANGED, event_data)
