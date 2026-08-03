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
Usage: $0 [uv] [--codex-ssh SSH_TARGET]

With no manager, uses uv.

  uv         Locked, repeatable project environment

Optional Story generation:
  --codex-ssh SSH_TARGET
             Transfers each story session and runs Codex on another machine over SSH.
             SSH_TARGET is an alias or user@host reachable with key authentication.

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

# Read the manager and optional remote Codex target in either order.
selected_manager="uv"
manager_was_selected=0
codex_ssh_target=""

while (( $# > 0 )); do
    case "$1" in
        uv|conda)
            if (( manager_was_selected )); then
                echo "Choose only one environment manager." >&2
                exit 2
            fi
            selected_manager="$1"
            manager_was_selected=1
            shift
            ;;
        --codex-ssh)
            if (( $# < 2 )) || [[ "$2" == -* ]]; then
                echo "--codex-ssh requires an SSH target." >&2
                exit 2
            fi
            codex_ssh_target="$2"
            shift 2
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
done

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
    *)
        echo "Only uv is currently supported." >&2
        exit 2
        ;;
esac

if [[ -n "${codex_ssh_target}" ]]; then
    printf 'Checking Codex SSH target: %s\n' "${codex_ssh_target}"
    ssh_options=(-o BatchMode=yes -o ConnectTimeout=10)
    remote_codex_probe='if command -v codex >/dev/null 2>&1; then command -v codex; elif [ -x /opt/homebrew/bin/codex ]; then printf "%s\n" /opt/homebrew/bin/codex; elif [ -x "$HOME/.local/bin/codex" ]; then printf "%s\n" "$HOME/.local/bin/codex"; else exit 127; fi'

    if ! remote_codex_executable="$(
        ssh "${ssh_options[@]}" "${codex_ssh_target}" "${remote_codex_probe}"
    )"; then
        echo "Could not connect to Codex SSH target '${codex_ssh_target}' or find Codex there." >&2
        exit 1
    fi
    remote_codex_executable="${remote_codex_executable%%$'\n'*}"
    if [[ ! "${remote_codex_executable}" =~ ^[A-Za-z0-9_./-]+$ ]]; then
        echo "Codex SSH target returned an unsafe executable path." >&2
        exit 1
    fi
    if ! ssh "${ssh_options[@]}" "${codex_ssh_target}" \
        "${remote_codex_executable}" login status; then
        echo "Codex is not authenticated on SSH target '${codex_ssh_target}'." >&2
        exit 1
    fi

    export ODIA_CODEX_SSH_TARGET="${codex_ssh_target}"
    export ODIA_CODEX_REMOTE_EXECUTABLE="${remote_codex_executable}"
    printf 'Remote Codex ready: %s (%s)\n' \
        "${codex_ssh_target}" "${remote_codex_executable}"
fi

# ----- Step 6: Start the main program from the project root -----

# All manager commands run from the repository root.
cd "${project_root}"

# ----- Step 7: Run the uv manager script -----

# uv prepares its project-local environment and starts ODIA.
printf '\nPlatform: %s\n' "${platform_name}"
printf 'Selected: uv\n'
printf 'Preparing the project-local environment…\n\n'
exec "${bootstrap_dir}/managers/uv.sh"
