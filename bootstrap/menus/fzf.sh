#!/usr/bin/env bash

# Choose a manager with fzf when fzf is already installed.
choose_manager() {
    local choice

    if [[ ! -t 0 ]]; then
        echo "Cannot open the menu. Choose directly: $0 uv" >&2
        return 2
    fi

    if ! choice="$(
        printf '%s\n' \
            "⚡️ uv          Locked and portable (recommended)" \
            "🐍 Conda       Installed automatically if missing" |
            "${fzf_command}" \
                --border \
                --border-label=' ODIA ENV SETUP ' \
                --border-label-pos=2 \
                --color='pointer:yellow,label:yellow,header:gray' \
                --cycle \
                --gap=1 \
                --height=16 \
                --header=$'Why uv is recommended:\nPortability: The same workflow works across supported operating systems.\nConsistency: uv.lock keeps dependency versions consistent across computers.\nIsolation: uv manages Python locally instead of using system Python.\nValidation: uv sync --locked detects dependency changes before launch.\n\nPython environments and packages stay under .odia/.\n↑/↓ move • Enter select • Q cancel' \
                --highlight-line \
                --info=hidden \
                --layout=reverse \
                --no-input \
                --no-multi \
                --pointer='▶' \
                --bind='q:abort'
    )"; then
        return 130
    fi

    case "${choice}" in
        "⚡️ uv"*) selected_manager="uv" ;;
        "🐍 Conda"*) selected_manager="conda" ;;
        *) return 2 ;;
    esac
}
