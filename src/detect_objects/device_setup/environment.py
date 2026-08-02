"""Detect and describe the environment in which the application runs."""

from __future__ import annotations

import json
import platform
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Environment:
    """Immutable operating-system and Python runtime details."""

    os: str
    release: str
    machine: str
    python: str
    rpi: str | None = None

    def __str__(self) -> str:
        """Return this environment as a JSON string."""
        return json.dumps(self.as_dict(), ensure_ascii=False)

    @classmethod
    def detect(cls) -> Environment:
        """Read environment details from the current machine."""
        return cls(
            os=platform.system() or "Unknown",
            release=platform.release(),
            machine=platform.machine(),
            python=platform.python_version(),
            # TODO: get_raspberry_pi_model() — 파이 연결하면 채운다.
            #       그때까지는 어느 보드든 None.
            rpi=None,
        )

    def as_dict(self) -> dict[str, str | None]:
        """Return a plain dict for the JSON report."""
        return asdict(self)
