from androguard.core.dex import DEX
import os

os.chdir("/Users/lulusensei/Documents/0x Alpha/pulse-re/pkgs/jcvitalpro-extracted")
d = DEX(open("classes6.dex", "rb").read())
classes = {c.get_name(): c for c in d.get_classes()}
c = classes["Lcom/example/jcring_blue/JcringBluePlugin;"]

out = open("/Users/lulusensei/Documents/0x Alpha/pulse-re/scripts/jcring_plugin_dump.txt", "w")
for m in c.get_methods():
    out.write(f"\nMETHOD {m.get_access_flags_string()} {m.get_name()}{m.get_descriptor()}\n")
    code = m.get_code()
    if code is None:
        continue
    for ins in m.get_instructions():
        try:
            out.write(f"    {ins.get_output()}\n")
        except Exception as e:
            out.write(f"    <err>\n")
out.close()
print("methods:", len(list(c.get_methods())))
print("size:", os.path.getsize("/Users/lulusensei/Documents/0x Alpha/pulse-re/scripts/jcring_plugin_dump.txt"))
