#!/usr/bin/env bash

set -euo pipefail

platform_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "bootstrap/linux/setup.sh can only run on Linux." >&2
    exit 2
fi

ODIA_BOOTSTRAP_PLATFORM_NAME="Linux" \
ODIA_BOOTSTRAP_PLATFORM_NOTE="Audio may require the PortAudio runtime from your Linux distribution." \
    exec "${platform_dir}/../setup.sh" "$@"
