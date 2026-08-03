"""Fast tests for model handler input contracts."""

import unittest

from detect_objects.distributed.model_handlers import EchoHandler, _required_base64


class EchoHandlerTests(unittest.TestCase):
    def test_returns_payload_without_loading_ai_dependencies(self) -> None:
        handler = EchoHandler()

        self.assertEqual(handler({"number": 3}), {"echo": {"number": 3}})


class Base64ValidationTests(unittest.TestCase):
    def test_rejects_malformed_binary_payload(self) -> None:
        with self.assertRaisesRegex(ValueError, "valid base64"):
            _required_base64({"audio": "%%%"}, "audio")


if __name__ == "__main__":
    unittest.main()
