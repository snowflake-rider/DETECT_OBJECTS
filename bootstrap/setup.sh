#!/usr/bin/env bash

set -euo pipefail

bootstrap_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${bootstrap_dir}/.." && pwd)"
selected_manager=""
install_only=0
dry_run=0

case "$(uname -s)" in
    Darwin)
        detected_platform_name="macOS"
        detected_platform_note="Apple Silicon and Intel installers are selected automatically."
        ;;
    Linux)
        detected_platform_name="Linux"
        detected_platform_note="Audio may require the PortAudio runtime from your Linux distribution."
        ;;
    MINGW*|MSYS*|CYGWIN*)
        echo "Native Windows setup requires PowerShell:" >&2
        echo "  .\\bootstrap\\windows\\setup.ps1" >&2
        exit 2
        ;;
    *)
        echo "Unsupported operating system: $(uname -s)" >&2
        exit 2
        ;;
esac
platform_name="${ODIA_BOOTSTRAP_PLATFORM_NAME:-${detected_platform_name}}"
platform_note="${ODIA_BOOTSTRAP_PLATFORM_NOTE:-${detected_platform_note}}"

usage() {
    cat <<EOF
Usage: $0 [uv|conda|miniconda] [--install-only] [--dry-run]

With no manager, opens the interactive ODIA environment chooser.

  uv             Install uv, Python, and the ODIA environment locally
  conda          Use an existing Conda executable with a local ODIA environment
  miniconda      Install a private Miniconda and ODIA environment locally
  --install-only Install and verify without launching ODIA device setup
  --no-launch    Alias for --install-only
  --dry-run      Show the selected setup and launch path without running them
EOF
}

while (( $# > 0 )); do
    case "$1" in
        uv|conda|miniconda)
            if [[ -n "${selected_manager}" ]]; then
                echo "Choose only one environment manager." >&2
                usage >&2
                exit 2
            fi
            selected_manager="$1"
            ;;
        --manager)
            shift
            if (( $# == 0 )); then
                echo "--manager requires uv, conda, or miniconda." >&2
                exit 2
            fi
            if [[ -n "${selected_manager}" ]]; then
                echo "Choose only one environment manager." >&2
                usage >&2
                exit 2
            fi
            case "$1" in
                uv|conda|miniconda) selected_manager="$1" ;;
                *)
                    echo "Unknown environment manager: $1" >&2
                    usage >&2
                    exit 2
                    ;;
            esac
            ;;
        --install-only|--no-launch)
            install_only=1
            ;;
        --dry-run)
            dry_run=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

render_option() {
    local option_index="$1"
    local label="$2"
    local description="$3"
    local location="$4"

    if (( option_index == menu_index )); then
        printf '\033[1;96m  > [ %-25s ]\033[0m\n' "${label}"
    else
        printf '    [ %-25s ]\n' "${label}"
    fi
    printf '      %s\n' "${description}"
    printf '\033[2m      %s\033[0m\n\n' "${location}"
}

render_menu() {
    printf '\033[2J\033[H'
    printf '\033[1;96mODIA · %s LOCAL ENVIRONMENT SETUP\033[0m\n\n' \
        "${platform_name}"
    printf 'Choose how ODIA should prepare Python and its dependencies.\n'
    printf 'Project environments, package caches, and managed tools stay in this repository.\n'
    printf 'Your shell profile will not be modified.\n\n'
    if [[ -n "${platform_note}" ]]; then
        printf '\033[2m%s\033[0m\n\n' "${platform_note}"
    fi
    render_option \
        0 \
        '★ Install uv' \
        'Recommended · usually the fastest and most reproducible for this project' \
        'Local tool, Python, odia-uv environment, and caches'
    render_option \
        1 \
        'Use Conda' \
        'Uses an existing Conda executable; does not change its base environment' \
        'Local odia-conda environment and package caches'
    render_option \
        2 \
        'Install Miniconda' \
        'Installs a private Miniconda distribution for ODIA' \
        'Local Miniconda, odia-miniconda environment, and caches'
    printf '\033[2m↑/↓ or j/k Move · Enter Install · 1–3 Quick select · q Cancel\033[0m\n'
}

choose_with_numbers() {
    local choice

    printf 'ODIA %s local environment setup\n\n' "${platform_name}"
    if [[ -n "${platform_note}" ]]; then
        printf '%s\n\n' "${platform_note}"
    fi
    printf '1) ★ Install uv (recommended; usually fastest)\n'
    printf '2) Use existing Conda with a local ODIA environment\n'
    printf '3) Install a private Miniconda locally\n\n'
    printf 'Choose 1–3: '
    IFS= read -r choice || return 130
    case "${choice}" in
        1) selected_manager="uv" ;;
        2) selected_manager="conda" ;;
        3) selected_manager="miniconda" ;;
        q|Q) return 130 ;;
        *)
            echo "Invalid selection." >&2
            return 2
            ;;
    esac
}

choose_interactively() {
    local key suffix
    local managers=(uv conda miniconda)
    menu_index=0

    if [[ ! -t 0 || ! -t 1 ]]; then
        echo "Interactive setup requires a terminal." >&2
        echo "Choose explicitly: $0 uv|conda|miniconda" >&2
        return 2
    fi

    if [[ "${TERM:-dumb}" == "dumb" ]]; then
        choose_with_numbers
        return
    fi

    while true; do
        render_menu
        key=""
        IFS= read -rsn1 key || return 130
        case "${key}" in
            '')
                selected_manager="${managers[menu_index]}"
                printf '\033[2J\033[H'
                return 0
                ;;
            1) selected_manager="uv"; printf '\033[2J\033[H'; return 0 ;;
            2) selected_manager="conda"; printf '\033[2J\033[H'; return 0 ;;
            3) selected_manager="miniconda"; printf '\033[2J\033[H'; return 0 ;;
            j|J) menu_index=$(( (menu_index + 1) % 3 )) ;;
            k|K) menu_index=$(( (menu_index + 2) % 3 )) ;;
            q|Q)
                printf '\nSetup cancelled.\n'
                return 130
                ;;
            $'\033')
                suffix=""
                IFS= read -rsn2 -t 1 suffix || true
                case "${suffix}" in
                    '[A') menu_index=$(( (menu_index + 2) % 3 )) ;;
                    '[B') menu_index=$(( (menu_index + 1) % 3 )) ;;
                esac
                ;;
        esac
    done
}

resolve_project_path() {
    case "$1" in
        /*) printf '%s\n' "$1" ;;
        *) printf '%s/%s\n' "${project_root}" "$1" ;;
    esac
}

run_setup() {
    local setup_script="${bootstrap_dir}/${selected_manager}/setup.sh"

    printf '\nPlatform: %s\n' "${platform_name}"
    printf 'Note: %s\n' "${platform_note}"
    printf 'Selected: %s\n' "${selected_manager}"
    if (( dry_run == 1 )); then
        printf 'Would run: %s\n' "${setup_script}"
        return 0
    fi

    printf 'Preparing the project-local environment…\n\n'
    "${setup_script}"
}

launch_uv() {
    local uv_install_dir uv_command uv_environment uv_cache_dir uv_python_dir
    uv_install_dir="$(resolve_project_path "${ODIA_UV_INSTALL_DIR:-.odia-tools/bin}")"
    uv_command="${uv_install_dir}/uv"
    uv_environment="$(resolve_project_path "${UV_PROJECT_ENVIRONMENT:-odia-uv}")"
    uv_cache_dir="$(resolve_project_path "${ODIA_UV_CACHE_DIR:-.odia-tools/uv-cache}")"
    uv_python_dir="$(resolve_project_path "${ODIA_UV_PYTHON_INSTALL_DIR:-.odia-tools/uv-python}")"

    if (( dry_run == 1 )); then
        printf 'Would launch: %s run odia (environment: %s)\n' \
            "${uv_command}" "${uv_environment}"
        return 0
    fi
    if [[ ! -x "${uv_command}" ]]; then
        echo "uv setup succeeded but ${uv_command} is unavailable." >&2
        return 1
    fi

    exec env \
        UV_CACHE_DIR="${uv_cache_dir}" \
        UV_PROJECT_ENVIRONMENT="${uv_environment}" \
        UV_PYTHON_INSTALL_DIR="${uv_python_dir}" \
        "${uv_command}" run odia
}

launch_conda() {
    local conda_command conda_env_dir conda_pkgs_dir pip_cache_dir

    if [[ "${selected_manager}" == "miniconda" ]]; then
        local miniconda_install_dir
        miniconda_install_dir="$(resolve_project_path "${ODIA_MINICONDA_INSTALL_DIR:-${ODIA_CONDA_INSTALL_DIR:-.odia-tools/miniconda3}}")"
        conda_command="${miniconda_install_dir}/bin/conda"
        conda_env_dir="${ODIA_CONDA_ENV_DIR:-odia-miniconda}"
    else
        conda_command="${ODIA_CONDA_COMMAND:-$(command -v conda || true)}"
        conda_env_dir="${ODIA_CONDA_ENV_DIR:-${ODIA_CONDA_ENV:-odia-conda}}"
    fi

    conda_env_dir="$(resolve_project_path "${conda_env_dir}")"
    conda_pkgs_dir="$(resolve_project_path "${ODIA_CONDA_PKGS_DIR:-.odia-tools/conda-pkgs}")"
    pip_cache_dir="$(resolve_project_path "${ODIA_PIP_CACHE_DIR:-.odia-tools/pip-cache}")"

    if (( dry_run == 1 )); then
        printf 'Would launch: %s run --prefix %s odia\n' \
            "${conda_command:-conda}" "${conda_env_dir}"
        return 0
    fi
    if [[ -z "${conda_command}" || ! -x "${conda_command}" ]]; then
        echo "The selected Conda executable is unavailable: ${conda_command:-not found}" >&2
        return 1
    fi

    exec env \
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
        "${conda_command}" run --prefix "${conda_env_dir}" odia
}

cd "${project_root}"

if [[ -z "${selected_manager}" ]]; then
    choose_interactively
fi

run_setup

if (( install_only == 1 )); then
    if (( dry_run == 0 )); then
        printf '\n%s environment is ready.\n' "${selected_manager}"
    fi
    exit 0
fi

if (( dry_run == 0 )); then
    printf '\nEnvironment ready. Starting ODIA device and model setup…\n\n'
fi

case "${selected_manager}" in
    uv) launch_uv ;;
    conda|miniconda) launch_conda ;;
esac
