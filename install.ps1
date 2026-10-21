$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/aozocchi/deactra.git"
$AppDir = Join-Path $env:LOCALAPPDATA "Programs\Deactra"
$BinDir = Join-Path $env:LOCALAPPDATA "Deactra\bin"
$VenvDir = Join-Path $AppDir ".venv"
$Launcher = Join-Path $BinDir "deactra.cmd"

function Stop-Installer([string]$Message) {
    Write-Host "[error] $Message" -ForegroundColor Red
    throw $Message
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Stop-Installer "Git is required. Install Git for Windows, then retry."
}

# Prefer the Python launcher; fall back to python.exe.
$Python = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    try {
        & py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))"
        if ($LASTEXITCODE -eq 0) { $Python = "py" }
    } catch {}
}

if (-not $Python -and (Get-Command python -ErrorAction SilentlyContinue)) {
    try {
        & python -c "import sys; sys.exit(sys.version_info < (3, 10))"
        if ($LASTEXITCODE -eq 0) { $Python = "python" }
    } catch {}
}

if (-not $Python) {
    Stop-Installer "Python 3.10+ is required. Install Python and retry."
}

New-Item -ItemType Directory -Force -Path (Split-Path $AppDir) | Out-Null
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

if (Test-Path (Join-Path $AppDir ".git")) {
    Write-Host "[deactra] Updating existing checkout..."
    git -C $AppDir pull --ff-only
    if ($LASTEXITCODE -ne 0) {
        Stop-Installer "Could not update checkout. Resolve local changes and retry."
    }
} elseif (Test-Path $AppDir) {
    Stop-Installer "$AppDir exists but is not a Git repository. Move it and retry."
} else {
    Write-Host "[deactra] Cloning repository..."
    git clone $RepoUrl $AppDir
    if ($LASTEXITCODE -ne 0) {
        Stop-Installer "Git clone failed."
    }
}

Write-Host "[deactra] Creating virtual environment..."
if (-not (Test-Path (Join-Path $VenvDir "Scripts\python.exe"))) {
    if ($Python -eq "py") {
        & py -3 -m venv $VenvDir
    } else {
        & python -m venv $VenvDir
    }
    if ($LASTEXITCODE -ne 0) {
        Stop-Installer "Could not create virtual environment."
    }
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
Write-Host "[deactra] Installing package..."
& $VenvPython -m pip install $AppDir
if ($LASTEXITCODE -ne 0) {
    Stop-Installer "Package installation failed."
}

$Exe = Join-Path $VenvDir "Scripts\deactra.exe"
if (-not (Test-Path $Exe)) {
    Stop-Installer "The deactra launcher was not created. Check pyproject.toml."
}

# A .cmd shim allows the same `deactra` command in PowerShell and cmd.exe.
$LauncherContent = "@echo off`r`n`"$Exe`" %*`r`n"
Set-Content -LiteralPath $Launcher -Value $LauncherContent -Encoding ASCII

# Persist the launcher directory in the current user's PATH.
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$PathEntries = @($UserPath -split ";" | Where-Object { $_ })
if ($PathEntries -notcontains $BinDir) {
    $NewUserPath = (@($PathEntries) + $BinDir) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $NewUserPath, "User")
}

if (($env:Path -split ";") -notcontains $BinDir) {
    $env:Path = "$BinDir;$env:Path"
}

Write-Host "`n[deactra] Installation complete!" -ForegroundColor Green
& $Launcher --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "Run 'deactra --help' in a new terminal."
}
Write-Host "If another terminal was already open, restart it to refresh PATH."
