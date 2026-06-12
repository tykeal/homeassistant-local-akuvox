# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Validation and conversion helpers for Akuvox services."""

from __future__ import annotations

import datetime as dt
import re
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DAY_NAME_TO_DIGIT

if TYPE_CHECKING:
    from pylocal_akuvox import AccessSchedule, User


REQUIRED_SCHEDULE_FIELDS: dict[str, tuple[str, ...]] = {
    "0": ("week", "date_start", "date_end"),
    "1": ("week",),
    "2": (),
}
REQUIRED_FIELDS = REQUIRED_SCHEDULE_FIELDS
FACTORY_SCHEDULE_IDS: frozenset[str] = frozenset({"1001", "1002"})


def csv_to_list(value: Any) -> list[str]:
    """Split a comma-separated string into a list of trimmed strings.

    Also flattens lists that contain comma-separated items.
    Coerces other iterables via ``cv.ensure_list``.

    """
    if isinstance(value, str):
        return [s.strip() for s in value.split(",") if s.strip()]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, str):
                for part in item.split(","):
                    stripped = part.strip()
                    if stripped:
                        result.append(stripped)
            else:
                result.append(str(item))
        return result
    return cv.ensure_list(value)


def validate_pin(pin: str | None) -> None:
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


def is_cloud_provisioned_user(user: User) -> bool:
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


def is_cloud_provisioned_schedule(schedule: AccessSchedule) -> bool:
    """Return True if the schedule is cloud-provisioned.

    Schedule ``source_type`` uses numeric codes:
    ``"1"``=Local, ``"2"``=Cloud, ``"3"``=ACMS, ``"4"``=SDMC.
    Treated as local when absent, empty, or ``"1"``;
    otherwise non-local.

    Factory schedules 1001 ("Always") and 1002 ("Never") are
    always treated as local even when a cloud enrolment sets
    their ``source_type`` to a non-local value.
    """
    if schedule.display_id in FACTORY_SCHEDULE_IDS:
        return False
    return schedule.source_type is not None and schedule.source_type not in (
        "1",
        "",
    )


def check_required_schedule_fields(
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
    for field in REQUIRED_SCHEDULE_FIELDS.get(schedule_type, ()):
        if kwargs.get(field) is None:
            raise ServiceValidationError(
                f"Field '{field}' is required for schedule type {schedule_type}",
            )


def convert_week(days: list[str]) -> str:
    """Convert day-name list to device digit string.

    Args:
        days: List of day abbreviations (e.g. ["mon", "fri"]).

    Returns:
        Sorted digit string for the device (e.g. "15").

    """
    digits = sorted(DAY_NAME_TO_DIGIT[d] for d in days)
    return "".join(digits)


def convert_date(value: dt.date) -> str:
    """Convert a date object to YYYYMMDD string.

    Args:
        value: The date to convert.

    Returns:
        Date formatted as YYYYMMDD for the device.

    """
    return value.strftime("%Y%m%d")


def convert_time(value: dt.time) -> str:
    """Convert a time object to HH:MM string.

    Args:
        value: The time to convert.

    Returns:
        Time formatted as HH:MM for the device.

    """
    return value.strftime("%H:%M")


def build_schedule_relay(display_ids: list[str], relay_number: int) -> str:
    """Build a schedule_relay string from display_ids.

    Pairs each display_id with the provided relay number
    using comma separation (device firmware requirement).

    Args:
        display_ids: Schedule display_ids to assign.
        relay_number: The 1-based relay number.

    Returns:
        Formatted schedule_relay string (e.g. ``"10-1,20-1"``).

    """
    parts: list[str] = []
    for did in display_ids:
        parts.append(f"{did}-{relay_number}")
    return ",".join(parts)


def parse_schedule_relay_pairs(
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
            "schedule_relay must contain at least one '<schedule_id>-<relay_id>' pair.",
        )
    return pairs
