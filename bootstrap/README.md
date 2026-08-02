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

Choose **uv** (recommended), an existing **Conda**, or a private **Miniconda**.
To skip the menu, pass the choice directly:

```bash
./bootstrap/setup.sh uv
```

## Local state

```text
.odia/
├── envs/      # Python environments
├── tools/     # uv, Python, and Miniconda
└── caches/    # downloaded packages
```

## Packages

Rerun setup to update the environment:

```bash
./bootstrap/setup.sh uv
```

With uv, add or remove dependencies using `.odia/tools/bin/uv add PACKAGE` or
`.odia/tools/bin/uv remove PACKAGE`.
