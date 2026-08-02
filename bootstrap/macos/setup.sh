#!/usr/bin/env bash

set -euo pipefail

platform_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "bootstrap/macos/setup.sh can only run on macOS." >&2
    exit 2
fi

ODIA_BOOTSTRAP_PLATFORM_NAME="macOS" \
ODIA_BOOTSTRAP_PLATFORM_NOTE="Apple Silicon and Intel installers are selected automatically." \
    exec "${platform_dir}/../setup.sh" "$@"
