# Bootstrap

Bootstrap prepares Python, installs the packages, and starts ODIA.

## macOS or Linux

Open a terminal in the project folder:

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
- `conda`: use Conda already installed on your computer
- `miniconda`: install a private Miniconda for this project

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
