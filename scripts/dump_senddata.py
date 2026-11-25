from androguard.core.dex import DEX
import os

os.chdir("/Users/lulusensei/Documents/0x Alpha/pulse-re/pkgs/jcvitalpro-extracted")
d = DEX(open("classes7.dex", "rb").read())
classes = {c.get_name(): c for c in d.get_classes()}

out = open("/Users/lulusensei/Documents/0x Alpha/pulse-re/scripts/senddata_dump.txt", "w")

def dump_class(name):
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
        out.write(f"\nMETHOD {m.get_access_flags_string()} {m.get_name()}{m.get_descriptor()}\n")
        code = m.get_code()
        if code is None:
            out.write("  (abstract/native)\n")
            continue
        for ins in m.get_instructions():
            op = ins.get_name()
            try:
                operands = ins.get_operands()
                ops = []
                for o in operands:
                    kind = o[0]
                    val = o[2] if len(o) > 2 else o[1]
                    if kind == 1:  # register
                        ops.append(f"r{val}")
                    elif kind == 0x10:  # string
                        ops.append(f"str:{val!r}")
                    else:
                        if isinstance(val, bytes):
                            val = val.hex()
                        ops.append(f"{val}")
                out.write(f"    {op} {', '.join(ops)}\n")
            except Exception as e:
                out.write(f"    {op} <err {e}>\n")

for cls in ["Lio/flutter/plugins/SendData;",
            "Lio/flutter/plugins/BleData;",
            "Lio/flutter/plugins/ResolveData;",
            "Lio/flutter/plugins/ResolveDeviceData;"]:
    dump_class(cls)
out.close()
print("done, size:", os.path.getsize("/Users/lulusensei/Documents/0x Alpha/pulse-re/scripts/senddata_dump.txt"))
