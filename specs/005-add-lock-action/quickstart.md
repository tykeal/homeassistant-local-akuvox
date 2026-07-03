<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Quickstart: Add Lock Action

## What This Feature Does

Replaces the existing "lock not supported" error with a working lock
action on all Akuvox relay lock entities. Behavior depends on relay
mode:

- **Bistable relays**: Sends a lock command when the relay is
  confirmed unlocked; no-op when already locked.
- **Auto-close relays**: Never sends a command; performs a state
  refresh only.

## Prerequisites

- Existing Akuvox integration setup with at least one relay
  configured
- Home Assistant ≥2026.7.0
- pylocal-akuvox ≥0.2.3

## Files Modified

**`custom_components/akuvox/lock.py`**: Replace `async_lock` stub;
add `_async_finish_optimistic_lock`; refactor
`_schedule_delayed_refresh` to accept callback.

**`tests/test_lock.py`**: Replace error test; add
bistable/auto-close lock tests.

## How to Test

### Run All Tests

```bash
uv run pytest tests/test_lock.py -x -q
```

### Run Only Lock-Action Tests

```bash
uv run pytest tests/test_lock.py -x -q -k "lock" --no-header
```

### Manual Verification

1. Set up an Akuvox relay in **bistable mode** (relay_mode=1)
2. Call `lock.unlock` on the entity → state becomes "unlocked"
3. Call `lock.lock` on the entity → state becomes "locked"
4. Call `lock.lock` again → no-op, state stays "locked"

For auto-close relays:

1. Set up an Akuvox relay in **auto-close mode** (relay_mode=0)
2. Call `lock.unlock` → state becomes "unlocked"
3. Call `lock.lock` → state refresh only, no command sent
4. Wait for hold_delay to expire → state becomes "locked"

## Key Design Decisions

- **No new files**: All changes are within existing `lock.py` and
  `test_lock.py`
- **Reuses existing patterns**: Same `trigger_relay`, optimistic
  state, and delayed refresh infrastructure as unlock
- **Pre-action refresh**: FR-009 requires a coordinator refresh
  before deciding whether to send a command, to avoid acting on
  stale state
- **1-second post-lock refresh**: Bistable relays toggle instantly;
  the short refresh delay confirms device state without the longer
  `hold_delay + buffer` used by unlock
