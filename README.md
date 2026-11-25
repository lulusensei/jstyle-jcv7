# Pulse → JCV7 Revival Kit

Open-source driver and documentation for the **JStyle JCV7** health band —
the hardware that was sold as the **Pulse** DePIN health wearable. When the
Pulse project shut down in April 2026 (sunset May 14, 2026), the band's cloud
died with it. This project makes the hardware usable again, no cloud required.

```
Device     : J-STYLE JCV7 (models 2208A / 2208A2 / 2318)
Firmware   : V_30303033 build 260331, hw V_1.0
Connection : Bluetooth LE (the supplied USB cable is charge-only)
GATT       : standard HeartRate / SpO2 / Battery / DeviceInfo + vendor FFF0
Status     : protocol core verified against live hardware
```

## Why this exists

Pulse was a crypto-incentivized health-data network ("DePIN"). It ran out of
funding, and its app/website were retired after users were told to migrate to
the OEM's app. The band itself is a perfectly good BLE device — with a little
reverse engineering it works with any platform, forever.

Everything here was produced from:

1. Static analysis of the official **JCVitalPro** Android app
   (decompiled `classes7.dex`, `io/flutter/plugins/SendData` et al.)
2. Live BLE probing with `bleak` against the real band
3. Public reporting on the Pulse shutdown

See `docs/PROTOCOL.md` for the full protocol and `docs/HOW-WE-DID-IT.md` for
the reproducible methodology (including REA — the Reverse Engineer Anything
toolkit).

## Quick start

```bash
pip install bleak            # or: pip install -e . in this repo
python -m jstyle_jcv7.cli scan
python -m jstyle_jcv7.cli --address <UUID-or-MAC> info
python -m jstyle_jcv7.cli --address <UUID> time --sync
python -m jstyle_jcv7.cli --address <UUID> sleep
```

Library use:

```python
import asyncio
from jstyle_jcv7 import PulseBand

async def main():
    async with PulseBand("YOUR-BAND-ADDRESS") as band:
        print("battery:", await band.get_battery(), "%")
        print("mac    :", await band.get_mac())
        print("time   :", await band.get_time())
        await band.set_time()          # sync device clock to host
        for pkt in await band.get_sleep_activity():
            print(pkt.hour, pkt.value)

asyncio.run(main())
```

On macOS the band appears as a UUID (CoreBluetooth); on Linux/Windows it is a
MAC address. Wake the band first (button or charger) and keep any phone app
from holding the BLE connection.

## What works today

- Battery level, firmware version, MAC, device clock (read + sync)
- User profile (read/write)
- Sleep/activity history stream (partial format)
- Raw frame console (`raw` / `monitor`) for experiments
- Standard BLE services work with *any* BLE client: live HR (`0x2A37` when
  the band streams it), SpO2 (`0x2A5F`), battery (`0x2A19`)

## What the community can finish

See the open-questions list at the end of `docs/PROTOCOL.md` — history-record
formats, live-HR trigger, the `0x92` file-transfer channel (firmware dump for
preservation), and the DFU update path. These need patient protocol probing
or Dart-snapshot analysis; the hard part (framing, checksum, command table)
is done and documented.

## Safety notes

- `0x12 SET_FACTORY`, `0x2E SET_MCU_RESET`, `0x47 SET_DFU_MODE` are known
  but deliberately untested/unused here — the second can reboot the band and
  the third enters the bootloader.
- Nothing in this repository transmits your health data anywhere. It is a
  local driver, by design.

## License

MIT — see [LICENSE](LICENSE).
