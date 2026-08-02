#!/usr/bin/env bash

set -euo pipefail

bootstrap_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${bootstrap_dir}/../.." && pwd)"
conda_env_name="${ODIA_CONDA_ENV:-odia-conda}"

source "${bootstrap_dir}/../reporting.sh"
bootstrap_report_init \
    "conda" \
    "${conda_env_name}" \
    "${project_root}" \
    "bootstrap/conda/setup.sh"
bootstrap_report_install_exit_trap

bootstrap_report_step_start "Locate Conda"
conda_command="${ODIA_CONDA_COMMAND:-$(command -v conda || true)}"

if [[ -z "${conda_command}" ]]; then
    echo "Conda was not found." >&2
    echo "Install Conda first, or run ./bootstrap/miniconda/setup.sh." >&2
    exit 1
fi

if ! "${conda_command}" --version >/dev/null 2>&1; then
    echo "Unable to run Conda using ${conda_command}." >&2
    exit 1
fi
bootstrap_report_step_end

cd "${project_root}"

bootstrap_report_step_start "Prepare Python 3.11 environment"
if ! "${conda_command}" run --name "${conda_env_name}" python -c "import sys; raise SystemExit(sys.version_info[:2] != (3, 11))" >/dev/null 2>&1; then
    "${conda_command}" create --name "${conda_env_name}" python=3.11 pip --yes
fi
bootstrap_report_step_end

bootstrap_report_step_start "Install Python dependencies"
"${conda_command}" run --name "${conda_env_name}" \
    python -m pip install --requirement requirements.txt
bootstrap_report_step_end
bootstrap_report_step_start "Install ODIA package"
"${conda_command}" run --name "${conda_env_name}" \
    python -m pip install --no-deps --editable .
bootstrap_report_step_end
bootstrap_report_step_start "Download required models"
"${conda_command}" run --name "${conda_env_name}" \
    python bootstrap/download_models.py
bootstrap_report_step_end
bootstrap_report_step_start "Verify environment"
"${conda_command}" run --name "${conda_env_name}" \
    python bootstrap/verify_environment.py
bootstrap_report_step_end

echo
echo "Environment ready. Run ODIA with:"
echo "  \"${conda_command}\" run --name \"${conda_env_name}\" odia"
echo
echo "Or activate the environment:"
conda_bin_dir="$(cd "$(dirname "${conda_command}")" 2>/dev/null && pwd || true)"
if [[ -n "${conda_bin_dir}" && -f "${conda_bin_dir}/activate" ]]; then
    echo "  source \"${conda_bin_dir}/activate\" \"${conda_env_name}\""
else
    echo "  conda activate ${conda_env_name}"
fi
echo "  odia"
