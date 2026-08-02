# New-machine bootstrap

This directory provides reproducible setup paths for new contributors. Run all
commands from the repository root.

## Recommended: uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) once, then
run:

```bash
./bootstrap/uv/setup.sh
uv run odia
```

The script installs the locked Python 3.11 environment into `.venv`, installs
the local `detect_objects` package, and verifies required imports and runtime
resources.

## Conda

Install Miniconda or Anaconda, then run:

```bash
./bootstrap/conda/setup.sh
conda activate odia
odia
```

The default environment name is `odia`. To choose another name:

```bash
ODIA_CONDA_ENV=my-environment ./bootstrap/conda/setup.sh
conda activate my-environment
```

The Conda path creates a Python 3.11 environment and installs
`requirements.txt` followed by the local src-layout package.

## Verify an existing environment

With the desired environment active, run:

```bash
python bootstrap/verify_environment.py
```

The verifier does not access the camera or microphone. Hardware access is
tested interactively when ODIA starts.
