# SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
# SPDX-License-Identifier: Apache-2.0

"""Tests for capability support helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from pylocal_akuvox import (
    AkuvoxUnsupportedError,
    Capability,
    CapabilityStatus,
    DeviceCapabilities,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.local_akuvox.capability_support import (
    apply_capability_options,
    async_clear_unsupported_capability_issue,
    async_clear_unsupported_flow_issue,
    async_report_unsupported_capability,
    build_default_capabilities,
    get_effective_attempt_unknown,
    is_capability_usable,
    sanitize_value,
    serialize_capabilities,
)
from custom_components.local_akuvox.const import (
    CONF_ATTEMPT_UNKNOWN_CAPABILITY,
    DOMAIN,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_UPSTREAM_GUIDANCE = (
    "Report this device upstream by opening a new-device issue at pylocal-akuvox "
    "and attaching this integration's diagnostics download so it can be added "
    "to the capability matrix."
)


def _entry(
    data: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> MockConfigEntry:
    """Return a mock config entry for helper tests."""
    return MockConfigEntry(domain=DOMAIN, data=data, options=options or {})


def test_effective_attempt_unknown_defaults_and_options_override() -> None:
    """Test the effective option reader is absent-safe."""
    assert get_effective_attempt_unknown(_entry({})) is False
    assert (
        get_effective_attempt_unknown(
            _entry(
                {CONF_ATTEMPT_UNKNOWN_CAPABILITY: False},
                {CONF_ATTEMPT_UNKNOWN_CAPABILITY: True},
            )
        )
        is True
    )


def test_apply_capability_options_sets_device_after_entry() -> None:
    """Test capability options are applied to the entered device."""
    device = MagicMock()
    device.attempt_unknown_capability = False

    apply_capability_options(device, attempt_unknown=True)

    assert device.attempt_unknown_capability is True


def test_capability_usable_respects_unknown_opt_in(
    unknown_capabilities: DeviceCapabilities,
) -> None:
    """Test UNKNOWN capabilities follow the explicit opt-in."""
    assert (
        is_capability_usable(
            unknown_capabilities,
            Capability.RELAY_TRIGGER_API,
            attempt_unknown=False,
        )
        is False
    )
    assert (
        is_capability_usable(
            unknown_capabilities,
            Capability.RELAY_TRIGGER_API,
            attempt_unknown=True,
        )
        is True
    )


def test_capability_usable_rejects_unsupported(
    unsupported_relay_status_capabilities: DeviceCapabilities,
) -> None:
    """Test UNSUPPORTED capabilities are never treated as usable."""
    assert (
        is_capability_usable(
            unsupported_relay_status_capabilities,
            Capability.RELAY_STATUS,
            attempt_unknown=True,
        )
        is False
    )


def test_default_capabilities_are_conservative() -> None:
    """Test fallback capabilities do not expose supported actions."""
    capabilities = build_default_capabilities()

    assert capabilities.device_class == "unknown"
    assert (
        capabilities.status_of(Capability.RELAY_TRIGGER_API) is CapabilityStatus.UNKNOWN
    )
    assert (
        is_capability_usable(
            capabilities,
            Capability.RELAY_TRIGGER_API,
            attempt_unknown=False,
        )
        is False
    )


def test_unsupported_issue_translation_guidance_in_sync() -> None:
    """Test unsupported capability repair guidance is translated consistently."""
    descriptions: list[str] = []

    for relative_path in (
        "custom_components/local_akuvox/strings.json",
        "custom_components/local_akuvox/translations/en.json",
    ):
        data = json.loads((_REPO_ROOT / relative_path).read_text(encoding="utf-8"))
        description = data["issues"]["unsupported_capability"]["description"]
        assert _UPSTREAM_GUIDANCE in description
        assert "{mitigation}" not in description
        descriptions.append(description)

    assert descriptions[0] == descriptions[1]


async def test_report_and_clear_unsupported_issue(
    hass: HomeAssistant,
) -> None:
    """Test unsupported capability reporting deduplicates repairs issues."""
    entry = _entry({})
    entry.add_to_hass(hass)
    err = AkuvoxUnsupportedError(
        "blocked",
        reason="capability_missing",
        capability=Capability.USER_LIST,
        device_class="E21V",
    )

    await async_report_unsupported_capability(
        hass,
        entry,
        err,
        context="unit test",
    )
    issue_ids = hass.data[DOMAIN]["unsupported_capability_issue_ids"]
    assert len(issue_ids) == 1
    issue_id = next(iter(issue_ids))
    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.learn_more_url == (
        "https://github.com/tykeal/pylocal-akuvox/issues/new?template=new_device.yml"
    )
    assert issue.translation_placeholders is not None
    assert "mitigation" not in issue.translation_placeholders

    await async_report_unsupported_capability(
        hass,
        entry,
        err,
        context="unit test",
    )
    assert len(issue_ids) == 1

    ir.async_delete_issue(hass, DOMAIN, issue_id)
    await async_report_unsupported_capability(
        hass,
        entry,
        err,
        context="unit test",
    )
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None

    await async_clear_unsupported_capability_issue(
        hass,
        entry,
        reason="capability_missing",
        capability=Capability.USER_LIST,
    )
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None


async def test_report_flow_scoped_unknown_issue_and_clear_all(
    hass: HomeAssistant,
) -> None:
    """Test flow-scoped unknown issues use safe identifiers."""
    entry = _entry({})
    entry.add_to_hass(hass)
    err = AkuvoxUnsupportedError(
        "blocked",
        reason=None,
        capability=None,
        device_class=None,
    )

    await async_report_unsupported_capability(
        hass,
        None,
        err,
        context="setup flow",
        issue_scope="Host 1!",
    )
    flow_issue_id = next(iter(hass.data[DOMAIN]["unsupported_capability_issue_ids"]))
    assert "_flow_host_1_unknown_unknown" in flow_issue_id

    entry_err = AkuvoxUnsupportedError(
        "blocked",
        reason="capability_unknown",
        capability=Capability.CONTACT_ADD,
    )
    await async_report_unsupported_capability(
        hass,
        entry,
        entry_err,
        context="unit test",
    )
    assert len(hass.data[DOMAIN]["unsupported_capability_issue_ids"]) == 2

    await async_clear_unsupported_capability_issue(
        hass,
        entry,
        reason=None,
        capability=None,
    )

    issue_ids = hass.data[DOMAIN]["unsupported_capability_issue_ids"]
    assert flow_issue_id in issue_ids
    assert len(issue_ids) == 1

    await async_clear_unsupported_flow_issue(
        hass,
        issue_scope="Host 1!",
        reason=None,
        capability=None,
    )
    assert DOMAIN not in hass.data


async def test_clear_flow_issue_handles_empty_store(
    hass: HomeAssistant,
) -> None:
    """Test clearing a flow issue with no issue ids is a no-op."""
    hass.data[DOMAIN] = {}

    await async_clear_unsupported_flow_issue(
        hass,
        issue_scope="host",
        reason=None,
        capability=None,
    )

    assert hass.data[DOMAIN] == {}


async def test_clear_flow_issue_by_capability_and_reason(
    hass: HomeAssistant,
) -> None:
    """Test flow-scoped issue cleanup can target capability or reason."""
    first = AkuvoxUnsupportedError(
        "blocked",
        reason="capability_unknown",
        capability=Capability.USER_LIST,
    )
    second = AkuvoxUnsupportedError(
        "blocked",
        reason="capability_missing",
        capability=Capability.CONTACT_ADD,
    )

    await async_report_unsupported_capability(
        hass,
        None,
        first,
        context="flow test",
        issue_scope="host",
    )
    await async_report_unsupported_capability(
        hass,
        None,
        second,
        context="flow test",
        issue_scope="host",
    )

    await async_clear_unsupported_flow_issue(
        hass,
        issue_scope="host",
        reason=None,
        capability=Capability.USER_LIST,
    )
    issue_ids = hass.data[DOMAIN]["unsupported_capability_issue_ids"]
    assert len(issue_ids) == 1

    await async_clear_unsupported_flow_issue(
        hass,
        issue_scope="host",
        reason="capability_missing",
        capability=Capability.CONTACT_ADD,
    )
    assert DOMAIN not in hass.data


def test_serialize_capabilities_sanitizes_notes() -> None:
    """Test capability serialization redacts sensitive note keys."""
    capabilities = DeviceCapabilities(
        device_class="E21V",
        firmware_version="1.0.0",
        capabilities={Capability.USER_LIST: CapabilityStatus.SUPPORTED},
        field_aliases={},
        schema_shapes={},
        notes={"private_pin": "1234", "safe": "ok"},
    )

    result = serialize_capabilities(capabilities)

    assert result["capabilities"] == {"user.list": "supported"}
    assert result["notes"]["private_pin"] == "**REDACTED**"
    assert result["notes"]["safe"] == "ok"


def test_sanitize_value_handles_dataclasses_enums_sequences_and_long_strings() -> None:
    """Test diagnostic sanitization handles complex JSON-like values."""
    from dataclasses import dataclass

    @dataclass
    class Payload:
        """Small dataclass used for sanitization coverage."""

        capability: Capability
        password: str

    result = sanitize_value(
        {
            "payload": Payload(Capability.USER_LIST, "secret"),
            "items": (Capability.RELAY_STATUS, {"card_code": "123"}),
            "note": "x" * 700,
        }
    )

    assert result["payload"]["capability"] == "user.list"
    assert result["payload"]["password"] == "**REDACTED**"  # noqa: S105
    assert result["items"][0] == "relay.status"
    assert result["items"][1]["card_code"] == "**REDACTED**"
    assert len(result["note"]) < 700


def test_serialize_capabilities_none_returns_empty_dict() -> None:
    """Test serializing missing capabilities returns an empty mapping."""
    assert serialize_capabilities(None) == {}
