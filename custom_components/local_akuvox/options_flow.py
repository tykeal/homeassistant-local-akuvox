# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Options flow for the Akuvox integration."""

from __future__ import annotations

import secrets
from typing import Any

# aislop-ignore-next-line ai-slop/hallucinated-import -- provided by homeassistant
import voluptuous as vol  # provided by homeassistant
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from pylocal_akuvox import (
    AkuvoxDevice,
    AkuvoxUnsupportedError,
    AuthConfig,
    AuthMethod,
)

from .capability_support import (
    apply_capability_options,
    async_report_unsupported_capability,
    get_mapping_attempt_unknown,
)
from .const import (
    AUTH_BASIC,
    AUTH_DIGEST,
    AUTH_NONE,
    CONF_ATTEMPT_UNKNOWN_CAPABILITY,
    CONF_AUTH_METHOD,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_REQUEST_DELAY,
    CONF_USE_SSL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    CONF_WEBHOOK_ENABLED,
    CONF_WEBHOOK_ID,
    DEFAULT_ATTEMPT_UNKNOWN_CAPABILITY,
    DEFAULT_REQUEST_DELAY,
    get_auth_method_map,
)
from .webhook import build_action_urls


class AkuvoxOptionsFlow(OptionsFlow):
    """Handle options flow for Akuvox integration."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow.

        Args:
            config_entry: The config entry being configured.

        """
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> Any:
        """Handle the init step of options flow.

        Presents all connection parameters pre-filled with current
        values. On submit, saves to entry.options and triggers
        integration reload.

        Args:
            user_input: User input from the form.

        Returns:
            Flow result for entry creation or form.

        """
        if user_input is not None:
            errors: dict[str, str] = {}

            host = user_input.get(CONF_HOST, "")
            if not host or not host.strip():
                errors["base"] = "invalid_host"
            else:
                user_input[CONF_HOST] = host.strip()

            auth = user_input.get(CONF_AUTH_METHOD, AUTH_NONE)
            if auth in (AUTH_BASIC, AUTH_DIGEST):
                username = user_input.get(CONF_USERNAME, "")
                password = user_input.get(CONF_PASSWORD, "")
                if not username or not password:
                    errors.setdefault("base", "invalid_auth")

            if not errors:
                webhook_err = await self._async_handle_webhook_change(
                    user_input,
                )
                if webhook_err:
                    errors["base"] = webhook_err

            if errors:
                current = {
                    **self._config_entry.data,
                    **self._config_entry.options,
                    **user_input,
                }
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._build_schema(current),
                    errors=errors,
                )

            return self.async_create_entry(
                title="",
                data=user_input,
            )

        current = {
            **self._config_entry.data,
            **self._config_entry.options,
        }

        return self.async_show_form(
            step_id="init",
            data_schema=self._build_schema(current),
        )

    async def _async_handle_webhook_change(
        self,
        user_input: dict[str, Any],
    ) -> str | None:
        """Handle webhook enable/disable changes in options flow.

        Pushes action URL config to device when webhook state changes.

        Args:
            user_input: User input from the options form.

        Returns:
            Error string if push failed, None on success.

        """
        current = {
            **self._config_entry.data,
            **self._config_entry.options,
        }
        was_enabled = current.get(CONF_WEBHOOK_ENABLED, False)
        now_enabled = user_input.get(CONF_WEBHOOK_ENABLED, False)

        if was_enabled == now_enabled:
            # Preserve existing webhook fields unchanged
            if CONF_WEBHOOK_ID not in user_input:
                user_input[CONF_WEBHOOK_ID] = current.get(
                    CONF_WEBHOOK_ID,
                )
            user_input[CONF_WEBHOOK_ENABLED] = was_enabled
            return None

        # Resolve or generate webhook_id
        webhook_id = current.get(CONF_WEBHOOK_ID)
        if now_enabled and webhook_id is None:
            webhook_id = secrets.token_hex(32)

        if webhook_id is None:
            return None

        try:
            enable_payload, disable_payload = build_action_urls(
                self.hass,
                str(webhook_id),
                warn_http=now_enabled,
            )
        except Exception:
            return "webhook_push_failed"

        payload = enable_payload if now_enabled else disable_payload

        # Use merged settings for device connection
        effective = {**current, **user_input}
        auth_method_str = effective.get(
            CONF_AUTH_METHOD,
            AUTH_NONE,
        )
        auth_method = get_auth_method_map().get(
            auth_method_str,
            AuthMethod.NONE,
        )

        auth_config: AuthConfig | None = None
        if auth_method in (AuthMethod.BASIC, AuthMethod.DIGEST):
            auth_config = AuthConfig(
                method=auth_method,
                username=str(
                    effective.get(CONF_USERNAME, ""),
                ),
                password=str(
                    effective.get(CONF_PASSWORD, ""),
                ),
            )
        else:
            auth_config = AuthConfig(method=auth_method)

        device = AkuvoxDevice(
            host=str(effective.get(CONF_HOST, "")),
            auth=auth_config,
            use_ssl=bool(effective.get(CONF_USE_SSL, False)),
            verify_ssl=bool(
                effective.get(CONF_VERIFY_SSL, True),
            ),
            request_delay=float(  # type: ignore[call-arg]
                effective.get(CONF_REQUEST_DELAY, DEFAULT_REQUEST_DELAY)
            ),
        )

        try:
            async with device:
                apply_capability_options(
                    device,
                    attempt_unknown=get_mapping_attempt_unknown(effective),
                )
                await device.set_device_config(payload)  # type: ignore[attr-defined]
        except AkuvoxUnsupportedError as err:
            await async_report_unsupported_capability(
                self.hass,
                self._config_entry,
                err,
                context="options webhook change",
            )
            return "webhook_push_failed"
        except Exception:
            return "webhook_push_failed"

        user_input[CONF_WEBHOOK_ID] = str(webhook_id)
        user_input[CONF_WEBHOOK_ENABLED] = now_enabled
        return None

    @staticmethod
    def _build_schema(
        current: dict[str, Any],
    ) -> vol.Schema:
        """Build the options flow form schema.

        Args:
            current: Current configuration values.

        Returns:
            A voluptuous schema with pre-filled defaults.

        """
        return vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=current.get(CONF_HOST, ""),
                ): str,
                vol.Required(
                    CONF_USE_SSL,
                    default=current.get(CONF_USE_SSL, False),
                ): bool,
                vol.Required(
                    CONF_VERIFY_SSL,
                    default=current.get(CONF_VERIFY_SSL, True),
                ): bool,
                vol.Required(
                    CONF_AUTH_METHOD,
                    default=current.get(CONF_AUTH_METHOD, AUTH_NONE),
                ): vol.In([AUTH_NONE, AUTH_BASIC, AUTH_DIGEST]),
                vol.Optional(
                    CONF_USERNAME,
                    default=current.get(CONF_USERNAME, ""),
                ): str,
                vol.Optional(
                    CONF_PASSWORD,
                    default=current.get(CONF_PASSWORD, ""),
                ): str,
                vol.Optional(
                    CONF_REQUEST_DELAY,
                    default=current.get(CONF_REQUEST_DELAY, DEFAULT_REQUEST_DELAY),
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=5.0)),
                vol.Required(
                    CONF_ATTEMPT_UNKNOWN_CAPABILITY,
                    default=bool(
                        current.get(
                            CONF_ATTEMPT_UNKNOWN_CAPABILITY,
                            DEFAULT_ATTEMPT_UNKNOWN_CAPABILITY,
                        )
                    ),
                ): bool,
                vol.Required(
                    CONF_WEBHOOK_ENABLED,
                    default=current.get(CONF_WEBHOOK_ENABLED, False),
                ): bool,
            }
        )
