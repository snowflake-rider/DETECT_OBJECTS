"""Runtime interfaces available after device and model setup."""

from enum import StrEnum


class RuntimeMode(StrEnum):
    """Choose how ODIA presents its live runtime."""

    DESKTOP = "desktop"
    CLASSIC = "classic"
