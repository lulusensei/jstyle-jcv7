import asyncio, sys
from bleak import BleakClient

ADDR = sys.argv[1] if len(sys.argv) > 1 else "93633342-1CE2-A410-529D-C41D12F6F6FF"
FFF6_WRITE = "0000fff6-0000-1000-8000-00805f9b34fb"
FFF7_NOTIFY = "0000fff7-0000-1000-8000-00805f9b34fb"

def frame(cmd: int, params: bytes = b"") -> bytes:
    f = bytearray(16)
    f[0] = cmd
    f[1:1+len(params)] = params
    f[15] = sum(f) & 0xFF
    return bytes(f)

def frame_short(cmd: int, params: bytes = b"") -> bytes:
    f = bytearray()
    f.append(cmd)
    f += params
    f.append(sum(f) & 0xFF)
    return bytes(f)

async def main():
    async with BleakClient(ADDR, timeout=15) as client:
        print("connected:", client.is_connected, flush=True)
        got = asyncio.Event()
        log = []

        def on_notify(ch, data):
            log.append(data)
            print(f"<< FFF7: {data.hex(' ')}", flush=True)

        await client.start_notify(FFF7_NOTIFY, on_notify)
        await asyncio.sleep(1)

        tests = [
            ("battery16", frame(0x13)),
            ("battery_short", frame_short(0x13)),
            ("version16", frame(0x27)),
            ("version_short", frame_short(0x27)),
            ("gettime16", frame(0x41)),
            ("gettime_short", frame_short(0x41)),
        ]
        for name, payload in tests:
            print(f">> {name}: {payload.hex(' ')}", flush=True)
            try:
                await client.write_gatt_char(FFF6_WRITE, payload, response=False)
            except Exception as e:
                print(f"   write failed: {e}", flush=True)
            await asyncio.sleep(1.2)

        print("--- summary ---", flush=True)
        print(f"total notifications: {len(log)}", flush=True)
        try:
            await client.stop_notify(FFF7_NOTIFY)
        except Exception:
            pass

asyncio.run(main())
