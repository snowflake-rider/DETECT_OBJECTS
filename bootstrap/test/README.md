# Bootstrap from-scratch tests and timing reports

Each top-level bootstrap script writes its latest timing report here:

- `conda.md`
- `miniconda.md`
- `uv.md`

Reports include the environment, result, total duration, and per-stage timings.
Generated reports are machine-specific and ignored by Git. Set
`ODIA_BOOTSTRAP_REPORT_DIR` to write them elsewhere, or set
`ODIA_BOOTSTRAP_REPORT=0` to disable reporting.

Run all three setup paths from clean, isolated installations with:

```bash
./bootstrap/test/test.sh
```

The harness removes only `bootstrap/test/.state`, never system or personal
Conda, Miniconda, or uv installations. It cleans test-owned installations both
before and after the run. Environments, package-manager binaries, caches, and
managed Python installations are all isolated below that directory. Set
`ODIA_BOOTSTRAP_TEST_KEEP_STATE=1` to preserve the test state for debugging
after a run.

Remove leftover test-owned installations without running setup again:

```bash
./bootstrap/test/test.sh --clean-only
```
