"""Tests for communication between distributed ODIA nodes."""

import json
import socket
from threading import Event, Thread
import time
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from detect_objects.distributed.comm import receive_classes, send_classes


class SendClassesTests(unittest.TestCase):
    @patch("detect_objects.distributed.comm.urlopen")
    def test_posts_class_names_to_classes_endpoint(self, mock_urlopen) -> None:
        response = MagicMock()
        mock_urlopen.return_value.__enter__.return_value = response

        send_classes("http://192.168.1.10:8000/", ["person", "backpack"])

        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://192.168.1.10:8000/classes")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {"classes": ["person", "backpack"]},
        )
        mock_urlopen.assert_called_once_with(request, timeout=5)
        response.read.assert_called_once_with()

    def test_rejects_empty_yolo_address(self) -> None:
        with self.assertRaisesRegex(ValueError, "address cannot be empty"):
            send_classes("  ", ["person"])


class ReceiveClassesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.port = self._find_free_port()
        self.shutdown_event = Event()
        self.received: list[list[str]] = []
        self.server_thread = Thread(
            target=receive_classes,
            args=("127.0.0.1", self.port, self.received.append, self.shutdown_event),
            daemon=True,
        )
        self.server_thread.start()
        self._wait_until_server_starts()

    def tearDown(self) -> None:
        self.shutdown_event.set()
        self.server_thread.join(timeout=1)

    @staticmethod
    def _find_free_port() -> int:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    def _wait_until_server_starts(self) -> None:
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.1):
                    return
            except OSError:
                time.sleep(0.01)
        self.fail("Class receiver did not start")

    def test_receives_class_names(self) -> None:
        body = json.dumps({"classes": ["person", "backpack"]}).encode("utf-8")
        request = Request(
            f"http://127.0.0.1:{self.port}/classes",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlopen(request, timeout=1) as response:
            self.assertEqual(response.status, 204)

        self.assertEqual(self.received, [["person", "backpack"]])

    def test_rejects_invalid_message(self) -> None:
        request = Request(
            f"http://127.0.0.1:{self.port}/classes",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=1)

        self.assertEqual(raised.exception.code, 400)
        raised.exception.close()
        self.assertEqual(self.received, [])


if __name__ == "__main__":
    unittest.main()
