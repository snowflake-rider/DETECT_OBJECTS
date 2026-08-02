"""Tests for selectable model presets and runtime factories."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from detect_objects.models import (
    DEFAULT_VISION_MODEL_ID,
    DEFAULT_VOICE_MODEL_ID,
    ModelSelection,
    get_model_option,
    list_model_options,
)
from detect_objects.models.factory import (
    create_vision_manager,
    create_voice_manager,
)


class ModelCatalogTests(unittest.TestCase):
    def test_default_selection_points_to_recommended_presets(self) -> None:
        selection = ModelSelection()

        self.assertEqual(selection.vision_id, DEFAULT_VISION_MODEL_ID)
        self.assertEqual(selection.voice_id, DEFAULT_VOICE_MODEL_ID)
        self.assertTrue(get_model_option(selection.vision_id).recommended)
        self.assertTrue(get_model_option(selection.voice_id).recommended)

    def test_catalog_separates_vision_and_voice_options(self) -> None:
        vision_options = list_model_options("vision")
        voice_options = list_model_options("voice")

        self.assertTrue(vision_options)
        self.assertTrue(voice_options)
        self.assertTrue(all(option.kind == "vision" for option in vision_options))
        self.assertTrue(all(option.kind == "voice" for option in voice_options))
        self.assertIn("whisper_tiny_ko", {option.id for option in voice_options})

    def test_selection_rejects_unknown_presets(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown vision model preset"):
            ModelSelection(vision_id="missing-model")


class ModelFactoryTests(unittest.TestCase):
    @patch("detect_objects.models.yolo_world_module.YOLO_World_Manager")
    def test_creates_default_vision_manager(self, manager_class) -> None:
        manager = create_vision_manager(DEFAULT_VISION_MODEL_ID)

        self.assertIs(manager, manager_class.return_value)
        manager_class.assert_called_once_with()

    @patch(
        "detect_objects.voice_text_convert.mic_whisper_manager.Whisper_Audio_Manager"
    )
    def test_creates_selected_whisper_variant(self, manager_class) -> None:
        manager = create_voice_manager("whisper_tiny_ko", device_id=7)

        self.assertIs(manager, manager_class.return_value)
        manager_class.assert_called_once_with(
            device_id=7,
            model_name="tiny",
            sample_rate=16000,
            channels=1,
            block_size=1024,
            record_seconds=5,
            language="ko",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
