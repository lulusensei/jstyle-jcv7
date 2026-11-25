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
        state = {"n": 0, "tag": "-"}
        def on_notify(ch, data):
            state["n"] += 1
            print(f"<< #{state['n']:03d} [{state['tag']}]: {data.hex(' ')}", flush=True)
        await client.start_notify(FFF7, on_notify)
        await asyncio.sleep(0.5)

        async def send(name, payload, wait=6.0):
            print(f">> {name}: {payload.hex(' ')}", flush=True)
            state["tag"] = name
            await client.write_gatt_char(FFF6, payload, response=False)
            await asyncio.sleep(wait)

        # write user profile back with same values (safe round-trip test)
        await send("SET_USERINFO(m,34,175,64)", frame(0x02, bytes([0x01, 0x22, 0xAF, 0x40])))
        await send("GET_USERINFO", frame(0x42))
        # sleep activity with false param
        await send("getSleepActivity(false)", frame(0x16, b"\x00"), wait=8)
        # day data for past week indices
        for p in (0x01, 0x02, 0x03):
            await send(f"getDayData({p})", frame(0x43, bytes([p])), wait=6)
        # heart/breath again with longer wait
        await send("getHeartBreath(0)", frame(0x17, b"\x00"), wait=10)
        print(f"--- total {state['n']} packets ---", flush=True)

asyncio.run(main())
