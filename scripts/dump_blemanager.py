from androguard.core.dex import DEX
import os

os.chdir("/Users/lulusensei/Documents/0x Alpha/pulse-re/pkgs/jcvitalpro-extracted")
d = DEX(open("classes7.dex", "rb").read())
classes = {c.get_name(): c for c in d.get_classes()}

out = open("/Users/lulusensei/Documents/0x Alpha/pulse-re/scripts/blemanager_dump.txt", "w")

def dump_class(name, with_bytecode=True, only_methods=None):
    c = classes.get(name)
    if c is None:
        out.write(f"!!! {name} NOT FOUND\n")
        return
    out.write(f"\n{'='*70}\n===== {name} =====\n{'='*70}\n")
    for f in c.get_fields():
        v = f.get_init_value()
        try:
            val = v.get_value() if v else None
        except Exception:
            val = None
        if isinstance(val, bytes):
            val = val.hex()
        out.write(f"FIELD {f.get_access_flags_string()} {f.get_name()} : {f.get_descriptor()} = {val}\n")
    for m in c.get_methods():
        if only_methods and m.get_name() not in only_methods:
            continue
        out.write(f"\nMETHOD {m.get_access_flags_string()} {m.get_name()}{m.get_descriptor()}\n")
        code = m.get_code()
        if code is None:
            out.write("  (abstract/native)\n")
            continue
        if not with_bytecode:
            continue
        for ins in m.get_instructions():
            try:
                out.write(f"    {ins.get_output()}\n")
            except Exception as e:
                out.write(f"    <err {e}>\n")

# BleManager: full method list first, bytecode only for onMethodCall-ish methods
dump_class("Lio/flutter/plugins/ble/BleManager;", with_bytecode=False)
out.close()
print("done:", os.path.getsize("/Users/lulusensei/Documents/0x Alpha/pulse-re/scripts/blemanager_dump.txt"))
