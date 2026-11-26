from androguard.core.dex import DEX
import os

os.chdir("/Users/lulusensei/Documents/0x Alpha/pulse-re/pkgs/jcvitalpro-extracted")
d = DEX(open("classes6.dex", "rb").read())

plugins = sorted(set(c.get_name() for c in d.get_classes() if "jcring" in c.get_name().lower()))
print(f"jcring classes in classes6: {len(plugins)}")
for p in plugins[:40]:
    print(" ", p)
