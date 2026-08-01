"""Manage YOLO-World model loading, custom classes, prediction, and cleanup."""

from __future__ import annotations

import gc
from pathlib import Path
from typing import Sequence

import numpy as np
import torch
from ultralytics import YOLOWorld
from ultralytics.engine.results import Boxes

from models.device_selector import DeviceInfo, DeviceSelector
from typing import Self


class YOLO_World_Manager:
    """Own a YOLO-World model and expose its inference lifecycle."""

    def __init__(
        self,
        model_path: str | Path = "yolov8s-worldv2.pt",
        confidence: float = 0.25,
        image_size: np.array = [640, 640],
    ) -> None:
        """Configure model location, confidence threshold, image size, and device."""
        self._model_path = Path(model_path)
        print(f"model path:{model_path}\n")
        self._confidence = confidence
        self._image_size = image_size
        self._device_info: DeviceInfo = DeviceSelector.select()
        self._model: YOLOWorld | None = None
        self._class_embedding_cache: dict[str, torch.Tensor] = {}
        print("manager initialized..\n")

    @property
    def is_loaded(self) -> bool:
        """Return whether a YOLO-World model instance is currently loaded."""
        return (self._model is not None) and (isinstance(self._model, YOLOWorld))

    @property
    def device(self) -> str:
        """Return the selected PyTorch device identifier."""
        return self._device_info.device

    @property
    def device_name(self) -> str:
        """Return a human-readable name for the selected inference device."""
        return self._device_info.name

    def load(self) -> None:
        """Load model weights unless the model has already been initialized."""
        if self.is_loaded:
            print("model loaded already")
            return

        print(f"YOLO-World 모델 로딩: {self._model_path}")
        print(f"추론 장치: {self._device_info.device} ({self._device_info.name})")
        self._model = YOLOWorld(str(self._model_path))

    def set_classes(self, classes: Sequence[str]) -> None:
        """Normalize and apply the object classes the model should detect."""
        self.__classes = self._normalize_classes(classes)
        self._model.set_classes(self.__classes)

    def cache_class_embeddings(self, classes: Sequence[str]) -> None:
        """Create class embeddings once and retain CPU copies for fast reuse."""
        model = self._require_model()
        normalized_classes = self._normalize_classes(classes)
        world_model = model.model
        stored_names = (
            list(world_model.names.values())
            if isinstance(world_model.names, dict)
            else list(world_model.names)
        )
        stored_features = world_model.txt_feats.detach().cpu()
        stored_indexes = {
            class_name: index
            for index, class_name in enumerate(stored_names)
        }
        missing_classes = [
            name for name in normalized_classes if name not in stored_indexes
        ]

        # yolov8s-worldv2.pt already contains COCO embeddings. Reuse them so
        # the runtime swap does not need CLIP or another set_classes() call.
        if missing_classes:
            model.set_classes(normalized_classes)
            stored_features = model.model.txt_feats.detach().cpu()
            stored_indexes = {
                class_name: index
                for index, class_name in enumerate(normalized_classes)
            }

        if stored_features.shape[1] < len(stored_indexes):
            raise RuntimeError(
                "클래스 개수와 텍스트 임베딩 개수가 일치하지 않습니다"
            )

        self._class_embedding_cache = {
            class_name: stored_features[
                :, stored_indexes[class_name]:stored_indexes[class_name] + 1, :
            ].clone()
            for class_name in normalized_classes
        }
        self.__classes = normalized_classes
        print(f"클래스 임베딩 캐시 완료: {len(self._class_embedding_cache)}개")

    def activate_cached_classes(self, classes: Sequence[str]) -> None:
        """Change detection classes by replacing only cached text embeddings."""
        model = self._require_model()
        normalized_classes = self._normalize_classes(classes)
        missing_classes = [
            name
            for name in normalized_classes
            if name not in self._class_embedding_cache
        ]
        if missing_classes:
            raise ValueError(f"캐시에 없는 클래스입니다: {missing_classes}")

        world_model = model.model
        world_model.txt_feats = torch.cat(
            [self._class_embedding_cache[name] for name in normalized_classes],
            dim=1,
        )
        world_model.model[-1].nc = len(normalized_classes)
        world_model.names = normalized_classes

        if model.predictor is not None:
            model.predictor.model.names = normalized_classes

        self.__classes = normalized_classes

    def predict(self, frame: np.ndarray | str) -> tuple[Boxes, dict[int, str]]:
        """Run inference on an image or frame and return CPU boxes and names."""
        model = self._require_model()
        try:
            results = self._predict(model, frame)
        except RuntimeError as error:
            if (
                self._device_info.device != "mps"
                or "Placeholder storage has not been allocated" not in str(error)
            ):
                raise

            # Some YOLO-World operations/text embeddings are not stable on MPS.
            # Fall back once to CPU instead of terminating the whole pipeline.
            print(f"MPS 추론 실패, CPU로 전환합니다: {error}")
            self._device_info = DeviceInfo(
                device="cpu",
                name="CPU (MPS fallback)",
                acclerator=False,
            )
            # Reloading avoids copying an already-invalid MPS placeholder tensor.
            self._model = YOLOWorld(str(self._model_path))
            self._model.set_classes(self.__classes)
            results = self._predict(self._model, frame)

        return results.boxes.cpu(), results.names

    def _predict(self, model: YOLOWorld, frame: np.ndarray | str):
        return model.predict(
            source=frame,
            device=self._device_info.device,
            conf=self._confidence,
            imgsz=self._image_size,
            verbose=False,
        )[0]

    def close(self) -> None:
        """Drop the model and clear accelerator caches when available."""
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
        """Load the model when entering a context-manager block."""
        print("loading weight file\n")
        self.load()
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        """Release model resources when leaving a context-manager block."""
        self.close()

    def _require_model(self) -> YOLOWorld:
        """Return the loaded model or raise a lifecycle usage error."""
        if not self.is_loaded:
            raise RuntimeError(
                "YOLO-World 모델이 로딩되지 않았습니다. 먼저 load()를 호출하세요."
            )

        return self._model

    @staticmethod
    def _normalize_classes(classes: Sequence[str]) -> list[str]:
        """Trim class names, remove duplicates, and reject an empty class list."""
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
            result = manager.predict("./image.png", ["cat"])
            print(result[0].boxes)
        # manager = YOLO_World_Manager(confidence=0.45)
        # manager.load()
    except (ValueError, RuntimeError) as e:
        print(e)
