# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Helpers for Akuvox capability options, repairs, and diagnostics."""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, cast

from homeassistant.helpers import issue_registry as ir
from pylocal_akuvox import (
    AkuvoxDevice,
    AkuvoxUnsupportedError,
    Capability,
    CapabilityStatus,
    DeviceCapabilities,
)

from .const import (
    CONF_ATTEMPT_UNKNOWN_CAPABILITY,
    DEFAULT_ATTEMPT_UNKNOWN_CAPABILITY,
    DOMAIN,
    REPAIR_UNSUPPORTED_CAPABILITY_PREFIX,
    REPAIR_UNSUPPORTED_CAPABILITY_TRANSLATION_KEY,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

_SAFE_ID_RE = re.compile(r"[^a-z0-9_]+")
_UNSUPPORTED_ISSUE_IDS = "unsupported_capability_issue_ids"
_SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "pin",
    "card",
    "token",
    "secret",
    "webhook",
    "authorization",
    "cookie",
)


def get_effective_attempt_unknown(entry: ConfigEntry) -> bool:
    """Return the effective unknown-capability opt-in for a config entry."""
    return bool(
        entry.options.get(
            CONF_ATTEMPT_UNKNOWN_CAPABILITY,
            entry.data.get(
                CONF_ATTEMPT_UNKNOWN_CAPABILITY,
                DEFAULT_ATTEMPT_UNKNOWN_CAPABILITY,
            ),
        )
    )


def get_mapping_attempt_unknown(data: Mapping[str, Any]) -> bool:
    """Return the unknown-capability opt-in from a mapping."""
    return bool(
        data.get(
            CONF_ATTEMPT_UNKNOWN_CAPABILITY,
            DEFAULT_ATTEMPT_UNKNOWN_CAPABILITY,
        )
    )


def apply_capability_options(
    device: AkuvoxDevice,
    *,
    attempt_unknown: bool,
) -> None:
    """Apply capability options after the device context is entered."""
    device.attempt_unknown_capability = bool(attempt_unknown)


def is_capability_usable(
    capabilities: DeviceCapabilities,
    capability: Capability,
    *,
    attempt_unknown: bool,
) -> bool:
    """Return whether a capability should be exposed by the integration."""
    status = capabilities.status_of(capability)
    if status is CapabilityStatus.SUPPORTED:
        return True
    if status is CapabilityStatus.UNKNOWN:
        return bool(attempt_unknown)
    return False


def build_default_capabilities(
    *,
    device_class: str = "unknown",
    firmware_version: str = "",
) -> DeviceCapabilities:
    """Return a conservative capability profile for missing snapshots."""
    return DeviceCapabilities(
        device_class=device_class,
        firmware_version=firmware_version,
        capabilities={
            capability: CapabilityStatus.UNKNOWN for capability in Capability
        },
        field_aliases={},
        schema_shapes={},
    )


def _safe_identifier(value: str) -> str:
    """Normalize a string for use in deterministic issue identifiers."""
    normalized = _SAFE_ID_RE.sub("_", value.lower()).strip("_")
    return normalized or "unknown"


def _capability_value(capability: Capability | None) -> str:
    """Return a safe string representation of a capability."""
    if capability is None:
        return "unknown"
    return capability.value


def _unsupported_issue_id(
    entry: ConfigEntry | None,
    err: AkuvoxUnsupportedError,
    *,
    issue_scope: str | None,
) -> str:
    """Build a deterministic unsupported-capability repairs issue id."""
    reason = _safe_identifier(str(err.reason or "unknown"))
    capability = _safe_identifier(_capability_value(err.capability))
    if entry is None:
        scope = _safe_identifier(issue_scope or "unknown")
        return (
            f"{REPAIR_UNSUPPORTED_CAPABILITY_PREFIX}_flow_{scope}_{reason}_{capability}"
        )
    entry_id = _safe_identifier(entry.entry_id)
    return f"{REPAIR_UNSUPPORTED_CAPABILITY_PREFIX}_{entry_id}_{reason}_{capability}"


def _issue_store(hass: HomeAssistant) -> set[str]:
    """Return the in-memory unsupported issue id tracker."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    issue_ids = domain_data.setdefault(_UNSUPPORTED_ISSUE_IDS, set())
    return cast(set[str], issue_ids)


async def async_report_unsupported_capability(
    hass: HomeAssistant,
    entry: ConfigEntry | None,
    err: AkuvoxUnsupportedError,
    *,
    context: str,
    issue_scope: str | None = None,
) -> None:
    """Log and surface an unsupported Akuvox capability as a repairs issue."""
    issue_id = _unsupported_issue_id(entry, err, issue_scope=issue_scope)
    issue_ids = _issue_store(hass)
    issue_registry = ir.async_get(hass)
    if (
        issue_id in issue_ids
        and issue_registry.async_get_issue(DOMAIN, issue_id) is not None
    ):
        return
    issue_ids.add(issue_id)

    capability = _capability_value(err.capability)
    reason = str(err.reason or "unknown")
    entry_title = entry.title if entry is not None else "setup flow"
    entry_id = entry.entry_id if entry is not None else issue_scope or "flow"
    device_class = str(err.device_class or "unknown")
    _LOGGER.warning(
        "Akuvox unsupported capability in %s for %s (%s): "
        "reason=%s capability=%s device_class=%s error=%s",
        context,
        entry_title,
        entry_id,
        reason,
        capability,
        device_class,
        err,
    )

    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.WARNING,
        learn_more_url=(
            "https://github.com/tykeal/pylocal-akuvox/issues/new?"
            "template=new_device.yml"
        ),
        translation_key=REPAIR_UNSUPPORTED_CAPABILITY_TRANSLATION_KEY,
        translation_placeholders={
            "entry_title": entry_title,
            "entry_id": entry_id,
            "context": context,
            "reason": reason,
            "capability": capability,
            "device_class": device_class,
        },
    )


async def async_clear_unsupported_flow_issue(
    hass: HomeAssistant,
    *,
    issue_scope: str,
    reason: str | None,
    capability: Capability | None,
) -> None:
    """Clear flow-scoped unsupported-capability repairs issues."""
    domain_data = hass.data.get(DOMAIN)
    if domain_data is None:
        return
    issue_ids = domain_data.get(_UNSUPPORTED_ISSUE_IDS)
    if not issue_ids:
        return

    prefix = (
        f"{REPAIR_UNSUPPORTED_CAPABILITY_PREFIX}_flow_{_safe_identifier(issue_scope)}_"
    )
    if reason is None and capability is None:
        stale_ids = {issue_id for issue_id in issue_ids if issue_id.startswith(prefix)}
    elif reason is None:
        suffix = f"_{_safe_identifier(_capability_value(capability))}"
        stale_ids = {
            issue_id
            for issue_id in issue_ids
            if issue_id.startswith(prefix) and issue_id.endswith(suffix)
        }
    else:
        err = AkuvoxUnsupportedError(
            "clear",
            reason=reason,
            capability=capability,
        )
        stale_ids = {_unsupported_issue_id(None, err, issue_scope=issue_scope)}
    for issue_id in stale_ids:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        issue_ids.discard(issue_id)
    if not issue_ids:
        domain_data.pop(_UNSUPPORTED_ISSUE_IDS, None)
    if not domain_data:
        hass.data.pop(DOMAIN, None)


async def async_clear_unsupported_capability_issue(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    reason: str | None,
    capability: Capability | None,
) -> None:
    """Clear a previously reported unsupported-capability repairs issue."""
    domain_data = hass.data.get(DOMAIN)
    if domain_data is None:
        return
    issue_ids = domain_data.get(_UNSUPPORTED_ISSUE_IDS)
    if not issue_ids:
        return
    if reason is None and capability is None:
        prefix = (
            f"{REPAIR_UNSUPPORTED_CAPABILITY_PREFIX}_"
            f"{_safe_identifier(entry.entry_id)}_"
        )
        stale_ids = {issue_id for issue_id in issue_ids if issue_id.startswith(prefix)}
    elif reason is None:
        prefix = (
            f"{REPAIR_UNSUPPORTED_CAPABILITY_PREFIX}_"
            f"{_safe_identifier(entry.entry_id)}_"
        )
        suffix = f"_{_safe_identifier(_capability_value(capability))}"
        stale_ids = {
            issue_id
            for issue_id in issue_ids
            if issue_id.startswith(prefix) and issue_id.endswith(suffix)
        }
    else:
        err = AkuvoxUnsupportedError(
            "clear",
            reason=reason,
            capability=capability,
        )
        stale_ids = {_unsupported_issue_id(entry, err, issue_scope=None)}
    for issue_id in stale_ids:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        issue_ids.discard(issue_id)
    if not issue_ids:
        domain_data.pop(_UNSUPPORTED_ISSUE_IDS, None)
    if not domain_data:
        hass.data.pop(DOMAIN, None)


def sanitize_value(value: Any) -> Any:
    """Return a JSON-safe value with sensitive fields redacted."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return sanitize_value(asdict(value))
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_str = str(key)
            if any(
                fragment in key_str.lower() for fragment in _SENSITIVE_KEY_FRAGMENTS
            ):
                sanitized[key_str] = "**REDACTED**"
            else:
                sanitized[key_str] = sanitize_value(item)
        return sanitized
    if isinstance(value, (list, tuple, set, frozenset)):
        return [sanitize_value(item) for item in value]
    if isinstance(value, str) and len(value) > 512:
        return f"{value[:256]}…{value[-128:]}"
    return value


def serialize_capabilities(capabilities: DeviceCapabilities | None) -> dict[str, Any]:
    """Serialize a DeviceCapabilities snapshot for diagnostics."""
    if capabilities is None:
        return {}
    return {
        "device_class": capabilities.device_class,
        "firmware_version": capabilities.firmware_version,
        "capabilities": {
            capability.value: status.value
            for capability, status in capabilities.capabilities.items()
        },
        "field_aliases": sanitize_value(capabilities.field_aliases),
        "schema_shapes": sanitize_value(capabilities.schema_shapes),
        "notes": sanitize_value(capabilities.notes),
        "provenance": sanitize_value(capabilities.provenance),
    }
