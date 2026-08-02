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
./bootstrap/test/test.sh all
```

Run one setup path from a clean, isolated installation with:

```bash
./bootstrap/test/test.sh miniconda
./bootstrap/test/test.sh conda
./bootstrap/test/test.sh uv
```

The harness removes only `bootstrap/test/.state`, never system or personal
Conda, Miniconda, or uv installations. It cleans test-owned installations both
before the run, between every package-manager setup, and after the run.
Environments, package-manager binaries, caches, and managed Python
installations are all isolated below that directory. Set
`ODIA_BOOTSTRAP_TEST_KEEP_STATE=1` to preserve the final uv test state for
debugging after a run.

The Conda setup requires an existing Conda executable as its engine, but starts
with an empty project environment and package caches. The harness discovers
common Conda locations automatically. Override it when needed:

```bash
ODIA_BOOTSTRAP_TEST_CONDA_COMMAND=/path/to/conda ./bootstrap/test/test.sh
```

After an `all` run, `comparison.md` summarizes total times. An individual run
writes only its selected report and removes any stale `comparison.md`. The
individual reports contain per-stage timings. Required shared model weights are
provisioned before timing starts so the first package manager does not pay a
one-time download penalty.

Remove leftover test-owned installations without running setup again:

```bash
./bootstrap/test/test.sh --clean-only
```
