"""Tests for the dependency-free bootstrap environment selector."""

from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETUP_SCRIPT = PROJECT_ROOT / "bootstrap" / "setup.sh"
WINDOWS_SETUP_SCRIPT = PROJECT_ROOT / "bootstrap" / "setup.ps1"


class SetupSelectorTests(unittest.TestCase):
    def run_setup(
        self,
        *arguments: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SETUP_SCRIPT), *arguments],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_help_lists_available_managers(self) -> None:
        result = self.run_setup("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[uv|conda|miniconda]", result.stdout)

    def test_invalid_manager_returns_usage_error(self) -> None:
        result = self.run_setup("unknown")

        self.assertEqual(result.returncode, 2)
        self.assertIn("Choose uv, conda, or miniconda", result.stderr)

    def test_noninteractive_run_requires_explicit_manager(self) -> None:
        result = self.run_setup()

        self.assertEqual(result.returncode, 2)
        self.assertIn("Choose directly", result.stderr)

    def test_windows_entrypoint_uses_native_installers_and_paths(self) -> None:
        script = WINDOWS_SETUP_SCRIPT.read_text(encoding="utf-8")

        self.assertIn('Write-Host "1) uv (recommended: faster)"', script)
        self.assertIn('Write-Host "2) Conda"', script)
        self.assertIn('Write-Host "3) Miniconda"', script)
        self.assertIn('Read-Host "Choose 1-3"', script)
        self.assertIn("uv.exe", script)
        self.assertIn("UV_UNMANAGED_INSTALL", script)
        self.assertIn('Join-Path $ProjectRoot ".odia"', script)
        self.assertIn('Join-Path $StateDir "envs\\uv"', script)
        self.assertIn('Join-Path $StateDir "caches\\conda"', script)
        self.assertIn("Miniconda3-latest-Windows-x86_64.exe", script)
        self.assertIn("Invoke-WebRequest", script)
        self.assertIn("Environment ready. Starting ODIA", script)


if __name__ == "__main__":
    unittest.main(verbosity=2)
