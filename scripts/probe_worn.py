import asyncio, sys, time
from bleak import BleakClient

ADDR = "93633342-1CE2-A410-529D-C41D12F6F6FF"
HR_MEAS = "00002a37-0000-1000-8000-00805f9b34fb"
HR_LOC = "00002a38-0000-1000-8000-00805f9b34fb"
PLX_SPOT = "00002a5f-0000-1000-8000-00805f9b34fb"
BAT = "00002a19-0000-1000-8000-00805f9b34fb"
FFF7 = "0000fff7-0000-1000-8000-00805f9b34fb"

async def main():
    async with BleakClient(ADDR, timeout=15) as client:
        print("connected", flush=True)
        try:
            loc = await client.read_gatt_char(HR_LOC)
            print(f"sensor location: {loc.hex()} (0x02=wrist? value={loc[0] if loc else '?'})", flush=True)
        except Exception as e:
            print(f"sensor location read failed: {e}", flush=True)
        try:
            bat = await client.read_gatt_char(BAT)
            print(f"battery: {bat[0]}%", flush=True)
        except Exception as e:
            print(f"battery read failed: {e}", flush=True)

        t0 = time.time()
        counts = {"hr": 0, "spo2": 0, "fff7": 0}
        def hr_cb(ch, data):
            flags = data[0]
            bpm = int.from_bytes(data[1:3], "little") if flags & 1 else data[1]
            counts["hr"] += 1
            print(f"[{time.time()-t0:6.1f}s] HR: {bpm} bpm  (raw {data.hex(' ')})", flush=True)
        def plx_cb(ch, data):
            counts["spo2"] += 1
            print(f"[{time.time()-t0:6.1f}s] PLX: {data.hex(' ')}", flush=True)
        def fff7_cb(ch, data):
            counts["fff7"] += 1
            print(f"[{time.time()-t0:6.1f}s] FFF7: {data.hex(' ')}", flush=True)

        await client.start_notify(HR_MEAS, hr_cb)
        await client.start_notify(PLX_SPOT, plx_cb)
        await client.start_notify(FFF7, fff7_cb)
        print("listening 30s — keep the band snug and still", flush=True)
        await asyncio.sleep(30)
        print(f"--- totals: HR={counts['hr']} PLX={counts['spo2']} FFF7={counts['fff7']} ---", flush=True)

asyncio.run(main())
