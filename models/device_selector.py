from dataclasses import dataclass

import torch

@dataclass(frozen=True)
class DeviceInfo:
    device:str
    name:str
    acclerator:bool

class DeviceSelector:
    @staticmethod
    def select()->DeviceInfo:
        # Apple Silicon GPU
        if(
            hasattr(torch.backends,"mps")
            and torch.backends.mps.is_built()
            and torch.backends.mps.is_available
        ):
            return DeviceInfo(device="mps",name="Apple Metal Performance Shaders",acclerator=True)

        # CUDA GPU
        if torch.cuda.is_initialized() and torch.cuda.is_available():
            gpu_index = 0
            return DeviceInfo(
                device=f"cuda:{gpu_index}",
                    name=torch.cuda.get_device_name(gpu_index),
                    acclerator=True
                )
        # CPU fallback
        return DeviceInfo(
            device="cpu",
            name="CPU",
            acclerator=False
        )