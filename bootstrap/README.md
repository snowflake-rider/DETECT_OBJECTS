# Bootstrap

Bootstrap installs Python, packages, and ODIA locally. Generated files stay in
`.odia/`, and your shell profile is not changed.

## Start

```bash
# macOS or Linux
./bootstrap/setup.sh
```

```powershell
# Windows
.\bootstrap\setup.ps1
```

Setup uses **uv**. Conda support is currently disabled.

uv is recommended for four reasons:

- **Portability:** The same workflow works across supported operating systems.
- **Consistency:** `uv.lock` keeps dependency versions consistent.
- **Isolation:** Python and packages stay inside the project.
- **Validation:** `uv sync --locked` checks the environment before launch.

The default setup installs both the Classic runtime and the PySide6 Desktop
Dashboard. Development tools and experimental Apple audio packages are not
installed into the runtime environment.

## Local state

```text
.odia/
├── envs/      # Python environments
├── tools/     # uv and its managed Python
└── caches/    # downloaded packages
```

Setup runs ODIA inside the chosen environment without activating it in the
current terminal.

## Packages

Rerun setup to update the environment:

```bash
./bootstrap/setup.sh uv
```

With uv, add or remove dependencies using `.odia/tools/bin/uv add PACKAGE` or
`.odia/tools/bin/uv remove PACKAGE`.

## Optional features

The base dependency set provides YOLO, Whisper, Textual setup, the Classic
OpenCV runtime, and the required PySide6 Desktop Dashboard. Optional features
are declared separately:

- `apple-audio`: Apple SoundAnalysis and MLX-Audio prototypes
- `dev`: tests, notebooks, and formatting tools

The standard bootstrap excludes both optional sets so rerunning it produces the
same runtime on every supported platform.
