<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Contracts: Config Flow

**Feature**: 001-akuvox-lock-integration
**Component**: `config_flow.py`

## Config Flow Steps

### Step 1: User (Initial Device Setup)

**Input Schema**:

```python
vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USE_SSL, default=False): bool,
    }
)
```

**Validation**:

- `host` must be a valid IP address or hostname
- Proceed to Step 2 (SSL) if `use_ssl` is True, else Step 3 (Auth)

**Errors**:

- `invalid_host` — Malformed IP/hostname

### Step 2: SSL Options (Conditional)

Only shown when `use_ssl` is True in Step 1.

**Input Schema**:

```python
vol.Schema(
    {
        vol.Required(CONF_VERIFY_SSL, default=False): bool,
    }
)
```

**Validation**: None (boolean toggle)

**Next**: Step 3 (Auth)

### Step 3: Authentication

**Input Schema**:

```python
vol.Schema(
    {
        vol.Required(CONF_AUTH_METHOD, default=AUTH_NONE): vol.In(
            [
                AUTH_NONE,  # "None / AllowList" in UI
                AUTH_BASIC,
                AUTH_DIGEST,
            ]
        ),
    }
)
```

**Validation**:

- If `auth_method` is `basic` or `digest`, proceed to Step 4
- If `auth_method` is `none` (covers both no-auth and allowlist
  devices), proceed to connection test

### Step 4: Credentials (Conditional)

Only shown for Basic Auth or Digest Auth.

**Input Schema**:

```python
vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)
```

**Validation**:

- Both fields must be non-empty strings
- Proceed to connection test

### Connection Test

After all steps, validate by connecting to the device:

1. Create `AkuvoxDevice` with collected parameters
2. Call `await device.get_info()` to verify connectivity and get
   device metadata
3. Check `mac_address` against existing entries for duplicate
   detection

**Success**: Create config entry with all collected data

**Errors**:

- `cannot_connect` — `AkuvoxConnectionError`
- `invalid_auth` — `AkuvoxAuthenticationError`
- `already_configured` — Duplicate MAC address detected
- `unknown` — Any other `AkuvoxError`

## Options Flow

Allows reconfiguring all connection parameters (FR-010).

**Input Schema**: Same fields as config flow Steps 1-4, pre-filled
with current values.

**On Save**: Reload the integration entry to apply new settings.
