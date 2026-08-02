"""Tests for choosing the runtime interface after device setup."""

from __future__ import annotations

import unittest

from textual.app import App
from textual.widgets import Button, RadioButton, RadioSet, Static

from detect_objects.launch_mode import RuntimeMode
from detect_objects.tui.runtime_mode_screen import RuntimeModeScreen


class RuntimeModeTestApp(App[RuntimeMode | None]):
    """Host the launch-mode screen without running device discovery."""

    def on_mount(self) -> None:
        self.push_screen(RuntimeModeScreen(), self.exit)


class RuntimeModeScreenTests(unittest.IsolatedAsyncioTestCase):
    async def test_presents_clear_desktop_and_classic_choices(self) -> None:
        app = RuntimeModeTestApp()

        async with app.run_test(size=(110, 32)) as pilot:
            await pilot.pause()
            content = " ".join(
                str(widget.content) for widget in app.screen.query(Static)
            )
            labels = " ".join(
                str(widget.label) for widget in app.screen.query(RadioButton)
            )

            self.assertIn("integrated desktop preview", content)
            self.assertIn("Desktop Dashboard", labels)
            self.assertIn("PySide6", content)
            self.assertIn("Classic Runtime", labels)
            self.assertIn("OpenCV", content)
            self.assertIsNotNone(app.screen.query_one("#mode-desktop", RadioButton))
            self.assertIsNotNone(app.screen.query_one("#mode-classic", RadioButton))
            self.assertIsNotNone(app.screen.query_one("#launch-runtime", Button))
            selected = app.screen.query_one("#runtime-mode", RadioSet).pressed_button
            self.assertEqual(selected.id, "mode-classic")

    async def test_returns_desktop_mode(self) -> None:
        app = RuntimeModeTestApp()

        async with app.run_test(size=(110, 32)) as pilot:
            await pilot.click("#mode-desktop")
            await pilot.click("#launch-runtime")
            await pilot.pause()

        self.assertIs(app.return_value, RuntimeMode.DESKTOP)

    async def test_returns_classic_mode(self) -> None:
        app = RuntimeModeTestApp()

        async with app.run_test(size=(110, 32)) as pilot:
            await pilot.click("#launch-runtime")
            await pilot.pause()

        self.assertIs(app.return_value, RuntimeMode.CLASSIC)


if __name__ == "__main__":
    unittest.main(verbosity=2)
