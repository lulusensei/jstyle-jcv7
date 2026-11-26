"""jcv7 — command line for the JStyle JCV7 / Pulse health band."""

from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import sys

from . import protocol
from .client import PulseBand
from .transport import scan


def _pp(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


async def cmd_scan(args) -> None:
    devices = await scan(args.timeout)
    if not devices:
        print("no bands found — wake the band (button/charger) and keep phones away")
        return
    for d in devices:
        print(f"{d['address']}  rssi={d['rssi']:>4}  {d['name']}  mfr={d['manufacturer']}")


async def cmd_info(args) -> None:
    async with PulseBand(args.address) as band:
        battery = await band.get_battery()
        version = await band.get_version()
        mac = await band.get_mac()
        device_time = await band.get_time()
        user = await band.get_user_info()
        _pp({
            "battery_percent": battery,
            "version_raw": version.hex(":") if version else None,
            "mac": mac,
            "device_time": str(device_time),
            "host_time": str(datetime.datetime.now()),
            "clock_drift_seconds": (datetime.datetime.now() - device_time).total_seconds() if device_time else None,
            "user": user,
        })


async def cmd_time(args) -> None:
    async with PulseBand(args.address) as band:
        if args.sync:
            ok = await band.set_time()
            print("synced:", ok)
        print("device time:", await band.get_time())
        print("host time  :", datetime.datetime.now())


async def cmd_user(args) -> None:
    async with PulseBand(args.address) as band:
        if args.set:
            gender = 0x01 if args.gender == "male" else 0x00
            ok = await band.set_user_info(gender, args.age, args.height, args.weight)
            print("written:", ok)
        _pp(await band.get_user_info())


async def cmd_sleep(args) -> None:
    async with PulseBand(args.address) as band:
        for p in await band.get_sleep_activity(wait=args.wait):
            print(f"hour={p.hour:02d}:00 value={p.value} raw={p.raw.hex(' ')}")


async def cmd_raw(args) -> None:
    payload = bytes.fromhex(args.hex.replace(" ", ""))
    async with PulseBand(args.address) as band:
        for f in await band.transport.request(payload, delay=args.wait):
            valid = protocol.is_valid(f)
            print(("OK " if valid else "?? ") + f.hex(" "))


async def cmd_monitor(args) -> None:
    from .transport import Transport

    async with Transport(args.address) as t:
        print("listening on FFF7 — Ctrl-C to stop")
        while True:
            for f in await t.drain(1.0):
                print(protocol.is_valid(f) * "OK " + f.hex(" "))


async def cmd_report(args) -> None:
    import asyncio as _aio
    from .report import gather, render_report, decode_sleep, decode_hr5, decode_minute

    battery, version, mac, user, streams = await gather(args.address)
    sessions = decode_sleep(streams.get(0x53, b""))
    hr5 = decode_hr5(streams.get(0x55, b""))
    minute_hr = decode_minute(streams.get(0x58, b""))
    body = render_report(battery, version, mac, user, sessions, hr5, minute_hr)
    if args.mail:
        from .mailer import send_report
        import datetime as _dt
        send_report(f"JCV7 report {_dt.date.today()}", body)
        print("report emailed")
    if args.out:
        with open(args.out, "w") as f:
            f.write(body)
        print(f"report written to {args.out}")
    print(body)


def main() -> None:
    p = argparse.ArgumentParser(prog="jcv7", description="JStyle JCV7 / Pulse band CLI")
    p.add_argument("--address", "-a", help="band MAC/UUID (omit with scan)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="scan for nearby bands")
    s.add_argument("--timeout", type=float, default=10.0)
    s.set_defaults(fn=cmd_scan)

    s = sub.add_parser("info", help="battery, version, mac, time, user")
    s.set_defaults(fn=cmd_info)

    s = sub.add_parser("time", help="read or sync device clock")
    s.add_argument("--sync", action="store_true", help="set device clock to host time")
    s.set_defaults(fn=cmd_time)

    s = sub.add_parser("user", help="read or write user profile")
    s.add_argument("--set", action="store_true")
    s.add_argument("--gender", choices=["male", "female"], default="male")
    s.add_argument("--age", type=int, default=30)
    s.add_argument("--height", type=int, default=170)
    s.add_argument("--weight", type=int, default=65)
    s.set_defaults(fn=cmd_user)

    s = sub.add_parser("sleep", help="dump sleep/activity stream")
    s.add_argument("--wait", type=float, default=6.0)
    s.set_defaults(fn=cmd_sleep)

    s = sub.add_parser("raw", help="send a raw 16-byte frame (hex)")
    s.add_argument("hex")
    s.add_argument("--wait", type=float, default=2.0)
    s.set_defaults(fn=cmd_raw)

    s = sub.add_parser("report", help="harvest + decode the night, print/mail it")
    s.add_argument("--mail", action="store_true", help="send by email (needs mail config)")
    s.add_argument("--out", help="also write the report to a file")
    s.set_defaults(fn=cmd_report)

    s = sub.add_parser("monitor", help="log all notifications")
    s.set_defaults(fn=cmd_monitor)

    args = p.parse_args()
    if args.cmd != "scan" and not args.address:
        p.error("this command needs --address (run 'jcv7 scan' first)")
    asyncio.run(args.fn(args))


if __name__ == "__main__":
    main()
