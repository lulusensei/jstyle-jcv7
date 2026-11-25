from androguard.core.dex import DEX
import os, re

os.chdir("/Users/lulusensei/Documents/0x Alpha/pulse-re/pkgs/jcvitalpro-extracted")
names = ["classes.dex", "classes5.dex", "classes6.dex", "classes7.dex", "classes8.dex", "classes2.dex", "classes3.dex", "classes4.dex"]
pat = re.compile(r"SendData|ParseData|BleCmd|BleManager|CmdData|DataUtils|BleUtils|JstyleBle|JBle|HeartRate|BloodPressure|Spo2|SpO2|Ecg|ECG", re.I)
for n in names:
    if not os.path.exists(n):
        continue
    d = DEX(open(n, "rb").read())
    hits = sorted(set(c.get_name() for c in d.get_classes() if pat.search(c.get_name())))
    if hits:
        print(f"--- {n}: {len(hits)} hits ---")
        for hname in hits:
            print(" ", hname)
