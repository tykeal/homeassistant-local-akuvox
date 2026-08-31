<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Data Model: Add Lock Action

## Existing Entities (No Changes)

This feature does not introduce new entities, fields, or data
structures. It modifies the behavior of the existing
`AkuvoxLockEntity` entity class.

### RelayConfig (unchanged)

```python
@dataclass(frozen=True)
class RelayConfig:
    name: str = ""
    hold_delay: int = DEFAULT_HOLD_DELAY_SECONDS  # 5
    relay_type: int = DEFAULT_RELAY_TYPE  # 0 (NO)
    relay_mode: int = DEFAULT_RELAY_MODE  # 0 (Auto-close)
```

- `relay_mode = 0`: Auto-close (monostable) — relay auto-locks
  after `hold_delay` seconds
- `relay_mode = 1`: Manual (bistable) — relay stays toggled until
  explicitly toggled again

### AkuvoxLockEntity State Fields (unchanged)

| Field                     | Type                    | Purpose                |
| ------------------------- | ----------------------- | ---------------------- |
| `_optimistic_locked`      | `bool \| None`          | Optimistic override    |
| `_delayed_refresh_cancel` | `CALLBACK_TYPE \| None` | Pending refresh cancel |
| `_relay_number`           | `int`                   | 1-based relay number   |
| `_relay_key`              | `str`                   | Relay status key       |

## State Transitions

### Bistable Relay Lock Flow

```text
User calls lock.lock
  │
  ├─ Cancel pending unlock refresh (if any)
  │    └─ Clear _optimistic_locked → None
  │
  ├─ Coordinator refresh (FR-009)
  │    └─ is_locked reads from device state (override is None)
  │
  ├─ Check is_locked
  │    ├─ True  → return (no-op, FR-008)
  │    └─ False → continue
  │         │
  │         ├─ trigger_relay(num, delay, level, mode)
  │         │    ├─ Success:
  │         │    │    ├─ _optimistic_locked = True
  │         │    │    ├─ async_write_ha_state()
  │         │    │    └─ _schedule_delayed_refresh(0,
  │         │    │         finish_callback=
  │         │    │         self._async_finish_optimistic_lock)
  │         │    │         └─ Timer fires after 1s:
  │         │    │              ├─ coordinator.async_refresh()
  │         │    │              └─ _optimistic_locked
  │         │    │                   = None
  │         │    │
  │         │    └─ AkuvoxError:
  │         │         └─ raise HomeAssistantError (FR-006)
  │         │              state unchanged
  │
  └─ None (unknown) → treat as unlocked, continue with command
```

### Auto-Close Relay Lock Flow

```text
User calls lock.lock
  │
  ├─ Do NOT cancel pending unlock refresh (FR-005)
  │
  ├─ Coordinator refresh (FR-004, FR-009)
  │    └─ State updated from device
  │
  └─ async_write_ha_state()
       └─ Return (no command sent, FR-008)
```

## Optimistic State Lifecycle

### During Unlock (existing, unchanged)

```text
async_unlock()
  → _optimistic_locked = False
  → schedule refresh at hold_delay + 1s
  → timer fires → _async_finish_optimistic_unlock()
       → coordinator.async_refresh()
       → _optimistic_locked = None
```

### During Lock (new)

```text
async_lock() [bistable only]
  → cancel pending unlock refresh (if any)
  → _optimistic_locked = None  (clear stale unlock override)
  → coordinator.async_refresh() (FR-009)
  → check is_locked → if unlocked:
       → trigger_relay()
       → _optimistic_locked = True
       → schedule refresh at 0 + 1s buffer
       → timer fires → _async_finish_optimistic_lock()
            → coordinator.async_refresh()
            → _optimistic_locked = None
```

### Lock Followed by Unlock (interaction)

```text
lock sets _optimistic_locked = True, schedules 1s refresh
  → user calls unlock before 1s:
       unlock cancels the lock's pending refresh
       (existing _schedule_delayed_refresh cancels previous timer)
       unlock calls trigger_relay()
       _optimistic_locked = False
       schedules hold_delay + 1s refresh
```

### Unlock Followed by Lock (interaction)

```text
unlock sets _optimistic_locked = False, schedules hold+1s refresh
  → user calls lock before hold+1s:
       lock cancels the unlock's pending refresh
       lock clears _optimistic_locked = None
       lock refreshes coordinator (FR-009)
       if device is unlocked: trigger_relay, set True, schedule 1s
       if device is locked: no-op
```

## Refactored Method

### `_schedule_delayed_refresh` (modified)

The existing `_schedule_delayed_refresh` is hardcoded to call
`_async_finish_optimistic_unlock`. To support both lock and unlock,
it must be generalized to accept a completion callback.

```python
def _schedule_delayed_refresh(
    self,
    hold_delay: int,
    finish_callback: Callable[[], Coroutine[Any, Any, None]] | None = None,
) -> None:
```

The `finish_callback` parameter defaults to
`self._async_finish_optimistic_unlock` for backward compatibility.
The lock action passes `self._async_finish_optimistic_lock`.

### `_async_finish_optimistic_lock` (new)

Mirrors `_async_finish_optimistic_unlock`. Refreshes coordinator
then clears `_optimistic_locked` in a `finally` block.

```python
async def _async_finish_optimistic_lock(self) -> None:
    """Refresh coordinator then clear optimistic lock state."""
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
```

**Note**: This method is identical in structure to
`_async_finish_optimistic_unlock`. A future refactor could unify
them into a single `_async_finish_optimistic_state` method, but
keeping them separate preserves clear log messages and avoids
changing existing tested code (SC-005).
