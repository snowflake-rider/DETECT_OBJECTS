"""Tests for AI-model TOML configuration validation."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from detect_objects.models.model_config import (
    load_sam_audio_mlx_config,
)

VALID_SEPARATOR_CONFIG = """
[audio.source_separator]
backend = "sam_audio_mlx"
model_id = "mlx-community/sam-audio-small-fp16"
artifact_dir = "../model_artifacts/audio/sam_audio_small_fp16"
text_encoder_id = "google-t5/t5-base"
text_encoder_dir = "../model_artifacts/audio/t5_base"
chunk_seconds = 10.0
overlap_seconds = 3.0
ode_step_size = 0.0625
ode_decode_chunk_size = 50
seed = 42
"""


class SamAudioMlxConfigTests(unittest.TestCase):
    """Verify MLX source-separator configuration and path handling."""

    def _write_config(self, contents: str) -> Path:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        config_dir = Path(temporary_directory.name) / "config"
        config_dir.mkdir()
        path = config_dir / "models.toml"
        path.write_text(contents, encoding="utf-8")
        return path

    def test_loads_separator_and_resolves_artifact_directory(self) -> None:
        config_path = self._write_config(VALID_SEPARATOR_CONFIG)

        config = load_sam_audio_mlx_config(config_path)

        self.assertEqual(config.backend, "sam_audio_mlx")
        self.assertEqual(config.model_id, "mlx-community/sam-audio-small-fp16")
        self.assertEqual(
            config.artifact_dir,
            (
                config_path.parent.parent / "model_artifacts/audio/sam_audio_small_fp16"
            ).resolve(),
        )
        self.assertEqual(config.text_encoder_id, "google-t5/t5-base")
        self.assertEqual(
            config.text_encoder_dir,
            (config_path.parent.parent / "model_artifacts/audio/t5_base").resolve(),
        )
        self.assertEqual(config.chunk_seconds, 10.0)
        self.assertEqual(config.overlap_seconds, 3.0)
        self.assertEqual(config.ode_decode_chunk_size, 50)
        self.assertEqual(config.seed, 42)

    def test_rejects_overlap_equal_to_chunk_duration(self) -> None:
        invalid_config = VALID_SEPARATOR_CONFIG.replace(
            "overlap_seconds = 3.0",
            "overlap_seconds = 10.0",
        )

        with self.assertRaisesRegex(ValueError, "overlap_seconds"):
            load_sam_audio_mlx_config(self._write_config(invalid_config))


if __name__ == "__main__":
    unittest.main(verbosity=2)
