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
keep_test_state="${ODIA_BOOTSTRAP_TEST_KEEP_STATE:-0}"
test_mode="${1:-run}"

if [[ "${test_mode}" != "run" && "${test_mode}" != "--clean-only" ]]; then
    echo "Usage: $0 [--clean-only]" >&2
    exit 2
fi

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
    for report_name in conda miniconda uv; do
        report_path="${test_dir}/${report_name}.md"
        if [[ -f "${report_path}" ]]; then
            rm -f -- "${report_path}"
        fi
    done
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
mkdir -p \
    "${test_home_dir}" \
    "${test_data_dir}" \
    "${test_bin_dir}" \
    "${test_tmp_dir}"

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

echo "Testing managed Miniconda from scratch..."
env "${test_environment[@]}" \
    ODIA_MINICONDA_INSTALL_DIR="${test_miniconda_dir}" \
    ODIA_CONDA_ENV_DIR="${test_miniconda_environment}" \
    ODIA_CONDA_PKGS_DIR="${test_conda_pkgs_dir}" \
    ODIA_PIP_CACHE_DIR="${test_pip_cache_dir}" \
    ./bootstrap/miniconda/setup.sh

echo
echo "Testing existing Conda setup with the isolated Miniconda installation..."
env "${test_environment[@]}" \
    ODIA_CONDA_COMMAND="${test_miniconda_dir}/bin/conda" \
    ODIA_CONDA_ENV_DIR="${test_conda_environment}" \
    ODIA_CONDA_PKGS_DIR="${test_conda_pkgs_dir}" \
    ODIA_PIP_CACHE_DIR="${test_pip_cache_dir}" \
    ./bootstrap/conda/setup.sh

echo
echo "Testing uv from scratch..."
env "${test_environment[@]}" \
    ODIA_UV_INSTALL_DIR="${test_bin_dir}" \
    ODIA_UV_CACHE_DIR="${test_uv_cache_dir}" \
    ODIA_UV_PYTHON_INSTALL_DIR="${test_uv_python_dir}" \
    UV_PROJECT_ENVIRONMENT="${test_uv_environment}" \
    ./bootstrap/uv/setup.sh

for report_name in miniconda conda uv; do
    report_path="${test_dir}/${report_name}.md"
    if [[ ! -f "${report_path}" ]]; then
        echo "Expected bootstrap report was not created: ${report_path}" >&2
        exit 1
    fi
done

echo
echo "All bootstrap paths completed successfully. Reports:"
echo "  ${test_dir}/miniconda.md"
echo "  ${test_dir}/conda.md"
echo "  ${test_dir}/uv.md"
