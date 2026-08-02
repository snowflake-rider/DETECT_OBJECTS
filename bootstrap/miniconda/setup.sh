#!/usr/bin/env bash

set -euo pipefail

bootstrap_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${bootstrap_dir}/../.." && pwd)"
conda_env_name="${ODIA_CONDA_ENV:-odia-miniconda}"

source "${bootstrap_dir}/../reporting.sh"
bootstrap_report_init \
    "miniconda" \
    "${conda_env_name}" \
    "${project_root}" \
    "bootstrap/miniconda/setup.sh"
bootstrap_report_install_exit_trap

download_file() {
    local url="$1"
    local destination="$2"

    if command -v curl >/dev/null 2>&1; then
        curl --proto '=https' --tlsv1.2 --fail --silent --show-error \
            --location "${url}" --output "${destination}"
    elif command -v wget >/dev/null 2>&1; then
        wget --https-only --quiet "${url}" --output-document="${destination}"
    else
        echo "Installing Miniconda requires curl or wget." >&2
        exit 1
    fi
}

miniconda_installer_name() {
    local operating_system
    local architecture

    operating_system="$(uname -s)"
    architecture="$(uname -m)"

    case "${operating_system}:${architecture}" in
        Darwin:arm64)
            echo "Miniconda3-latest-MacOSX-arm64.sh"
            ;;
        Darwin:x86_64)
            echo "Miniconda3-latest-MacOSX-x86_64.sh"
            ;;
        Linux:aarch64|Linux:arm64)
            echo "Miniconda3-latest-Linux-aarch64.sh"
            ;;
        Linux:x86_64)
            echo "Miniconda3-latest-Linux-x86_64.sh"
            ;;
        *)
            echo "No automatic Miniconda installer is configured for ${operating_system} ${architecture}." >&2
            return 1
            ;;
    esac
}

if [[ -z "${ODIA_MINICONDA_INSTALL_DIR:-}" &&
    -z "${ODIA_CONDA_INSTALL_DIR:-}" &&
    -z "${HOME:-}" &&
    -z "${XDG_DATA_HOME:-}" ]]; then
    echo "Installing Miniconda requires HOME or XDG_DATA_HOME to be set." >&2
    exit 1
fi

default_data_dir="${XDG_DATA_HOME:-${HOME:-}/.local/share}"
miniconda_install_dir="${ODIA_MINICONDA_INSTALL_DIR:-${ODIA_CONDA_INSTALL_DIR:-${default_data_dir}/odia/miniconda3}}"
conda_command="${miniconda_install_dir}/bin/conda"

bootstrap_report_step_start "Locate or install Miniconda"
if [[ ! -x "${conda_command}" ]]; then
    if [[ -e "${miniconda_install_dir}" ]]; then
        echo "${miniconda_install_dir} exists but does not contain Conda." >&2
        echo "Choose another location with ODIA_MINICONDA_INSTALL_DIR." >&2
        exit 1
    fi

    installer_name="$(miniconda_installer_name)"
    installer_temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/odia-miniconda-install.XXXXXX")"
    conda_installer="${installer_temp_dir}/${installer_name}"
    bootstrap_report_register_cleanup_file "${conda_installer}"
    bootstrap_report_register_cleanup_dir "${installer_temp_dir}"

    echo "Installing Miniconda into ${miniconda_install_dir}..."
    download_file \
        "https://repo.anaconda.com/miniconda/${installer_name}" \
        "${conda_installer}"
    bash "${conda_installer}" -b -p "${miniconda_install_dir}"
fi

if [[ ! -x "${conda_command}" ]]; then
    echo "Miniconda installation did not produce ${conda_command}." >&2
    exit 1
fi
bootstrap_report_step_end

bootstrap_report_step_start "Configure ODIA environment"
ODIA_BOOTSTRAP_REPORT=0 \
    ODIA_CONDA_ENV="${conda_env_name}" \
    ODIA_CONDA_COMMAND="${conda_command}" \
    "${project_root}/bootstrap/conda/setup.sh"
bootstrap_report_step_end
