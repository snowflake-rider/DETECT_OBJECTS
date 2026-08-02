#!/usr/bin/env bash

# Shared timing and Markdown reporting for bootstrap entry points.

bootstrap_report_init() {
    bootstrap_report_name="$1"
    bootstrap_report_environment="$2"
    bootstrap_report_project_root="$3"
    bootstrap_report_script="$4"
    bootstrap_report_enabled="${ODIA_BOOTSTRAP_REPORT:-1}"

    if [[ "${bootstrap_report_enabled}" == "0" ]]; then
        return
    fi

    bootstrap_report_dir="${ODIA_BOOTSTRAP_REPORT_DIR:-${bootstrap_report_project_root}/bootstrap/reports}"
    bootstrap_report_path="${bootstrap_report_dir}/${bootstrap_report_name}.md"
    bootstrap_report_started_epoch="$(date +%s)"
    bootstrap_report_started_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    bootstrap_report_platform="$(uname -s) $(uname -m)"
    bootstrap_report_step_names=()
    bootstrap_report_step_seconds=()
    bootstrap_report_active_step=""
    bootstrap_report_active_epoch=""
}

bootstrap_report_step_start() {
    if [[ "${bootstrap_report_enabled:-0}" == "0" ]]; then
        return
    fi

    if [[ -n "${bootstrap_report_active_step:-}" ]]; then
        bootstrap_report_step_end
    fi

    bootstrap_report_active_step="$1"
    bootstrap_report_active_epoch="$(date +%s)"
}

bootstrap_report_step_end() {
    if [[ "${bootstrap_report_enabled:-0}" == "0" ||
        -z "${bootstrap_report_active_step:-}" ]]; then
        return
    fi

    local finished_epoch elapsed_seconds
    finished_epoch="$(date +%s)"
    elapsed_seconds=$((finished_epoch - bootstrap_report_active_epoch))
    bootstrap_report_step_names+=("${bootstrap_report_active_step}")
    bootstrap_report_step_seconds+=("${elapsed_seconds}")
    bootstrap_report_active_step=""
    bootstrap_report_active_epoch=""
}

bootstrap_report_format_duration() {
    local total_seconds="$1"
    local hours minutes seconds
    hours=$((total_seconds / 3600))
    minutes=$(((total_seconds % 3600) / 60))
    seconds=$((total_seconds % 60))

    if ((hours > 0)); then
        printf '%dh %dm %ds' "${hours}" "${minutes}" "${seconds}"
    elif ((minutes > 0)); then
        printf '%dm %ds' "${minutes}" "${seconds}"
    else
        printf '%ds' "${seconds}"
    fi
}

bootstrap_report_finish() {
    local exit_status="$1"

    if [[ "${bootstrap_report_enabled:-0}" == "0" ]]; then
        return
    fi

    bootstrap_report_step_end

    local finished_epoch finished_at total_seconds status_label temporary_report
    local step_index step_duration
    finished_epoch="$(date +%s)"
    finished_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    total_seconds=$((finished_epoch - bootstrap_report_started_epoch))

    case "${exit_status}" in
        0)
            status_label="Success"
            ;;
        130|143)
            status_label="Interrupted (exit ${exit_status})"
            ;;
        *)
            status_label="Failed (exit ${exit_status})"
            ;;
    esac

    mkdir -p "${bootstrap_report_dir}" || return 1
    temporary_report="$(mktemp "${bootstrap_report_dir}/.${bootstrap_report_name}.XXXXXX")" || return 1

    {
        printf '# %s bootstrap report\n\n' "${bootstrap_report_name}"
        printf -- '- Status: **%s**\n' "${status_label}"
        printf -- '- Environment: `%s`\n' "${bootstrap_report_environment}"
        printf -- '- Script: `%s`\n' "${bootstrap_report_script}"
        printf -- '- Platform: `%s`\n' "${bootstrap_report_platform}"
        printf -- '- Started (UTC): `%s`\n' "${bootstrap_report_started_at}"
        printf -- '- Finished (UTC): `%s`\n' "${finished_at}"
        printf -- '- Total: **%s** (%s seconds)\n\n' \
            "$(bootstrap_report_format_duration "${total_seconds}")" \
            "${total_seconds}"
        printf '| Stage | Duration | Seconds |\n'
        printf '| --- | ---: | ---: |\n'
        for ((step_index = 0; step_index < ${#bootstrap_report_step_names[@]}; step_index++)); do
            step_duration="${bootstrap_report_step_seconds[step_index]}"
            printf '| %s | %s | %s |\n' \
                "${bootstrap_report_step_names[step_index]}" \
                "$(bootstrap_report_format_duration "${step_duration}")" \
                "${step_duration}"
        done
    } >"${temporary_report}"

    mv "${temporary_report}" "${bootstrap_report_path}" || return 1
    printf 'Bootstrap report: %s\n' "${bootstrap_report_path}"
}

bootstrap_report_on_exit() {
    local exit_status="$?"
    trap - EXIT
    if ! bootstrap_report_finish "${exit_status}"; then
        echo "Warning: unable to write the bootstrap report." >&2
    fi
    exit "${exit_status}"
}

bootstrap_report_install_exit_trap() {
    if [[ "${bootstrap_report_enabled:-0}" != "0" ]]; then
        trap bootstrap_report_on_exit EXIT
    fi
}
