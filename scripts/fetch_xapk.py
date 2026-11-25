from remotezip import RemoteZip
import os

os.chdir("/Users/lulusensei/Documents/0x Alpha/pulse-re/pkgs")
url = "https://d.apkpure.net/b/XAPK/com.jstyle.jcvitalpro?version=latest"
try:
    with RemoteZip(url, initial_buffer_size=1024*1024) as z:
        names = z.namelist()
        print("entries:", len(names))
        for n in names[:60]:
            info = z.getinfo(n)
            print(f"  {n}  {info.file_size/1024:.0f} KB")
        targets = [n for n in names if "arm64" in n or n.endswith((".apk", ".bin"))]
        print("targets:", targets)
        for n in targets:
            data = z.read(n)
            out = os.path.basename(n)
            with open(out, "wb") as f:
                f.write(data)
            print(f"saved {out}: {len(data)/1024/1024:.1f} MB")
except Exception as e:
    print("ERR:", type(e).__name__, e)
