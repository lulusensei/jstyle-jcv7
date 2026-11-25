import requests, struct, os

UA = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}
url = "https://d.apkpure.net/b/XAPK/com.jstyle.jcvitalpro?version=latest"
r = requests.get(url, headers=UA, stream=True, timeout=30)
final = r.url
r.close()
h = requests.head(final, headers=UA, timeout=30)
total = int(h.headers["Content-Length"])
start = total - 2 * 1024 * 1024
rr = requests.get(final, headers={**UA, "Range": f"bytes={start}-"}, timeout=120)
tail = rr.content
print("status:", rr.status_code, "tail:", len(tail))
eocd_pos = tail.rfind(b"PK\x05\x06")
print("eocd_pos in tail:", eocd_pos)
eocd = tail[eocd_pos:eocd_pos+22]
vals = struct.unpack("<IHHHHIIH", eocd)
print("eocd fields:", vals)
n_entries = vals[3]
cd_size = vals[5]
cd_off = vals[6]
print(f"entries={n_entries} cd_size={cd_size} cd_off={cd_off} abs_cd_end={cd_off+cd_size} total={total}")
abs_pos = start + eocd_pos
print("eocd abs:", abs_pos)
# CD end = eocd abs position; CD start = abs_pos - cd_size
cd_start_abs = abs_pos - cd_size
rr2 = requests.get(final, headers={**UA, "Range": f"bytes={cd_start_abs}-{abs_pos-1}"}, timeout=120)
cd = rr2.content
print("cd bytes:", len(cd), "sig:", cd[:4])
i = 0
while i + 46 <= len(cd) and cd[i:i+4] == b"PK\x01\x02":
    (sig, vmade, vneed, flags, method, mtime, mdate, crc, csize, usize,
     nlen, elen, clen, disk, iattr, eattr, lho) = struct.unpack("<IHHHHHHIIIHHHHHII", cd[i:i+46])
    name = cd[i+46:i+46+nlen].decode("utf-8", "replace")
    print(f"  {name}  csize={csize} usize={usize} method={method} lho={lho}")
    i += 46 + nlen + elen + clen
