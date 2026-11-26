"""Decode harvest captures v2: flexible envelope, stride from modal gaps,
HR-field correlation against the 0x55 five-minute HR history.

Usage: python3 scripts/parse_harvest2.py captures/harvest-YYYYMMDD-HHMMSS
"""
import os, sys, glob
from datetime import datetime, timedelta
from collections import Counter

def un_bcd(b):
    hi, lo = (b >> 4) & 0xF, b & 0xF
    if hi > 9 or lo > 9:
        return None
    return hi * 10 + lo

def try_dt(b, off, with_seconds):
    """Date starts at `off`: BCD yy MM dd HH mm [ss] — consumes exactly 5 or 6 bytes."""
    n = 6 if with_seconds else 5
    v = [un_bcd(b[off + i]) for i in range(n)]
    if any(x is None for x in v):
        return None
    yy, mo, dd, hh, mi = v[0], v[1], v[2], v[3], v[4]
    ss = v[5] if with_seconds else 0
    if not (20 <= yy <= 40 and 1 <= mo <= 12 and 1 <= dd <= 31 and hh <= 23 and mi <= 59 and ss <= 59):
        return None
    return datetime(2000 + yy, mo, dd, hh, mi, ss)

def analyze(stream, cmd):
    best = None
    for with_sec in (False, True):
        dtlen = 7 if with_sec else 6
        starts = [i for i in range(len(stream) - dtlen - 2)
                  if stream[i] == cmd and try_dt(stream, i + 3, with_sec)]
        if len(starts) < 2:
            continue
        gaps = Counter(b - a for a, b in zip(starts, starts[1:]) if 2 < b - a < 200)
        if not gaps:
            continue
        stride, freq = gaps.most_common(1)[0]
        score = freq
        if best is None or score > best[0]:
            best = (score, with_sec, dtlen, starts, stride)
    if best is None:
        return None
    _, with_sec, dtlen, starts, stride = best
    recs, pos = [], starts[0]
    while pos + 3 + dtlen <= len(stream) and stream[pos] == cmd:
        dt = try_dt(stream, pos + 3, with_sec)
        if dt is None:
            break
        recs.append((int.from_bytes(stream[pos+1:pos+3], "little"), dt,
                     stream[pos+3+dtlen:pos+stride]))
        pos += stride
    return recs, stride

def hr_series_from_55(recs):
    # 5-min log: payload may be [type][value] or just [value] depending on dt parse
    out = {}
    for seq, dt, p in recs:
        v = p[1] if len(p) >= 2 else (p[0] if p else None)
        if v is not None and 40 <= v <= 160:
            out[dt] = v
    return out

def main():
    base = sys.argv[1]
    streams = {}
    for f in glob.glob(os.path.join(base, "*.bin")):
        cmd = int(os.path.basename(f)[:2], 16)
        streams[cmd] = open(f, "rb").read()

    results = {}
    for cmd in sorted(streams):
        r = analyze(streams[cmd], cmd)
        results[cmd] = r
        if r is None:
            print(f"0x{cmd:02X}: no records ({len(streams[cmd])} bytes)")
            continue
        recs, stride = r
        print(f"0x{cmd:02X}: {len(recs)} records, stride={stride}, "
              f"{recs[0][1]} .. {recs[-1][1]}")

    # 0x55: 5-min HR history
    if results.get(0x55):
        recs, _ = results[0x55]
        series = hr_series_from_55(recs)
        print(f"\n--- 0x55 5-minute HR history ({len(series)} pts) ---")
        for dt in sorted(series):
            v = series[dt]
            bar = "▁▂▃▄▅▆▇█"[min(7, max(0, (v - 45) * 8 // 60))]
            print(f"  {dt:%m-%d %H:%M}  {v:3d} {bar}")

    # 0x58: correlate payload bytes with 5-min HR
    if results.get(0x58) and results.get(0x55):
        recs, stride = results[0x58]
        hr_ref = hr_series_from_55(results[0x55][0])
        plen = min(len(r[2]) for r in recs)
        best_pos, best_hits = None, -1
        for pos in range(plen):
            hits = 0
            for seq, dt, p in recs:
                ref = None
                for dref, v in hr_ref.items():
                    delta = (dt - dref).total_seconds()
                    if 0 <= delta <= 150:
                        ref = v
                        break
                if ref and abs(p[pos] - ref) <= 4:
                    hits += 1
            if hits > best_hits:
                best_hits, best_pos = hits, pos
        print(f"\n--- 0x58 minute log ({len(recs)} records, payload {plen}B) ---")
        print(f"  best HR-correlated payload byte: offset {best_pos} "
              f"({best_hits}/{len(recs)} matches vs 5-min HR)")
        if best_pos is not None:
            vals = [(dt, p[best_pos]) for seq, dt, p in recs if len(p) > best_pos]
            vals.sort(key=lambda x: x[0])
            by_hour = {}
            for dt, v in vals:
                if 40 <= v <= 140:
                    by_hour.setdefault(dt.strftime("%m-%d %H"), []).append(v)
            for hour in sorted(by_hour):
                v = by_hour[hour]
                avg = sum(v) // len(v)
                bar = "▁▂▃▄▅▆▇█"[min(7, max(0, (avg - 45) * 8 // 50))]
                print(f"  {hour}:00  n={len(v):3d}  min={min(v):3d} avg={avg:3d} max={max(v):3d} {bar}")

    # 0x53: sleep sessions
    if results.get(0x53):
        recs, stride = results[0x53]
        print(f"\n--- 0x53 sleep sessions ({len(recs)}) ---")
        from collections import Counter
        for seq, dt, p in recs:
            c = Counter(p)
            print(f"  {dt}  payload {len(p)}B  histogram={dict(sorted(c.items()))}")
            print(f"    raw: {p[:40].hex(' ')}")

    # SpO2 scan across all payloads (values 85..100 clustered)
    print("\n--- SpO2 candidate scan (bytes 85-100) ---")
    for cmd in sorted(results):
        r = results[cmd]
        if not r:
            continue
        recs, _ = r
        plen = min(len(x[2]) for x in recs)
        for pos in range(plen):
            vals = [p[pos] for _, _, p in recs if 85 <= p[pos] <= 100]
            if len(vals) > len(recs) * 0.6 and len(set(vals)) > 1:
                print(f"  0x{cmd:02X} payload[{pos}]: {len(vals)}/{len(recs)} in 85-100, "
                      f"sample={vals[:12]}")

main()
