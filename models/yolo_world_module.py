# yolo_world_manager.py

from __future__ import annotations

import gc
from pathlib import Path
from typing import Sequence

import numpy as np
import torch
from ultralytics import YOLOWorld
from ultralytics.engine.results import Results

from device_selector import DeviceInfo, DeviceSelector
from typing import Self

class YOLO_World_Manager:
    def __init__(
        self,
        model_path: str | Path = "yolov8s-worldv2.pt",
        confidence: float = 0.25,
        image_size: np.array = [640,640],
    ) -> None:
        self._model_path = Path(model_path)
        print(f"model path:{model_path}\n")
        self._confidence = confidence
        self._image_size = image_size
        self._device_info: DeviceInfo = DeviceSelector.select()
        self._model: YOLOWorld | None = None
        print("manager initialized..\n")

    @property
    def is_loaded(self) -> bool:
        return (self._model is not None)  and (isinstance(self._model,YOLOWorld))

    @property
    def device(self) -> str:
        return self._device_info.device

    @property
    def device_name(self) -> str:
        return self._device_info.name

    def load(self) -> None:
        if self.is_loaded:
            print("model loaded already")
            return 

        print(f"YOLO-World 모델 로딩: {self._model_path}")
        print(
            f"추론 장치: "
            f"{self._device_info.device} "
            f"({self._device_info.name})"
        )

        self._model = YOLOWorld(str(self._model_path))


    def predict(self, frame: np.ndarray|str,classes:Sequence[str]) -> Results:
        model = self._require_model()
        model.set_classes(classes)
        results = model.predict(
            source=frame,
            device=self._device_info.device,
            conf=self._confidence,
            imgsz=self._image_size,
            verbose=False,
        )

        return results

    def close(self) -> None:
        if self._model is None:
            return

        self._model = None

        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        if (
            hasattr(torch, "mps")
            and hasattr(torch.mps, "empty_cache")
            and torch.backends.mps.is_available()
        ):
            torch.mps.empty_cache()

        print("YOLO-World 모델 자원을 해제했습니다.")

    def __enter__(self) -> Self:
        print("loading weight file\n")
        self.load()
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()

    def _require_model(self) -> YOLOWorld:
        if not self.is_loaded:
            raise RuntimeError(
                "YOLO-World 모델이 로딩되지 않았습니다. "
                "먼저 load()를 호출하세요."
            )

        return self._model

    @staticmethod
    def _normalize_classes(classes: Sequence[str]) -> list[str]:
        normalized = []

        for class_name in classes:
            name = class_name.strip()

            if name and name not in normalized:
                normalized.append(name)

        if not normalized:
            raise ValueError("탐지 클래스가 최소 하나 이상 필요합니다.")

        return normalized


if __name__ == "__main__":
    try:
        with YOLO_World_Manager(confidence=0.45) as manager:
            print("manager")
            result = manager.predict("./image.png",["cat"])
            print(result.boxes)
        # manager = YOLO_World_Manager(confidence=0.45)
        # manager.load()
    except (ValueError,RuntimeError) as e:
        print(e)