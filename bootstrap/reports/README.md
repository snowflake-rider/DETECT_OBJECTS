# Bootstrap timing reports

Each top-level bootstrap script writes its latest timing report here:

- `conda.md`
- `miniconda.md`
- `uv.md`

Reports include the environment, result, total duration, and per-stage timings.
Generated reports are machine-specific and ignored by Git. Set
`ODIA_BOOTSTRAP_REPORT_DIR` to write them elsewhere, or set
`ODIA_BOOTSTRAP_REPORT=0` to disable reporting.
