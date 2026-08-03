"""Tests for the active Whisper performance benchmark."""

import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from detect_objects.voice_text_convert import measure_performance


class MeasurePerformanceTests(unittest.TestCase):
    def test_uses_models_selected_by_the_vad_refactor(self) -> None:
        self.assertEqual(
            measure_performance.MODEL_NAMES,
            ["base", "small", "medium", "large", "turbo"],
        )

    def test_calculates_cer_after_normalizing_korean_text(self) -> None:
        self.assertEqual(
            measure_performance.calculate_cer(
                "폰과 사람을 찾아줘",
                "폰과, 사람을 찾아줘!",
            ),
            0.0,
        )

    @patch.object(measure_performance, "release_model")
    @patch.object(measure_performance.whisper, "load_model")
    def test_releases_model_when_transcription_fails(
        self,
        load_model: MagicMock,
        release_model: MagicMock,
    ) -> None:
        model = MagicMock()
        model.transcribe.side_effect = RuntimeError("transcription failed")
        load_model.return_value = model

        with self.assertRaisesRegex(RuntimeError, "transcription failed"):
            measure_performance.benchmark_model(
                "base",
                np.zeros(16, dtype=np.float32),
                "cpu",
            )

        release_model.assert_called_once_with(model, "cpu")


if __name__ == "__main__":
    unittest.main()
