# Managed Miniconda setup

From the repository root, run:

```bash
./bootstrap/miniconda/setup.sh
```

The script installs a private Miniconda distribution under the standard user
data directory without modifying shell profiles. It then delegates environment
creation to `bootstrap/conda/setup.sh`. Automatic installation supports macOS
and Linux on Apple Silicon/ARM64 and x86-64.

Set `ODIA_CONDA_ENV` to choose a different environment name:

```bash
ODIA_CONDA_ENV=my-environment ./bootstrap/miniconda/setup.sh
```

Set `ODIA_MINICONDA_INSTALL_DIR` to choose the Miniconda installation location:

```bash
ODIA_MINICONDA_INSTALL_DIR=/path/to/miniconda3 ./bootstrap/miniconda/setup.sh
```

`ODIA_CONDA_INSTALL_DIR` remains supported as a legacy alias for the install
location.
