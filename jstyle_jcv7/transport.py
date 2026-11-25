"""BLE transport for the JCV7 band over bleak (CoreBluetooth/BlueZ/dbus)."""

from __future__ import annotations

import asyncio
from collections import deque

from bleak import BleakClient, BleakScanner

SERVICE_FFF0 = "0000fff0-0000-1000-8000-00805f9b34fb"
CHAR_WRITE = "0000fff6-0000-1000-8000-00805f9b34fb"
CHAR_NOTIFY = "0000fff7-0000-1000-8000-00805f9b34fb"

HEART_RATE_SERVICE = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT = "00002a37-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"
PLX_SPOT_CHECK = "00002a5f-0000-1000-8000-00805f9b34fb"

NAME_PREFIXES = ("JCV", "JStyle", "Pulse")


async def scan(timeout: float = 10.0) -> list[dict]:
    """Scan for bands that look like JStyle/JCV devices."""
    found: dict[str, dict] = {}

    def on_detect(device, adv):
        name = device.name or adv.local_name or ""
        if any(name.startswith(p) for p in NAME_PREFIXES) or SERVICE_FFF0 in (adv.service_uuids or []):
            found[device.address] = {
                "address": device.address,
                "name": name or "?",
                "rssi": adv.rssi,
                "manufacturer": {f"0x{k:04x}": v.hex() for k, v in (adv.manufacturer_data or {}).items()},
            }

    scanner = BleakScanner(detection_callback=on_detect)
    await scanner.start()
    await asyncio.sleep(timeout)
    await scanner.stop()
    return sorted(found.values(), key=lambda d: d["rssi"])


class Transport:
    """Connects to a band, subscribes FFF7, serializes writes to FFF6."""

    def __init__(self, address: str):
        self.address = address
        self.client: BleakClient | None = None
        self.notifications: deque[bytes] = deque(maxlen=512)
        self._notify_task: asyncio.Task | None = None

    async def connect(self) -> None:
        self.client = BleakClient(self.address, timeout=20)
        await self.client.connect()
        await self.client.start_notify(CHAR_NOTIFY, self._on_notify)

    async def _on_notify(self, _char, data: bytes) -> None:
        self.notifications.append(bytes(data))

    async def write(self, frame: bytes) -> None:
        if not self.client or not self.client.is_connected:
            raise ConnectionError("not connected")
        await self.client.write_gatt_char(CHAR_WRITE, frame, response=False)

    async def drain(self, delay: float = 1.0) -> list[bytes]:
        """Collect notifications that arrive within `delay` seconds."""
        before = len(self.notifications)
        await asyncio.sleep(delay)
        return list(self.notifications)[before:]

    async def request(self, frame: bytes, delay: float = 1.2) -> list[bytes]:
        """Send a command frame and return the response frames."""
        before = len(self.notifications)
        await self.write(frame)
        await asyncio.sleep(delay)
        return list(self.notifications)[before:]

    async def disconnect(self) -> None:
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    async def __aenter__(self) -> "Transport":
        await self.connect()
        return self

    async def __aexit__(self, *_exc) -> None:
        await self.disconnect()
