"""Tests for bootstrap Markdown timing reports."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTING_SCRIPT = PROJECT_ROOT / "bootstrap" / "lib" / "reporting.sh"


class BootstrapReportingTests(unittest.TestCase):
    """Verify successful and interrupted runs produce useful reports."""

    def _run_report(self, exit_status: int) -> tuple[subprocess.CompletedProcess, str]:
        with tempfile.TemporaryDirectory() as report_dir:
            environment = os.environ.copy()
            environment["ODIA_BOOTSTRAP_REPORT_DIR"] = report_dir
            script = f"""
                set -euo pipefail
                source {REPORTING_SCRIPT!s}
                bootstrap_report_init test test-env {PROJECT_ROOT!s} bootstrap/managers/test.sh
                bootstrap_report_install_exit_trap
                bootstrap_report_step_start "Example stage"
                exit {exit_status}
            """

            result = subprocess.run(
                ["bash", "-c", script],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            report = (Path(report_dir) / "test.md").read_text(encoding="utf-8")

        return result, report

    def test_success_report_includes_total_and_stage_duration(self) -> None:
        result, report = self._run_report(exit_status=0)

        self.assertEqual(result.returncode, 0)
        self.assertIn("Status: **Success**", report)
        self.assertIn("Total: **", report)
        self.assertIn("| Example stage |", report)

    def test_interrupted_report_preserves_exit_status(self) -> None:
        result, report = self._run_report(exit_status=130)

        self.assertEqual(result.returncode, 130)
        self.assertIn("Status: **Interrupted (exit 130)**", report)
        self.assertIn("| Example stage |", report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
