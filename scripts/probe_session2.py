import asyncio, sys, datetime
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

def bcd(v: int) -> int:
    return ((v // 10) << 4) | (v % 10)

async def main():
    async with BleakClient(ADDR, timeout=15) as client:
        print("connected:", flush=True)
        log = []
        def on_notify(ch, data):
            log.append((ch.uuid, data))
            print(f"<< {ch.uuid[4:8]}: {data.hex(' ')}", flush=True)
        def on_hr(ch, data):
            flags = data[0]
            bpm = int.from_bytes(data[1:3], "little") if flags & 1 else data[1]
            print(f"<< HR: {bpm} bpm", flush=True)

        await client.start_notify(FFF7, on_notify)
        await client.start_notify(HR_MEAS, on_hr)
        await asyncio.sleep(0.5)

        async def send(name, payload, wait=1.0):
            print(f">> {name}: {payload.hex(' ')}", flush=True)
            await client.write_gatt_char(FFF6, payload, response=False)
            await asyncio.sleep(wait)

        # 1. sync clock to now (BCD)
        now = datetime.datetime.now()
        ts = bytes([bcd(now.year % 100), bcd(now.month), bcd(now.day),
                    bcd(now.hour), bcd(now.minute), bcd(now.second), bcd(now.isoweekday() % 7)])
        await send("SET_TIME", frame(0x01, ts))

        # 2. read back time
        await send("GET_TIME", frame(0x41))

        # 3. MAC
        await send("GET_MAC", frame(0x22))

        # 4. user info
        await send("GET_USERINFO", frame(0x42))

        # 5. enable continuous HR
        await send("ENABLE_ACTIVITY_HEART(on)", frame(0x11, b"\x01"), wait=1.5)

        # 6. pull day data / sleep / heart-breath for day 0
        await send("GET_DAY_DATA(0)", frame(0x43, b"\x00"))
        await send("GET_SLEEP_DATA(0)", frame(0x44, b"\x00"))
        await send("GET_HEART_BREATH(0)", frame(0x17, b"\x00"))

        print("listening 15s for HR stream ...", flush=True)
        await asyncio.sleep(15)

        print(f"--- {len(log)} FFF7 notifications total ---", flush=True)

asyncio.run(main())
