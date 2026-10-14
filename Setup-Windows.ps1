param([switch]$SetupOnly)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$PythonExe = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
if (-not (Test-Path $PythonExe)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            $FoundPython = & py -3.11 -c 'import sys; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0) { $PythonExe = $FoundPython }
        } catch { }
    }
}
if (-not (Test-Path $PythonExe)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { throw 'Install Microsoft App Installer (WinGet), then rerun setup.' }
    & winget install --id Python.Python.3.11 --exact --scope user --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw 'Python installation failed.' }
    $PythonExe = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'
    if (-not (Test-Path $PythonExe)) { throw 'Python 3.11 was not found. Reopen PowerShell and rerun setup.' }
}
$Options = @()
if ($SetupOnly) { $Options += '--setup-only' }
& $PythonExe (Join-Path $PSScriptRoot 'scripts\setup_windows.py') @Options
if ($LASTEXITCODE -ne 0) { throw 'Setup failed. Review the error above, then rerun the same command.' }
