#!/usr/bin/env bash

set -euo pipefail

bootstrap_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${bootstrap_dir}/../.." && pwd)"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is required. Install it from https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

cd "${project_root}"
uv sync --locked
uv run python bootstrap/verify_environment.py

echo
echo "Environment ready. Run ODIA with: uv run odia"
