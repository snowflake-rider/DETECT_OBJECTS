# Conda setup

From the repository root, run:

```bash
./bootstrap/conda/setup.sh
```

Set `ODIA_CONDA_ENV` before running the script to use a different environment
name. The script prints a direct ODIA launch command and the correct activation
command for the Conda installation it used.

If Conda is missing, the script installs Miniconda into the standard user data
directory without modifying shell profiles. Automatic installation supports
macOS and Linux on Apple Silicon/ARM64 and x86-64.

To choose where Miniconda is installed:

```bash
ODIA_CONDA_INSTALL_DIR=/path/to/miniconda3 ./bootstrap/conda/setup.sh
```
