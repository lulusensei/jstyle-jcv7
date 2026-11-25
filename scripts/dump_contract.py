from androguard.core.dex import DEX
import os, re

os.chdir("/Users/lulusensei/Documents/0x Alpha/pulse-re/pkgs/jcvitalpro-extracted")
d = DEX(open("classes7.dex", "rb").read())

targets = [
    "Lcom/realsil/sdk/bbpro/core/protocol/Contract;",
    "Lcom/realsil/sdk/bbpro/core/protocol/CommandContract;",
    "Lcom/realsil/sdk/bbpro/core/protocol/EventContract;",
    "Lcom/realsil/sdk/bbpro/core/protocol/params/ConfigType;",
    "Lcom/realsil/sdk/bbpro/core/protocol/params/GetConfigType;",
    "Lcom/realsil/sdk/bbpro/core/protocol/params/Parameters;",
    "Lcom/realsil/sdk/bbpro/core/transportlayer/Command;",
    "Lcom/realsil/sdk/bbpro/core/transportlayer/CommandFactory;",
    "Lcom/realsil/sdk/bbpro/core/transportlayer/TransportLayerPacket;",
    "Lcom/realsil/sdk/bbpro/core/transportlayer/DefaultDataParser;",
    "Lcom/realsil/sdk/bbpro/core/transportlayer/TransportLayerConfig;",
    "Lcom/realsil/sdk/bbpro/core/transportlayer/AckPacket;",
    "Lcom/realsil/sdk/bbpro/core/transportlayer/EventPacket;",
]

classes = {c.get_name(): c for c in d.get_classes()}

def const_val(f):
    v = f.get_init_value()
    if v is None:
        return None
    try:
        return v.get_value()
    except Exception:
        return v

for t in targets:
    c = classes.get(t)
    if c is None:
        print(f"!!! {t} NOT FOUND")
        continue
    print(f"\n===== {t} =====")
    for f in c.get_fields():
        acc = f.get_access_flags_string()
        val = const_val(f)
        if val is not None:
            if isinstance(val, bytes):
                val = val.hex()
            print(f"  {acc} {f.get_name()} = {val}")
        else:
            print(f"  {acc} {f.get_name()}")
    print("  --- methods ---")
    for m in c.get_methods():
        print(f"  {m.get_access_flags_string()} {m.get_name()}{m.get_descriptor()}")
