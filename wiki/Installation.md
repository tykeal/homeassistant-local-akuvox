<!--
SPDX-FileCopyrightText: 2026 Andrew Grimberg <tykeal@bardicgrove.org>
SPDX-License-Identifier: Apache-2.0
-->

# Installation

## Requirements

- Home Assistant 2026.7.0 or later
- An Akuvox intercom or access control device with HTTP API enabled
  (see [Device Setup](Device-Setup))
- Network connectivity between Home Assistant and the device

## HACS (Recommended)

1. Open [HACS](https://hacs.xyz/) in Home Assistant.
2. Go to **Integrations** → click the three-dot menu → **Custom
   repositories**.
3. Add the repository URL:

   ```text
   https://github.com/tykeal/homeassistant-local-akuvox
   ```

4. Select category **Integration**.
5. Search for "Local Akuvox" and install it.
6. Restart Home Assistant.

## Manual Installation

1. Download the latest release from the
   [releases page](https://github.com/tykeal/homeassistant-local-akuvox/releases).
2. Copy the `custom_components/local_akuvox` directory into your
   Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.

## Verify Installation

After restarting, go to **Settings** → **Devices & Services** →
**Add Integration** and search for "Local Akuvox". If it appears in
the list, the installation was successful.

## Next Steps

- [Configure the integration](Configuration) using the setup wizard.
