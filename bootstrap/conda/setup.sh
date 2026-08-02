#!/usr/bin/env bash

set -euo pipefail

bootstrap_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${bootstrap_dir}/../.." && pwd)"
conda_env_name="${ODIA_CONDA_ENV:-odia}"

if ! command -v conda >/dev/null 2>&1; then
    echo "Conda is required. Install Miniconda or Anaconda first."
    exit 1
fi

cd "${project_root}"

if ! conda run --name "${conda_env_name}" python -c "import sys; raise SystemExit(sys.version_info[:2] != (3, 11))" >/dev/null 2>&1; then
    conda create --name "${conda_env_name}" python=3.11 pip --yes
fi

conda run --name "${conda_env_name}" \
    python -m pip install --requirement requirements.txt
conda run --name "${conda_env_name}" \
    python -m pip install --no-deps --editable .
conda run --name "${conda_env_name}" \
    python bootstrap/verify_environment.py

echo
echo "Environment ready. Run:"
echo "  conda activate ${conda_env_name}"
echo "  odia"
