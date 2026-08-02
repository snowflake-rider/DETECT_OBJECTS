"""Tests for local runtime preparation and startup updates."""

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from detect_objects.runtime import LocalRuntime, STARTUP_STEPS


class LocalRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = SimpleNamespace(
            models=SimpleNamespace(
                voice_id="test-voice",
                vision_id="test-vision",
            ),
            audio_input=SimpleNamespace(
                info=SimpleNamespace(index=3, name="Test Microphone")
            ),
            camera=SimpleNamespace(
                info=SimpleNamespace(
                    index=2,
                    name="Test Camera",
                    backend=100,
                )
            ),
        )

    def test_prepare_reports_each_finished_step(self) -> None:
        text_manager = MagicMock()
        text_manager.__enter__.return_value = text_manager
        text_manager.get_supported_yolo_classes.return_value = ["cat", "person"]

        whisper_manager = MagicMock()
        camera_manager = MagicMock()
        camera_manager.inference_device_name = "Apple MPS"

        with (
            patch(
                "detect_objects.runtime.Text_Manager",
                return_value=text_manager,
            ),
            patch(
                "detect_objects.runtime.create_voice_manager",
                return_value=whisper_manager,
            ) as voice_factory,
            patch(
                "detect_objects.runtime.Camera_Manager",
                return_value=camera_manager,
            ) as camera_factory,
        ):
            runtime = LocalRuntime(self.context)
            self.addCleanup(runtime.close)
            updates = []

            runtime.prepare(updates.append)

        finished_steps = [update.step for update in updates if update.finished]
        self.assertEqual(finished_steps, list(STARTUP_STEPS))
        self.assertIn("2 classes", updates[1].message)
        self.assertIn("Apple MPS", updates[-1].message)
        voice_factory.assert_called_once_with("test-voice", device_id=3)
        whisper_manager.load_model.assert_called_once_with()
        whisper_manager.create_stream.assert_called_once_with()
        camera_factory.assert_called_once_with(
            camera_index=2,
            camera_backend=100,
            thread_event=runtime.shutdown_event,
            class_names_queue=runtime.class_names_queue,
            supported_classes=["cat", "person"],
            vision_model_id="test-vision",
        )
        camera_manager.load_model.assert_called_once_with()

    def test_run_requires_successful_preparation(self) -> None:
        runtime = LocalRuntime(self.context)
        self.addCleanup(runtime.close)

        with self.assertRaisesRegex(RuntimeError, "finish startup"):
            runtime.run()


if __name__ == "__main__":
    unittest.main(verbosity=2)
