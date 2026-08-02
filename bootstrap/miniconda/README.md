# Managed Miniconda setup

From the repository root, run:

```bash
./bootstrap/miniconda/setup.sh
```

The script installs a private Miniconda distribution under the project-local
`.odia-tools/miniconda3` directory without modifying shell profiles. It then
delegates creation of the `odia-miniconda` environment directory to
`bootstrap/conda/setup.sh`. Automatic installation supports macOS and Linux on
Apple Silicon/ARM64 and x86-64. The delegated setup also downloads the
configured YOLO-World weights when they are missing.
The latest timing report is written to `bootstrap/test/miniconda.md`.

Set `ODIA_CONDA_ENV_DIR` to choose a different environment path:

```bash
ODIA_CONDA_ENV_DIR=/path/to/environment ./bootstrap/miniconda/setup.sh
```

Set `ODIA_MINICONDA_INSTALL_DIR` to choose the Miniconda installation location:

```bash
ODIA_MINICONDA_INSTALL_DIR=/path/to/miniconda3 ./bootstrap/miniconda/setup.sh
```

`ODIA_CONDA_INSTALL_DIR` remains supported as a legacy alias for the install
location.
