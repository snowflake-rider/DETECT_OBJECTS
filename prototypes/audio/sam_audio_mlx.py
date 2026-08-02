"""Prompt-guided SAM-Audio source separation through Apple MLX."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import platform
import re
from time import perf_counter
from typing import Any, Protocol, Self

from detect_objects.models.model_config import SamAudioMlxConfig


class SamAudioUnavailableError(RuntimeError):
    """Raised when the MLX separator cannot run on the current platform."""


class SamAudioSeparationError(RuntimeError):
    """Raised when SAM-Audio cannot download, load, or separate an input."""


@dataclass(frozen=True)
class SeparationOutput:
    """Files and measurements produced by one separation request."""

    target_path: Path
    residual_path: Path
    prompt: str
    elapsed_seconds: float
    peak_memory_gb: float | None


class SamAudioRuntime(Protocol):
    """Operations that isolate the MLX dependency from project logic."""

    def download_model(self, config: SamAudioMlxConfig) -> Path:
        """Download or locate the configured model artifact directory."""
        ...

    def load_model(
        self,
        model_path: Path,
        config: SamAudioMlxConfig,
    ) -> tuple[Any, Any]:
        """Return a loaded SAM-Audio model and processor."""
        ...

    def separate(
        self,
        model: Any,
        processor: Any,
        audio_path: Path,
        prompt: str,
        config: SamAudioMlxConfig,
    ) -> Any:
        """Run prompt-guided source separation."""
        ...

    def save_audio(self, audio: Any, path: Path, sample_rate: int) -> None:
        """Save one separated waveform as a WAV file."""
        ...

    def clear_cache(self) -> None:
        """Release cached MLX allocations where possible."""
        ...


class MlxAudioRuntime:
    """Concrete adapter around Hugging Face, MLX, and MLX-Audio."""

    def download_model(self, config: SamAudioMlxConfig) -> Path:
        """Keep SAM-Audio and its T5 encoder in project artifact directories."""
        from huggingface_hub import snapshot_download

        if not _has_local_checkpoint(config.artifact_dir):
            config.artifact_dir.mkdir(parents=True, exist_ok=True)
            snapshot_download(
                repo_id=config.model_id,
                local_dir=str(config.artifact_dir),
                allow_patterns=["*.safetensors", "*.json"],
            )

        if not _has_text_encoder_artifacts(config.text_encoder_dir):
            config.text_encoder_dir.mkdir(parents=True, exist_ok=True)
            snapshot_download(
                repo_id=config.text_encoder_id,
                local_dir=str(config.text_encoder_dir),
                allow_patterns=[
                    "config.json",
                    "model.safetensors",
                    "spiece.model",
                    "tokenizer.json",
                    "tokenizer_config.json",
                    "special_tokens_map.json",
                ],
            )

        return config.artifact_dir

    def load_model(
        self,
        model_path: Path,
        config: SamAudioMlxConfig,
    ) -> tuple[Any, Any]:
        """Load SAM-Audio, T5, and audio preprocessing from local artifacts."""
        from mlx_audio.sts import SAMAudio, SAMAudioProcessor

        processor = SAMAudioProcessor.from_pretrained(model_path)
        model = SAMAudio.from_pretrained(model_path)
        self._load_text_encoder(model, config.text_encoder_dir)
        return model, processor

    @staticmethod
    def _load_text_encoder(model: Any, text_encoder_dir: Path) -> None:
        """Preload T5 locally so MLX-Audio never downloads during inference."""
        import mlx.core as mx
        from mlx_audio.sts.models.sam_audio.text_encoder import T5Config, T5Encoder
        from transformers import AutoTokenizer

        with (text_encoder_dir / "config.json").open(encoding="utf-8") as file:
            source_config = json.load(file)

        encoder_config = T5Config(
            vocab_size=source_config.get("vocab_size", 32128),
            d_model=source_config.get("d_model", 768),
            d_kv=source_config.get("d_kv", 64),
            d_ff=source_config.get("d_ff", 3072),
            num_layers=source_config.get("num_layers", 12),
            num_heads=source_config.get("num_heads", 12),
            relative_attention_num_buckets=source_config.get(
                "relative_attention_num_buckets", 32
            ),
            relative_attention_max_distance=source_config.get(
                "relative_attention_max_distance", 128
            ),
            dropout_rate=source_config.get("dropout_rate", 0.1),
            layer_norm_epsilon=source_config.get("layer_norm_epsilon", 1e-6),
            is_gated_act=source_config.get("is_gated_act", False),
            dense_act_fn=source_config.get("dense_act_fn", "relu"),
        )
        encoder = T5Encoder(encoder_config)
        weights = mx.load(str(text_encoder_dir / "model.safetensors"))
        encoder.load_weights(list(T5Encoder.sanitize(weights).items()))
        mx.eval(encoder.parameters())
        encoder.eval()

        model.text_encoder.tokenizer = AutoTokenizer.from_pretrained(
            text_encoder_dir,
            local_files_only=True,
        )
        model.text_encoder.model = encoder

    def separate(
        self,
        model: Any,
        processor: Any,
        audio_path: Path,
        prompt: str,
        config: SamAudioMlxConfig,
    ) -> Any:
        """Separate a possibly long file with overlapped MLX chunks."""
        batch = processor(
            descriptions=[prompt],
            audios=[str(audio_path)],
        )
        return model.separate_long(
            batch.audios,
            descriptions=batch.descriptions,
            chunk_seconds=config.chunk_seconds,
            overlap_seconds=config.overlap_seconds,
            anchor_ids=batch.anchor_ids,
            anchor_alignment=batch.anchor_alignment,
            ode_opt={"method": "midpoint", "step_size": config.ode_step_size},
            ode_decode_chunk_size=config.ode_decode_chunk_size,
            seed=config.seed,
        )

    def save_audio(self, audio: Any, path: Path, sample_rate: int) -> None:
        """Delegate WAV encoding to MLX-Audio."""
        from mlx_audio.sts import save_audio

        save_audio(audio, str(path), sample_rate=sample_rate)

    def clear_cache(self) -> None:
        """Release reusable MLX Metal allocations."""
        import mlx.core as mx

        mx.clear_cache()


class SamAudioMlxSeparator:
    """Own a lazily loaded SAM-Audio Small model and separate requested sounds."""

    def __init__(
        self,
        config: SamAudioMlxConfig,
        runtime: SamAudioRuntime | None = None,
    ) -> None:
        """Configure model artifacts and allow a fake runtime in tests."""
        self._config = config
        self._runtime = runtime or MlxAudioRuntime()
        self._model: Any | None = None
        self._processor: Any | None = None

    @property
    def is_loaded(self) -> bool:
        """Return whether both the model and processor are ready."""
        return self._model is not None and self._processor is not None

    @property
    def artifact_dir(self) -> Path:
        """Return the configured local model-artifact directory."""
        return self._config.artifact_dir

    def download(self) -> Path:
        """Download the checkpoint if it is not already present."""
        self._ensure_available()
        try:
            return self._runtime.download_model(self._config)
        except (ImportError, OSError, RuntimeError) as error:
            raise SamAudioSeparationError(
                f"Could not download SAM-Audio model: {error}"
            ) from error

    def load(self) -> None:
        """Load the checkpoint and processor once for repeated separations."""
        if self.is_loaded:
            return

        model_path = self.download()
        try:
            self._model, self._processor = self._runtime.load_model(
                model_path,
                self._config,
            )
        except (ImportError, OSError, RuntimeError, ValueError) as error:
            raise SamAudioSeparationError(
                f"Could not load SAM-Audio model from {model_path}: {error}"
            ) from error

    def separate_file(
        self,
        audio_path: str | Path,
        prompt: str,
        output_dir: str | Path,
    ) -> SeparationOutput:
        """Extract a prompted sound and save target and residual WAV files."""
        normalized_prompt = prompt.strip()
        if not normalized_prompt:
            raise ValueError("prompt must be non-empty")

        resolved_audio_path = Path(audio_path).expanduser().resolve()
        if not resolved_audio_path.is_file():
            raise FileNotFoundError(f"Audio file was not found: {resolved_audio_path}")

        resolved_output_dir = Path(output_dir).expanduser().resolve()
        resolved_output_dir.mkdir(parents=True, exist_ok=True)
        prompt_slug = _slugify(normalized_prompt)
        output_prefix = f"{resolved_audio_path.stem}__{prompt_slug}"
        target_path = resolved_output_dir / f"{output_prefix}__target.wav"
        residual_path = resolved_output_dir / f"{output_prefix}__residual.wav"

        self.load()
        started_at = perf_counter()
        try:
            result = self._runtime.separate(
                self._model,
                self._processor,
                resolved_audio_path,
                normalized_prompt,
                self._config,
            )
            sample_rate = int(self._model.sample_rate)
            self._runtime.save_audio(result.target[0], target_path, sample_rate)
            self._runtime.save_audio(result.residual[0], residual_path, sample_rate)
        except (OSError, RuntimeError, ValueError, IndexError, AttributeError) as error:
            raise SamAudioSeparationError(
                f"SAM-Audio separation failed for {resolved_audio_path}: {error}"
            ) from error

        peak_memory = getattr(result, "peak_memory", None)
        return SeparationOutput(
            target_path=target_path,
            residual_path=residual_path,
            prompt=normalized_prompt,
            elapsed_seconds=perf_counter() - started_at,
            peak_memory_gb=float(peak_memory) if peak_memory is not None else None,
        )

    def close(self) -> None:
        """Drop loaded model references and release cached MLX allocations."""
        self._model = None
        self._processor = None
        self._runtime.clear_cache()

    def __enter__(self) -> Self:
        """Load the separator for one or more requests."""
        self.load()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        """Release model resources when leaving the context."""
        self.close()

    @staticmethod
    def _ensure_available() -> None:
        """Require an Apple Silicon Mac before importing MLX dependencies."""
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            raise SamAudioUnavailableError(
                "SAM-Audio MLX requires a macOS computer with Apple Silicon"
            )


def _slugify(value: str) -> str:
    """Create a readable, filesystem-safe fragment from a text prompt."""
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "target_sound"


def _has_local_checkpoint(directory: Path) -> bool:
    """Return whether a local model directory has config and safe weights."""
    return (directory / "config.json").is_file() and (
        directory / "model.safetensors"
    ).is_file()


def _has_text_encoder_artifacts(directory: Path) -> bool:
    """Return whether T5 weights and at least one tokenizer format exist."""
    return _has_local_checkpoint(directory) and any(
        (directory / filename).is_file()
        for filename in ("tokenizer.json", "spiece.model")
    )
