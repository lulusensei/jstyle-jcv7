"""Frame encoding and decoding for the JStyle JCV7 BLE protocol (service FFF0).

Protocol facts established by static analysis of the JCVitalPro Android app
(classes7.dex, io/flutter/plugins/SendData) and confirmed against live hardware:

- Commands are written to characteristic FFF6 (write-without-response).
- Responses arrive as notifications on FFF7.
- Every frame is exactly 16 bytes: command byte, parameters, zero padding,
  and a trailing checksum equal to the byte-sum of bytes 0..14 mod 256.
- The band echoes the command byte as byte 0 of the response frame.
"""

from __future__ import annotations

import dataclasses
import datetime

FRAME_LEN = 16
CHECKSUM_INDEX = 15


class Command:
    """Command bytes from SendData (decompiled from JCVitalPro 2.0.7)."""

    SET_TIME = 0x01
    SET_USER_INFO = 0x02
    SET_DEVICE_ID = 0x05
    DISABLE_ANCS = 0x03  # sent once by the app right after subscribing
    ENABLE_ACTIVITY_HEART = 0x11
    SET_FACTORY = 0x12
    GET_BED_UP_TIME = 0x14
    GET_TURNOVER_DATA = 0x15
    GET_SLEEP_ACTIVITY = 0x16
    GET_HEART_BREATH_DATA = 0x17
    GET_BATTERY = 0x13
    GET_MAC = 0x22
    GET_VERSION = 0x27
    SET_MCU_RESET = 0x2E
    SEND_PWD = 0x3C
    SET_NAME = 0x3D
    GET_TIME = 0x41
    GET_USER_INFO = 0x42
    GET_DAY_DATA = 0x43
    GET_SLEEP_DATA = 0x44
    SET_DFU_MODE = 0x47
    SEND_READ = 0x77
    SHOW_VERSION = 0x63


# Hardcoded pairing payload used by the official app (sendPwd).
PWD_PAYLOAD = bytes([0x63, 0x4B, 0x3C, 0x34, 0x26, 0x2D])


def checksum(frame: bytearray) -> int:
    """Additive checksum used by the protocol: byte-sum of 0..14 mod 256."""
    return sum(frame[:CHECKSUM_INDEX]) & 0xFF


def build(cmd: int, params: bytes = b"") -> bytes:
    """Build a 16-byte command frame."""
    if len(params) > FRAME_LEN - 2:
        raise ValueError("too many params for one frame")
    f = bytearray(FRAME_LEN)
    f[0] = cmd
    f[1 : 1 + len(params)] = params
    f[CHECKSUM_INDEX] = checksum(f)
    return bytes(f)


def is_valid(frame: bytes) -> bool:
    return len(frame) == FRAME_LEN and frame[CHECKSUM_INDEX] == checksum(bytearray(frame))


def bcd(v: int) -> int:
    return ((v // 10) << 4) | (v % 10)


def un_bcd(b: int) -> int:
    return ((b >> 4) & 0xF) * 10 + (b & 0xF)


def build_time(dt: datetime.datetime | None = None) -> bytes:
    """BCD-encoded timestamp: yy MM dd HH mm ss weekday (Mon=1..Sun=0)."""
    dt = dt or datetime.datetime.now()
    return bytes([
        bcd(dt.year % 100),
        bcd(dt.month),
        bcd(dt.day),
        bcd(dt.hour),
        bcd(dt.minute),
        bcd(dt.second),
        bcd(dt.isoweekday() % 7),
    ])


def parse_time(payload: bytes) -> dict:
    """Parse a GET_TIME response payload (bytes 1..8)."""
    return {
        "year": 2000 + un_bcd(payload[0]),
        "month": un_bcd(payload[1]),
        "day": un_bcd(payload[2]),
        "hour": un_bcd(payload[3]),
        "minute": un_bcd(payload[4]),
        "second": un_bcd(payload[5]),
        "weekday": payload[6],
        "flag": payload[7],  # observed 0xf4 on every read; meaning unknown
    }


@dataclasses.dataclass
class UserInfo:
    gender: str
    age: int
    height_cm: int
    weight_kg: int
    goal: int
    user_id: str

    @classmethod
    def parse(cls, payload: bytes) -> "UserInfo":
        # Observed: 42 01 22 AF 40 4C 38 38 38 38 38 38
        # [1] gender (0x01 male), [2] age, [3] height, [4] weight,
        # [5] goal (unknown unit, changes on SET_USER_INFO), [6..] user id ascii
        return cls(
            gender="male" if payload[0] == 1 else "female",
            age=payload[1],
            height_cm=payload[2],
            weight_kg=payload[3],
            goal=payload[4],
            user_id=payload[5:11].decode("ascii", "replace").strip("\x00 "),
        )


@dataclasses.dataclass
class SleepActivityPacket:
    """One packet of the GET_SLEEP_ACTIVITY (0x16) multi-packet stream.

    Observed stream: 16 05 00, 16 06 00, 16 07 01, 16 08 01 — best current
    interpretation is [cmd, hour_of_day, active_flag]; semantics are still
    being pinned down (see docs/PROTOCOL.md open questions).
    """

    hour: int
    value: int
    raw: bytes
