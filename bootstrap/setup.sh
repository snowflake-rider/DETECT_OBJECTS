#!/usr/bin/env bash

# ----- Step 1: Enable safer Bash behavior -----

# Stop on command errors (e), missing variables (u), and failed pipeline commands (o).
set -euo pipefail

# Bash commands used later in this script:
# | Command | What it does                                      |
# | ------- | ------------------------------------------------- |
# | echo    | Print a simple line of text                        |
# | printf  | Print formatted text with explicit newlines       |
# | exec    | Replace setup.sh with the uv manager script       |

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
Usage: $0 [uv]

With no manager, uses uv.

  uv         Locked, repeatable project environment

Why uv is used for this project:
  Portability: The same setup workflow works on macOS, Linux, and Windows.
  Consistency: uv.lock keeps dependency versions consistent across computers.
  Isolation: uv installs Python without relying on the system Python.
  Validation: uv sync --locked detects an outdated lockfile before launch.

Conda status:
  Temporarily disabled because the uv workflow is verified and working reliably.
  Setup stays on one known-good environment path while Conda support is reviewed.
EOF
}

# ----- Step 5: Read and validate the optional manager argument -----

# $1 is the first argument given to this script, such as "uv".
# ${1:-uv} uses $1 when it exists and defaults to uv otherwise.
selected_manager="${1:-uv}"

case "${selected_manager}" in
    uv)
        ;;
    conda)
        # Keep Conda as an explicit disabled option so the reason is visible to
        # callers instead of treating it as an unknown manager.
        echo "Conda setup is temporarily disabled because the uv workflow is verified and working reliably." >&2
        echo "Use uv while Conda support is reviewed." >&2
        exit 2
        ;;
    -h|--help)
        usage
        exit 0
        ;;
    *)
        echo "Only uv is currently supported." >&2
        exit 2
        ;;
esac

# ----- Step 6: Start the main program from the project root -----

# All manager commands run from the repository root.
cd "${project_root}"

# ----- Step 7: Run the uv manager script -----

# uv prepares its project-local environment and starts ODIA.
printf '\nPlatform: %s\n' "${platform_name}"
printf 'Selected: uv\n'
printf 'Preparing the project-local environment…\n\n'
exec "${bootstrap_dir}/managers/uv.sh"
