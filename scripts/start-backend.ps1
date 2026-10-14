$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$PythonExe = Join-Path $ProjectRoot 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path $PythonExe)) { throw 'Run Setup-Windows.ps1 first.' }
& $PythonExe (Join-Path $PSScriptRoot 'manage_database.py') migrate
if ($LASTEXITCODE -ne 0) { throw 'Database startup/migration failed.' }
$env:OMP_NUM_THREADS = '2'
$env:MKL_NUM_THREADS = '2'
$env:ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS = '2'
Set-Location (Join-Path $ProjectRoot 'backend')
$Bind = (& $PythonExe -c 'import json; from app.core.config import get_settings; s=get_settings(); print(json.dumps(dict(host=s.backend_host, port=s.backend_port)))') | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Cannot read backend configuration.' }
& $PythonExe -m uvicorn app.main:app --host $Bind.host --port $Bind.port
if ($LASTEXITCODE -ne 0) { throw 'Backend server failed.' }
