<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Contract: validation.py Module Interface

**Module**: `custom_components/local_akuvox/validation.py` **Type**: Internal
module API (not user-facing) **Consumers**: `services.py`, `lock.py`

## Public Functions

### csv_to_list

```python
def csv_to_list(value: Any) -> list[str]:
    """Split a comma-separated string into a list of trimmed strings.

    Also flattens lists that contain comma-separated items.
    Coerces other iterables via ``cv.ensure_list``.

    Args:
        value: A string, list, or other iterable to convert.

    Returns:
        List of non-empty trimmed strings.

    """
```

**Contract**:

- Input `"a, b, c"` → `["a", "b", "c"]`
- Input `["a,b", "c"]` → `["a", "b", "c"]`
- Input `[]` → `[]`
- Empty segments after splitting are excluded

______________________________________________________________________

### validate_pin

```python
def validate_pin(pin: str | None) -> None:
    """Validate private_pin is 4-8 digits if provided.

    Args:
        pin: The PIN string to validate, or None.

    Raises:
        ServiceValidationError: If PIN is not 4-8 decimal digits.

    """
```

**Contract**:

- `None` → no-op (no exception)
- `"1234"` → no-op
- `"12345678"` → no-op
- `"123"` → raises `ServiceValidationError("PIN must be 4-8 digits")`
- `"123456789"` → raises `ServiceValidationError("PIN must be 4-8 digits")`
- `"12ab"` → raises `ServiceValidationError("PIN must be 4-8 digits")`

______________________________________________________________________

### is_cloud_provisioned_user

```python
def is_cloud_provisioned_user(user: User) -> bool:
    """Return True if the user is cloud-provisioned.

    Checks both ``source`` and ``source_type`` fields to handle
    firmware variants across Akuvox models.

    Args:
        user: User object from pylocal_akuvox.

    Returns:
        True if cloud-provisioned, False if locally managed.

    """
```

**Contract**:

- `source="Cloud"` → `True`
- `source="SDMC"` → `True`
- `source="Local"` → `False`
- `source=""` → `False`
- `source=None, source_type="2"` → `True`
- `source=None, source_type="1"` → `False`
- `source=None, source_type=None` → `False`

______________________________________________________________________

### is_cloud_provisioned_schedule

```python
def is_cloud_provisioned_schedule(schedule: AccessSchedule) -> bool:
    """Return True if the schedule is cloud-provisioned.

    Factory schedules 1001 and 1002 are always treated as local.

    Args:
        schedule: AccessSchedule object from pylocal_akuvox.

    Returns:
        True if cloud-provisioned, False if locally managed.

    """
```

**Contract**:

- `display_id="1001"` → always `False` (factory)
- `display_id="1002"` → always `False` (factory)
- `source_type="2"` (non-factory) → `True`
- `source_type="3"` (ACMS) → `True`
- `source_type="1"` → `False`
- `source_type=""` → `False`
- `source_type=None` → `False`

______________________________________________________________________

### check_required_schedule_fields

```python
def check_required_schedule_fields(schedule_type: str, **kwargs: Any) -> None:
    """Validate required fields are present for the schedule type.

    Args:
        schedule_type: The schedule type ("0", "1", "2").
        **kwargs: Service call data fields.

    Raises:
        ServiceValidationError: If a required field is missing.

    """
```

**Contract**:

- Type "0" requires: `week`, `date_start`, `date_end`
- Type "1" requires: `week`
- Type "2" requires: nothing extra
- Missing field →
  `ServiceValidationError(f"Field '{field}' is required for schedule type {schedule_type}")`

______________________________________________________________________

### convert_week

```python
def convert_week(days: list[str]) -> str:
    """Convert day-name list to device digit string.

    Args:
        days: List of day abbreviations (e.g. ["mon", "fri"]).

    Returns:
        Sorted digit string for the device (e.g. "15").

    """
```

**Contract**:

- `["mon", "fri"]` → `"15"`
- `["sun"]` → `"0"`
- `["sat", "sun"]` → `"06"`
- Output digits are always sorted ascending

______________________________________________________________________

### convert_date

```python
def convert_date(value: dt.date) -> str:
    """Convert a date object to YYYYMMDD string.

    Args:
        value: The date to convert.

    Returns:
        Date formatted as YYYYMMDD for the device.

    """
```

**Contract**:

- `date(2026, 1, 5)` → `"20260105"`

______________________________________________________________________

### convert_time

```python
def convert_time(value: dt.time) -> str:
    """Convert a time object to HH:MM string.

    Args:
        value: The time to convert.

    Returns:
        Time formatted as HH:MM for the device.

    """
```

**Contract**:

- `time(9, 30)` → `"09:30"`
- `time(0, 0)` → `"00:00"`

______________________________________________________________________

### build_schedule_relay

```python
def build_schedule_relay(display_ids: list[str], relay_number: int) -> str:
    """Build a schedule_relay string from display_ids.

    Pairs each display_id with the given relay number.

    Args:
        display_ids: Schedule display_ids to assign.
        relay_number: The 1-based relay number.

    Returns:
        Formatted schedule_relay string (e.g. "10-1,20-1").

    """
```

**Contract**:

- `(["10", "20"], 1)` → `"10-1,20-1"`
- `(["5"], 2)` → `"5-2"`

______________________________________________________________________

### parse_schedule_relay_pairs

```python
def parse_schedule_relay_pairs(
    raw: str,
    *,
    allow_empty: bool = False,
) -> list[str]:
    """Parse a schedule_relay string into validated pairs.

    Accepts comma or semicolon separators and strips whitespace.
    Each pair must match ``<digits>-<digits>`` format.

    Args:
        raw: Raw schedule_relay string.
        allow_empty: If True, return empty list instead of raising.

    Returns:
        List of validated "schedule_id-relay_id" pairs.

    Raises:
        ServiceValidationError: If any pair is malformed or
            result is empty (unless allow_empty).

    """
```

**Contract**:

- `"10-1,20-2"` → `["10-1", "20-2"]`
- `"10-1;20-2"` → `["10-1", "20-2"]`
- `" 10-1 , 20-2 "` → `["10-1", "20-2"]`
- `"abc-1"` → raises `ServiceValidationError`
- `""` with `allow_empty=False` → raises `ServiceValidationError`
- `""` with `allow_empty=True` → `[]`

## Public Constants

```python
REQUIRED_SCHEDULE_FIELDS: dict[str, tuple[str, ...]]
FACTORY_SCHEDULE_IDS: frozenset[str]
```
