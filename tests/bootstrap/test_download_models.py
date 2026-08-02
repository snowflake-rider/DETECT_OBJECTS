"""Tests for required model artifact provisioning."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from bootstrap.download_models import download_required_models
from detect_objects.models.model_config import configured_yolo_world_weights_path


VALID_YOLO_CONFIG = """
[vision.yolo_world]
weights = "../model_artifacts/vision/yolov8s-worldv2.pt"
confidence = 0.65
image_size = [640, 640]
"""


class DownloadModelsTests(unittest.TestCase):
    """Verify configured YOLO-World weights are present after provisioning."""

    def _write_config(self) -> tuple[Path, Path]:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        config_dir = Path(temporary_directory.name) / "config"
        config_dir.mkdir()
        config_path = config_dir / "models.toml"
        config_path.write_text(VALID_YOLO_CONFIG, encoding="utf-8")
        expected_weights = (
            Path(temporary_directory.name)
            / "model_artifacts"
            / "vision"
            / "yolov8s-worldv2.pt"
        ).resolve()
        return config_path, expected_weights

    def test_resolves_configured_weights_before_file_exists(self) -> None:
        config_path, expected_weights = self._write_config()

        weights = configured_yolo_world_weights_path(config_path)

        self.assertEqual(weights, expected_weights)

    def test_downloads_missing_weights_to_configured_path(self) -> None:
        config_path, expected_weights = self._write_config()

        def downloader(destination: Path) -> str:
            destination.write_bytes(b"model weights")
            return str(destination)

        downloaded = download_required_models(config_path, downloader=downloader)

        self.assertEqual(downloaded, (expected_weights,))
        self.assertTrue(expected_weights.is_file())

    def test_skips_download_when_weights_exist(self) -> None:
        config_path, expected_weights = self._write_config()
        expected_weights.parent.mkdir(parents=True)
        expected_weights.write_bytes(b"existing model weights")
        downloader = Mock()

        downloaded = download_required_models(config_path, downloader=downloader)

        self.assertEqual(downloaded, (expected_weights,))
        downloader.assert_not_called()

    def test_fails_when_downloader_does_not_create_weights(self) -> None:
        config_path, expected_weights = self._write_config()

        with self.assertRaisesRegex(RuntimeError, str(expected_weights)):
            download_required_models(config_path, downloader=lambda destination: "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
