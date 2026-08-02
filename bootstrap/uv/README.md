# uv setup

From the repository root, run:

```bash
./bootstrap/uv/setup.sh
```

If necessary, the script first installs `uv` into the standard user executable
directory without modifying shell profiles. It then creates or updates the
`odia-uv` environment directory from `uv.lock`, downloads the configured
YOLO-World weights when they are missing, verifies the installation, and prints
exact launch and activation commands.
The latest timing report is written to `bootstrap/reports/uv.md`.

Set `UV_PROJECT_ENVIRONMENT` to choose a different environment directory:

```bash
UV_PROJECT_ENVIRONMENT=my-environment ./bootstrap/uv/setup.sh
```

To choose where the `uv` executable is installed:

```bash
ODIA_UV_INSTALL_DIR=/path/to/bin ./bootstrap/uv/setup.sh
```
