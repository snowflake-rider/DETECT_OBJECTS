#!/usr/bin/env bash

# Print the two manager labels with > beside the selected one.
# $1 is the selected index: 0 for uv or 1 for Conda.
print_manager_options() {
    local selected_index="$1"
    local uv_label="⚡️ uv          Locked and portable (recommended)"
    local conda_label="🐍 Conda       Installed automatically if missing"

    case "${selected_index}" in
        0)
            printf '> %s\n' "${uv_label}"
            printf '  %s\n' "${conda_label}"
            ;;
        1)
            printf '  %s\n' "${uv_label}"
            printf '> %s\n' "${conda_label}"
            ;;
    esac
}

# Ask the user to choose an environment manager.
choose_manager() {
    local options=("uv" "conda")
    local selected_index=0
    local key
    local alternate_screen_on
    local alternate_screen_off
    local screen_clear

    # Keyboard values used by the menu:
    # | Value | Meaning                             |
    # | ----- | ----------------------------------- |
    # | $'\e' | Escape character (ASCII decimal 27) |
    # | "[A"  | Up arrow after reading ESC          |
    # | "[B"  | Down arrow after reading ESC        |
    local escape=$'\e'
    local up_arrow_key="[A"
    local down_arrow_key="[B"

    if [[ ! -t 0 ]]; then
        echo "Cannot open the menu. Choose directly: $0 uv" >&2
        return 2
    fi

    # tput supplies terminal commands and is included with macOS and most Linux.
    if ! command -v tput >/dev/null 2>&1; then
        echo "The interactive menu requires tput." >&2
        return 2
    fi

    # Terminal commands used by the menu:
    # | Command | Saved variable       | Purpose                    |
    # | ------- | -------------------- | -------------------------- |
    # | smcup   | alternate_screen_on  | Open a temporary screen    |
    # | rmcup   | alternate_screen_off | Restore the normal screen  |
    # | clear   | screen_clear         | Clear and move to top-left |
    alternate_screen_on="$(tput smcup)"
    alternate_screen_off="$(tput rmcup)"
    screen_clear="$(tput clear)"

    printf '%s' "${alternate_screen_on}"

    # Restore the normal screen if setup exits before the user makes a choice.
    trap 'printf "%s" "${alternate_screen_off}"' EXIT
    trap 'exit 130' INT TERM

    while true; do
        printf '%s' "${screen_clear}"
        echo "🛠️  ODIA setup (${platform_name})"
        echo
        echo "Why uv is recommended:"
        echo "Portability: The same workflow works across supported operating systems."
        echo "Consistency: uv.lock keeps dependency versions consistent across computers."
        echo "Isolation: uv manages Python locally instead of using system Python."
        echo "Validation: uv sync --locked detects dependency changes before launch."
        echo
        echo "Python environments and packages stay under .odia/."
        echo
        print_manager_options "${selected_index}"
        echo
        echo "Use ↑/↓ and Enter, or press 1-2. Press Q or Ctrl+C to cancel."

        # Read one key silently without waiting for Enter.
        read -r -s -n 1 key

        # Arrow keys send ESC followed by two more bytes.
        if [[ "${key}" == "${escape}" ]]; then
            read -r -s -n 2 key
        fi

        case "${key}" in
            "${up_arrow_key}")
                if ((selected_index > 0)); then
                    selected_index=$((selected_index - 1))
                fi
                ;;
            "${down_arrow_key}")
                if ((selected_index < ${#options[@]} - 1)); then
                    selected_index=$((selected_index + 1))
                fi
                ;;
            "")
                selected_manager="${options[selected_index]}"
                break
                ;;
            1) selected_manager="uv"; break ;;
            2) selected_manager="conda"; break ;;
            q|Q) exit 130 ;;
        esac
    done

    printf '%s' "${alternate_screen_off}"
    trap - INT TERM EXIT
}
