# Contributing

Contributions are welcome — this is a revival project for hardware the
original vendor abandoned.

## Ground rules

1. **Legality**: analyze only firmware/apps you legally obtained. Do not
   commit or redistribute the JCVitalPro APK, its DEX files, `libapp.so`, or
   any extracted firmware images — document offsets and findings instead.
2. **Verify before documenting**: every protocol claim in
   `docs/PROTOCOL.md` should be backed by either decompiled code or a live
   capture (paste both into the PR description).
3. **Keep it local**: no cloud calls, no telemetry. Health data stays on the
   user's machine.
4. **Be careful with destructive commands** (`0x12`, `0x2E`, `0x47`): test on
   hardware you accept to risk, and never in CI.

## High-value open work

See the open-questions list in `docs/PROTOCOL.md`. Concretely, in order of
impact:

1. Decode `0x43` day-data / `0x44` sleep-data / `0x17` heart-breath record
   layouts (probe on a worn band, or analyze the Dart snapshot strings in
   `libapp.so`).
2. Find the live-HR trigger so `0x2A37` streams continuously.
3. Map the `0x92` file-transfer channel well enough to **read** flash and
   archive firmware images from multiple hardware revisions (preservation!).
4. Reverse `libRtkAesJni.so` to document the OTA image encryption.
5. Test on sibling white-label hardware (CORE VITALS, LivLive) and record
   differences.

## Dev setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
python -m jstyle_jcv7.cli scan
```

Please keep PRs focused: one protocol finding or one driver feature each.
