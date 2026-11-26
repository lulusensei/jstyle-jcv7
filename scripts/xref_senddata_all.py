from androguard.core.dex import DEX
import os

os.chdir("/Users/lulusensei/Documents/0x Alpha/pulse-re/pkgs/jcvitalpro-extracted")
d = DEX(open("classes7.dex", "rb").read())

out = open("/Users/lulusensei/Documents/0x Alpha/pulse-re/scripts/xref_all.txt", "w")
count = 0
for c in d.get_classes():
    cname = c.get_name()
    for m in c.get_methods():
        code = m.get_code()
        if code is None:
            continue
        calls = []
        for ins in m.get_instructions():
            try:
                o = ins.get_output()
                if "SendData;->" in o:
                    calls.append(o.strip())
            except Exception:
                pass
        if calls:
            count += 1
            out.write(f"\n{cname} -> {m.get_name()}\n")
            for call in sorted(set(calls)):
                out.write(f"    {call}\n")
out.close()
print("methods calling SendData:", count)
