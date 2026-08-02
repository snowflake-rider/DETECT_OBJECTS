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

Choose **uv** (recommended) or **Conda**. Setup installs Conda automatically
when it is missing.

uv is recommended for four reasons:

- **Portability:** The same workflow works across supported operating systems.
- **Consistency:** `uv.lock` keeps dependency versions consistent.
- **Isolation:** Python and packages stay inside the project.
- **Validation:** `uv sync --locked` checks the environment before launch.

Setup uses `fzf` for the menu when available. If it is missing, setup asks
whether to install it under `.odia/tools/fzf`. Declining or a failed installation
uses the built-in arrow-key menu instead.
To skip the menu, pass the choice directly:

```bash
./bootstrap/setup.sh uv
```

## Local state

```text
.odia/
├── envs/      # Python environments
├── tools/     # uv, Python, and the private Miniconda fallback
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
