# uv setup

From the repository root, run:

```bash
./bootstrap/uv/setup.sh
```

The script installs its own uv executable under `.odia-tools/bin` without
modifying shell profiles. It creates or updates the `odia-uv` environment from
`uv.lock`, keeps the uv cache and managed Python installations under
`.odia-tools`, downloads the configured YOLO-World weights when missing,
verifies the installation, and prints exact launch and activation commands.
The latest timing report is written to `bootstrap/test/uv.md`.

Set `UV_PROJECT_ENVIRONMENT` to choose a different environment directory:

```bash
UV_PROJECT_ENVIRONMENT=my-environment ./bootstrap/uv/setup.sh
```

To choose where the `uv` executable is installed:

```bash
ODIA_UV_INSTALL_DIR=/path/to/bin ./bootstrap/uv/setup.sh
```

Override the project-local cache and managed-Python directories with
`ODIA_UV_CACHE_DIR` and `ODIA_UV_PYTHON_INSTALL_DIR`.
