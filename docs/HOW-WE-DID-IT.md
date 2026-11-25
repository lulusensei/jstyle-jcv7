# How the Pulse band was reverse engineered

A reproducible walkthrough of the investigation, so the community can verify,
extend, and apply the same method to sibling devices (JStyle white-labels:
2208A, 2208A2, 2318, "CORE VITALS", "LivLive", ...).

## 1. Identify the device

- USB enumeration on macOS showed nothing → the cable is charge-only.
- A BLE scan (`bleak`) found `JCV7 3E4E` advertising manufacturer id `0x1234`
  with payload `f7a9404f 3e4e 57533031412d30312d3031323236 0008`
  (`WS01A-01-01226` ASCII, protocol v8).
- Public reporting on the Pulse shutdown confirmed the OEM: Pulse users were
  migrated to the **JStyle** "JCVitalPro" app.

## 2. Map the GATT profile

Connected with bleak and enumerated services: standard Heart Rate, Pulse
Oximeter, Battery, Device Information, RSC — plus vendor service `FFF0` with
`FFF6` (write) and `FFF7` (notify). Device Info gave `J-STYLE`, `JCV7`,
fw `V_30303033-260331`.

## 3. Get the official app

- APKPure served `JCVitalPro_2.0.7` (base APK 491 MB + split APKs).
- Downloads were throttled, so the split APKs were fetched with HTTP range
  requests only (see `scripts/fetch_arm64_chunked.py`).

## 4. Decompile the DEX

- `androguard` light-parsed `classes7.dex` (no full xref analysis needed).
- String scan for `fff` UUIDs located the vendor protocol classes:
  `io/flutter/plugins/SendData` (command builders), `ResolveData` /
  `ResolveDeviceData` (checksums, BCD, date helpers), `ble/BleService`
  (connection + write queue), `ble/BleManager`.
- Field/method dumps of those classes exposed the command constants
  (`CMD_GET_BATTERY = 19` etc.), the additive checksum (`crcValue`), and the
  16-byte frame layout (fixed-size arrays + checksum at last index).
- Cross-referencing `SendData` invocations showed the app layer is only a
  pipe to Flutter/Dart — business logic lives in `libapp.so`.

## 5. Verify against hardware

Probes (`scripts/probe_*.py`) confirmed each command live:

- 16-byte frames accepted; short frames ignored
- battery/version/time/MAC/userinfo responses decoded as documented
- clock sync (BCD `SET_TIME`) works
- multi-packet stream observed for `0x16`

## 6. Tooling notes

- [REA](https://github.com/morluto/rea) (Reverse Engineer Anything) is the
  agent-facing toolkit this project used for app/binary triage; its
  `decode-android-resources`, `identify-flutter-build` and evidence commands
  are useful for the remaining Dart-side work.
- `androguard` (light DEX parse + instruction dumps) did the heavy lifting
  for the Java/Kotlin layer.
- Everything runs locally; no device data leaves the machine.

## Reproduce

```bash
pip install androguard bleak remotezip requests
python scripts/list_classes.py        # class inventory of classes7.dex
python scripts/dump_contract.py       # Realtek protocol tables (audio SDK)
python scripts/dump_senddata.py       # JStyle command builders + bytecode
python scripts/probe_live.py          # live band probing
```

Place `classes7.dex` in `pkgs/jcvitalpro-extracted/` (extract it yourself
from the APK you download — do not redistribute it).
