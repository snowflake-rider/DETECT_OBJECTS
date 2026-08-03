"""Tests for the dependency-free bootstrap environment selector."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tomllib
import unittest

from bootstrap.tools.verify_environment import REQUIRED_MODULES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETUP_SCRIPT = PROJECT_ROOT / "bootstrap" / "setup.sh"
WINDOWS_SETUP_SCRIPT = PROJECT_ROOT / "bootstrap" / "setup.ps1"
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

    def test_help_describes_uv_only_setup(self) -> None:
        result = self.run_setup("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[uv]", result.stdout)
        self.assertIn("Conda status:", result.stdout)
        self.assertIn("uv workflow is verified and working reliably", result.stdout)
        self.assertIn("while Conda support is reviewed", result.stdout)
        self.assertIn("Portability:", result.stdout)
        self.assertIn("Consistency:", result.stdout)
        self.assertIn("Isolation:", result.stdout)
        self.assertIn("Validation:", result.stdout)
        self.assertIn("uv.lock keeps dependency versions consistent", result.stdout)
        self.assertIn("uv sync --locked detects an outdated lockfile", result.stdout)

    def test_invalid_manager_returns_usage_error(self) -> None:
        result = self.run_setup("unknown")

        self.assertEqual(result.returncode, 2)
        self.assertIn("Only uv is currently supported", result.stderr)

    def test_conda_is_disabled(self) -> None:
        result = self.run_setup("conda")

        self.assertEqual(result.returncode, 2)
        self.assertIn("Conda setup is temporarily disabled", result.stderr)
        self.assertIn("uv workflow is verified and working reliably", result.stderr)
        self.assertIn("while Conda support is reviewed", result.stderr)

    def test_miniconda_is_not_a_separate_manager_choice(self) -> None:
        result = self.run_setup("miniconda")

        self.assertEqual(result.returncode, 2)
        self.assertIn("Only uv is currently supported", result.stderr)

    def test_unix_entrypoint_defaults_to_uv_without_a_menu(self) -> None:
        setup = SETUP_SCRIPT.read_text(encoding="utf-8")

        self.assertIn('selected_manager="${1:-uv}"', setup)
        self.assertIn('exec "${bootstrap_dir}/managers/uv.sh"', setup)
        self.assertNotIn("menus/fzf.sh", setup)
        self.assertNotIn("menus/simple.sh", setup)

        manager = (PROJECT_ROOT / "bootstrap" / "managers" / "uv.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("sync --locked --no-dev", manager)
        self.assertIn("run --no-dev odia", manager)

    def test_mandatory_desktop_and_optional_audio_dependencies(self) -> None:
        with (PROJECT_ROOT / "pyproject.toml").open("rb") as project_file:
            project = tomllib.load(project_file)

        base_dependencies = project["project"]["dependencies"]
        optional_dependencies = project["project"]["optional-dependencies"]

        self.assertIn("PySide6==6.11.1", base_dependencies)
        self.assertNotIn("pandas>=3.0.5", base_dependencies)
        self.assertNotIn("desktop", optional_dependencies)
        self.assertTrue(
            any(
                dependency.startswith("mlx-audio==")
                for dependency in optional_dependencies["apple-audio"]
            )
        )

        self.assertIn("PySide6", REQUIRED_MODULES)
        self.assertNotIn("mlx_audio", REQUIRED_MODULES)
        self.assertNotIn("SoundAnalysis", REQUIRED_MODULES)

    def test_conda_uses_private_miniconda_as_a_fallback(self) -> None:
        conda_manager = CONDA_MANAGER.read_text(encoding="utf-8")
        miniconda_manager = MINICONDA_MANAGER.read_text(encoding="utf-8")

        self.assertIn('exec "${bootstrap_dir}/managers/miniconda.sh"', conda_manager)
        self.assertIn('conda_env_dir="${state_dir}/envs/conda"', miniconda_manager)

    def test_windows_entrypoint_defaults_to_uv_and_disables_conda(self) -> None:
        script = WINDOWS_SETUP_SCRIPT.read_text(encoding="utf-8")

        self.assertIn('[string]$Manager = "uv"', script)
        self.assertIn('if ($Manager -eq "conda")', script)
        self.assertIn("Conda setup is temporarily disabled", script)
        self.assertIn("uv workflow is verified and working reliably", script)
        self.assertIn("while Conda support is reviewed", script)
        self.assertIn("Start-WithUv", script)
        self.assertNotIn("Choose-Manager", script)
        self.assertNotIn("[Console]::ReadKey", script)
        self.assertIn("uv.exe", script)
        self.assertIn("UV_UNMANAGED_INSTALL", script)
        self.assertIn(") | Out-Host", script)
        self.assertIn('Join-Path $ProjectRoot ".odia"', script)
        self.assertIn('Join-Path $StateDir "envs\\uv"', script)
        self.assertIn("Invoke-WebRequest", script)
        self.assertIn("Environment ready. Starting ODIA", script)
        self.assertIn('@("sync", "--locked", "--no-dev")', script)
        self.assertIn("run --no-dev odia", script)


if __name__ == "__main__":
    unittest.main(verbosity=2)
