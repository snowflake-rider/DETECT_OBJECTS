#!/usr/bin/env bash

# ----- Step 1: Enable safer Bash behavior -----

# Stop on command errors (e), missing variables (u), and failed pipeline commands (o).
set -euo pipefail

# Bash commands used later in this script:
# | Command    | What it does                                         |
# | ---------- | ---------------------------------------------------- |
# | read       | Read keyboard input into a variable                  |
# | source     | Load another shell file into the current shell       |
# | echo       | Print a simple line of text                           |
# | command -v | Find a command and print its location                 |
# | printf     | Print formatted text with explicit newlines          |
# | exec       | Replace setup.sh with the selected manager script    |

# ----- Step 2: Find the bootstrap directory and project root -----

# BASH_SOURCE[0] is this script's path. (e.g. ../detect_objects/bootstrap/setup.sh)
# dirname removes "setup.sh", then cd enters bootstrap/ and pwd returns its full path.
bootstrap_dir="$(
    cd "$(dirname "${BASH_SOURCE[0]}")" &&
    pwd
)"

# .. moves one level up from bootstrap/ to the project root.
project_root="$(
    cd "${bootstrap_dir}/.." &&
    pwd
)"

# ----- Step 3: Detect the operating system -----

# uname -s returns
# 1. Darwin on macOS or
# 2. Linux on Linux.
# NOTE: Windows uses setup.ps1.
case "$(uname -s)" in
    Darwin)
        platform_name="macOS"
        ;;
    Linux)
        platform_name="Linux"
        ;;
    *)
        echo "setup.sh supports macOS and Linux." >&2
        echo "On Windows, run: .\\bootstrap\\setup.ps1" >&2
        exit 2
        ;;
esac

# ----- Step 4: Define the help function -----

# Defining a function stores its commands; the commands do not run yet.
# Step 5 calls usage only when the user passes -h or --help.
usage() {
    cat <<EOF
Usage: $0 [uv|conda]

With no manager, opens the interactive ODIA environment chooser.

  uv         Locked, repeatable project environment (recommended)
  conda      Use Conda (installed automatically if missing)

Why uv is recommended for this project:
  Portability: The same setup workflow works on macOS, Linux, and Windows.
  Consistency: uv.lock keeps dependency versions consistent across computers.
  Isolation: uv installs Python without relying on the system Python.
  Validation: uv sync --locked detects an outdated lockfile before launch.
EOF
}

# ----- Step 5: Read and validate the optional manager argument -----

# $1 is the first argument given to this script, such as "uv".
# ${1:-} uses $1 when it exists; otherwise, :- supplies an empty default value.
# This lets the script run without an argument and show the menu instead.
selected_manager="${1:-}"

case "${selected_manager}" in
    "")
        # No argument: the menu will ask the user.
        ;;
    uv|conda)
        # The user selected a supported manager.
        ;;
    -h|--help)
        usage
        exit 0
        ;;
    *)
        echo "Choose uv or conda." >&2
        exit 2
        ;;
esac

# ----- Step 6: Start the main program from the project root -----

# All manager commands run from the repository root.
cd "${project_root}"

# ----- Step 7: Ask for a manager when none was provided -----

# -z is true when a string has zero characters (it is empty).
# If no manager was given, selected_manager is empty, so show the menu.
if [[ -z "${selected_manager}" ]]; then
    fzf_command="$(command -v fzf || true)"
    project_fzf="${project_root}/.odia/tools/fzf/bin/fzf"

    # Reuse the project-local fzf when a previous setup installed it.
    if [[ -z "${fzf_command}" && -x "${project_fzf}" ]]; then
        fzf_command="${project_fzf}"
    fi

    # Ask before installing optional menu software.
    if [[ -z "${fzf_command}" && -t 0 ]]; then
        read -r -p "fzf is not installed. Install it locally? [y/N] " install_fzf_choice

        if [[ "${install_fzf_choice}" == "y" || "${install_fzf_choice}" == "Y" ]]; then
            source "${bootstrap_dir}/tools/install_fzf.sh"

            if ! install_project_fzf; then
                echo "fzf installation failed; using the simple menu." >&2
                fzf_command=""
            fi
        fi
    fi

    if [[ -n "${fzf_command}" ]]; then
        source "${bootstrap_dir}/menus/fzf.sh"
    else
        source "${bootstrap_dir}/menus/simple.sh"
    fi

    choose_manager
fi

# ----- Step 8: Run the selected manager script -----

# The selected manager prepares its environment and starts ODIA.
manager_script="${bootstrap_dir}/managers/${selected_manager}.sh"
printf '\nPlatform: %s\n' "${platform_name}"
printf 'Selected: %s\n' "${selected_manager}"
printf 'Preparing the project-local environment…\n\n'
exec "${manager_script}"
