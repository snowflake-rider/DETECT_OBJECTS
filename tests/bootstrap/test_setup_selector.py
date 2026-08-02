"""Tests for the dependency-free bootstrap environment selector."""

from __future__ import annotations

from pathlib import Path
import platform
import subprocess
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETUP_SCRIPT = PROJECT_ROOT / "bootstrap" / "setup.sh"
MACOS_SETUP_SCRIPT = PROJECT_ROOT / "bootstrap" / "macos" / "setup.sh"
LINUX_SETUP_SCRIPT = PROJECT_ROOT / "bootstrap" / "linux" / "setup.sh"
WINDOWS_SETUP_SCRIPT = PROJECT_ROOT / "bootstrap" / "windows" / "setup.ps1"


class SetupSelectorTests(unittest.TestCase):
    def run_setup(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SETUP_SCRIPT), *arguments],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_uv_dry_run_is_recommended_local_path(self) -> None:
        result = self.run_setup("uv", "--dry-run")

        self.assertEqual(result.returncode, 0, result.stderr)
        expected_platform = "macOS" if platform.system() == "Darwin" else "Linux"
        self.assertIn(f"Platform: {expected_platform}", result.stdout)
        self.assertIn("Selected: uv", result.stdout)
        self.assertIn("bootstrap/uv/setup.sh", result.stdout)
        self.assertIn(".odia-tools/bin/uv run odia", result.stdout)
        self.assertIn("odia-uv", result.stdout)

    def test_conda_and_miniconda_dispatch_to_distinct_setups(self) -> None:
        conda = self.run_setup("conda", "--dry-run")
        miniconda = self.run_setup("miniconda", "--dry-run")

        self.assertEqual(conda.returncode, 0, conda.stderr)
        self.assertEqual(miniconda.returncode, 0, miniconda.stderr)
        self.assertIn("bootstrap/conda/setup.sh", conda.stdout)
        self.assertIn("odia-conda", conda.stdout)
        self.assertIn("bootstrap/miniconda/setup.sh", miniconda.stdout)
        self.assertIn(".odia-tools/miniconda3/bin/conda", miniconda.stdout)
        self.assertIn("odia-miniconda", miniconda.stdout)

    def test_install_only_omits_launch(self) -> None:
        result = self.run_setup("uv", "--install-only", "--dry-run")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Would run:", result.stdout)
        self.assertNotIn("Would launch:", result.stdout)

    def test_invalid_manager_returns_usage_error(self) -> None:
        result = self.run_setup("unknown")

        self.assertEqual(result.returncode, 2)
        self.assertIn("Unknown option", result.stderr)

    def test_rejects_multiple_manager_choices(self) -> None:
        result = self.run_setup("uv", "--manager", "conda", "--dry-run")

        self.assertEqual(result.returncode, 2)
        self.assertIn("Choose only one", result.stderr)

    def test_noninteractive_run_requires_explicit_manager(self) -> None:
        result = self.run_setup()

        self.assertEqual(result.returncode, 2)
        self.assertIn("Choose explicitly", result.stderr)

    def test_current_unix_platform_entrypoint_dispatches(self) -> None:
        setup_script = (
            MACOS_SETUP_SCRIPT if platform.system() == "Darwin" else LINUX_SETUP_SCRIPT
        )
        result = subprocess.run(
            ["bash", str(setup_script), "uv", "--dry-run"],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        expected_name = "macOS" if platform.system() == "Darwin" else "Linux"
        self.assertIn(f"Platform: {expected_name}", result.stdout)

    def test_wrong_unix_platform_entrypoint_is_rejected(self) -> None:
        setup_script = (
            LINUX_SETUP_SCRIPT if platform.system() == "Darwin" else MACOS_SETUP_SCRIPT
        )
        result = subprocess.run(
            ["bash", str(setup_script), "uv", "--dry-run"],
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("can only run", result.stderr)

    def test_windows_entrypoint_uses_native_installers_and_paths(self) -> None:
        script = WINDOWS_SETUP_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("[char]0x2605", script)
        self.assertIn('Label = "$star Install uv"', script)
        self.assertIn('Label = "Use Conda"', script)
        self.assertIn('Label = "Install Miniconda"', script)
        self.assertIn("uv.exe", script)
        self.assertIn("UV_UNMANAGED_INSTALL", script)
        self.assertIn("Miniconda3-latest-Windows-x86_64.exe", script)
        self.assertIn("Invoke-WebRequest", script)
        self.assertIn("Starting ODIA device and model setup", script)


if __name__ == "__main__":
    unittest.main(verbosity=2)
