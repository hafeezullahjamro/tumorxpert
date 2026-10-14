param([switch]$NoBrowser, [switch]$Stop)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$PythonExe = Join-Path $PSScriptRoot 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path $PythonExe)) { throw 'Run Setup-Windows.ps1 first.' }
$Options = @('start', '--production', '--build-if-needed')
if ($Stop) { $Options = @('stop') }
elseif (-not $NoBrowser) { $Options += '--open-browser' }
& $PythonExe (Join-Path $PSScriptRoot 'scripts\local-services.py') @Options
if ($LASTEXITCODE -ne 0) { throw 'TumorXpert startup/stop failed. Review the message above and logs in .run.' }
