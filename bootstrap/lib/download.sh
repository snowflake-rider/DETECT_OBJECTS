#!/usr/bin/env bash

# Shared download helper used by:
#   - managers/uv.sh to download the uv installer.
#   - managers/miniconda.sh to download the Miniconda installer.

download_file() {
    # local creates a variable that exists only inside download_file().
    #
    # Function arguments are numbered in the order they were provided:
    #   $1 = first argument:  the URL to download
    #   $2 = second argument: the file where the download will be saved
    #   $3 = third argument:  the dependency name used in error messages
    #
    # For example:
    #   download_file "https://example.com/tool.sh" "/tmp/tool.sh" "tool"
    #
    # local url="$1" saves the first argument in a local variable named url.
    local url="$1"
    local destination="$2"
    local dependency_name="$3"

    # command -v asks the shell whether it can find a command named curl.
    #
    # Each process has two normal output streams:
    #   1 = standard output (normal information)
    #   2 = standard error (error information)
    #
    # > redirects standard output.
    # /dev/null discards anything written to it.
    # 2> redirects standard error.
    # &1 means "send it to the same place as standard output."
    #
    # Together, >/dev/null 2>&1 checks for curl without printing anything.
    # ! means "not", so this block runs when curl cannot be found.
    if ! command -v curl >/dev/null 2>&1; then
        # >&2 sends this message to standard error.
        # return 1 stops the function and reports failure.
        echo "Installing ${dependency_name} requires curl." >&2
        return 1
    fi

    # curl is a command-line program for transferring and downloading data.
    #
    # --fail           treats HTTP error responses as command failures.
    # --location       follows redirects to another URL.
    # --proto '=https' allows only HTTPS downloads.
    # --output         saves the result in destination instead of printing it.
    #
    # The backslash (\) continues the command on the next line.
    curl \
        --fail \
        --location \
        --proto '=https' \
        --output "${destination}" \
        "${url}"
}
