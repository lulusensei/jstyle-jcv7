import asyncio, sys
from bleak import BleakClient

ADDR = sys.argv[1] if len(sys.argv) > 1 else "93633342-1CE2-A410-529D-C41D12F6F6FF"
FFF6 = "0000fff6-0000-1000-8000-00805f9b34fb"
FFF7 = "0000fff7-0000-1000-8000-00805f9b34fb"

def frame(cmd: int, params: bytes = b"") -> bytes:
    f = bytearray(16)
    f[0] = cmd
    f[1:1+len(params)] = params
    f[15] = sum(f) & 0xFF
    return bytes(f)

async def main():
    async with BleakClient(ADDR, timeout=15) as client:
        print("connected", flush=True)
        count = [0]
        def on_notify(ch, data):
            count[0] += 1
            print(f"<< #{count[0]:03d} {data.hex(' ')}", flush=True)
        await client.start_notify(FFF7, on_notify)
        await asyncio.sleep(0.5)

        async def send(name, payload, wait=1.5):
            print(f">> {name}: {payload.hex(' ')}", flush=True)
            await client.write_gatt_char(FFF6, payload, response=False)
            await asyncio.sleep(wait)

        # password auth attempt (from sendPwd bytecode: 3C 63 4B 3C 34 26 2D)
        await send("sendPwd", frame(0x3C, bytes([0x63, 0x4B, 0x3C, 0x34, 0x26, 0x2D])))
        # show version on display
        await send("sendShowVersion", frame(0x63, bytes([0x00, 0x11, 0x00, 0x11, 0x00])))
        # read trigger
        await send("sendRAED", frame(0x77))
        # day data with param variations
        for p in (0x00, 0x01, 0x02):
            await send(f"getDayData({p})", frame(0x43, bytes([p])))
        for p in (0x00, 0x01):
            await send(f"getSleepData({p})", frame(0x44, bytes([p])))
            await send(f"getHeartBreath({p})", frame(0x17, bytes([p])))
        # bed/turnover (device-family extras)
        await send("getBedUpTime(1)", frame(0x14, b"\x01"))
        await send("getTurnOver(1)", frame(0x15, b"\x01"))
        await send("getSleepActivity(true)", frame(0x16, b"\x01"))
        # hr again
        await send("enableActivityHeart(true)", frame(0x11, b"\x01"))
        await send("enableActivityHeart(false)", frame(0x11, b"\x00"))
        # factory reset probe? NO - skip destructive. MCU restart skip.
        print(f"--- done, {count[0]} notifications ---", flush=True)

asyncio.run(main())
