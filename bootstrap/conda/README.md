# Existing Conda setup

This setup path uses an existing Conda installation, including Miniconda,
Miniforge, or Anaconda Distribution. It does not install a Conda distribution.

From the repository root, run:

```bash
./bootstrap/conda/setup.sh
```

Set `ODIA_CONDA_ENV` before running the script to use a different environment
name. The script prints a direct ODIA launch command and an activation command.

If `conda` is not on `PATH`, provide its executable explicitly:

```bash
ODIA_CONDA_COMMAND=/path/to/conda ./bootstrap/conda/setup.sh
```

To install a private Miniconda distribution for ODIA instead, run:

```bash
./bootstrap/miniconda/setup.sh
```
