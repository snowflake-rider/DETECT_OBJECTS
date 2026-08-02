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
    # local means these variables exist only inside choose_manager().
    local options=("uv" "conda" "miniconda")
    local labels=("⚡ uv (recommended)" "🐍 Conda" "📦 Miniconda")
    local selected_index=0
    local key
    local index
    local alternate_screen_on
    local alternate_screen_off
    local screen_clear

    # $'...' lets Bash translate backslash codes into actual characters.
    # \e is the Escape character, whose ASCII value is decimal 27.
    # ASCII is contained inside UTF-8, so ESC is the same single byte in both.
    local escape=$'\e'

    # After the first ESC byte is read separately, an arrow key has two bytes
    # left. Up leaves "[A" and Down leaves "[B" in the key variable.
    local up_arrow_key="[A"
    local down_arrow_key="[B"

    # The menu needs an interactive keyboard.
    if [[ ! -t 0 ]]; then
        echo "Cannot open the menu. Choose directly: $0 uv" >&2
        return 2
    fi

    # tput asks the terminal for its supported control commands. It is included
    # with macOS and most Linux installations as part of ncurses.
    if ! command -v tput >/dev/null 2>&1; then
        echo "The interactive menu requires tput." >&2
        return 2
    fi

    # smcup opens the alternate screen used by programs such as vim.
    # rmcup closes it and returns to the user's normal terminal screen.
    # clear erases the alternate screen and moves the cursor to the top-left.
    alternate_screen_on="$(tput smcup)"
    alternate_screen_off="$(tput rmcup)"
    screen_clear="$(tput clear)"

    # Open the alternate screen.
    # The emoji labels are regular Unicode text stored and displayed as UTF-8;
    # they are separate from the terminal commands returned by tput.
    printf '%s' "${alternate_screen_on}"

    # trap asks Bash to run a command when a particular event occurs.
    # EXIT is a special event that happens whenever this script exits, including
    # after an error. Its command restores the normal terminal screen.
    trap 'printf "%s" "${alternate_screen_off}"' EXIT

    # INT is the interrupt sent by Ctrl+C. TERM is a normal request from another
    # process to terminate this script. Both exit with status 130. That exit then
    # triggers the EXIT trap above, so the terminal is restored before Bash ends.
    trap 'exit 130' INT TERM

    # Keep drawing the menu until the user selects a manager.
    while true; do
        # Clear the temporary screen and move the cursor to the top-left.
        printf '%s' "${screen_clear}"
        echo "🛠️  ODIA setup (${platform_name})"
        echo

        # This is Bash's arithmetic for loop:
        #   index = 0 starts at the first array position (arrays start at zero).
        #   ${#options[@]} is the number of entries in the options array.
        #   index++ adds one after each pass through the loop.
        # The loop therefore visits indexes 0, 1, and 2 and prints every option.
        for ((index = 0; index < ${#options[@]}; index++)); do
            if ((index == selected_index)); then
                printf '> %s\n' "${labels[index]}"
            else
                printf '  %s\n' "${labels[index]}"
            fi
        done

        echo
        echo "Use ↑/↓ and Enter, or press 1-3. Press Q or Ctrl+C to cancel."

        # read waits for keyboard input and saves it in the variable named key.
        #   -r keeps backslashes literal instead of treating them specially.
        #   -s means silent, so the pressed key is not printed on the screen.
        #   -n 1 stops after one character instead of waiting for Enter.
        read -r -s -n 1 key

        # Arrow keys send a three-character escape sequence. For example:
        #   Up   sends ESC, [, A
        #   Down sends ESC, [, B
        # The first read receives ESC. This second read collects the last two
        # characters and replaces key with "[A" or "[B" for the case below.
        if [[ "${key}" == "${escape}" ]]; then
            read -r -s -n 2 key
        fi

        # case compares one value against several patterns:
        #   case VALUE in
        #       PATTERN) commands ;;
        #   esac
        # "[A" and "[B" are arrow-key patterns, "" is Enter, and q|Q means
        # lowercase q OR uppercase Q. ;; ends one pattern's commands.
        case "${key}" in
            "${up_arrow_key}")
                # Up arrow: move up unless the first option is selected.
                if ((selected_index > 0)); then
                    selected_index=$((selected_index - 1))
                fi
                ;;
            "${down_arrow_key}")
                # Down arrow: move down unless the last option is selected.
                if ((selected_index < ${#options[@]} - 1)); then
                    selected_index=$((selected_index + 1))
                fi
                ;;
            "")
                # Enter returns an empty value and confirms the highlighted row.
                selected_manager="${options[selected_index]}"
                break
                ;;
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
            q|Q)
                exit 130
                ;;
        esac
    done

    # Return to the user's normal terminal screen.
    printf '%s' "${alternate_screen_off}"

    # trap - removes our custom actions and restores the default signal actions.
    # The terminal is already restored, so the EXIT cleanup is no longer needed.
    trap - INT TERM EXIT
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
