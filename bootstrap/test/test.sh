#!/usr/bin/env bash

set -euo pipefail

test_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${test_dir}/../.." && pwd)"
test_state_dir="${test_dir}/.state"
test_home_dir="${test_state_dir}/home"
test_data_dir="${test_state_dir}/data"
test_bin_dir="${test_state_dir}/bin"
test_tmp_dir="${test_state_dir}/tmp"
test_miniconda_dir="${test_state_dir}/miniconda3"
test_miniconda_environment="${test_state_dir}/odia-miniconda"
test_conda_environment="${test_state_dir}/odia-conda"
test_conda_pkgs_dir="${test_state_dir}/conda-pkgs"
test_pip_cache_dir="${test_state_dir}/pip-cache"
test_uv_environment="${test_state_dir}/odia-uv"
test_uv_cache_dir="${test_state_dir}/uv-cache"
test_uv_python_dir="${test_state_dir}/uv-python"
required_model_path="${project_root}/model_artifacts/vision/yolov8s-worldv2.pt"
keep_test_state="${ODIA_BOOTSTRAP_TEST_KEEP_STATE:-0}"
test_mode="${1:-all}"

if (( $# > 1 )); then
    echo "Usage: $0 [miniconda|conda|uv|all|--clean-only]" >&2
    exit 2
fi

case "${test_mode}" in
    miniconda|conda|uv|all|--clean-only) ;;
    *)
        echo "Usage: $0 [miniconda|conda|uv|all|--clean-only]" >&2
        exit 2
        ;;
esac

assert_safe_test_state() {
    if [[ "${test_state_dir}" != "${test_dir}/.state" ||
        "${test_state_dir}" == "/" ||
        "${test_state_dir}" == "${HOME:-}" ]]; then
        echo "Refusing to clean unsafe test state path: ${test_state_dir}" >&2
        exit 1
    fi
}

clean_test_state() {
    assert_safe_test_state
    if [[ -e "${test_state_dir}" ]]; then
        echo "Removing test-owned installations: ${test_state_dir}"
        rm -rf -- "${test_state_dir}"
    fi
}

clean_test_reports() {
    local report_name report_path
    local report_names=("${test_mode}" comparison)

    if [[ "${test_mode}" == "all" || "${test_mode}" == "--clean-only" ]]; then
        report_names=(conda miniconda uv comparison)
    fi

    for report_name in "${report_names[@]}"; do
        report_path="${test_dir}/${report_name}.md"
        if [[ -f "${report_path}" ]]; then
            rm -f -- "${report_path}"
        fi
    done
}

prepare_test_state() {
    mkdir -p \
        "${test_home_dir}" \
        "${test_data_dir}" \
        "${test_bin_dir}" \
        "${test_tmp_dir}"
}

ensure_required_model() {
    local model_download_path model_url

    if [[ -f "${required_model_path}" ]]; then
        echo "Shared YOLO-World weights are already available."
        return
    fi

    model_download_path="${test_state_dir}/yolov8s-worldv2.pt.download"
    model_url="https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s-worldv2.pt"
    mkdir -p "$(dirname "${required_model_path}")"
    echo "Pre-downloading shared YOLO-World weights outside timed setup runs..."

    if command -v curl >/dev/null 2>&1; then
        curl --proto '=https' --tlsv1.2 --fail --location \
            "${model_url}" --output "${model_download_path}"
    elif command -v wget >/dev/null 2>&1; then
        wget --https-only "${model_url}" --output-document="${model_download_path}"
    else
        echo "Model pre-download requires curl or wget." >&2
        exit 1
    fi

    if [[ ! -s "${model_download_path}" ]]; then
        echo "Model pre-download produced an empty file." >&2
        exit 1
    fi
    mv "${model_download_path}" "${required_model_path}"
}

find_conda_engine() {
    local candidate detected

    if [[ -n "${ODIA_BOOTSTRAP_TEST_CONDA_COMMAND:-}" ]]; then
        if [[ ! -x "${ODIA_BOOTSTRAP_TEST_CONDA_COMMAND}" ]]; then
            echo "ODIA_BOOTSTRAP_TEST_CONDA_COMMAND is not executable: ${ODIA_BOOTSTRAP_TEST_CONDA_COMMAND}" >&2
            return 1
        fi
        printf '%s\n' "${ODIA_BOOTSTRAP_TEST_CONDA_COMMAND}"
        return
    fi

    detected="$(command -v conda || true)"
    if [[ -n "${detected}" ]]; then
        printf '%s\n' "${detected}"
        return
    fi

    if [[ -n "${HOME:-}" ]]; then
        for candidate in \
            "${HOME}/miniconda3/bin/conda" \
            "${HOME}/anaconda3/bin/conda" \
            "${HOME}/.local/share/odia/miniconda3/bin/conda"; do
            if [[ -x "${candidate}" ]]; then
                printf '%s\n' "${candidate}"
                return
            fi
        done
    fi

    candidate="${project_root}/.odia-tools/miniconda3/bin/conda"
    if [[ -x "${candidate}" ]]; then
        printf '%s\n' "${candidate}"
        return
    fi

    echo "The Conda comparison requires an existing Conda executable." >&2
    echo "Set ODIA_BOOTSTRAP_TEST_CONDA_COMMAND=/path/to/conda." >&2
    return 1
}

report_total_seconds() {
    sed -n 's/.*(\([0-9][0-9]*\) seconds).*/\1/p' "$1" | head -1
}

write_comparison_report() {
    local conda_seconds miniconda_seconds uv_seconds comparison_path
    conda_seconds="$(report_total_seconds "${test_dir}/conda.md")"
    miniconda_seconds="$(report_total_seconds "${test_dir}/miniconda.md")"
    uv_seconds="$(report_total_seconds "${test_dir}/uv.md")"
    comparison_path="${test_dir}/comparison.md"

    {
        printf '# Bootstrap from-scratch comparison\n\n'
        printf 'Every setup started with an empty environment and empty package caches. '
        printf 'Shared model weights were provisioned before timing.\n\n'
        printf '| Setup | Total seconds | Included in timing |\n'
        printf '| --- | ---: | --- |\n'
        printf '| Conda | %s | Fresh project environment and caches; existing Conda executable |\n' "${conda_seconds}"
        printf '| Miniconda | %s | Project-local Miniconda installation, environment, and caches |\n' "${miniconda_seconds}"
        printf '| uv | %s | Project-local uv installation, environment, Python, and caches |\n' "${uv_seconds}"
        printf '\nSee `conda.md`, `miniconda.md`, and `uv.md` for stage timings.\n'
    } >"${comparison_path}"
}

run_miniconda_test() {
    echo "Testing managed Miniconda from scratch..."
    env "${test_environment[@]}" \
        ODIA_MINICONDA_INSTALL_DIR="${test_miniconda_dir}" \
        ODIA_CONDA_ENV_DIR="${test_miniconda_environment}" \
        ODIA_CONDA_PKGS_DIR="${test_conda_pkgs_dir}" \
        ODIA_PIP_CACHE_DIR="${test_pip_cache_dir}" \
        ./bootstrap/miniconda/setup.sh
}

run_conda_test() {
    local conda_engine
    conda_engine="$(find_conda_engine)"

    echo "Testing Conda from empty environment and package caches..."
    echo "Conda engine (not installed or timed): ${conda_engine}"
    env "${test_environment[@]}" \
        ODIA_CONDA_COMMAND="${conda_engine}" \
        ODIA_CONDA_ENV_DIR="${test_conda_environment}" \
        ODIA_CONDA_PKGS_DIR="${test_conda_pkgs_dir}" \
        ODIA_PIP_CACHE_DIR="${test_pip_cache_dir}" \
        ./bootstrap/conda/setup.sh
}

run_uv_test() {
    echo "Testing uv from scratch..."
    env "${test_environment[@]}" \
        ODIA_UV_INSTALL_DIR="${test_bin_dir}" \
        ODIA_UV_CACHE_DIR="${test_uv_cache_dir}" \
        ODIA_UV_PYTHON_INSTALL_DIR="${test_uv_python_dir}" \
        UV_PROJECT_ENVIRONMENT="${test_uv_environment}" \
        ./bootstrap/uv/setup.sh
}

run_selected_test() {
    case "$1" in
        miniconda) run_miniconda_test ;;
        conda) run_conda_test ;;
        uv) run_uv_test ;;
    esac
}

finish_test() {
    local exit_status="$?"
    trap - EXIT

    if [[ "${keep_test_state}" == "1" ]]; then
        echo "Keeping test state for debugging: ${test_state_dir}"
    else
        clean_test_state
    fi

    exit "${exit_status}"
}

trap finish_test EXIT

clean_test_state
if [[ "${test_mode}" == "--clean-only" ]]; then
    echo "Test-owned Conda, Miniconda, and uv installations are removed."
    exit 0
fi

clean_test_reports
prepare_test_state
ensure_required_model

# Exclude user-managed Conda and uv executables from discovery. All tools
# installed during this test remain below bootstrap/test/.state.
test_path="${test_bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin"
test_environment=(
    "HOME=${test_home_dir}"
    "XDG_DATA_HOME=${test_data_dir}"
    "XDG_BIN_HOME=${test_bin_dir}"
    "TMPDIR=${test_tmp_dir}"
    "PATH=${test_path}"
    "ODIA_BOOTSTRAP_REPORT_DIR=${test_dir}"
)

cd "${project_root}"

if [[ "${test_mode}" == "all" ]]; then
    selected_tests=(miniconda conda uv)
else
    selected_tests=("${test_mode}")
fi

for test_name in "${selected_tests[@]}"; do
    if [[ "${test_name}" != "${selected_tests[0]}" ]]; then
        echo
        clean_test_state
        prepare_test_state
    fi
    run_selected_test "${test_name}"
done

for report_name in "${selected_tests[@]}"; do
    report_path="${test_dir}/${report_name}.md"
    if [[ ! -f "${report_path}" ]]; then
        echo "Expected bootstrap report was not created: ${report_path}" >&2
        exit 1
    fi
done

if [[ "${test_mode}" == "all" ]]; then
    write_comparison_report
fi

echo
if [[ "${test_mode}" == "all" ]]; then
    echo "All bootstrap paths completed successfully. Reports:"
    echo "  ${test_dir}/miniconda.md"
    echo "  ${test_dir}/conda.md"
    echo "  ${test_dir}/uv.md"
    echo "  ${test_dir}/comparison.md"
else
    echo "${test_mode} bootstrap completed successfully. Report:"
    echo "  ${test_dir}/${test_mode}.md"
fi
