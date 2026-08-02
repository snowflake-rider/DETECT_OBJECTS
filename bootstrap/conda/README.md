# Existing Conda setup

This setup path uses an existing Conda installation, including Miniconda,
Miniforge, or Anaconda Distribution. It does not install a Conda distribution.

From the repository root, run:

```bash
./bootstrap/conda/setup.sh
```

The environment is created at the project-local `odia-conda` directory. Set
`ODIA_CONDA_ENV_DIR` to use a different path. `ODIA_CONDA_ENV` remains supported
as a project-relative directory name. The script prints a direct ODIA launch
command and an activation command. After installing the Python package, it
downloads the configured YOLO-World weights when they are missing.
The latest timing report is written to `bootstrap/test/conda.md`.

Conda and pip package caches default to `.odia-tools/conda-pkgs` and
`.odia-tools/pip-cache`. Override them with `ODIA_CONDA_PKGS_DIR` and
`ODIA_PIP_CACHE_DIR`.

If `conda` is not on `PATH`, provide its executable explicitly:

```bash
ODIA_CONDA_COMMAND=/path/to/conda ./bootstrap/conda/setup.sh
```

The executable is used only to create and operate the project-local prefix; no
packages are installed into its base or named environments.

To install a private Miniconda distribution for ODIA instead, run:

```bash
./bootstrap/miniconda/setup.sh
```
