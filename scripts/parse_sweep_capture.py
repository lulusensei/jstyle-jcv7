"""Parse the 2026-11-25 command-sweep capture into per-command history records.

Record envelope (observed for 0x51-0x59, 0x5C dump commands):
  [0]     cmd echo
  [1:3]   sequence (u16 LE)
  [3]     0x00
  [4:11]  BCD datetime  yy MM dd HH mm ss
  [11:]   type-specific payload
"""
import re
from collections import Counter
from datetime import datetime

LOG = "/Users/lulusensei/Documents/0x Alpha/pulse-re/captures/sweep-2026-11-25.log"

def load_blobs():
    blobs = []
    for line in open(LOG):
        m = re.search(r'FFF7 after \[([^\]]*)\]: ((?:[0-9a-f]{2} )+[0-9a-f]{2})', line)
        if m:
            blobs.append(bytes.fromhex(m.group(2).replace(" ", "")))
    return blobs

def un_bcd(b):
    hi, lo = (b >> 4) & 0xF, b & 0xF
    if hi > 9 or lo > 9:
        return None
    return hi * 10 + lo

def valid_dt(rec):
    if len(rec) < 11 or rec[3] != 0x26:
        return None
    vals = [un_bcd(rec[i]) for i in range(4, 11)]
    if any(v is None for v in vals):
        return None
    yy, mo, dd, hh, mi, ss, extra = vals
    if not (1 <= mo <= 12 and 1 <= dd <= 31 and hh <= 23 and mi <= 59 and ss <= 59):
        return None
    return datetime(2000 + yy, mo, dd, hh, mi, ss)

def split_records(stream: bytes, cmd: int):
    cands = [i for i in range(len(stream) - 11)
             if stream[i] == cmd and stream[i + 3] == 0x26 and valid_dt(stream[i:i + 11])]
    if not cands:
        return [], 0
    # modal gap between consecutive candidates = record stride
    gaps = Counter(b - a for a, b in zip(cands, cands[1:]) if 0 < b - a < 256)
    stride = gaps.most_common(1)[0][0] if gaps else len(stream) - cands[0]
    # walk the chain from the first candidate
    starts, pos = [], cands[0]
    while pos + stride <= len(stream) and stream[pos] == cmd:
        if valid_dt(stream[pos:pos + 11]):
            starts.append(pos)
        else:
            break
        pos += stride
    records = []
    for s in starts:
        rec = stream[s:s + stride]
        records.append((int.from_bytes(rec[1:3], "little"), valid_dt(rec), rec[11:]))
    return records, stride

def summarize(cmd, result):
    records, stride = result
    print(f"\n=== cmd 0x{cmd:02X}: {len(records)} records, stride={stride} ===")
    if not records:
        return
    print(f"  time range: {records[0][1]} .. {records[-1][1]}")
    for seq, dt, p in records[:3]:
        print(f"  seq={seq:4d} {dt}  payload={p.hex(' ')}")
    seq, dt, p = records[-1]
    print(f"  ... last: seq={seq:4d} {dt}  payload={p.hex(' ')}")

blobs = load_blobs()
stream_by_cmd = {}
for b in blobs:
    if b[0] in (0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x58, 0x59, 0x5C):
        stream_by_cmd[b[0]] = stream_by_cmd.get(b[0], b"") + b

for cmd in sorted(stream_by_cmd):
    r = split_records(stream_by_cmd[cmd], cmd)
    summarize(cmd, r)
