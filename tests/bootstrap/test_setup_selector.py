"""Tests for the dependency-free bootstrap environment selector."""

from __future__ import annotations

from pathlib import Path
import subprocess
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETUP_SCRIPT = PROJECT_ROOT / "bootstrap" / "setup.sh"
WINDOWS_SETUP_SCRIPT = PROJECT_ROOT / "bootstrap" / "setup.ps1"
FZF_MENU_SCRIPT = PROJECT_ROOT / "bootstrap" / "menus" / "fzf.sh"
SIMPLE_MENU_SCRIPT = PROJECT_ROOT / "bootstrap" / "menus" / "simple.sh"
FZF_INSTALLER = PROJECT_ROOT / "bootstrap" / "tools" / "install_fzf.sh"
CONDA_MANAGER = PROJECT_ROOT / "bootstrap" / "managers" / "conda.sh"
MINICONDA_MANAGER = PROJECT_ROOT / "bootstrap" / "managers" / "miniconda.sh"


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
        self.assertIn("[uv|conda]", result.stdout)
        self.assertIn("Portability:", result.stdout)
        self.assertIn("Consistency:", result.stdout)
        self.assertIn("Isolation:", result.stdout)
        self.assertIn("Validation:", result.stdout)
        self.assertIn("uv.lock keeps dependency versions consistent", result.stdout)
        self.assertIn("uv sync --locked detects an outdated lockfile", result.stdout)

    def test_invalid_manager_returns_usage_error(self) -> None:
        result = self.run_setup("unknown")

        self.assertEqual(result.returncode, 2)
        self.assertIn("Choose uv or conda", result.stderr)

    def test_miniconda_is_not_a_separate_manager_choice(self) -> None:
        result = self.run_setup("miniconda")

        self.assertEqual(result.returncode, 2)
        self.assertIn("Choose uv or conda", result.stderr)

    def test_noninteractive_run_requires_explicit_manager(self) -> None:
        result = self.run_setup()

        self.assertEqual(result.returncode, 2)
        self.assertIn("Choose directly", result.stderr)

    def test_unix_menu_uses_optional_fzf_with_simple_fallback(self) -> None:
        setup = SETUP_SCRIPT.read_text(encoding="utf-8")
        fzf_menu = FZF_MENU_SCRIPT.read_text(encoding="utf-8")
        simple_menu = SIMPLE_MENU_SCRIPT.read_text(encoding="utf-8")
        installer = FZF_INSTALLER.read_text(encoding="utf-8")

        self.assertIn("fzf is not installed. Install it locally?", setup)
        self.assertIn('menus/fzf.sh', setup)
        self.assertIn('menus/simple.sh', setup)
        self.assertIn('install_project_fzf', installer)
        self.assertIn('--bin', installer)
        self.assertIn('fzf_version="0.72.0"', installer)
        self.assertIn('choose_manager()', fzf_menu)
        self.assertIn('choose_manager()', simple_menu)
        self.assertIn("Portability:", fzf_menu)
        self.assertIn("Consistency:", simple_menu)
        self.assertIn("uv.lock keeps dependency versions consistent", fzf_menu)
        self.assertIn("uv manages Python locally", fzf_menu)
        self.assertIn("uv sync --locked detects dependency changes", fzf_menu)
        self.assertIn("uv.lock keeps dependency versions consistent", simple_menu)
        self.assertIn("uv manages Python locally", simple_menu)
        self.assertIn("uv sync --locked detects dependency changes", simple_menu)

    def test_conda_uses_private_miniconda_as_a_fallback(self) -> None:
        conda_manager = CONDA_MANAGER.read_text(encoding="utf-8")
        miniconda_manager = MINICONDA_MANAGER.read_text(encoding="utf-8")

        self.assertIn('exec "${bootstrap_dir}/managers/miniconda.sh"', conda_manager)
        self.assertIn('conda_env_dir="${state_dir}/envs/conda"', miniconda_manager)

    def test_windows_entrypoint_uses_native_installers_and_paths(self) -> None:
        script = WINDOWS_SETUP_SCRIPT.read_text(encoding="utf-8")

        self.assertIn('"⚡️ uv          Locked and portable (recommended)"', script)
        self.assertIn('"🐍 Conda       Installed automatically if missing"', script)
        self.assertIn("Portability:", script)
        self.assertIn("Consistency:", script)
        self.assertIn("Isolation:", script)
        self.assertIn("Validation:", script)
        self.assertIn("uv.lock keeps dependency versions consistent", script)
        self.assertIn("uv manages Python locally", script)
        self.assertIn("uv sync --locked detects dependency changes", script)
        self.assertIn("[Console]::ReadKey", script)
        self.assertIn('"UpArrow"', script)
        self.assertIn('"DownArrow"', script)
        self.assertNotIn('return "miniconda"', script)
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
