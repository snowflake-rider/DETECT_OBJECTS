"""Tests for routing a completed setup to its selected runtime interface."""

from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from detect_objects.launch_mode import RuntimeMode
from detect_objects.main import main


class LaunchRoutingTests(unittest.TestCase):
    def test_desktop_mode_uses_the_optional_desktop_launcher(self) -> None:
        context = SimpleNamespace(runtime_mode=RuntimeMode.DESKTOP)

        with (
            patch("detect_objects.main.run_app", return_value=context),
            patch("detect_objects.main._run_desktop_mode", return_value=0) as launch,
        ):
            result = main()

        self.assertEqual(result, 0)
        launch.assert_called_once_with()

    def test_classic_mode_keeps_the_existing_runtime_path(self) -> None:
        context = SimpleNamespace(
            runtime_mode=RuntimeMode.CLASSIC,
            ui_theme="monokai",
        )
        runtime = MagicMock()

        with (
            patch("detect_objects.main.run_app", return_value=context),
            patch("detect_objects.main.LocalRuntime", return_value=runtime),
            patch("detect_objects.main.run_startup_app", return_value=True) as startup,
        ):
            result = main()

        self.assertEqual(result, 0)
        startup.assert_called_once_with(runtime.prepare, "monokai")
        runtime.run.assert_called_once_with()
        runtime.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main(verbosity=2)
