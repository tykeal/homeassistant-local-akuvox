# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""DataUpdateCoordinator for the Akuvox integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from time import monotonic
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from pylocal_akuvox import (
    AkuvoxAuthenticationError,
    AkuvoxConnectionError,
    AkuvoxDevice,
    AkuvoxDeviceError,
    AkuvoxError,
    AkuvoxParseError,
    AkuvoxUnsupportedError,
    Capability,
    DeviceCapabilities,
    DeviceInfo,
    User,
)

from .capability_support import (
    async_clear_unsupported_capability_issue,
    async_report_unsupported_capability,
    build_default_capabilities,
)
from .const import (
    CONFIG_KEY_LOCATION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    RELAY_KEY_RE,
)
from .relay_config import RelayConfig, _build_relay_config

_LOGGER = logging.getLogger(__name__)

_USER_CACHE_TTL_SECONDS = 300  # 5 minutes


@dataclass
class AkuvoxCoordinatorData:
    """Data class for coordinator update results."""

    device_info: DeviceInfo
    relay_status: dict[str, Any]
    device_name: str = ""
    capabilities: DeviceCapabilities = field(default_factory=build_default_capabilities)
    relay_configs: dict[str, RelayConfig] = field(default_factory=dict)
    users: list[User] = field(default_factory=list)


class AkuvoxDataUpdateCoordinator(
    DataUpdateCoordinator[AkuvoxCoordinatorData],
):
    """Coordinator to manage Akuvox device data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        device: AkuvoxDevice,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: The Home Assistant instance.
            device: The AkuvoxDevice instance for API calls.

        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.device = device
        self.config_entry: ConfigEntry | None = None
        self._cached_device_info: DeviceInfo | None = None
        self._cached_device_name: str | None = None
        self._cached_relay_configs: dict[str, RelayConfig] | None = None
        self._cached_users: list[User] = []
        self._last_user_fetch: float | None = None
        self._was_unavailable: bool = False

    def get_user_by_pin(self, pin: str) -> User | None:
        """Look up a user by their private PIN from the cache.

        Args:
            pin: The PIN code to match against cached users.

        Returns:
            The matching User, or None if not found.

        """
        for user in self._cached_users:
            if user.private_pin == pin:
                return user
        return None

    def update_user_cache(self, users: list[User]) -> None:
        """Replace the cached user list.

        Args:
            users: Fresh user list from the device.

        """
        self._cached_users = list(users)
        self._last_user_fetch = monotonic()

    def _should_fetch_config(self) -> bool:
        """Determine whether device config should be fetched.

        Returns:
            True if config has never been fetched or device
            recovered from unavailable state.

        """
        if self._cached_device_name is None:
            return True
        return bool(self._was_unavailable)

    def _get_capabilities(self) -> DeviceCapabilities:
        """Return the current device capability snapshot."""
        missing = object()
        capabilities = getattr(self.device, "capabilities", missing)
        if capabilities is missing:
            return build_default_capabilities()
        if capabilities is None:
            msg = "Akuvox device capabilities are unavailable outside context"
            raise UpdateFailed(msg)
        if isinstance(capabilities, DeviceCapabilities):
            return capabilities
        return build_default_capabilities()

    async def _async_report_unsupported(
        self,
        err: AkuvoxUnsupportedError,
        *,
        context: str,
    ) -> None:
        """Report an unsupported capability with coordinator entry context."""
        await async_report_unsupported_capability(
            self.hass,
            getattr(self, "config_entry", None),
            err,
            context=context,
        )

    def _fetch_config_from_device_config(
        self,
        device_config: Any,
        relay_status: dict[str, Any],
    ) -> None:
        """Parse device config and update cached values.

        Args:
            device_config: DeviceConfig from the device.
            relay_status: Current relay status dict for
                discovering relay letters.

        """
        self._cached_device_name = device_config.get(
            CONFIG_KEY_LOCATION,
            "",
        )
        relay_configs: dict[str, RelayConfig] = {}
        for key in relay_status:
            match = RELAY_KEY_RE.fullmatch(key)
            if match:
                letter = match.group(1)
                relay_configs[letter] = _build_relay_config(
                    device_config,
                    letter,
                )
        self._cached_relay_configs = relay_configs

    def _apply_default_config(
        self,
        relay_status: dict[str, Any],
        model: str,
    ) -> None:
        """Apply default config values when fetch fails.

        Only overwrites cached values if none exist yet.

        Args:
            relay_status: Current relay status dict.
            model: Device model for fallback name.

        """
        if self._cached_device_name is None:
            self._cached_device_name = f"Akuvox {model}"
        if self._cached_relay_configs is None:
            relay_configs: dict[str, RelayConfig] = {}
            for key in relay_status:
                match = RELAY_KEY_RE.fullmatch(key)
                if match:
                    letter = match.group(1)
                    relay_configs[letter] = RelayConfig()
            self._cached_relay_configs = relay_configs

    async def _async_fetch_device_config(
        self,
        relay_status: dict[str, Any],
    ) -> None:
        """Fetch and parse device config if needed.

        Args:
            relay_status: Current relay status for letter discovery.

        Raises:
            ConfigEntryAuthFailed: On authentication errors.

        """
        if not self._should_fetch_config():
            return

        get_device_config = getattr(self.device, "get_device_config", None)
        if not callable(get_device_config):
            _LOGGER.warning(
                "Device does not support get_device_config; using %s values",
                "cached" if self._cached_device_name is not None else "default",
            )
            self._apply_default_config(
                relay_status,
                self._cached_device_info.model
                if self._cached_device_info is not None
                else "Unknown",
            )
            self._was_unavailable = False
            return

        try:
            device_config = await get_device_config()
            self._fetch_config_from_device_config(
                device_config,
                relay_status,
            )
            if self.config_entry is not None:
                await async_clear_unsupported_capability_issue(
                    self.hass,
                    self.config_entry,
                    reason=None,
                    capability=Capability.DEVICE_CONFIG_GET,
                )
        except AkuvoxUnsupportedError as err:
            await self._async_report_unsupported(
                err,
                context="coordinator device config fetch",
            )
            self._apply_default_config(
                relay_status,
                self._cached_device_info.model
                if self._cached_device_info is not None
                else "Unknown",
            )
        except AkuvoxAuthenticationError as err:
            raise ConfigEntryAuthFailed(
                f"Authentication failed during config fetch: {err}",
            ) from err
        except (
            AkuvoxConnectionError,
            AkuvoxDeviceError,
            AkuvoxParseError,
        ) as err:
            _LOGGER.warning(
                "Failed to fetch device config (%s), using %s values",
                err,
                "cached" if self._cached_device_name is not None else "default",
            )
            self._apply_default_config(
                relay_status,
                self._cached_device_info.model
                if self._cached_device_info is not None
                else "Unknown",
            )
        self._was_unavailable = False

    async def _async_fetch_users(self) -> None:
        """Fetch and cache user list from the device.

        Skips the fetch if the cache was populated within the TTL
        window.  Non-fatal: logs a warning on failure and keeps the
        previous cache intact.

        """
        if (
            self._last_user_fetch is not None
            and monotonic() - self._last_user_fetch < _USER_CACHE_TTL_SECONDS
        ):
            return

        list_users = getattr(self.device, "list_users", None)
        if not callable(list_users):
            return

        try:
            users = await list_users(page=None)
            self._cached_users = users if users is not None else []
            self._last_user_fetch = monotonic()
            if self.config_entry is not None:
                await async_clear_unsupported_capability_issue(
                    self.hass,
                    self.config_entry,
                    reason=None,
                    capability=Capability.USER_LIST,
                )
        except AkuvoxUnsupportedError as err:
            self._last_user_fetch = monotonic()
            await self._async_report_unsupported(
                err,
                context="coordinator user cache fetch",
            )
        except AkuvoxError as err:
            _LOGGER.warning(
                "Failed to fetch users from Akuvox device; keeping cache: %s",
                err,
            )
        except Exception:
            _LOGGER.exception(
                "Unexpected error while fetching users; keeping cache",
            )

    async def _async_update_data(self) -> AkuvoxCoordinatorData:
        """Fetch data from the Akuvox device.

        Returns:
            AkuvoxCoordinatorData with device info, relay status,
            device name, and relay configs.

        Raises:
            UpdateFailed: On connection, device, or parse errors.
            ConfigEntryAuthFailed: On authentication errors.

        """
        capabilities = self._get_capabilities()
        try:
            relay_status = await self.device.get_relay_status()
            if self.config_entry is not None:
                await async_clear_unsupported_capability_issue(
                    self.hass,
                    self.config_entry,
                    reason=None,
                    capability=Capability.RELAY_STATUS,
                )
        except AkuvoxUnsupportedError as err:
            await self._async_report_unsupported(
                err,
                context="coordinator relay status fetch",
            )
            relay_status = {}
        except AkuvoxAuthenticationError as err:
            self._was_unavailable = True
            raise ConfigEntryAuthFailed(
                f"Authentication failed: {err}",
            ) from err
        except AkuvoxConnectionError as err:
            self._was_unavailable = True
            raise UpdateFailed(
                f"Connection error: {err}",
            ) from err
        except AkuvoxDeviceError as err:
            self._was_unavailable = True
            raise UpdateFailed(
                f"Device error: {err}",
            ) from err
        except AkuvoxParseError as err:
            self._was_unavailable = True
            raise UpdateFailed(
                f"Parse error: {err}",
            ) from err

        if self._cached_device_info is None:
            try:
                self._cached_device_info = await self.device.get_info()
            except AkuvoxAuthenticationError as err:
                raise ConfigEntryAuthFailed(
                    f"Authentication failed: {err}",
                ) from err
            except (
                AkuvoxConnectionError,
                AkuvoxDeviceError,
                AkuvoxParseError,
            ) as err:
                raise UpdateFailed(
                    f"Failed to get device info: {err}",
                ) from err

        await self._async_fetch_device_config(relay_status)

        await self._async_fetch_users()

        return AkuvoxCoordinatorData(
            device_info=self._cached_device_info,
            relay_status=relay_status,
            device_name=self._cached_device_name or "",
            relay_configs=self._cached_relay_configs or {},
            capabilities=capabilities,
            users=list(self._cached_users),
        )
