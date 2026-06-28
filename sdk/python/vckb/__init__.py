"""
VC-Keyboard Python SDK
USB CDC Serial 驱动 ESP32-S3 外设板
"""

from .device import (
    VCKeyboard,
    BLACK, WHITE, RED, GREEN, BLUE,
    YELLOW, CYAN, MAGENTA, ORANGE, GRAY,
    rgb565,
)

__version__ = "1.0.0"
