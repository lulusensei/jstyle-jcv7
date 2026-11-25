from androguard.core.dex import DEX
import os

os.chdir("/Users/lulusensei/Documents/0x Alpha/pulse-re/pkgs/jcvitalpro-extracted")
d = DEX(open("classes7.dex", "rb").read())

plugins = sorted(set(c.get_name() for c in d.get_classes() if c.get_name().startswith("Lio/flutter/plugins/")))
print(f"io/flutter/plugins classes: {len(plugins)}")
for p in plugins:
    print(" ", p)
