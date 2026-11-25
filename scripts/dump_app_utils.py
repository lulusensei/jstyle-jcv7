from androguard.core.dex import DEX
import os

os.chdir("/Users/lulusensei/Documents/0x Alpha/pulse-re/pkgs/jcvitalpro-extracted")
d = DEX(open("classes7.dex", "rb").read())
classes = {c.get_name(): c for c in d.get_classes()}

targets = [
    "Lcom/jstyle/jcvitalpro/RtkUtils;",
    "Lcom/jstyle/jcvitalpro/HuiDingUtils;",
    "Lcom/jstyle/jcvitalpro/DeviceUpdateUtils;",
]

for t in targets:
    c = classes.get(t)
    if c is None:
        print(f"!!! {t} NOT FOUND")
        continue
    print(f"\n===== {t} =====")
    for f in c.get_fields():
        v = f.get_init_value()
        try:
            val = v.get_value() if v else None
        except Exception:
            val = None
        if isinstance(val, bytes):
            val = val.hex()
        print(f"  FIELD {f.get_access_flags_string()} {f.get_name()} = {val}")
    for m in c.get_methods():
        print(f"  METHOD {m.get_access_flags_string()} {m.get_name()}{m.get_descriptor()}")
        code = m.get_code()
        if code is None:
            continue
        strs = []
        for ins in m.get_instructions():
            op = ins.get_name()
            if "string" in op:
                try:
                    s = ins.get_string()
                    strs.append(s)
                except Exception:
                    pass
        for s in sorted(set(strs)):
            if len(s) < 200:
                print(f"      STR {s!r}")
