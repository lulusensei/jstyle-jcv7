"""Decode harvest captures: minute log, sleep sessions, hourly activity.

Usage: python3 scripts/parse_harvest.py captures/harvest-20261126-084527
"""
import os, sys, glob
from datetime import datetime, timedelta

def un_bcd(b):
    hi, lo = (b >> 4) & 0xF, b & 0xF
    if hi > 9 or lo > 9:
        return None
    return hi * 10 + lo

def valid_dt(b, off):
    if b[off] != 0x26:
        return None
    v = [un_bcd(b[off + i]) for i in range(1, 7)]
    if any(x is None for x in v):
        return None
    yy, mo, dd, hh, mi, ss = v
    if not (1 <= mo <= 12 and 1 <= dd <= 31 and hh <= 23 and mi <= 59 and ss <= 59):
        return None
    return datetime(2000 + yy, mo, dd, hh, mi, ss)

def split_stream(stream, cmd):
    """Split concatenated records with envelope [cmd][seq:2][00][dt:7][payload]."""
    starts = [i for i in range(len(stream) - 11)
              if stream[i] == cmd and valid_dt(stream, i + 3) is not None]
    if not starts:
        return []
    gaps = {}
    for a, b2 in zip(starts, starts[1:]):
        if 10 < b2 - a < 300:
            gaps[b2 - a] = gaps.get(b2 - a, 0) + 1
    if not gaps:
        stride = len(stream) - starts[0]
    else:
        stride = max(gaps, key=gaps.get)
    recs, pos = [], starts[0]
    while pos + 11 <= len(stream) and stream[pos] == cmd:
        dt = valid_dt(stream, pos + 3)
        if dt is None:
            break
        recs.append((int.from_bytes(stream[pos+1:pos+3], "little"), dt,
                     stream[pos+11:pos+stride]))
        pos += stride
    return recs

def decode_58(recs):
    """Minute log: payload = 13B + c0 [state] [has_hr] [hr] [steps:2?] ..."""
    print(f"\n=== 0x58 minute log: {len(recs)} records ===")
    hrs, times = [], []
    for seq, dt, p in recs:
        if len(p) >= 7 and p[13] == 0xC0:
            has_hr, hr = p[15], p[16]
            if has_hr in (1,) and hr:
                hrs.append(hr)
                times.append(dt)
    if hrs:
        lo, hi = min(hrs), max(hrs)
        avg = sum(hrs) / len(hrs)
        print(f"  HR samples: {len(hrs)}  range {lo}-{hi}  avg {avg:.0f} bpm")
        # hourly summary
        by_hour = {}
        for t, h in zip(times, hrs):
            by_hour.setdefault(t.strftime("%m-%d %H"), []).append(h)
        for hour in sorted(by_hour):
            v = by_hour[hour]
            print(f"  {hour}:00  n={len(v):3d}  min={min(v):3d} avg={sum(v)//len(v):3d} max={max(v):3d}  " + "▁▂▃▅▆▇"[min(5, (sum(v)//len(v) - 40) // 10 if sum(v)//len(v) > 40 else 0)])
    # show 3 raw samples
    for seq, dt, p in recs[:2] + recs[-1:]:
        print(f"  seq={seq} {dt} payload={p.hex(' ')}")

def decode_53(recs):
    """Sleep sessions."""
    print(f"\n=== 0x53 sleep sessions: {len(recs)} records ===")
    from collections import Counter
    for seq, dt, p in recs:
        dur = int.from_bytes(p[0:2], "big") if len(p) >= 2 else 0
        stages = p[2:]
        c = Counter(stages)
        end = dt + timedelta(minutes=dur) if dur else "?"
        print(f"  session {dt} -> +{dur}min ({end})")
        print(f"    stage histogram: {dict(sorted(c.items()))}")
        print(f"    stages: {''.join(str(s) for s in stages[:80])}")
        print(f"    raw head: {p[:24].hex(' ')}")

def decode_52(recs):
    print(f"\n=== 0x52 hourly activity: {len(recs)} records ===")
    for seq, dt, p in recs[:6]:
        print(f"  {dt}  payload={p.hex(' ')}")

def decode_generic(name, recs):
    print(f"\n=== 0x{name:02X}: {len(recs)} records ===")
    for seq, dt, p in recs[:5]:
        print(f"  seq={seq} {dt} payload={p.hex(' ')}")

def main():
    base = sys.argv[1]
    data = {}
    for f in glob.glob(os.path.join(base, "*.bin")):
        cmd = int(os.path.basename(f)[:2], 16)
        data[cmd] = open(f, "rb").read()

    for cmd in sorted(data):
        stream = data[cmd]
        if not stream:
            continue
        recs = split_stream(stream, cmd)
        if cmd == 0x58:
            decode_58(recs)
        elif cmd == 0x53:
            decode_53(recs)
        elif cmd == 0x52:
            decode_52(recs)
        else:
            decode_generic(cmd, recs)

main()
