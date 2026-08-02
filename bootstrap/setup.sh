#!/usr/bin/env bash

# Safer Bash settings:
# -e stops the script when a command fails.
# -u stops the script when it uses a variable that was not set.
# -o pipefail makes a pipeline fail if any command in it fails.
set -euo pipefail

# Simple workflow:
#   1. Find the project and operating system.
#   2. Ask the user to choose uv, Conda, or Miniconda.
#   3. Let that manager prepare Python and packages.
#   4. Start ODIA.

# BASH_SOURCE[0] is the path to this setup.sh file.
# dirname removes the filename and returns its directory.
# cd enters that directory, and pwd prints its full path.
bootstrap_dir="$(
    cd "$(dirname "${BASH_SOURCE[0]}")" &&
    pwd
)"

# .. means the parent directory, so this moves from bootstrap/ to the project root.
project_root="$(
    cd "${bootstrap_dir}/.." &&
    pwd
)"

# Detect macOS or Linux. Windows uses bootstrap/setup.ps1 instead.
# uname prints system information. The -s option prints the system name.
# $(uname -s) runs that command and inserts its result here.
# case then matches the result: Darwin means macOS and Linux means Linux.
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

# Print command help for the user.
usage() {
    cat <<EOF
Usage: $0 [uv|conda|miniconda]

With no manager, opens the interactive ODIA environment chooser.

  uv         Install uv, Python, and the ODIA environment locally
  conda      Use an existing Conda executable with a local ODIA environment
  miniconda  Install a private Miniconda and ODIA environment locally
EOF
}

# $1 is the first argument given to this script, such as "uv".
# ${1:-} uses $1 when it exists; otherwise, :- supplies an empty default value.
# This lets the script run without an argument and show the menu instead.
selected_manager="${1:-}"

case "${selected_manager}" in
    "")
        # No argument: the menu will ask the user.
        ;;
    uv|conda|miniconda)
        # The user selected a supported manager.
        ;;
    -h|--help)
        usage
        exit 0
        ;;
    *)
        echo "Choose uv, conda, or miniconda." >&2
        exit 2
        ;;
esac

# Ask the user to choose an environment manager.
choose_manager() {
    # local means this variable exists only inside choose_manager().
    local choice

    # The menu needs an interactive keyboard.
    if [[ ! -t 0 ]]; then
        echo "Cannot open the menu. Choose directly: $0 uv" >&2
        return 2
    fi

    echo "🛠️  ODIA setup (${platform_name})"
    echo "1) ⚡ uv (recommended: faster)"
    echo "2) 🐍 Conda"
    echo "3) 📦 Miniconda"
    echo
    echo "Press Ctrl+C to cancel."

    # Keep asking until the user enters 1, 2, or 3.
    while true; do
        # read waits for keyboard input and saves it in choice.
        # -r reads the input exactly, and -p displays the prompt first.
        read -r -p "Choose 1-3: " choice

        # A valid choice sets the manager, and break ends the loop.
        case "${choice}" in
            1)
                selected_manager="uv"
                break
                ;;
            2)
                selected_manager="conda"
                break
                ;;
            3)
                selected_manager="miniconda"
                break
                ;;
            # * matches any other answer, then the loop asks again.
            *)
                echo "Please choose 1, 2, or 3." >&2
                ;;
        esac
    done
}

# ----- Main program starts here -----

# All manager commands run from the repository root.
cd "${project_root}"

# -z is true when a string has zero characters (it is empty).
# If no manager was given, selected_manager is empty, so show the menu.
if [[ -z "${selected_manager}" ]]; then
    choose_manager
fi

# The selected manager prepares its environment and starts ODIA.
manager_script="${bootstrap_dir}/managers/${selected_manager}.sh"
printf '\nPlatform: %s\n' "${platform_name}"
printf 'Selected: %s\n' "${selected_manager}"
printf 'Preparing the project-local environment…\n\n'
exec "${manager_script}"
