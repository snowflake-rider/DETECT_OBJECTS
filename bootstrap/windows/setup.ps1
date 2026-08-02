[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("uv", "conda", "miniconda")]
    [string]$Manager,

    [Alias("NoLaunch")]
    [switch]$InstallOnly,

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if ($env:OS -ne "Windows_NT") {
    throw "bootstrap/windows/setup.ps1 can only run on Windows."
}

$BootstrapDir = Split-Path -Parent $PSScriptRoot
$ProjectRoot = Split-Path -Parent $BootstrapDir
$ReportDir = Join-Path $BootstrapDir "test"
$StartedAt = Get-Date
$Stages = @()

function Resolve-ProjectPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    if ([IO.Path]::IsPathRooted($Path)) {
        return [IO.Path]::GetFullPath($Path)
    }
    return [IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path))
}

function Get-ConfiguredPath {
    param(
        [string]$Value,
        [Parameter(Mandatory = $true)][string]$Default
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return Resolve-ProjectPath $Default
    }
    return Resolve-ProjectPath $Value
}

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit $LASTEXITCODE`: $FilePath $($Arguments -join ' ')"
    }
}

function Invoke-Stage {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )

    $watch = [Diagnostics.Stopwatch]::StartNew()
    try {
        & $Action
    }
    finally {
        $watch.Stop()
        $script:Stages += [PSCustomObject]@{
            Name = $Name
            Seconds = [int][Math]::Round($watch.Elapsed.TotalSeconds)
        }
    }
}

function Format-Duration {
    param([int]$Seconds)

    if ($Seconds -ge 3600) {
        return "{0}h {1}m {2}s" -f [Math]::Floor($Seconds / 3600), [Math]::Floor(($Seconds % 3600) / 60), ($Seconds % 60)
    }
    if ($Seconds -ge 60) {
        return "{0}m {1}s" -f [Math]::Floor($Seconds / 60), ($Seconds % 60)
    }
    return "${Seconds}s"
}

function Write-BootstrapReport {
    param(
        [Parameter(Mandatory = $true)][string]$Status,
        [Parameter(Mandatory = $true)][string]$EnvironmentPath
    )

    $finishedAt = Get-Date
    $totalSeconds = [int][Math]::Round(($finishedAt - $StartedAt).TotalSeconds)
    $lines = @(
        "# $Manager bootstrap report",
        "",
        "- Status: **$Status**",
        ('- Environment: `{0}`' -f $EnvironmentPath),
        '- Script: `bootstrap/windows/setup.ps1`',
        "- Platform: ``Windows $env:PROCESSOR_ARCHITECTURE``",
        "- Started (UTC): ``$($StartedAt.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))``",
        "- Finished (UTC): ``$($finishedAt.ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'))``",
        "- Total: **$(Format-Duration $totalSeconds)** ($totalSeconds seconds)",
        "",
        "| Stage | Duration | Seconds |",
        "| --- | ---: | ---: |"
    )
    foreach ($stage in $Stages) {
        $lines += "| $($stage.Name) | $(Format-Duration $stage.Seconds) | $($stage.Seconds) |"
    }

    New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null
    $reportPath = Join-Path $ReportDir "$Manager.md"
    Set-Content -LiteralPath $reportPath -Value $lines -Encoding UTF8
    Write-Host "Bootstrap report: $reportPath"
}

function Show-EnvironmentMenu {
    $star = [char]0x2605
    $options = @(
        [PSCustomObject]@{
            Id = "uv"
            Label = "$star Install uv"
            Description = "Recommended - usually fastest and most reproducible"
            Location = "Local tool, Python, odia-uv environment, and caches"
        },
        [PSCustomObject]@{
            Id = "conda"
            Label = "Use Conda"
            Description = "Uses an existing Conda executable without changing base"
            Location = "Local odia-conda environment and package caches"
        },
        [PSCustomObject]@{
            Id = "miniconda"
            Label = "Install Miniconda"
            Description = "Installs a private Miniconda distribution for ODIA"
            Location = "Local Miniconda, odia-miniconda environment, and caches"
        }
    )

    if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected) {
        throw "Interactive setup requires a terminal. Pass uv, conda, or miniconda explicitly."
    }

    $index = 0
    while ($true) {
        Clear-Host
        Write-Host "ODIA - WINDOWS LOCAL ENVIRONMENT SETUP" -ForegroundColor Cyan
        Write-Host
        Write-Host "Choose how ODIA should prepare Python and its dependencies."
        Write-Host "Project environments, package caches, and managed tools stay in this repository."
        Write-Host "Your PowerShell profile will not be modified."
        Write-Host

        for ($optionIndex = 0; $optionIndex -lt $options.Count; $optionIndex++) {
            $option = $options[$optionIndex]
            if ($optionIndex -eq $index) {
                Write-Host ("  > [ {0,-25} ]" -f $option.Label) -ForegroundColor Cyan
            }
            else {
                Write-Host ("    [ {0,-25} ]" -f $option.Label)
            }
            Write-Host "      $($option.Description)"
            Write-Host "      $($option.Location)" -ForegroundColor DarkGray
            Write-Host
        }
        Write-Host "Up/Down Move | Enter Install | 1-3 Quick select | q Cancel" -ForegroundColor DarkGray

        $key = [Console]::ReadKey($true)
        switch ($key.Key) {
            "UpArrow" { $index = ($index + $options.Count - 1) % $options.Count }
            "DownArrow" { $index = ($index + 1) % $options.Count }
            "Enter" { return $options[$index].Id }
            "D1" { return "uv" }
            "NumPad1" { return "uv" }
            "D2" { return "conda" }
            "NumPad2" { return "conda" }
            "D3" { return "miniconda" }
            "NumPad3" { return "miniconda" }
            "Q" { exit 130 }
        }
    }
}

function Resolve-ExistingConda {
    $candidates = @(
        $env:ODIA_CONDA_COMMAND,
        $env:CONDA_EXE,
        (Join-Path $env:USERPROFILE "miniconda3\Scripts\conda.exe"),
        (Join-Path $env:USERPROFILE "miniconda3\condabin\conda.bat"),
        (Join-Path $env:USERPROFILE "anaconda3\Scripts\conda.exe"),
        (Join-Path $env:USERPROFILE "anaconda3\condabin\conda.bat")
    )
    foreach ($candidate in $candidates) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path -LiteralPath $candidate)) {
            return [IO.Path]::GetFullPath($candidate)
        }
    }

    foreach ($commandName in @("conda.exe", "conda.bat")) {
        $command = Get-Command $commandName -ErrorAction SilentlyContinue
        if ($null -ne $command -and -not [string]::IsNullOrWhiteSpace($command.Source)) {
            return $command.Source
        }
    }
    return $null
}

function Resolve-ManagedConda {
    param([Parameter(Mandatory = $true)][string]$InstallDir)

    foreach ($candidate in @(
        (Join-Path $InstallDir "Scripts\conda.exe"),
        (Join-Path $InstallDir "condabin\conda.bat"),
        (Join-Path $InstallDir "_conda.exe")
    )) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    return $null
}

function Use-CleanCondaEnvironment {
    param([Parameter(Mandatory = $true)][scriptblock]$Action)

    $variableNames = @(
        "CONDA_DEFAULT_ENV", "CONDA_EXE", "CONDA_PREFIX", "CONDA_PROMPT_MODIFIER",
        "CONDA_PYTHON_EXE", "CONDA_SHLVL", "_CE_CONDA", "_CE_M",
        "CONDA_PKGS_DIRS", "PIP_CACHE_DIR"
    )
    $saved = @{}
    foreach ($name in $variableNames) {
        $value = [Environment]::GetEnvironmentVariable($name, "Process")
        if ($null -ne $value) {
            $saved[$name] = $value
        }
        [Environment]::SetEnvironmentVariable($name, $null, "Process")
    }

    try {
        $env:CONDA_PKGS_DIRS = $script:CondaPackagesDir
        $env:PIP_CACHE_DIR = $script:PipCacheDir
        & $Action
    }
    finally {
        foreach ($name in $variableNames) {
            if ($saved.ContainsKey($name)) {
                [Environment]::SetEnvironmentVariable($name, $saved[$name], "Process")
            }
            else {
                [Environment]::SetEnvironmentVariable($name, $null, "Process")
            }
        }
    }
}

function Install-ManagedMiniconda {
    param([Parameter(Mandatory = $true)][string]$InstallDir)

    $existing = Resolve-ManagedConda $InstallDir
    if ($null -ne $existing) {
        return $existing
    }
    if (Test-Path -LiteralPath $InstallDir) {
        throw "$InstallDir exists but does not contain a working Conda executable."
    }
    if ($env:PROCESSOR_ARCHITECTURE -notin @("AMD64", "ARM64")) {
        throw "Managed Miniconda setup supports 64-bit Windows only. Choose uv or existing Conda."
    }

    $installer = Join-Path ([IO.Path]::GetTempPath()) ("odia-miniconda-{0}.exe" -f [Guid]::NewGuid())
    try {
        Write-Host "Downloading the Windows Miniconda installer..."
        Invoke-WebRequest -UseBasicParsing -Uri "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe" -OutFile $installer
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $InstallDir) | Out-Null
        # /D must be the final argument and unquoted. NSIS treats the remaining
        # command-line text as the destination, including any spaces.
        $arguments = "/InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=$InstallDir"
        $process = Start-Process -FilePath $installer -ArgumentList $arguments -Wait -PassThru
        if ($process.ExitCode -ne 0) {
            throw "Miniconda installer failed with exit $($process.ExitCode)."
        }
    }
    finally {
        Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
    }

    $installed = Resolve-ManagedConda $InstallDir
    if ($null -eq $installed) {
        throw "Miniconda installation did not create a Conda executable under $InstallDir."
    }
    return $installed
}

function Install-ProjectUv {
    param([Parameter(Mandatory = $true)][string]$InstallDir)

    $uv = Join-Path $InstallDir "uv.exe"
    if (Test-Path -LiteralPath $uv) {
        return $uv
    }

    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
    $installer = Join-Path ([IO.Path]::GetTempPath()) ("odia-uv-{0}.ps1" -f [Guid]::NewGuid())
    try {
        Write-Host "Downloading the Windows uv installer..."
        Invoke-WebRequest -UseBasicParsing -Uri "https://astral.sh/uv/install.ps1" -OutFile $installer
        $env:UV_UNMANAGED_INSTALL = $InstallDir
        $env:UV_NO_MODIFY_PATH = "1"
        Invoke-NativeCommand "powershell.exe" @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $installer
        )
    }
    finally {
        Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
    }

    if (-not (Test-Path -LiteralPath $uv)) {
        throw "uv installation did not create $uv."
    }
    return $uv
}

function Setup-UvEnvironment {
    $script:EnvironmentPath = Get-ConfiguredPath $env:UV_PROJECT_ENVIRONMENT "odia-uv"
    $uvInstallDir = Get-ConfiguredPath $env:ODIA_UV_INSTALL_DIR ".odia-tools\bin"
    $uvCacheDir = Get-ConfiguredPath $env:ODIA_UV_CACHE_DIR ".odia-tools\uv-cache"
    $uvPythonDir = Get-ConfiguredPath $env:ODIA_UV_PYTHON_INSTALL_DIR ".odia-tools\uv-python"

    Invoke-Stage "Locate or install uv" {
        $script:UvCommand = Install-ProjectUv $uvInstallDir
    }
    $env:UV_CACHE_DIR = $uvCacheDir
    $env:UV_PROJECT_ENVIRONMENT = $EnvironmentPath
    $env:UV_PYTHON_INSTALL_DIR = $uvPythonDir
    Invoke-Stage "Sync Python environment" {
        Invoke-NativeCommand $UvCommand @("sync", "--locked")
    }
    Invoke-Stage "Download required models" {
        Invoke-NativeCommand $UvCommand @("run", "python", "bootstrap/download_models.py")
    }
    Invoke-Stage "Verify environment" {
        Invoke-NativeCommand $UvCommand @("run", "python", "bootstrap/verify_environment.py")
    }
}

function Setup-CondaEnvironment {
    param(
        [Parameter(Mandatory = $true)][string]$CondaCommand,
        [Parameter(Mandatory = $true)][string]$EnvironmentDir
    )

    $script:CondaCommand = $CondaCommand
    $script:EnvironmentPath = $EnvironmentDir
    $script:CondaPackagesDir = Get-ConfiguredPath $env:ODIA_CONDA_PKGS_DIR ".odia-tools\conda-pkgs"
    $script:PipCacheDir = Get-ConfiguredPath $env:ODIA_PIP_CACHE_DIR ".odia-tools\pip-cache"
    New-Item -ItemType Directory -Force -Path $CondaPackagesDir, $PipCacheDir | Out-Null

    Invoke-Stage "Prepare Python 3.11 environment" {
        $valid = Use-CleanCondaEnvironment {
            & $CondaCommand run --prefix $EnvironmentDir python -c "import sys; raise SystemExit(sys.version_info[:2] != (3, 11))" *> $null
            return ($LASTEXITCODE -eq 0)
        }
        if (-not $valid) {
            Use-CleanCondaEnvironment {
                Invoke-NativeCommand $CondaCommand @(
                    "create", "--prefix", $EnvironmentDir, "--override-channels",
                    "--channel", "conda-forge", "python=3.11", "pip", "--yes"
                )
            }
        }
    }
    Invoke-Stage "Install Python dependencies" {
        Use-CleanCondaEnvironment {
            Invoke-NativeCommand $CondaCommand @(
                "run", "--prefix", $EnvironmentDir,
                "python", "-m", "pip", "install", "--requirement", "requirements.txt"
            )
        }
    }
    Invoke-Stage "Install ODIA package" {
        Use-CleanCondaEnvironment {
            Invoke-NativeCommand $CondaCommand @(
                "run", "--prefix", $EnvironmentDir,
                "python", "-m", "pip", "install", "--no-deps", "--editable", "."
            )
        }
    }
    Invoke-Stage "Download required models" {
        Use-CleanCondaEnvironment {
            Invoke-NativeCommand $CondaCommand @(
                "run", "--prefix", $EnvironmentDir, "python", "bootstrap/download_models.py"
            )
        }
    }
    Invoke-Stage "Verify environment" {
        Use-CleanCondaEnvironment {
            Invoke-NativeCommand $CondaCommand @(
                "run", "--prefix", $EnvironmentDir, "python", "bootstrap/verify_environment.py"
            )
        }
    }
}

function Show-DryRun {
    Write-Host "Platform: Windows"
    Write-Host "Selected: $Manager"
    switch ($Manager) {
        "uv" {
            $environment = Get-ConfiguredPath $env:UV_PROJECT_ENVIRONMENT "odia-uv"
            Write-Host "Would install with project-local uv and launch: $environment"
        }
        "conda" {
            $environment = Get-ConfiguredPath $env:ODIA_CONDA_ENV_DIR "odia-conda"
            Write-Host "Would use existing Conda and launch: $environment"
        }
        "miniconda" {
            $environment = Get-ConfiguredPath $env:ODIA_CONDA_ENV_DIR "odia-miniconda"
            Write-Host "Would install project-local Miniconda and launch: $environment"
        }
    }
}

Set-Location $ProjectRoot
if ([string]::IsNullOrWhiteSpace($Manager)) {
    $Manager = Show-EnvironmentMenu
}

if ($DryRun) {
    Show-DryRun
    exit 0
}

$EnvironmentPath = ""
try {
    switch ($Manager) {
        "uv" {
            Setup-UvEnvironment
        }
        "conda" {
            $existingConda = Resolve-ExistingConda
            if ($null -eq $existingConda) {
                throw "Conda was not found. Choose uv or Miniconda, or set ODIA_CONDA_COMMAND."
            }
            $environment = Get-ConfiguredPath $env:ODIA_CONDA_ENV_DIR "odia-conda"
            Setup-CondaEnvironment $existingConda $environment
        }
        "miniconda" {
            $installDir = Get-ConfiguredPath $env:ODIA_MINICONDA_INSTALL_DIR ".odia-tools\miniconda3"
            Invoke-Stage "Locate or install Miniconda" {
                $script:CondaCommand = Install-ManagedMiniconda $installDir
            }
            $environment = Get-ConfiguredPath $env:ODIA_CONDA_ENV_DIR "odia-miniconda"
            Setup-CondaEnvironment $CondaCommand $environment
        }
    }
    Write-BootstrapReport "Success" $EnvironmentPath
}
catch {
    if ([string]::IsNullOrWhiteSpace($EnvironmentPath)) {
        $EnvironmentPath = "not created"
    }
    Write-BootstrapReport "Failed" $EnvironmentPath
    Write-Host "Setup failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

if ($InstallOnly) {
    Write-Host "$Manager environment is ready."
    exit 0
}

Write-Host
Write-Host "Environment ready. Starting ODIA device and model setup..." -ForegroundColor Green
switch ($Manager) {
    "uv" {
        & $UvCommand run odia
        exit $LASTEXITCODE
    }
    "conda" {
        Use-CleanCondaEnvironment {
            & $CondaCommand run --prefix $EnvironmentPath odia
            $script:ApplicationExitCode = $LASTEXITCODE
        }
        exit $ApplicationExitCode
    }
    "miniconda" {
        Use-CleanCondaEnvironment {
            & $CondaCommand run --prefix $EnvironmentPath odia
            $script:ApplicationExitCode = $LASTEXITCODE
        }
        exit $ApplicationExitCode
    }
}
