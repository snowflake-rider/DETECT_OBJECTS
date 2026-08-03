[CmdletBinding()]
param(
    # The first optional argument selects uv directly:
    #   .\bootstrap\setup.ps1 uv
    # Conda remains accepted only so callers receive a clear disabled message.
    [Parameter(Position = 0)]
    [ValidateSet("uv", "conda")]
    [string]$Manager = "uv"
)

# Stop when a command or PowerShell operation fails.
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# $PSScriptRoot is the directory containing this setup.ps1 file.
# Split-Path moves one directory up, from bootstrap/ to the project root.
$BootstrapDir = $PSScriptRoot
$ProjectRoot = Split-Path -Parent $BootstrapDir
$StateDir = Join-Path $ProjectRoot ".odia"

if ($env:OS -ne "Windows_NT") {
    throw "setup.ps1 supports Windows only."
}

# Run a program and stop setup when that program reports an error.
function Invoke-Program {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

# Find Conda on PATH or in its usual Windows installation directories.
function Find-Conda {
    foreach ($Name in @("conda.exe", "conda.bat")) {
        $Command = Get-Command $Name -ErrorAction SilentlyContinue
        if ($null -ne $Command) {
            return $Command.Source
        }
    }

    $CommonPaths = @(
        (Join-Path $env:USERPROFILE "miniconda3\Scripts\conda.exe"),
        (Join-Path $env:USERPROFILE "miniconda3\condabin\conda.bat"),
        (Join-Path $env:USERPROFILE "anaconda3\Scripts\conda.exe"),
        (Join-Path $env:USERPROFILE "anaconda3\condabin\conda.bat")
    )

    foreach ($Path in $CommonPaths) {
        if (Test-Path $Path) {
            return $Path
        }
    }

    return $null
}

# Find Conda inside the private Miniconda directory.
function Find-PrivateConda {
    param([Parameter(Mandatory = $true)][string]$InstallDir)

    $Candidates = @(
        (Join-Path $InstallDir "Scripts\conda.exe"),
        (Join-Path $InstallDir "condabin\conda.bat"),
        (Join-Path $InstallDir "_conda.exe")
    )

    foreach ($Path in $Candidates) {
        if (Test-Path $Path) {
            return $Path
        }
    }

    return $null
}

# Install uv under .odia/tools/bin when it is not already there.
function Install-Uv {
    $InstallDir = Join-Path $StateDir "tools\bin"
    $UvCommand = Join-Path $InstallDir "uv.exe"

    if (Test-Path $UvCommand) {
        return $UvCommand
    }

    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    $Installer = Join-Path ([IO.Path]::GetTempPath()) "odia-uv-install.ps1"

    try {
        Write-Host "uv was not found; installing it into $InstallDir..."
        Invoke-WebRequest -UseBasicParsing -Uri "https://astral.sh/uv/install.ps1" -OutFile $Installer

        # These settings apply only while this setup process is running.
        $env:UV_UNMANAGED_INSTALL = $InstallDir
        $env:UV_NO_MODIFY_PATH = "1"

        Invoke-Program "powershell.exe" @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", $Installer
        ) | Out-Host
    }
    finally {
        Remove-Item $Installer -Force -ErrorAction SilentlyContinue
        Remove-Item Env:UV_UNMANAGED_INSTALL -ErrorAction SilentlyContinue
        Remove-Item Env:UV_NO_MODIFY_PATH -ErrorAction SilentlyContinue
    }

    if (-not (Test-Path $UvCommand)) {
        throw "uv installation did not create $UvCommand."
    }

    return $UvCommand
}

# Install a private Miniconda under .odia/tools/miniconda3.
function Install-Miniconda {
    $InstallDir = Join-Path $StateDir "tools\miniconda3"
    $CondaCommand = Find-PrivateConda $InstallDir

    if ($null -ne $CondaCommand) {
        return $CondaCommand
    }
    if (Test-Path $InstallDir) {
        throw "$InstallDir exists but does not contain Conda."
    }

    $Installer = Join-Path ([IO.Path]::GetTempPath()) "odia-miniconda-install.exe"

    try {
        Write-Host "Installing Miniconda into $InstallDir..."
        Invoke-WebRequest -UseBasicParsing -Uri "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe" -OutFile $Installer

        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $InstallDir) | Out-Null

        # /S installs silently. /D chooses the installation directory.
        $InstallerArguments = "/InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=$InstallDir"
        $Process = Start-Process -FilePath $Installer -ArgumentList $InstallerArguments -Wait -PassThru

        if ($Process.ExitCode -ne 0) {
            throw "Miniconda installation failed."
        }
    }
    finally {
        Remove-Item $Installer -Force -ErrorAction SilentlyContinue
    }

    $CondaCommand = Find-PrivateConda $InstallDir
    if ($null -eq $CondaCommand) {
        throw "Miniconda installation did not create a Conda command."
    }

    return $CondaCommand
}

# Prepare the project with uv, then launch ODIA.
function Start-WithUv {
    $UvCommand = Install-Uv
    $UvEnvironment = Join-Path $StateDir "envs\uv"

    # These variables keep uv's environment, Python, and cache inside .odia/.
    $env:UV_PROJECT_ENVIRONMENT = $UvEnvironment
    $env:UV_PYTHON_INSTALL_DIR = Join-Path $StateDir "tools\python"
    $env:UV_CACHE_DIR = Join-Path $StateDir "caches\uv"

    Write-Host "Preparing the Python environment..."
    Invoke-Program $UvCommand @("sync", "--locked")

    Write-Host "Downloading required models..."
    Invoke-Program $UvCommand @("run", "python", "bootstrap/tools/download_models.py")

    Write-Host "Verifying the environment..."
    Invoke-Program $UvCommand @("run", "python", "bootstrap/tools/verify_environment.py")

    Write-Host
    Write-Host "Environment ready. Starting ODIA..."
    & $UvCommand run odia
    exit $LASTEXITCODE
}

# Prepare one Conda environment, then launch ODIA.
function Start-WithConda {
    param(
        [Parameter(Mandatory = $true)][string]$CondaCommand,
        [Parameter(Mandatory = $true)][string]$EnvironmentDir
    )

    # These cache settings exist only while this setup process is running.
    $env:CONDA_PKGS_DIRS = Join-Path $StateDir "caches\conda"
    $env:PIP_CACHE_DIR = Join-Path $StateDir "caches\pip"
    New-Item -ItemType Directory -Force -Path $env:CONDA_PKGS_DIRS, $env:PIP_CACHE_DIR | Out-Null

    Write-Host "Preparing the Python 3.11 environment..."
    & $CondaCommand run --prefix $EnvironmentDir python -c "import sys; raise SystemExit(sys.version_info[:2] != (3, 11))" *> $null
    if ($LASTEXITCODE -ne 0) {
        Invoke-Program $CondaCommand @(
            "create", "--prefix", $EnvironmentDir,
            "--override-channels", "--channel", "conda-forge",
            "python=3.11", "pip", "--yes"
        )
    }

    Write-Host "Installing Python dependencies..."
    Invoke-Program $CondaCommand @(
        "run", "--prefix", $EnvironmentDir,
        "python", "-m", "pip", "install", "--requirement", "requirements.txt"
    )

    Write-Host "Installing ODIA..."
    Invoke-Program $CondaCommand @(
        "run", "--prefix", $EnvironmentDir,
        "python", "-m", "pip", "install", "--no-deps", "--editable", "."
    )

    Write-Host "Downloading required models..."
    Invoke-Program $CondaCommand @(
        "run", "--prefix", $EnvironmentDir,
        "python", "bootstrap/tools/download_models.py"
    )

    Write-Host "Verifying the environment..."
    Invoke-Program $CondaCommand @(
        "run", "--prefix", $EnvironmentDir,
        "python", "bootstrap/tools/verify_environment.py"
    )

    Write-Host
    Write-Host "Environment ready. Starting ODIA..."
    & $CondaCommand run --prefix $EnvironmentDir odia
    exit $LASTEXITCODE
}

# ----- Main program starts here -----

Set-Location $ProjectRoot

if ($Manager -eq "conda") {
    [Console]::Error.WriteLine(
        "Conda setup is temporarily disabled because the uv workflow is verified and working reliably."
    )
    [Console]::Error.WriteLine("Use uv while Conda support is reviewed.")
    exit 2
}

Write-Host
Write-Host "Selected: uv"
Write-Host "Preparing the project-local environment..."
Write-Host

Start-WithUv
