"""High-level client for the JStyle JCV7 band (a.k.a. Pulse / 2208A / 2318)."""

from __future__ import annotations

import asyncio
import datetime

from . import protocol
from .protocol import Command, UserInfo
from .transport import Transport


class PulseBand:
    def __init__(self, address: str):
        self.transport = Transport(address)

    async def __aenter__(self) -> "PulseBand":
        await self.transport.connect()
        return self

    async def __aexit__(self, *_exc) -> None:
        await self.transport.disconnect()

    @staticmethod
    def _expect(responses: list[bytes], cmd: int) -> bytes | None:
        for f in responses:
            if len(f) == protocol.FRAME_LEN and f[0] == cmd and protocol.is_valid(f):
                return f
        return None

    async def get_battery(self) -> int | None:
        res = await self.transport.request(protocol.build(Command.GET_BATTERY))
        f = self._expect(res, Command.GET_BATTERY)
        return f[1] if f else None

    async def get_version(self) -> bytes | None:
        res = await self.transport.request(protocol.build(Command.GET_VERSION))
        f = self._expect(res, Command.GET_VERSION)
        return bytes(f[4:8]) if f else None

    async def get_mac(self) -> str | None:
        res = await self.transport.request(protocol.build(Command.GET_MAC))
        f = self._expect(res, Command.GET_MAC)
        return ":".join(f"{b:02X}" for b in f[1:7]) if f else None

    async def get_time(self) -> datetime.datetime | None:
        res = await self.transport.request(protocol.build(Command.GET_TIME))
        f = self._expect(res, Command.GET_TIME)
        if not f:
            return None
        t = protocol.parse_time(f[1:9])
        return datetime.datetime(**{k: t[k] for k in ("year", "month", "day", "hour", "minute", "second")})

    async def set_time(self, dt: datetime.datetime | None = None) -> bool:
        res = await self.transport.request(protocol.build(Command.SET_TIME, protocol.build_time(dt)))
        f = self._expect(res, Command.SET_TIME)
        return f is not None

    async def get_user_info(self) -> UserInfo | None:
        res = await self.transport.request(protocol.build(Command.GET_USER_INFO))
        f = self._expect(res, Command.GET_USER_INFO)
        return UserInfo.parse(f[1:]) if f else None

    async def set_user_info(self, gender: int, age: int, height_cm: int, weight_kg: int, goal: int = 0) -> bool:
        params = bytes([gender & 0xFF, age & 0xFF, height_cm & 0xFF, weight_kg & 0xFF, goal & 0xFF])
        res = await self.transport.request(protocol.build(Command.SET_USER_INFO, params))
        f = self._expect(res, Command.SET_USER_INFO)
        return f is not None and f[1] == 0x00

    async def send_password(self) -> list[bytes]:
        return await self.transport.request(protocol.build(Command.SEND_PWD, protocol.PWD_PAYLOAD))

    async def send_read_trigger(self) -> list[bytes]:
        return await self.transport.request(protocol.build(Command.SEND_READ))

    async def get_sleep_activity(self, active: bool = True, wait: float = 6.0) -> list[protocol.SleepActivityPacket]:
        res = await self.transport.request(
            protocol.build(Command.GET_SLEEP_ACTIVITY, b"\x01" if active else b"\x00"), delay=wait
        )
        packets = []
        for f in res:
            if len(f) == protocol.FRAME_LEN and f[0] == Command.GET_SLEEP_ACTIVITY:
                packets.append(protocol.SleepActivityPacket(hour=f[1], value=f[2], raw=f))
        return packets

    async def get_day_data(self, index: int = 0, wait: float = 6.0) -> list[bytes]:
        return await self.transport.request(
            protocol.build(Command.GET_DAY_DATA, bytes([index & 0xFF])), delay=wait
        )

    async def get_sleep_data(self, index: int = 0, wait: float = 6.0) -> list[bytes]:
        return await self.transport.request(
            protocol.build(Command.GET_SLEEP_DATA, bytes([index & 0xFF])), delay=wait
        )

    async def get_heart_breath(self, index: int = 0, wait: float = 6.0) -> list[bytes]:
        return await self.transport.request(
            protocol.build(Command.GET_HEART_BREATH_DATA, bytes([index & 0xFF])), delay=wait
        )

    async def raw(self, cmd: int, params: bytes = b"", wait: float = 2.0) -> list[bytes]:
        return await self.transport.request(protocol.build(cmd, params), delay=wait)


async def demo(address: str) -> None:
    async with PulseBand(address) as band:
        print("battery :", await band.get_battery(), "%")
        print("version :", (await band.get_version()), "(raw bytes)")
        print("mac     :", await band.get_mac())
        now = await band.get_time()
        print("time    :", now)
        if now is None or abs((datetime.datetime.now() - now).total_seconds()) > 60:
            print("clock drift detected -> syncing")
            print("sync ok :", await band.set_time())
            print("time now:", await band.get_time())
        user = await band.get_user_info()
        print("user    :", user)
        print("sleep/activity stream:")
        for p in await band.get_sleep_activity():
            print(f"  hour {p.hour:02d}:00 value={p.value}")


if __name__ == "__main__":
    import sys

    asyncio.run(demo(sys.argv[1] if len(sys.argv) > 1 else "93633342-1CE2-A410-529D-C41D12F6F6FF"))
