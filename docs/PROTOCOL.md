# JStyle JCV7 BLE Protocol

Reverse-engineered from the JCVitalPro Android app 2.0.7 (`com.jstyle.jcvitalpro`)
and verified against live hardware. The same hardware was sold as the
**Pulse** DePIN health wearable (models **2208A / 2208A2 / 2318**; sibling
white-labels include "CORE VITALS" and "LivLive").

## Radio layer

| Item | Value |
|---|---|
| Transport | Bluetooth Low Energy |
| Advertised name | `JCV7 XXXX` (last 4 hex digits of the MAC) |
| Manufacturer ID | `0x1234` |
| Advertisement payload | `f7a9404f` (device id) + `3e4e` (MAC suffix) + ASCII model e.g. `WS01A-01-01226` + `0008` (protocol version 8) |
| USB cable | **charge-only** — all data goes over BLE |

### GATT profile

| Service | Characteristic | Purpose |
|---|---|---|
| `0x180D` Heart Rate | `0x2A37` (notify), `0x2A38` (read) | standard HR — **streams live ~1 Hz when worn** (verified: 21 samples/30 s, values 59–70 bpm, sensor location `0x02` = wrist); no proprietary handshake required |
| `0x1822` Pulse Oximeter | `0x2A5F` (notify) | standard SpO2 spot-check |
| `0x180A` Device Information | `0x2A29`, `0x2A24`, `0x2A25`, `0x2A27`, `0x2A26` | `J-STYLE`, `JCV7`, serial `88888801`, hw `V_1.0`, fw `V_30303033-260331` |
| `0x180F` Battery | `0x2A19` (read/notify) | standard battery level |
| `0x1814` Running Speed & Cadence | `0x2A53` (notify) | standard RSC |
| **`0xFFF0` vendor** | **`0xFFF6` (write-no-rsp), `0xFFF7` (notify)** | proprietary command channel |

Older JStyle bands (ID107 era) used FFF1–FFF4; this generation moved to
FFF6/FFF7. Nordic's Android BLE library plus Realtek (`com.realsil.sdk.bbpro`,
DFU + `libRtkAesJni.so`) and Goodix ("HuiDing") OTA stacks are bundled in the
official app.

## Frame format (FFF6 / FFF7)

Every frame is **exactly 16 bytes**:

```
offset  0    1..14               15
        CMD  params / data        CHECKSUM
```

- `CHECKSUM = (sum of bytes 0..14) & 0xFF` — plain additive checksum,
  implemented in `SendData.crcValue`.
- Requests are written to **FFF6** with write-without-response.
- Responses arrive on **FFF7** with the command byte echoed at offset 0.
- Bytes 1..14 are zero-padded. We verified short frames are silently ignored.
- Some commands answer with a multi-packet stream (see 0x16 below).
- Writes are serialized by the official app through a command queue
  (`BleService.offerValue` / `nextQueue`).

Observed ACK styles:

- `SET_USER_INFO` ack: `[cmd, 0x00, 0x00…]` — status `0x00` = success
- `SET_TIME` ack: `[cmd, 0xF4, 0x00…]` — `0xF4` = success (also appears in
  time payloads; meaning still unconfirmed)

## Command table

| Cmd | Name | Params | Response (byte offsets) |
|---|---|---|---|
| `0x01` | SET_TIME | `yy MM dd HH mm ss w` as **BCD** (`w` = weekday, Mon=1..Sun=0) | ack `[0]=01 [1]=F4` |
| `0x02` | SET_USER_INFO | `gender age height weight goal` (all u8) | ack status `00` |
| `0x03` | DISABLE_ANCS | — | sent by app right after subscribing; no reply observed |
| `0x05` | SET_DEVICE_ID | — | not yet exercised |
| `0x11` | ENABLE_ACTIVITY_HEART | `flag` (0/1) | no reply observed |
| `0x12` | SET_FACTORY | — | **destructive, untested** |
| `0x14` | GET_BED_UP_TIME | `x` | echo + data |
| `0x15` | GET_TURNOVER_DATA | `x` | echo + data (bed-sensor feature) |
| `0x16` | GET_SLEEP_ACTIVITY | `flag` | **multi-packet stream** |
| `0x17` | GET_HEART_BREATH_DATA | `index` | silent in tests so far |
| `0x22` | GET_MAC | — | `[1..6]` = MAC bytes |
| `0x27` | GET_VERSION | — | `[4..7]` = fw (e.g. `03 26 03 31`) |
| `0x2E` | SET_MCU_RESET | — | **reboots MCU, untested** |
| `0x3C` | SEND_PWD | `63 4B 3C 34 26 2D` (hardcoded in app) | silent in tests |
| `0x3D` | SET_NAME | ascii | not yet exercised (renames device) |
| `0x41` | GET_TIME | — | `[1..7]` BCD `yy MM dd HH mm ss w`, `[8]=F4` |
| `0x42` | GET_USER_INFO | — | `[1]` gender, `[2]` age, `[3]` height, `[4]` weight, `[5]` goal, `[6..11]` user id ascii |
| `0x43` | GET_DAY_DATA | `index` | silent in tests so far |
| `0x44` | GET_SLEEP_DATA | `index` | silent in tests so far |
| `0x47` | SET_DFU_MODE | — | reboots into bootloader (**use with care**) |
| `0x63` | SHOW_VERSION | `00 11 00 11 00` | event `0xE3` observed |
| `0x77` | SEND_READ ("RAED") | — | `[1..2]`=0x35A8, `[3..4]`=0x0020, `[5..7]`=0x0FE0 (flash metadata, see below) |

### Verified examples

```
→ 13 00 … 13                      GET_BATTERY
← 13 63 00 43 62 …                battery = 0x63 = 99 %

→ 27 00 … 27                      GET_VERSION
← 27 00 00 00 03 26 03 31 …       fw 03.26.03.31

→ 41 00 … 41                      GET_TIME
← 41 26 11 24 10 49 47 02 F4 …    2026-11-24 10:49:47 weekday=2 flag=F4

→ 01 26 11 24 10 49 46 02 … FD    SET_TIME (BCD)
← 01 F4 00 … F5                   ok

→ 22 00 … 22                      GET_MAC
← 22 F7 A9 40 4F 3E 4E …          MAC F7:A9:40:4F:3E:4E

→ 42 00 … 42                      GET_USER_INFO
← 42 01 22 AF 40 4C 38×6 …        male, 34y, 175cm, 64kg, goal=0x4C, id "888888"

→ 16 01 … 17                      GET_SLEEP_ACTIVITY
← 16 05 00 … / 16 06 00 … /
  16 07 01 … / 16 08 01 …         stream of per-hour records
```

### GET_SLEEP_ACTIVITY (0x16) — multi-packet stream

The band answers with several 16-byte frames back to back:

```
[0] = 0x16 (echo)
[1] = record index — observed 05, 06, 07, 08
[2] = value        — observed 00, 00, 01, 01
```

Working hypothesis: `[1]` is an hour of day and `[2]` an activity/sleep flag
(00 = resting, 01 = active). The stream was identical across queries, which
suggests a server-side cursor or a fixed "last night" window. If `[1]` were a
packet sequence we would expect 1..N — packets 1–4 have never been observed,
supporting the hour interpretation (05:00–08:00).

## History dump commands (0x51-0x5C)

Writing a bare 16-byte frame `[cmd, 0x00…]` for these commands makes the band
stream its stored history as bursts of large (MTU-sized) notifications. Each
record follows the envelope:

```
[0]      cmd echo
[1:3]    record sequence (u16 LE)
[3]      0x00
[4:11]   BCD date-time  yy MM dd HH mm ss
[11:]    type-specific payload
```

| Cmd | Content (provisional) | Notes |
|---|---|---|
| `0x51` | **daily summaries** | 1 record per day, u16 LE counters (steps/kcal/dist — units TBD) |
| `0x52` | **hourly activity** (steps/calories per hour) | 25-byte records |
| `0x53` | **sleep sessions** | 2-hour blocks, 130-byte records: `[cmd][seq:2][yy MM dd HH mm][minutes-covered][120 × stage/min]` — codes `0`=awake, `1`=deep?, `2`=light?, `3`=REM?, `5`=in-bed awake |
| `0x54` | **workout HR series** | HR byte sequence after timestamp |
| `0x55` | **5-minute HR log** | 10-byte records `[cmd][seq:2][yy MM dd HH mm][type][hr]` |
| `0x56` | periodic snapshot (6-byte payload) | every ~10-15 min; meaning TBD |
| `0x58` | **minute-by-minute sensor log** | 33-byte records, payload[18] ≈ HR (verified vs 5-min log) |
| `0x59` | **event log** | state events, `88 88 11 11` markers |
| `0x5B`, `0x60`, `0x62` | short acks `[cmd, FF]` | **one of these vibrates the band once** (likely "find device") |
| `0x5C` | **manual measurement snapshots** | timestamp + HR + float32 temperature (°C) + second float |

Verified overnight (2026-11-25→26): sleep stages from `0x53` (6 × 2 h
blocks), 5-min HR from `0x55` (92 pts, 54-76 bpm), minute HR from `0x58`
(350 records). No SpO2 values were stored overnight — auto-measurement is
either disabled by default or requires a settings command.

Factory QC records (Feb-Mar 2026) are still in flash, so history survives
resets and re-pairing. Resynchronize record boundaries on the pattern
`cmd, ?, 0x00, 0x26` with BCD validation — see
`scripts/parse_sweep_capture.py`.

## Firmware / file transfer channel (0x92 family)

A second protocol runs on the same characteristics for firmware files
(`SendData.checkFile`, `ResolveDeviceData.checkFile`):

- Header `0x92` (`cmdCheck`), frames are **27 bytes**, CRC16 over payload.
- CRC16 polynomial `0xA001` (reflected CRC-16/MODBUS), init `0xFFFF`
  (`ResolveData.CalcCRC16`).
- `deleteFile(id)` = `92 70 00 <id:u32le> <crc16:le>` (`0x70` = 'p').
- `checkUpdateFile` / `endUpdateFile` build 27-byte frames carrying 16-byte
  chunks of a firmware file plus CRC16.
- `SEND_READ (0x77)` returns flash metadata
  (`0x35A8`, `0x0020`, `0x0FE0` — likely record count / page / remaining).
- OTA paths: **Realtek DFU** (`com.realsil.sdk.dfu`, `RtkUtils`,
  channel `rtk_ota_01`, `SET_DFU_MODE (0x47)`) for model list
  `2208A / 2208A2 / 2318 / CORE VITALS / LivLive`, and **Goodix DFU**
  (`HuiDingUtils`) for other variants.
- `libRtkAesJni.so` in the app suggests OTA images are AES-encrypted.

## Open questions

1. **0x43 GET_DAY_DATA / 0x44 GET_SLEEP_DATA / 0x17 GET_HEART_BREATH_DATA**
   remain silent — the history data instead lives in the dump commands
   0x51-0x59 / 0x5C (see above); their exact payload semantics (sleep-stage
   interval length, counter units, float fields) still need pinning down.
2. **SpO2 trigger**: a blind sweep of command ids 0x18-0x63 while worn never
   produced PLX (`0x2A5F`) traffic. The service has no Features/Spot-Check
   characteristics, so SpO2 is continuous-only; the trigger is either a
   command outside the swept range or automatic (sleep mode — the app's
   `spo2hDataAuto` strings suggest background measurement).
3. **0xF4 status byte** — success flag? Checksum scheme for a different frame
   class? Appears in acks and time payloads.
4. **`0x77` flash metadata** — needs experiments to map to a flash-read
   command (would enable a full **firmware dump for preservation** without
   entering DFU mode).
5. **User-info goal field** — writing 4 params shifted the stored goal
   (0x3D → 0x4C). The official app probably sends 5+ params.
6. **Vibrate/alert commands** — one of `0x5B` / `0x60` / `0x62` fires a
   single vibration (harmless one-shot, no persistent alarm observed).

Artifacts for further work (not redistributed in this repo — see
CONTRIBUTING.md): `libapp.so` (Dart AOT snapshot, 28 MB) and the extracted
`classes7.dex` from JCVitalPro 2.0.7.
