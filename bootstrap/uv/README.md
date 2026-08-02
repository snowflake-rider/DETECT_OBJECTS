# uv setup

From the repository root, run:

```bash
./bootstrap/uv/setup.sh
```

If necessary, the script first installs `uv` into the standard user executable
directory without modifying shell profiles. It then creates or updates `.venv`
from `uv.lock`, verifies the installation, and prints the exact command to
launch ODIA.

To choose where the `uv` executable is installed:

```bash
ODIA_UV_INSTALL_DIR=/path/to/bin ./bootstrap/uv/setup.sh
```
