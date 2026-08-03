"""Model adapters exposed by a distributed inference worker."""

from __future__ import annotations

import base64
import binascii
import threading
from typing import Any, Protocol

JsonObject = dict[str, Any]

YOLO_CAPABILITY = "vision:yolo_world_v2_small"
WHISPER_MODELS = ("tiny", "base", "small", "medium", "large-v3")
WHISPER_CAPABILITIES = tuple(f"voice:whisper_{name}_ko" for name in WHISPER_MODELS)
BUILTIN_CAPABILITIES = ("system:echo", YOLO_CAPABILITY, *WHISPER_CAPABILITIES)


class ModelHandler(Protocol):
    """Small worker seam hiding a model's loading and inference details."""

    def __call__(self, payload: JsonObject) -> JsonObject: ...

    def close(self) -> None: ...


class EchoHandler:
    """Dependency-free handler used to verify the cluster path."""

    def __call__(self, payload: JsonObject) -> JsonObject:
        return {"echo": payload}

    def close(self) -> None:
        return


class YoloWorldHandler:
    """Keep YOLO loaded and run JPEG frames sent by cluster clients."""

    def __init__(self) -> None:
        from ..models.factory import create_vision_manager
        from ..voice_text_convert.parse_and_match_module import Text_Manager

        manager = create_vision_manager("yolo_world_v2_small")
        manager.load()
        with Text_Manager() as text_manager:
            supported_classes = text_manager.get_supported_yolo_classes()
        manager.cache_class_embeddings(supported_classes)
        self._manager = manager
        self._supported_classes = frozenset(supported_classes)
        self._active_classes: tuple[str, ...] = ()
        self._lock = threading.Lock()

    def __call__(self, payload: JsonObject) -> JsonObject:
        import cv2
        import numpy as np

        encoded = _required_base64(payload, "image_jpeg_base64")
        classes = payload.get("classes")
        if not isinstance(classes, list) or not classes or not all(
            isinstance(name, str) and name for name in classes
        ):
            raise ValueError("classes must be a non-empty list of names")
        normalized_classes = tuple(dict.fromkeys(classes))
        unsupported = sorted(set(normalized_classes) - self._supported_classes)
        if unsupported:
            raise ValueError(f"unsupported YOLO classes: {', '.join(unsupported)}")

        frame = cv2.imdecode(np.frombuffer(encoded, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("image_jpeg_base64 is not a valid JPEG image")

        with self._lock:
            if normalized_classes != self._active_classes:
                self._manager.activate_cached_classes(normalized_classes)
                self._active_classes = normalized_classes
            boxes, names = self._manager.predict(frame)

        detections = []
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            class_id = int(box.cls[0].item())
            detections.append(
                {
                    "bounds": [int(x1), int(y1), int(x2), int(y2)],
                    "class_name": names[class_id],
                    "confidence": float(box.conf[0].item()),
                }
            )
        height, width = frame.shape[:2]
        return {"width": width, "height": height, "detections": detections}

    def close(self) -> None:
        self._manager.close()


class WhisperHandler:
    """Keep one Whisper model loaded and transcribe mono 16 kHz PCM."""

    def __init__(self, model_name: str) -> None:
        import torch
        import whisper

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = whisper.load_model(model_name, device=self._device)
        self._lock = threading.Lock()

    def __call__(self, payload: JsonObject) -> JsonObject:
        import numpy as np

        if payload.get("sample_rate", 16000) != 16000:
            raise ValueError("Whisper input sample_rate must be 16000")
        pcm = _required_base64(payload, "audio_pcm16_base64")
        if len(pcm) % 2:
            raise ValueError("audio_pcm16_base64 must contain 16-bit PCM samples")
        audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        if audio.size == 0:
            raise ValueError("audio_pcm16_base64 cannot be empty")

        with self._lock:
            result = self._model.transcribe(
                audio,
                language="ko",
                task="transcribe",
                fp16=self._device == "cuda",
            )
        return {"text": result["text"].strip(), "language": "ko"}

    def close(self) -> None:
        self._model = None


def create_model_handler(capability: str) -> ModelHandler:
    """Load the model adapter named by one advertised capability."""
    if capability == "system:echo":
        return EchoHandler()
    if capability == YOLO_CAPABILITY:
        return YoloWorldHandler()
    if capability in WHISPER_CAPABILITIES:
        model_name = capability.removeprefix("voice:whisper_").removesuffix("_ko")
        return WhisperHandler(model_name)
    available = ", ".join(BUILTIN_CAPABILITIES)
    raise ValueError(f"unknown model capability {capability!r}; choose from: {available}")


def _required_base64(payload: JsonObject, key: str) -> bytes:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty base64 string")
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError(f"{key} must be valid base64") from error
