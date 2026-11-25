"""jstyle_jcv7 — open-source driver for the JStyle JCV7 health band.

The band was sold as the "Pulse" DePIN health wearable and abandoned when the
Pulse project shut down in 2026. This package keeps the hardware alive.
"""

from .client import PulseBand
from .protocol import Command, UserInfo, build
from .transport import Transport, scan

__version__ = "0.1.0"

__all__ = ["PulseBand", "Transport", "Command", "UserInfo", "build", "scan", "__version__"]
