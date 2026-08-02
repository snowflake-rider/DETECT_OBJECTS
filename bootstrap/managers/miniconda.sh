#!/usr/bin/env bash

set -euo pipefail

# Miniconda workflow:
#   1. Choose fixed Miniconda paths inside .odia/.
#   2. Download and install Miniconda if it is missing.
#   3. Ask conda.sh to create the environment and start ODIA.

# Find this file, bootstrap/, and then the project root.
manager_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bootstrap_dir="$(cd "${manager_dir}/.." && pwd)"
project_root="$(cd "${bootstrap_dir}/.." && pwd)"

# source loads the shared download function.
source "${bootstrap_dir}/lib/download.sh"

# Choose the Miniconda installer for this operating system and CPU.
miniconda_installer_name() {
    local platform
    platform="$(uname -s):$(uname -m)"

    case "${platform}" in
        Darwin:arm64) echo "Miniconda3-latest-MacOSX-arm64.sh" ;;
        Darwin:x86_64) echo "Miniconda3-latest-MacOSX-x86_64.sh" ;;
        Linux:aarch64|Linux:arm64) echo "Miniconda3-latest-Linux-aarch64.sh" ;;
        Linux:x86_64) echo "Miniconda3-latest-Linux-x86_64.sh" ;;
        *)
            echo "No Miniconda installer is available for ${platform}." >&2
            return 1
            ;;
    esac
}

# Keep Miniconda and its Python environment inside the project.
state_dir="${project_root}/.odia"
conda_env_dir="${state_dir}/envs/miniconda"
miniconda_install_dir="${state_dir}/tools/miniconda3"
conda_command="${miniconda_install_dir}/bin/conda"

# Install Miniconda only when its Conda executable is missing.
if [[ ! -x "${conda_command}" ]]; then
    # An existing but incomplete directory should not be overwritten.
    if [[ -e "${miniconda_install_dir}" ]]; then
        echo "${miniconda_install_dir} exists but does not contain Conda." >&2
        exit 1
    fi

    # Select the installer for macOS/Linux and Intel/ARM.
    installer_name="$(miniconda_installer_name)"

    # Download into a unique temporary directory.
    installer_temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/odia-miniconda-install.XXXXXX")"
    conda_installer="${installer_temp_dir}/${installer_name}"

    # Remove the temporary directory even if installation fails.
    trap 'rm -rf "${installer_temp_dir}"' EXIT

    echo "Installing Miniconda into ${miniconda_install_dir}..."
    download_file \
        "https://repo.anaconda.com/miniconda/${installer_name}" \
        "${conda_installer}" \
        "Miniconda"
    bash "${conda_installer}" -b -p "${miniconda_install_dir}"

    # Installation finished, so clean up and remove the EXIT trap.
    rm -rf "${installer_temp_dir}"
    trap - EXIT
fi

if [[ ! -x "${conda_command}" ]]; then
    echo "Miniconda installation did not produce ${conda_command}." >&2
    exit 1
fi

# Pass the managed Conda paths to conda.sh.
# exec replaces this script with conda.sh instead of creating another process.
exec env \
    ODIA_CONDA_ENV_DIR="${conda_env_dir}" \
    ODIA_CONDA_COMMAND="${conda_command}" \
    "${bootstrap_dir}/managers/conda.sh"
