#!/usr/bin/env bash

set -euo pipefail

bootstrap_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${bootstrap_dir}/../.." && pwd)"
conda_env_dir="${ODIA_CONDA_ENV_DIR:-${project_root}/${ODIA_CONDA_ENV:-odia-conda}}"
conda_pkgs_dir="${ODIA_CONDA_PKGS_DIR:-${project_root}/.odia-tools/conda-pkgs}"
pip_cache_dir="${ODIA_PIP_CACHE_DIR:-${project_root}/.odia-tools/pip-cache}"
conda_channel="${ODIA_CONDA_CHANNEL:-conda-forge}"

if [[ "${conda_env_dir}" != /* ]]; then
    conda_env_dir="${project_root}/${conda_env_dir}"
fi

source "${bootstrap_dir}/../reporting.sh"
bootstrap_report_init \
    "conda" \
    "${conda_env_dir}" \
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
mkdir -p "${conda_pkgs_dir}" "${pip_cache_dir}"

conda_project_command() {
    env \
        -u CONDA_DEFAULT_ENV \
        -u CONDA_EXE \
        -u CONDA_PREFIX \
        -u CONDA_PROMPT_MODIFIER \
        -u CONDA_PYTHON_EXE \
        -u CONDA_SHLVL \
        -u _CE_CONDA \
        -u _CE_M \
        CONDA_PKGS_DIRS="${conda_pkgs_dir}" \
        PIP_CACHE_DIR="${pip_cache_dir}" \
        "${conda_command}" "$@"
}

bootstrap_report_step_start "Prepare Python 3.11 environment"
if ! conda_project_command run --prefix "${conda_env_dir}" python -c "import sys; raise SystemExit(sys.version_info[:2] != (3, 11))" >/dev/null 2>&1; then
    conda_project_command create \
        --prefix "${conda_env_dir}" \
        --override-channels \
        --channel "${conda_channel}" \
        python=3.11 pip --yes
fi
bootstrap_report_step_end

bootstrap_report_step_start "Install Python dependencies"
conda_project_command run --prefix "${conda_env_dir}" \
    python -m pip install --requirement requirements.txt
bootstrap_report_step_end
bootstrap_report_step_start "Install ODIA package"
conda_project_command run --prefix "${conda_env_dir}" \
    python -m pip install --no-deps --editable .
bootstrap_report_step_end
bootstrap_report_step_start "Download required models"
conda_project_command run --prefix "${conda_env_dir}" \
    python bootstrap/download_models.py
bootstrap_report_step_end
bootstrap_report_step_start "Verify environment"
conda_project_command run --prefix "${conda_env_dir}" \
    python bootstrap/verify_environment.py
bootstrap_report_step_end

echo
echo "Environment ready. Run ODIA with:"
echo "  CONDA_PKGS_DIRS=\"${conda_pkgs_dir}\" \"${conda_command}\" run --prefix \"${conda_env_dir}\" odia"
echo
echo "Or activate the environment:"
conda_bin_dir="$(cd "$(dirname "${conda_command}")" 2>/dev/null && pwd || true)"
if [[ -n "${conda_bin_dir}" && -f "${conda_bin_dir}/activate" ]]; then
    echo "  source \"${conda_bin_dir}/activate\" \"${conda_env_dir}\""
else
    echo "  conda activate \"${conda_env_dir}\""
fi
echo "  odia"
