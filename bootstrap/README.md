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
3.11 environment into `.venv`, installs the local `detect_objects` package,
and verifies required imports and runtime resources. The script prints the
exact command to launch ODIA.

## Conda

Run:

```bash
./bootstrap/conda/setup.sh
```

The default environment name is `odia`. To choose another name:

```bash
ODIA_CONDA_ENV=my-environment ./bootstrap/conda/setup.sh
```

If `conda` is missing, the script installs Miniconda under the standard user
data directory without editing shell profiles. The Conda path then creates a
Python 3.11 environment and installs `requirements.txt` followed by the local
src-layout package. Automatic Miniconda installation supports macOS and Linux
on Apple Silicon/ARM64 and x86-64.
The script prints both a direct launch command and the appropriate activation
command.

Both installers require either `curl` or `wget`. Custom install locations are
available through `ODIA_UV_INSTALL_DIR` and `ODIA_CONDA_INSTALL_DIR`.

## Verify an existing environment

With the desired environment active, run:

```bash
python bootstrap/verify_environment.py
```

The verifier does not access the camera or microphone. Hardware access is
tested interactively when ODIA starts.
