# Bootstrap

Bootstrap prepares Python, installs the packages, and starts ODIA.

## macOS

### 1. Install Homebrew

Check whether Homebrew is already installed:

```bash
brew --version
```

If the command is not found, install Homebrew:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow any instructions printed by the Homebrew installer before continuing.

### 2. Install fzf

```bash
brew install fzf
```

### 3. Run setup

Open a terminal in the project folder and run:

```bash
./bootstrap/setup.sh
```

## Linux

### 1. Install fzf

Use the command for your Linux distribution:

```bash
# Ubuntu or Debian
sudo apt update
sudo apt install -y fzf
```

```bash
# Fedora
sudo dnf install -y fzf
```

```bash
# Arch Linux
sudo pacman -S fzf
```

### 2. Run setup

Open a terminal in the project folder and run:

```bash
./bootstrap/setup.sh
```

## Windows

Open PowerShell in the project folder:

```powershell
.\bootstrap\setup.ps1
```

## Choose an environment

- `uv`: recommended
- `conda`: use Conda; setup installs it automatically when it is missing

### Why uv is recommended

For this project, uv provides the most repeatable setup:

- **Portability:** The same setup command works on macOS, Linux, and Windows.
- **Consistency:** `uv.lock` records the project's resolved package versions.
- **Isolation:** Python, packages, tools, and caches stay under `.odia/`.
- **Validation:** `uv sync --locked` stops when the project files and lockfile
  disagree instead of silently creating a different environment.

These checks improve reliability and portability between computers. Conda is
still available for users who already use it, but its result can depend more on
the installed Conda version and the packages currently available to it.

Use the arrow keys and Enter to choose.

You can also skip the menu:

```bash
./bootstrap/setup.sh uv
```

On Windows:

```powershell
.\bootstrap\setup.ps1 uv
```

Run the same command again whenever you want to start ODIA.

Setup does not activate the environment in your terminal. It runs ODIA inside
the selected environment, then leaves your terminal unchanged when ODIA closes.
