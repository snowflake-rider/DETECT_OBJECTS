#!/usr/bin/env bash

# Install a pinned fzf binary inside .odia/ without changing the user's shell.
install_project_fzf() {
    local fzf_version="0.72.0"
    local install_dir="${project_root}/.odia/tools/fzf"
    local temporary_dir
    local clone_dir

    if ! command -v git >/dev/null 2>&1; then
        echo "Installing fzf requires git." >&2
        return 1
    fi

    if [[ -e "${install_dir}" ]]; then
        echo "${install_dir} exists but does not contain a working fzf." >&2
        return 1
    fi

    if ! temporary_dir="$(mktemp -d "${TMPDIR:-/tmp}/odia-fzf-install.XXXXXX")"; then
        echo "Unable to create a temporary directory for fzf." >&2
        return 1
    fi
    clone_dir="${temporary_dir}/fzf"

    echo "Installing fzf ${fzf_version} into ${install_dir}..."

    if ! git clone \
        --branch "v${fzf_version}" \
        --depth 1 \
        https://github.com/junegunn/fzf.git \
        "${clone_dir}"; then
        rm -rf "${temporary_dir}"
        return 1
    fi

    # --bin downloads only the fzf executable. It does not edit shell profiles.
    if ! "${clone_dir}/install" --bin; then
        rm -rf "${temporary_dir}"
        return 1
    fi

    if [[ ! -x "${clone_dir}/bin/fzf" ]]; then
        echo "fzf installation did not produce an executable." >&2
        rm -rf "${temporary_dir}"
        return 1
    fi

    if ! mkdir -p "$(dirname "${install_dir}")" ||
        ! mv "${clone_dir}" "${install_dir}"; then
        echo "Unable to move fzf into ${install_dir}." >&2
        rm -rf "${temporary_dir}"
        return 1
    fi

    rm -rf "${temporary_dir}"

    fzf_command="${install_dir}/bin/fzf"
}
