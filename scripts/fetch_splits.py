import requests, struct, zipfile, io, os, sys

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0"}
url = "https://d.apkpure.net/b/XAPK/com.jstyle.jcvitalpro?version=latest"

# resolve final URL
r = requests.get(url, headers=UA, stream=True, timeout=30)
final = r.url
r.close()
print("final URL:", final[:100], "...")

# total size
h = requests.head(final, headers=UA, timeout=30)
total = int(h.headers["Content-Length"])
print("total:", total)

# fetch last 2 MB (central directory region)
start = total - 2 * 1024 * 1024
rr = requests.get(final, headers={**UA, "Range": f"bytes={start}-"}, timeout=120)
tail = rr.content
print("tail bytes:", len(tail))

# parse EOCD
eocd_pos = tail.rfind(b"PK\x05\x06")
assert eocd_pos >= 0, "no EOCD"
eocd = tail[eocd_pos:eocd_pos+22]
_, _, _, _, n_entries, cd_size, cd_off, _ = struct.unpack("<IHHHHIIH", eocd)
print(f"entries: {n_entries}, cd_size: {cd_size}, cd_off: {cd_off}")

# central directory may span further back if cd_off+cd_size < start
if cd_off + cd_size > start:
    need = start - cd_off
    rr = requests.get(final, headers={**UA, "Range": f"bytes={cd_off}-{start-1}"}, timeout=120)
    tail = rr.content + tail
    start = cd_off

cd = tail[cd_off - start: cd_off - start + cd_size]
entries = {}
i = 0
while i < len(cd):
    if cd[i:i+4] != b"PK\x01\x02":
        break
    (sig, vmade, vneed, flags, method, mtime, mdate, crc, csize, usize,
     nlen, elen, clen, disk, iattr, eattr, lho) = struct.unpack("<IHHHHHHIIIHHHHHII", cd[i:i+46])
    name = cd[i+46:i+46+nlen].decode("utf-8", "replace")
    entries[name] = (method, csize, usize, lho)
    i += 46 + nlen + elen + clen

for name, (method, csize, usize, lho) in entries.items():
    print(f"  {name}  csize={csize/1024/1024:.1f}MB usize={usize/1024/1024:.1f}MB method={method}")

os.chdir("/Users/lulusensei/Documents/0x Alpha/pulse-re/pkgs")
targets = [n for n in entries if "arm64" in n or n == "base.apk" or n.endswith(".apk")]
for name in targets:
    method, csize, usize, lho = entries[name]
    # local header: fetch 30 bytes first to compute name len
    lh = requests.get(final, headers={**UA, "Range": f"bytes={lho}-{lho+29}"}, timeout=60).content
    _, _, _, _, _, _, _, _, _, _, nlen, elen = struct.unpack("<IHHHHHHIIIHH", lh[:30])
    data_start = lho + 30 + nlen + elen
    print(f"fetching {name}: {csize/1024/1024:.1f} MB ...")
    rr = requests.get(final, headers={**UA, "Range": f"bytes={data_start}-{data_start+csize-1}"}, timeout=600)
    with open(os.path.basename(name), "wb") as f:
        f.write(rr.content)
    print(f"saved {os.path.basename(name)}: {len(rr.content)/1024/1024:.1f} MB")
print("DONE")
