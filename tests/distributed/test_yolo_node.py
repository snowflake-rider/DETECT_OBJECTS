"""Tests for the distributed YOLO node."""

import queue
import sys
from types import ModuleType
import unittest
from unittest.mock import MagicMock, patch

from detect_objects.distributed import yolo_node
from detect_objects.distributed.yolo_node import main, run_yolo_node, update_classes


class UpdateClassesTests(unittest.TestCase):
    @patch("detect_objects.distributed.yolo_node.time.perf_counter", return_value=12.5)
    def test_adds_class_names_to_empty_queue(self, _mock_time) -> None:
        class_queue = queue.Queue(maxsize=1)

        update_classes(["person"], class_queue)

        self.assertEqual(class_queue.get_nowait(), (["person"], 12.5))

    @patch("detect_objects.distributed.yolo_node.time.perf_counter", return_value=20.0)
    def test_replaces_old_class_names(self, _mock_time) -> None:
        class_queue = queue.Queue(maxsize=1)
        class_queue.put_nowait((["car"], 10.0))

        update_classes(["person", "backpack"], class_queue)

        self.assertEqual(
            class_queue.get_nowait(),
            (["person", "backpack"], 20.0),
        )


class RunYoloNodeTests(unittest.TestCase):
    @patch.object(yolo_node, "receive_classes")
    @patch.object(yolo_node, "Text_Manager")
    def test_connects_receiver_to_camera(self, text_manager_class, receive_classes) -> None:
        text_manager = text_manager_class.return_value.__enter__.return_value
        text_manager.get_supported_yolo_classes.return_value = ["person", "backpack"]

        def receive_one_message(host, port, callback, shutdown_event) -> None:
            callback(["backpack"])

        receive_classes.side_effect = receive_one_message

        camera_manager = MagicMock()
        camera_manager_class = MagicMock(return_value=camera_manager)
        camera_module = ModuleType("detect_objects.camera_cv.camera_cv")
        camera_module.Camera_Manager = camera_manager_class

        with patch.dict(
            sys.modules,
            {"detect_objects.camera_cv.camera_cv": camera_module},
        ):
            run_yolo_node("127.0.0.1", 8000, camera_index=3)

        camera_manager_class.assert_called_once()
        camera_arguments = camera_manager_class.call_args.kwargs
        self.assertEqual(camera_arguments["camera_index"], 3)
        self.assertEqual(
            camera_arguments["supported_classes"],
            ["person", "backpack"],
        )

        queued_classes, _received_at = camera_arguments[
            "class_names_queue"
        ].get_nowait()
        self.assertEqual(queued_classes, ["backpack"])
        self.assertTrue(camera_arguments["thread_event"].is_set())

        camera_manager.load_model.assert_called_once_with()
        camera_manager.start_record.assert_called_once_with()
        camera_manager.unload.assert_called_once_with()


class MainTests(unittest.TestCase):
    @patch.object(yolo_node, "run_yolo_node")
    def test_starts_yolo_node_with_command_line_options(self, run_node) -> None:
        exit_code = main(
            [
                "--host",
                "192.168.1.10",
                "--port",
                "9000",
                "--camera-index",
                "2",
            ]
        )

        self.assertEqual(exit_code, 0)
        run_node.assert_called_once_with(
            host="192.168.1.10",
            port=9000,
            camera_index=2,
        )


if __name__ == "__main__":
    unittest.main()
