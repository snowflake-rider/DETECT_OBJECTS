# New-machine bootstrap

This directory provides reproducible setup paths for new contributors. Run all
commands from the repository root.

## Recommended: uv

Run:

```bash
./bootstrap/uv/setup.sh
```

If `uv` is missing, the script installs it into the standard user executable
directory without editing shell profiles. It then installs the locked Python
3.11 environment into `odia-uv`, installs the local `detect_objects` package,
downloads the required YOLO-World weights, and verifies required imports and
runtime resources. The script prints the exact command to launch ODIA.

## Existing Conda

If Conda is already installed, run:

```bash
./bootstrap/conda/setup.sh
```

This path works with an existing Miniconda, Miniforge, or Anaconda Distribution
installation. It does not install Conda automatically and creates the
`odia-conda` environment by default.

## Managed Miniconda

To install a private Miniconda distribution for ODIA, run:

```bash
./bootstrap/miniconda/setup.sh
```

The default environment name is `odia-miniconda`. To choose another name:

```bash
ODIA_CONDA_ENV=my-environment ./bootstrap/miniconda/setup.sh
```

The managed path installs Miniconda under the standard user data directory
without editing shell profiles. It supports macOS and Linux on Apple
Silicon/ARM64 and x86-64. Both Conda paths create a Python 3.11 environment,
install `requirements.txt` and the local src-layout package, download the
required YOLO-World weights, verify the result, and print direct launch and
activation commands.

The uv and managed Miniconda installers require either `curl` or `wget`. Custom
install locations are available through `ODIA_UV_INSTALL_DIR` and
`ODIA_MINICONDA_INSTALL_DIR`.

## Verify an existing environment

With the desired environment active, run:

```bash
python bootstrap/verify_environment.py
```

The verifier does not access the camera or microphone. Hardware access is
tested interactively when ODIA starts.
