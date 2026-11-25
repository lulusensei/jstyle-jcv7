import asyncio, sys, time
from bleak import BleakClient

ADDR = sys.argv[1] if len(sys.argv) > 1 else "93633342-1CE2-A410-529D-C41D12F6F6FF"
FFF6 = "0000fff6-0000-1000-8000-00805f9b34fb"
FFF7 = "0000fff7-0000-1000-8000-00805f9b34fb"
HR_MEAS = "00002a37-0000-1000-8000-00805f9b34fb"

def frame(cmd: int, params: bytes = b"") -> bytes:
    f = bytearray(16)
    f[0] = cmd
    f[1:1+len(params)] = params
    f[15] = sum(f) & 0xFF
    return bytes(f)

async def main():
    async with BleakClient(ADDR, timeout=15) as client:
        print("connected", flush=True)
        state = {"n": 0, "last_cmd": "connect"}
        t0 = time.time()
        def on_notify(ch, data):
            state["n"] += 1
            dt = time.time() - t0
            print(f"<< {dt:6.2f}s #{state['n']:03d} after[{state['last_cmd']}]: {data.hex(' ')}", flush=True)
        hr_seen = []
        def on_hr(ch, data):
            flags = data[0]
            bpm = int.from_bytes(data[1:3], "little") if flags & 1 else data[1]
            hr_seen.append(bpm)
            print(f"<< HR: {bpm} bpm", flush=True)
        await client.start_notify(FFF7, on_notify)
        await client.start_notify(HR_MEAS, on_hr)
        await asyncio.sleep(0.5)

        async def send(name, payload, wait=8.0):
            print(f">> {name}: {payload.hex(' ')}", flush=True)
            state["last_cmd"] = name
            await client.write_gatt_char(FFF6, payload, response=False)
            await asyncio.sleep(wait)

        await send("getDayData(0)", frame(0x43, b"\x00"))
        await send("getDayData(1)", frame(0x43, b"\x01"))
        await send("getSleepData(0)", frame(0x44, b"\x00"))
        await send("getHeartBreath(0)", frame(0x17, b"\x00"))
        await send("getSleepActivity(true)", frame(0x16, b"\x01"), wait=10)
        await send("enableActivityHeart(true)", frame(0x11, b"\x01"), wait=20)
        print(f"--- total {state['n']} packets, HR samples: {hr_seen} ---", flush=True)

asyncio.run(main())
