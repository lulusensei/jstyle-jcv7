import requests, struct, zipfile, os, time

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

out = "/Users/lulusensei/Documents/0x Alpha/pulse-re/pkgs/config.arm64_v8a.apk"
CHUNK = 8 * 1024 * 1024
while True:
    have = os.path.getsize(out) if os.path.exists(out) else 0
    if have >= CSIZE:
        break
    end = min(data_start + have + CHUNK - 1, data_start + CSIZE - 1)
    try:
        rr = requests.get(final, headers={**UA, "Range": f"bytes={data_start+have}-{end}"}, timeout=150)
        if rr.status_code in (206, 200):
            with open(out, "ab") as f:
                f.write(rr.content)
            print(f"chunk: +{len(rr.content)} at {have/1024/1024:.0f}MB", flush=True)
        else:
            print("bad status", rr.status_code, flush=True)
            time.sleep(3)
    except Exception as e:
        print("retry:", type(e).__name__, flush=True)
        time.sleep(3)

print(f"complete: {os.path.getsize(out)} bytes")
z = zipfile.ZipFile(out)
for n in z.namelist():
    info = z.getinfo(n)
    print(f"  {n}  {info.file_size/1024:.0f} KB")
    if n.endswith(".so"):
        z.extract(n, "/Users/lulusensei/Documents/0x Alpha/pulse-re/pkgs/split-arm64")
print("extracted")
