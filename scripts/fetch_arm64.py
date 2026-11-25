import requests, struct, zipfile, os

UA = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}
url = "https://d.apkpure.net/b/XAPK/com.jstyle.jcvitalpro?version=latest"
r = requests.get(url, headers=UA, stream=True, timeout=30)
final = r.url
r.close()

LHO = 491446227
CSIZE = 56726808
lh = requests.get(final, headers={**UA, "Range": f"bytes={LHO}-{LHO+63}"}, timeout=60).content
_, _, _, _, _, _, _, _, _, nlen, elen = struct.unpack("<IHHHHHIIIHH", lh[:30])
data_start = LHO + 30 + nlen + elen
print("fetching config.arm64_v8a.apk ...")
rr = requests.get(final, headers={**UA, "Range": f"bytes={data_start}-{data_start+CSIZE-1}"}, timeout=900)
out = "/Users/lulusensei/Documents/0x Alpha/pulse-re/pkgs/config.arm64_v8a.apk"
with open(out, "wb") as f:
    f.write(rr.content)
print(f"saved: {len(rr.content)} bytes, status {rr.status_code}")

z = zipfile.ZipFile(out)
for n in z.namelist():
    info = z.getinfo(n)
    print(f"  {n}  {info.file_size/1024:.0f} KB")
    if n.endswith(".so"):
        z.extract(n, "/Users/lulusensei/Documents/0x Alpha/pulse-re/pkgs/split-arm64")
print("extracted to split-arm64/")
