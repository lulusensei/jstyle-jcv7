"""Harvest all history streams from the band and save raw captures.

Usage: python3 scripts/harvest_history.py [address]
Writes captures/harvest-<timestamp>/<cmd>.bin for each dump command.
"""
import asyncio, os, sys, time, datetime
from bleak import BleakClient

ADDR = sys.argv[1] if len(sys.argv) > 1 else "93633342-1CE2-A410-529D-C41D12F6F6FF"
FFF6 = "0000fff6-0000-1000-8000-00805f9b34fb"
FFF7 = "0000fff7-0000-1000-8000-00805f9b34fb"
HR_MEAS = "00002a37-0000-1000-8000-00805f9b34fb"

DUMP_CMDS = [0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x58, 0x59, 0x5C]

def frame(cmd: int, params: bytes = b"") -> bytes:
    f = bytearray(16)
    f[0] = cmd
    f[1:1 + len(params)] = params
    f[15] = sum(f) & 0xFF
    return bytes(f)

async def main():
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = os.path.join(os.path.dirname(__file__), "..", "captures", f"harvest-{stamp}")
    os.makedirs(outdir, exist_ok=True)

    async with BleakClient(ADDR, timeout=25) as client:
        print("connected", flush=True)
        buf = {c: bytearray() for c in DUMP_CMDS}
        last_rx = [time.time()]

        def on_notify(ch, data):
            last_rx[0] = time.time()
            b = bytes(data)
            if b and b[0] in buf:
                buf[b[0]].extend(b)

        hr_count = [0]
        def on_hr(ch, data):
            hr_count[0] += 1

        await client.start_notify(FFF7, on_notify)
        await client.start_notify(HR_MEAS, on_hr)

        for cmd in DUMP_CMDS:
            print(f">> requesting dump 0x{cmd:02X} ...", flush=True)
            before = len(buf[cmd])
            await client.write_gatt_char(FFF6, frame(cmd), response=False)
            # stream until 4s of silence or 45s cap
            deadline = time.time() + 45
            while time.time() < deadline:
                await asyncio.sleep(1)
                if time.time() - last_rx[0] > 4 and len(buf[cmd]) > before:
                    break
            got = len(buf[cmd]) - before
            print(f"   got {got} bytes", flush=True)

        for cmd, data in buf.items():
            path = os.path.join(outdir, f"{cmd:02x}.bin")
            with open(path, "wb") as f:
                f.write(data)
            print(f"saved {path} ({len(data)} bytes)", flush=True)
        with open(os.path.join(outdir, "meta.txt"), "w") as f:
            f.write(f"harvested {datetime.datetime.now().isoformat()}\n")
            f.write(f"hr notifications during harvest: {hr_count[0]}\n")
    print("done — run scripts/parse_sweep_capture.py style analysis next", flush=True)

asyncio.run(main())
