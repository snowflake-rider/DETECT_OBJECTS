#!/usr/bin/env bash

set -euo pipefail

# Conda workflow:
#   1. Use existing Conda, or install private Miniconda when it is missing.
#   2. Create a local Python 3.11 environment if needed.
#   3. Install dependencies and ODIA.
#   4. Download models, verify the environment, and start ODIA.

# Find this file, bootstrap/, and then the project root.
manager_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bootstrap_dir="$(cd "${manager_dir}/.." && pwd)"
project_root="$(cd "${bootstrap_dir}/.." && pwd)"

# Normal Conda uses these defaults. Miniconda supplies the two ODIA_CONDA
# variables when it delegates to this script.
state_dir="${project_root}/.odia"
conda_env_dir="${ODIA_CONDA_ENV_DIR:-${state_dir}/envs/conda}"
conda_pkgs_dir="${state_dir}/caches/conda"
pip_cache_dir="${state_dir}/caches/pip"
conda_command="${ODIA_CONDA_COMMAND:-$(command -v conda || true)}"

# If Conda is missing, let miniconda.sh install a private copy and return here.
if [[ -z "${conda_command}" ]]; then
    echo "Conda was not found; installing private Miniconda..."
    exec "${bootstrap_dir}/managers/miniconda.sh"
fi

# Confirm that the discovered Conda command actually runs.
if ! "${conda_command}" --version >/dev/null 2>&1; then
    echo "Unable to run Conda using ${conda_command}." >&2
    exit 1
fi

cd "${project_root}"
mkdir -p "${conda_pkgs_dir}" "${pip_cache_dir}"

# This wrapper clears any active Conda environment before running a command.
# env -u removes variables inherited from another active Conda environment.
# "$@" forwards every argument given to this function.
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

# Reuse the environment only when it already contains Python 3.11.
echo "Preparing the Python 3.11 environment..."
if ! conda_project_command run --prefix "${conda_env_dir}" python -c "import sys; raise SystemExit(sys.version_info[:2] != (3, 11))" >/dev/null 2>&1; then
    conda_project_command create \
        --prefix "${conda_env_dir}" \
        --override-channels \
        --channel conda-forge \
        python=3.11 pip --yes
fi

echo "Installing Python dependencies..."
conda_project_command run --prefix "${conda_env_dir}" \
    python -m pip install --requirement requirements.txt

echo "Installing ODIA..."
conda_project_command run --prefix "${conda_env_dir}" \
    python -m pip install --no-deps --editable .

echo "Downloading required models..."
conda_project_command run --prefix "${conda_env_dir}" \
    python bootstrap/tools/download_models.py

echo "Verifying the environment..."
conda_project_command run --prefix "${conda_env_dir}" \
    python bootstrap/tools/verify_environment.py

echo
echo "Environment ready. Starting ODIA..."

# Run ODIA inside the selected Conda environment.
conda_project_command run --prefix "${conda_env_dir}" odia
