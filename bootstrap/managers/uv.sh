#!/usr/bin/env bash

set -euo pipefail

# uv workflow:
#   1. Find the project and choose paths inside .odia/.
#   2. Install uv locally if it is missing.
#   3. Create or update the locked Python environment.
#   4. Download models, verify the environment, and start ODIA.

# Find this file, bootstrap/, and then the project root.
manager_dir="$(cd
    "$(dirname "${BASH_SOURCE[0]}")"
    && pwd
)"
bootstrap_dir="$(cd
    "${manager_dir}/.."
    && pwd
)"
project_root="$(cd
    "${bootstrap_dir}/.."
    && pwd
)"

# source reads download.sh inside this current shell; it does not start a
# separate shell program. download.sh defines download_file(), so nothing is
# downloaded yet. The function becomes available for this script to call later.
source "${bootstrap_dir}/lib/download.sh"

# Keep uv, Python, packages, and caches inside the project.
state_dir="${project_root}/.odia"
uv_environment="${state_dir}/envs/uv"
uv_install_dir="${state_dir}/tools/bin"
uv_cache_dir="${state_dir}/caches/uv"
uv_python_install_dir="${state_dir}/tools/python"
uv_command="${uv_install_dir}/uv"

# -x is true when the file exists and can be executed.
if [[ ! -x "${uv_command}" ]]; then
    # mktemp creates a unique temporary file for the downloaded installer.
    uv_installer="$(mktemp "${TMPDIR:-/tmp}/odia-uv-install.XXXXXX")"

    # trap schedules a command to run when a shell event occurs.
    # EXIT means whenever this script finishes, including after an error.
    # rm removes the temporary installer, and -f does not complain if it is gone.
    # This protects us from leaving the installer behind when setup stops early.
    trap 'rm -f "${uv_installer}"' EXIT

    echo "uv was not found; installing it into ${uv_install_dir}..."
    download_file "https://astral.sh/uv/install.sh" "${uv_installer}" "uv"

    # These exported variables are temporary installer settings.
    # They are available to the downloaded installer while it is running.
    # This assignment copies the directory path; it does not execute it.
    export UV_INSTALL_DIR="${uv_install_dir}"

    # 1 means "enabled": do not edit the user's shell profile or PATH.
    export UV_NO_MODIFY_PATH=1

    # sh executes the downloaded installer script.
    sh "${uv_installer}"

    # These settings were needed only by the installer, so remove them now.
    # This setup script cannot export them back into the parent terminal.
    unset UV_INSTALL_DIR UV_NO_MODIFY_PATH

    # Installation finished, so remove the installer now.
    rm -f "${uv_installer}"

    # trap - EXIT cancels the scheduled EXIT command because cleanup is done.
    trap - EXIT

    # -x checks whether uv exists and is executable.
    # ! reverses the result, so this block runs when installation failed to
    # create a uv command that the shell can execute.
    if [[ ! -x "${uv_command}" ]]; then
        echo "uv installation did not produce ${uv_command}." >&2
        exit 1
    fi
fi

# Export these settings so every following uv command uses the local paths.
cd "${project_root}"
export UV_CACHE_DIR="${uv_cache_dir}"
export UV_PROJECT_ENVIRONMENT="${uv_environment}"
export UV_PYTHON_INSTALL_DIR="${uv_python_install_dir}"

# "${uv_command}" expands to the uv executable path. Because it appears at the
# start of the line, Bash executes it as a command. These are real commands,
# not descriptions or dry runs.

# sync creates or updates the Python environment from uv.lock.
# --locked refuses to change uv.lock and fails when it is out of date.
echo "Preparing the Python environment..."
"${uv_command}" sync --locked

# uv run starts a command inside the prepared uv environment.
# This runs download_models.py, which downloads missing YOLO model files.
echo "Downloading required models..."
"${uv_command}" run python bootstrap/tools/download_models.py

# This runs verify_environment.py inside the same environment. It checks
# Python 3.11, required imports, configuration, models, and sample files.
echo "Verifying the environment..."
"${uv_command}" run python bootstrap/tools/verify_environment.py

echo
echo "Environment ready. Starting ODIA..."

# exec replaces this setup process with the ODIA process.
exec "${uv_command}" run odia
