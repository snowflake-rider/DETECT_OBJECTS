"""Tests for the Apple-Silicon SAM-Audio separator adapter."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from detect_objects.models.model_config import SamAudioMlxConfig
from detect_objects.models.sound.sam_audio_mlx import (
    SamAudioMlxSeparator,
    SamAudioUnavailableError,
)


class FakeRuntime:
    """Record separator lifecycle operations without loading MLX."""

    def __init__(self) -> None:
        self.download_calls = 0
        self.load_calls = 0
        self.separate_calls: list[tuple[Path, str]] = []
        self.saved: list[tuple[object, Path, int]] = []
        self.cache_cleared = False

    def download_model(self, config: SamAudioMlxConfig) -> Path:
        self.download_calls += 1
        return config.artifact_dir

    def load_model(self, model_path: Path, config: SamAudioMlxConfig):
        self.load_calls += 1
        return SimpleNamespace(sample_rate=48000), object()

    def separate(self, model, processor, audio_path, prompt, config):
        self.separate_calls.append((audio_path, prompt))
        return SimpleNamespace(
            target=["target-audio"],
            residual=["residual-audio"],
            peak_memory=1.25,
        )

    def save_audio(self, audio, path: Path, sample_rate: int) -> None:
        self.saved.append((audio, path, sample_rate))

    def clear_cache(self) -> None:
        self.cache_cleared = True


def make_config(artifact_dir: Path) -> SamAudioMlxConfig:
    """Return deterministic settings shared by separator tests."""
    return SamAudioMlxConfig(
        backend="sam_audio_mlx",
        model_id="mlx-community/sam-audio-small-fp16",
        artifact_dir=artifact_dir,
        text_encoder_id="google-t5/t5-base",
        text_encoder_dir=artifact_dir.parent / "t5_base",
        chunk_seconds=10.0,
        overlap_seconds=3.0,
        ode_step_size=0.0625,
        ode_decode_chunk_size=50,
        seed=42,
    )


class SamAudioMlxSeparatorTests(unittest.TestCase):
    """Verify lazy loading, result paths, reuse, and platform validation."""

    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.directory = Path(temporary_directory.name)
        self.audio_path = self.directory / "mixed.wav"
        self.audio_path.write_bytes(b"fake wav")
        self.runtime = FakeRuntime()
        self.separator = SamAudioMlxSeparator(
            make_config(self.directory / "artifacts"),
            runtime=self.runtime,
        )

    def test_separates_to_prompt_named_target_and_residual_paths(self) -> None:
        result = self.separator.separate_file(
            self.audio_path,
            prompt="Dog barking!",
            output_dir=self.directory / "outputs",
        )

        self.assertEqual(self.runtime.download_calls, 1)
        self.assertEqual(self.runtime.load_calls, 1)
        self.assertEqual(
            self.runtime.separate_calls,
            [(self.audio_path.resolve(), "Dog barking!")],
        )
        self.assertEqual(
            result.target_path.name,
            "mixed__dog_barking__target.wav",
        )
        self.assertEqual(
            result.residual_path.name,
            "mixed__dog_barking__residual.wav",
        )
        self.assertEqual(result.peak_memory_gb, 1.25)
        self.assertEqual(
            [saved[2] for saved in self.runtime.saved],
            [48000, 48000],
        )

    def test_reuses_loaded_model_for_multiple_requests(self) -> None:
        for prompt in ("dog barking", "cat meowing"):
            self.separator.separate_file(
                self.audio_path,
                prompt=prompt,
                output_dir=self.directory / "outputs",
            )

        self.assertEqual(self.runtime.download_calls, 1)
        self.assertEqual(self.runtime.load_calls, 1)
        self.assertEqual(len(self.runtime.separate_calls), 2)

    def test_rejects_empty_prompt_before_loading_model(self) -> None:
        with self.assertRaisesRegex(ValueError, "prompt must be non-empty"):
            self.separator.separate_file(
                self.audio_path,
                prompt="  ",
                output_dir=self.directory / "outputs",
            )

        self.assertEqual(self.runtime.download_calls, 0)

    def test_close_releases_loaded_state_and_clears_cache(self) -> None:
        self.separator.load()

        self.separator.close()

        self.assertFalse(self.separator.is_loaded)
        self.assertTrue(self.runtime.cache_cleared)

    def test_rejects_non_apple_silicon_platform(self) -> None:
        with (
            patch(
                "detect_objects.models.sound.sam_audio_mlx.platform.system",
                return_value="Linux",
            ),
            patch(
                "detect_objects.models.sound.sam_audio_mlx.platform.machine",
                return_value="x86_64",
            ),
        ):
            with self.assertRaises(SamAudioUnavailableError):
                self.separator.download()


if __name__ == "__main__":
    unittest.main(verbosity=2)
