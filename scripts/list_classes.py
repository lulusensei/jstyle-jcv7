from androguard.core.dex import DEX
import re, os

os.chdir("/Users/lulusensei/Documents/0x Alpha/pulse-re/pkgs/jcvitalpro-extracted")
d = DEX(open("classes7.dex", "rb").read())
classes = sorted(set(c.get_name() for c in d.get_classes()))

noise = re.compile(r"\$\$|R\$mipmap|BuildConfig")
filt = [c for c in classes
        if re.search(r"jstyle|lefu|ppscale|pp_bluetooth|realsil|HuiDing|Rtk", c, re.I)
        and not noise.search(c)]
print(f"filtered: {len(filt)}")
for c in filt:
    print(c)
