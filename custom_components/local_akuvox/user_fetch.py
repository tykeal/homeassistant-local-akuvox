# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Shared helper for fetching a device's complete user list.

``list_users(page=None)`` issues a single ``GET /api/user/get`` with no
``page`` parameter and returns only that one response. Devices paginate
at 10 users per page, so every caller that needs the *whole* user list
has to walk explicit pages on top of the parameterless call
(issues #128 and #321).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pylocal_akuvox import User

_LOGGER = logging.getLogger(__name__)

# Backstop for the paginated walk. Devices return 10 users per page, so
# 100 pages covers 1000 users -- far beyond the capacity of any supported
# Akuvox intercom. It exists only to bound the loop if a device returns
# non-empty, never-repeating pages indefinitely.
MAX_USER_PAGES: Final = 100

# Total seconds the paged walk may spend. The walk turns one request into
# up to MAX_USER_PAGES + 1 sequential requests, so it needs a ceiling of
# its own; exhausting it returns the users gathered so far rather than
# failing.
DEFAULT_WALK_BUDGET: Final = 30.0

ListUsers = Callable[..., Awaitable[list["User"] | None]]
UserKey = tuple[str, str]


def user_key(user: User) -> UserKey:
    """Return a stable identity key for deduplicating a user.

    ``User.id`` is the device-assigned identity and is used whenever it
    is present. Some firmware omits ``ID`` from ``/api/user/get``; those
    users fall back to the always-present ``user_id`` so they are still
    deduplicated instead of being dropped or duplicated.

    Args:
        user: The user to key.

    Returns:
        A hashable key identifying the user.

    """
    if user.id is not None:
        return ("id", user.id)
    return ("user_id", user.user_id)


async def _call(
    list_users: ListUsers,
    page: int | None,
    timeout: float | None,
) -> list[User] | None:
    """Invoke ``list_users`` for one page, optionally under a timeout.

    Args:
        list_users: The device's ``list_users`` coroutine function.
        page: Page number, or ``None`` for the parameterless call.
        timeout: Seconds to allow, or ``None`` for no limit.

    Returns:
        The users returned by the device, possibly ``None``.

    """
    if timeout is None:
        return await list_users(page=page)
    return await asyncio.wait_for(list_users(page=page), timeout=timeout)


async def async_fetch_all_users(
    list_users: ListUsers,
    *,
    baseline_timeout: float | None = None,
    walk_budget: float = DEFAULT_WALK_BUDGET,
) -> list[User]:
    """Fetch the device's complete user list across all pages.

    The parameterless ``list_users(page=None)`` call is issued first and
    its result is kept verbatim, so a device that works today behaves
    exactly as it does today. Pages ``1, 2, 3, ...`` are then walked and
    any users the baseline did not already contain are appended.

    Exceptions from the *baseline* call propagate so callers keep their
    existing error handling. Exceptions from the *paged* walk are
    contained: whatever has been accumulated so far is returned, which
    means a device that rejects the ``page`` parameter still yields
    exactly the baseline result.

    Args:
        list_users: The device's ``list_users`` coroutine function.
        baseline_timeout: Optional timeout for the baseline call. A
            timeout there propagates as ``TimeoutError`` -- nothing has
            been fetched yet, so nothing can be discarded.
        walk_budget: Total seconds allowed for the paged walk. When it
            is exhausted the walk stops and returns what it has.

    Returns:
        The union of the baseline users and every paged user, in
        discovery order, deduplicated by :func:`user_key`.

    Raises:
        Exception: Whatever the baseline call raises, unchanged.

    """
    baseline = await _call(list_users, None, baseline_timeout)
    merged: list[User] = list(baseline) if baseline else []
    merged_keys = {user_key(user) for user in merged}

    # Tracks only the keys returned by the paged walk. It must stay
    # separate from ``merged_keys``: if the baseline keys were seeded
    # here, page 1 (which normally repeats the baseline) would look like
    # a repeat and the walk would stop before ever requesting page 2 --
    # reintroducing the single-page bug this helper exists to fix.
    walk_seen: set[UserKey] = set()
    deadline = monotonic() + walk_budget

    for page in range(1, MAX_USER_PAGES + 1):
        remaining = deadline - monotonic()
        if remaining <= 0:
            _LOGGER.debug("Paged user walk ran out of time at page %s", page)
            break

        try:
            users = await _call(list_users, page, remaining)
        except Exception as err:  # noqa: BLE001 - best-effort augmentation
            _LOGGER.debug("Paged user walk stopped at page %s: %s", page, err)
            break

        if not users:
            break

        page_keys = {user_key(user) for user in users}
        if page > 1 and page_keys <= walk_seen:
            # The device ignored the page parameter and is repeating
            # earlier pages; stop rather than loop to the cap.
            break
        walk_seen |= page_keys

        for user in users:
            key = user_key(user)
            if key in merged_keys:
                continue
            merged_keys.add(key)
            merged.append(user)
    else:
        _LOGGER.debug(
            "Paged user walk hit the %s page limit; list may be truncated",
            MAX_USER_PAGES,
        )

    return merged
