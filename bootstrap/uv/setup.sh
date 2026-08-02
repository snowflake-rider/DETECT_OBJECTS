#!/usr/bin/env bash

set -euo pipefail

bootstrap_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${bootstrap_dir}/../.." && pwd)"
uv_environment="${UV_PROJECT_ENVIRONMENT:-odia-uv}"

source "${bootstrap_dir}/../reporting.sh"
bootstrap_report_init \
    "uv" \
    "${uv_environment}" \
    "${project_root}" \
    "bootstrap/uv/setup.sh"
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
        echo "Installing uv requires curl or wget." >&2
        exit 1
    fi
}

uv_command="$(command -v uv || true)"

bootstrap_report_step_start "Locate or install uv"
if [[ -z "${uv_command}" ]]; then
    if [[ -z "${HOME:-}" && -z "${XDG_BIN_HOME:-}" ]]; then
        echo "Installing uv requires HOME or XDG_BIN_HOME to be set." >&2
        exit 1
    fi

    uv_install_dir="${ODIA_UV_INSTALL_DIR:-${XDG_BIN_HOME:-${HOME}/.local/bin}}"
    uv_installer="$(mktemp "${TMPDIR:-/tmp}/odia-uv-install.XXXXXX")"
    trap 'rm -f "${uv_installer}"' EXIT

    echo "uv was not found; installing it into ${uv_install_dir}..."
    download_file "https://astral.sh/uv/install.sh" "${uv_installer}"
    UV_INSTALL_DIR="${uv_install_dir}" UV_NO_MODIFY_PATH=1 \
        sh "${uv_installer}"

    uv_command="${uv_install_dir}/uv"
    if [[ ! -x "${uv_command}" ]]; then
        echo "uv installation did not produce ${uv_command}." >&2
        exit 1
    fi
fi
bootstrap_report_step_end

cd "${project_root}"
bootstrap_report_step_start "Sync Python environment"
UV_PROJECT_ENVIRONMENT="${uv_environment}" "${uv_command}" sync --locked
bootstrap_report_step_end
bootstrap_report_step_start "Download required models"
UV_PROJECT_ENVIRONMENT="${uv_environment}" \
    "${uv_command}" run python bootstrap/download_models.py
bootstrap_report_step_end
bootstrap_report_step_start "Verify environment"
UV_PROJECT_ENVIRONMENT="${uv_environment}" \
    "${uv_command}" run python bootstrap/verify_environment.py
bootstrap_report_step_end

echo
echo "Environment ready. Run ODIA with:"
echo "  UV_PROJECT_ENVIRONMENT=\"${uv_environment}\" \"${uv_command}\" run odia"
echo
echo "Or activate the environment:"
echo "  source \"${uv_environment}/bin/activate\""
echo "  odia"
