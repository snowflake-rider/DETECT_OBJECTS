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

### Use Codex on another machine

When ODIA runs on a machine without Codex, setup can use an SSH host where the
Codex CLI is installed and authenticated:

```bash
./bootstrap/setup.sh uv --codex-ssh codex-mac
```

`codex-mac` may be an SSH config alias or `user@host`. The project machine must
be able to connect with key authentication, and Remote Login must be enabled on
the Codex host. Setup verifies both the remote executable and `codex login
status` before starting ODIA.

For local Story generation, ODIA also checks the common Homebrew and user-local
Codex locations. It adds the selected Codex directory to the child process PATH
so a GUI-launched app can find both the Codex script and its Node runtime.

For each Story request, ODIA streams `events.json`, snapshots, the prompt, and
the output schema into a temporary directory on the Codex host. Codex runs
ephemerally with a read-only sandbox; the remote temporary directory is removed
after the JSON result returns. No shared filesystem is required.

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

## Development tools

The base dependency set provides YOLO, Whisper, Textual setup, the Classic
OpenCV runtime, and the required PySide6 Desktop Dashboard.

Tests, notebooks, and formatting tools are declared in the `dev` dependency
group.

The standard bootstrap excludes development tools so rerunning it produces the
same runtime on every supported platform.
