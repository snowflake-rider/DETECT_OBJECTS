"""Select the fastest PyTorch inference device available on the host."""

from dataclasses import dataclass

import torch


@dataclass(frozen=True)
class DeviceInfo:
    """Describe a PyTorch device and whether it is hardware accelerated."""

    device: str
    name: str
    acclerator: bool


class DeviceSelector:
    """Choose between Apple MPS, NVIDIA CUDA, and a CPU fallback."""

    @staticmethod
    def select() -> DeviceInfo:
        """Return information for the preferred available inference device."""
        # Apple Silicon GPU
        if (
            hasattr(torch.backends, "mps")
            and torch.backends.mps.is_built()
            and torch.backends.mps.is_available()
        ):
            return DeviceInfo(
                device="mps", name="Apple Metal Performance Shaders", acclerator=True
            )

        # CUDA GPU
        if torch.cuda.is_initialized() and torch.cuda.is_available():
            gpu_index = 0
            return DeviceInfo(
                device=f"cuda:{gpu_index}",
                name=torch.cuda.get_device_name(gpu_index),
                acclerator=True,
            )
        # CPU fallback
        return DeviceInfo(device="cpu", name="CPU", acclerator=False)
