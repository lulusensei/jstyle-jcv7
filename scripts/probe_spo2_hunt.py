import asyncio, time
from bleak import BleakClient

ADDR = "93633342-1CE2-A410-529D-C41D12F6F6FF"
HR_MEAS = "00002a37-0000-1000-8000-00805f9b34fb"
PLX = "00002a5f-0000-1000-8000-00805f9b34fb"
FFF6 = "0000fff6-0000-1000-8000-00805f9b34fb"
FFF7 = "0000fff7-0000-1000-8000-00805f9b34fb"

def frame(cmd, params=b""):
    f = bytearray(16)
    f[0] = cmd
    f[1:1+len(params)] = params
    f[15] = sum(f) & 0xFF
    return bytes(f)

async def main():
    async with BleakClient(ADDR, timeout=15) as client:
        print("connected — keep the band on your wrist", flush=True)
        t0 = time.time()
        state = {"tag": "-", "hr": 0, "plx": 0, "fff7": 0}
        def tag(t): state["tag"] = t
        def hr_cb(ch, d):
            state["hr"] += 1
            bpm = d[1] if not (d[0] & 1) else int.from_bytes(d[1:3], "little")
            print(f"  [{time.time()-t0:6.1f}s] HR {bpm} bpm", flush=True)
        def plx_cb(ch, d):
            state["plx"] += 1
            print(f"  [{time.time()-t0:6.1f}s] *** PLX RESPONSE: {d.hex(' ')}", flush=True)
        def f7_cb(ch, d):
            state["fff7"] += 1
            print(f"  [{time.time()-t0:6.1f}s] FFF7 after [{state['tag']}]: {d.hex(' ')}", flush=True)
        await client.start_notify(HR_MEAS, hr_cb)
        await client.start_notify(PLX, plx_cb)
        await client.start_notify(FFF7, f7_cb)
        await asyncio.sleep(1)

        async def try_cmd(name, payload, wait=2.5):
            tag(name)
            print(f">> {name}: {payload.hex(' ')}", flush=True)
            await client.write_gatt_char(FFF6, payload, response=False)
            await asyncio.sleep(wait)

        # Plan A: targeted candidates
        await try_cmd("0x11 param=02", frame(0x11, b"\x02"))
        await try_cmd("0x11 param=03", frame(0x11, b"\x03"))
        await try_cmd("0x17 (heart-breath) p0", frame(0x17, b"\x00"), wait=4)
        await try_cmd("0x16 p2", frame(0x16, b"\x02"), wait=4)
        await try_cmd("0x77 p1 (setRAED1)", frame(0x77, b"\x01"), wait=4)
        await try_cmd("0x77 p2 (setRAED2)", frame(0x77, b"\x02"), wait=4)

        # Plan B: careful blind sweep of unknown command ids, param 0
        for cmd in list(range(0x18, 0x22)) + [0x24, 0x25, 0x26, 0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D, 0x2F] + list(range(0x30, 0x3C)) + [0x3E, 0x3F, 0x40, 0x45, 0x46] + list(range(0x48, 0x64)):
            if state["plx"] > 0:
                break
            await try_cmd(f"probe 0x{cmd:02X}", frame(cmd), wait=1.2)

        print(f"--- totals: HR={state['hr']} PLX={state['plx']} FFF7={state['fff7']} ---", flush=True)

asyncio.run(main())
