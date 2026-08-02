#!/usr/bin/env bash

set -euo pipefail

bootstrap_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${bootstrap_dir}/../.." && pwd)"
conda_env_name="${ODIA_CONDA_ENV:-odia}"

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

conda_command="$(command -v conda || true)"
conda_installed_by_bootstrap=false

if [[ -z "${conda_command}" ]]; then
    if [[ -z "${HOME:-}" && -z "${XDG_DATA_HOME:-}" ]]; then
        echo "Installing Miniconda requires HOME or XDG_DATA_HOME to be set." >&2
        exit 1
    fi

    conda_install_dir="${ODIA_CONDA_INSTALL_DIR:-${XDG_DATA_HOME:-${HOME}/.local/share}/odia/miniconda3}"
    conda_command="${conda_install_dir}/bin/conda"

    if [[ ! -x "${conda_command}" ]]; then
        if [[ -e "${conda_install_dir}" ]]; then
            echo "${conda_install_dir} exists but does not contain Conda." >&2
            echo "Choose another location with ODIA_CONDA_INSTALL_DIR." >&2
            exit 1
        fi

        installer_name="$(miniconda_installer_name)"
        conda_installer="$(mktemp "${TMPDIR:-/tmp}/odia-miniconda-install.XXXXXX")"
        trap 'rm -f "${conda_installer}"' EXIT

        echo "Conda was not found; installing Miniconda into ${conda_install_dir}..."
        download_file \
            "https://repo.anaconda.com/miniconda/${installer_name}" \
            "${conda_installer}"
        bash "${conda_installer}" -b -p "${conda_install_dir}"
    fi

    conda_installed_by_bootstrap=true
fi

cd "${project_root}"

if ! "${conda_command}" run --name "${conda_env_name}" python -c "import sys; raise SystemExit(sys.version_info[:2] != (3, 11))" >/dev/null 2>&1; then
    "${conda_command}" create --name "${conda_env_name}" python=3.11 pip --yes
fi

"${conda_command}" run --name "${conda_env_name}" \
    python -m pip install --requirement requirements.txt
"${conda_command}" run --name "${conda_env_name}" \
    python -m pip install --no-deps --editable .
"${conda_command}" run --name "${conda_env_name}" \
    python bootstrap/verify_environment.py

echo
echo "Environment ready. Run ODIA with:"
echo "  \"${conda_command}\" run --name \"${conda_env_name}\" odia"
echo
echo "Or activate the environment:"
if [[ "${conda_installed_by_bootstrap}" == true ]]; then
    echo "  source \"${conda_install_dir}/bin/activate\" \"${conda_env_name}\""
else
    echo "  conda activate ${conda_env_name}"
fi
echo "  odia"
