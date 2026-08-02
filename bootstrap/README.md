# New-machine bootstrap

This directory provides reproducible setup paths for new contributors. Run all
commands from the repository root.

## Guided setup

Choose the entrypoint for the current operating system:

```bash
# macOS
./bootstrap/macos/setup.sh

# Linux
./bootstrap/linux/setup.sh

# Windows PowerShell
powershell -ExecutionPolicy Bypass -File .\bootstrap\windows\setup.ps1
```

On macOS and Linux, `./bootstrap/setup.sh` remains a convenience entrypoint and
detects the platform automatically. The Windows entrypoint is native PowerShell
and does not require Git Bash or WSL.

Use the arrow keys and Enter to choose **★ uv (recommended)**, an existing
Conda installation, or a private project-local Miniconda installation. After
installation and verification, the launcher starts ODIA's device and model
selection wizard automatically.

uv is the recommended default because it is usually the fastest and most
reproducible option for this project. It is not accurate to call any virtual
environment fully portable between machines. The existing-Conda option keeps
the ODIA environment and caches local but reuses a Conda executable already on
the machine; Miniconda is the fully project-local Conda distribution option.

For automation, bypass the chooser or stop after installation:

```bash
./bootstrap/macos/setup.sh uv
./bootstrap/linux/setup.sh conda --install-only
powershell -ExecutionPolicy Bypass -File .\bootstrap\windows\setup.ps1 uv -InstallOnly
```

Each OS-specific entrypoint presents the same three choices and keeps the ODIA
environment and caches below the repository. The Windows script uses
Windows-native `uv.exe`, Conda executables, Miniconda installer, paths, and
PowerShell commands. macOS and Linux share the Bash interaction code but reject
being run on the wrong operating system.

On Linux, `sounddevice` may also require the PortAudio runtime supplied by the
distribution (for example, `libportaudio2` on Debian/Ubuntu). The script keeps
Python packages local but does not use `sudo` or install operating-system
packages automatically.

## Project-local layout

Bootstrap state is contained in the repository and ignored by Git:

```text
detect_objects/
├── bootstrap/
│   ├── macos/setup.sh         # guarded macOS entrypoint
│   ├── linux/setup.sh         # guarded Linux entrypoint
│   └── windows/setup.ps1      # native Windows entrypoint
├── odia-conda/                 # existing-Conda environment
├── odia-miniconda/             # managed-Miniconda environment
├── odia-uv/                    # uv environment
└── .odia-tools/
    ├── miniconda3/             # managed Miniconda distribution
    ├── bin/uv[.exe]            # project-local uv executable
    ├── conda-pkgs/             # Conda package cache
    ├── pip-cache/              # pip download cache
    ├── uv-cache/               # uv package cache
    └── uv-python/              # uv-managed Python installations
```

The existing-Conda path still requires a Conda executable, because Conda is a
package manager rather than a separate distribution installer. That executable
is used only as the engine for the project-local environment and cache. Use the
managed-Miniconda path when the Conda executable itself must also live inside
the repository.

## Recommended: uv

Run:

```bash
./bootstrap/uv/setup.sh
```

The script installs a project-local uv executable under `.odia-tools/bin` and
the locked Python 3.11 environment into `odia-uv`. Its cache and any uv-managed
Python installation also remain under `.odia-tools`. It installs the local
`detect_objects` package, downloads the required YOLO-World weights, verifies
runtime resources, and prints the exact command to launch ODIA.

## Existing Conda

If Conda is already installed, run:

```bash
./bootstrap/conda/setup.sh
```

This path works with an existing Miniconda, Miniforge, or Anaconda Distribution
installation only as the bootstrap executable. It does not install Conda
automatically. The environment is created at `odia-conda`, while Conda and pip
caches remain under `.odia-tools`; existing named environments are not used.

## Managed Miniconda

To install a private Miniconda distribution for ODIA, run:

```bash
./bootstrap/miniconda/setup.sh
```

The default environment directory is `odia-miniconda`. To choose another path:

```bash
ODIA_CONDA_ENV_DIR=/path/to/environment ./bootstrap/miniconda/setup.sh
```

The managed path installs Miniconda under `.odia-tools/miniconda3` without
editing shell profiles. It supports macOS and Linux on Apple Silicon/ARM64 and
x86-64. Both Conda paths create a project-local Python 3.11 environment,
install `requirements.txt` and the local src-layout package, download the
required YOLO-World weights, verify the result, and print launch and activation
commands.

The uv and managed Miniconda installers require either `curl` or `wget`.
Project-local defaults can be overridden through `ODIA_UV_INSTALL_DIR`,
`ODIA_MINICONDA_INSTALL_DIR`, and the environment-specific variables described
in each setup directory.

## Timing reports

Each top-level setup writes its latest Markdown timing report under
`bootstrap/test/`: `conda.md`, `miniconda.md`, or `uv.md`. Reports include
the result, environment, total duration, and per-stage timings. Interrupted and
failed runs are recorded too.

Set `ODIA_BOOTSTRAP_REPORT_DIR` to use another report directory, or disable
reporting with `ODIA_BOOTSTRAP_REPORT=0`.

Run `./bootstrap/test/test.sh` (or `./bootstrap/test/test.sh all`) to remove
prior test-owned installations and run all three setup paths from scratch. Pass
`miniconda`, `conda`, or `uv` instead to benchmark one setup independently. The
harness clears environments and caches between each selected setup, writes
`bootstrap/test/comparison.md` after an `all` run, isolates everything under
`bootstrap/test/.state`, and never removes system or personal installations.

## Verify an existing environment

With the desired environment active, run:

```bash
python bootstrap/verify_environment.py
```

The verifier does not access the camera or microphone. Hardware access is
tested interactively when ODIA starts.
