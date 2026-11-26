"""Daily report: harvest history, decode the night, render text/markdown.

Usage: python3 -m jstyle_jcv7.report [--address ADDR] [--out FILE]
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
from collections import Counter

from .client import PulseBand
from .transport import Transport


def un_bcd(b):
    hi, lo = (b >> 4) & 0xF, b & 0xF
    if hi > 9 or lo > 9:
        return None
    return hi * 10 + lo


def try_dt(b, off, with_seconds):
    n = 6 if with_seconds else 5
    v = [un_bcd(b[off + i]) for i in range(n)]
    if any(x is None for x in v):
        return None
    yy, mo, dd, hh, mi = v[:5]
    ss = v[5] if with_seconds else 0
    if not (20 <= yy <= 40 and 1 <= mo <= 12 and 1 <= dd <= 31 and hh <= 23 and mi <= 59 and ss <= 59):
        return None
    return datetime.datetime(2000 + yy, mo, dd, hh, mi, ss)


def split_stream(stream: bytes, cmd: int):
    best = None
    for with_sec in (False, True):
        dtlen = 6 if with_sec else 5
        starts = [i for i in range(len(stream) - dtlen - 2)
                  if stream[i] == cmd and try_dt(stream, i + 3, with_sec)]
        if len(starts) < 2:
            continue
        gaps = Counter(b - a for a, b in zip(starts, starts[1:]) if 2 < b - a < 300)
        if not gaps:
            continue
        stride, freq = gaps.most_common(1)[0]
        if best is None or freq > best[0]:
            best = (freq, with_sec, dtlen, starts, stride)
    if best is None:
        return []
    _, with_sec, dtlen, starts, stride = best
    recs, pos = [], starts[0]
    while pos + 3 + dtlen <= len(stream) and stream[pos] == cmd:
        dt = try_dt(stream, pos + 3, with_sec)
        if dt is None:
            break
        recs.append((int.from_bytes(stream[pos + 1:pos + 3], "little"), dt,
                     stream[pos + 3 + dtlen:pos + stride]))
        pos += stride
    return recs


def decode_sleep(stream: bytes) -> list[dict]:
    sessions = []
    for seq, dt, p in split_stream(stream, 0x53):
        if not p:
            continue
        covered = p[0]
        stages = p[1:]
        stages = [s for s in stages if s in (0, 1, 2, 3, 4, 5)]
        sessions.append({"start": dt, "covered": covered, "stages": stages})
    return sessions


def decode_hr5(stream: bytes) -> list[tuple]:
    out = []
    for seq, dt, p in split_stream(stream, 0x55):
        v = p[0] if p else None
        if v and 40 <= v <= 160:
            out.append((dt, v))
    return sorted(out)


def decode_minute(stream: bytes) -> list[tuple]:
    out = []
    for seq, dt, p in split_stream(stream, 0x58):
        if len(p) > 18 and 40 <= p[18] <= 140:
            out.append((dt, p[18]))
    return sorted(out)


STAGE_NAMES = {0: "awake", 1: "deep", 2: "light", 3: "REM", 4: "restless", 5: "in-bed"}


def render_report(battery, version, mac, user, sessions, hr5, minute_hr) -> str:
    lines = ["# JCV7 daily report", ""]
    lines.append(f"- Battery: {battery}%")
    lines.append(f"- Firmware: {version.hex(':') if version else '?'}")
    lines.append(f"- MAC: {mac}")
    if user:
        lines.append(f"- Profile: {user.gender}, {user.age}y, {user.height_cm}cm, {user.weight_kg}kg")
    lines.append("")

    if sessions:
        lines.append("## Sleep")
        all_stages = []
        for s in sessions:
            all_stages += s["stages"]
            c = Counter(STAGE_NAMES.get(v, str(v)) for v in s["stages"])
            lines.append(f"- Block {s['start']:%m-%d %H:%M}: " + ", ".join(f"{k} {v}min" for k, v in sorted(c.items())))
        if all_stages:
            c = Counter(STAGE_NAMES.get(v, str(v)) for v in all_stages)
            total_sleep = sum(v for k, v in c.items() if k in ("deep", "light", "REM"))
            lines.append(f"- **Total tracked: {len(all_stages)} min, sleep ~{total_sleep} min** — "
                         + ", ".join(f"{k} {v}min" for k, v in sorted(c.items())))
        lines.append("")

    if hr5 or minute_hr:
        lines.append("## Heart rate")
        pts = hr5 or minute_hr
        vals = [v for _, v in pts]
        lines.append(f"- {len(pts)} samples, min {min(vals)}, avg {sum(vals)//len(vals)}, max {max(vals)} bpm")
        by_hour = {}
        for dt, v in pts:
            by_hour.setdefault(dt.strftime("%m-%d %H"), []).append(v)
        for hour in sorted(by_hour):
            v = by_hour[hour]
            avg = sum(v) // len(v)
            bar = "▁▂▃▄▅▆▇█"[min(7, max(0, (avg - 45) * 8 // 60))]
            lines.append(f"- {hour}:00  avg {avg:3d}  min {min(v):3d}  max {max(v):3d}  {bar}")
        lines.append("")

    now = datetime.datetime.now()
    lines.append(f"_Generated {now:%Y-%m-%d %H:%M} by jstyle_jcv7 — no cloud involved._")
    return "\n".join(lines)


async def gather(address: str):
    async with PulseBand(address) as band:
        battery = await band.get_battery()
        version = await band.get_version()
        mac = await band.get_mac()
        user = await band.get_user_info()

        async with Transport(address) as t:
            streams = {}
            for cmd in (0x53, 0x55, 0x58):
                before = len(t.notifications)
                await t.write(bytes([cmd]) + bytes(14) + bytes([cmd]))
                await asyncio.sleep(6)
                blob = b"".join(list(t.notifications)[before:])
                streams[cmd] = blob
    return battery, version, mac, user, streams


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--address", required=True)
    ap.add_argument("--out", help="write report to file instead of stdout")
    args = ap.parse_args()

    battery, version, mac, user, streams = await gather(args.address)
    sessions = decode_sleep(streams.get(0x53, b""))
    hr5 = decode_hr5(streams.get(0x55, b""))
    minute_hr = decode_minute(streams.get(0x58, b""))
    report = render_report(battery, version, mac, user, sessions, hr5, minute_hr)
    if args.out:
        with open(args.out, "w") as f:
            f.write(report)
        print(f"report written to {args.out}")
    else:
        print(report)


if __name__ == "__main__":
    asyncio.run(main())
