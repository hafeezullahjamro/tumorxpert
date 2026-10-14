# Run TumorXpert on Windows

Use 64-bit Windows 10/11 and PowerShell. The setup uses Windows' WinGet package
manager (Microsoft App Installer), Python 3.11, Node.js LTS, and PostgreSQL 17.
Allow installer elevation dialogs when Windows requests them. No Docker or
manual virtual-environment activation is required.

## Clone the repository

If Git is not installed, run this once, then reopen PowerShell:

```powershell
winget install --id Git.Git --exact --silent --accept-package-agreements --accept-source-agreements
```

Clone into your preferred folder:

```powershell
cd $env:USERPROFILE
git lfs install
git clone https://github.com/hafeezullahjamro/tumorxpert.git
cd tumorxpert
```

## One command for installation, database creation, migrations, and launch

From the cloned `tumorxpert` folder:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Setup-Windows.ps1
```

This command:

1. Installs Python 3.11 if needed, and Node.js LTS if a suitable Node installation is missing.
2. Downloads all model checkpoints with Git LFS.
3. Creates `backend\.venv` and installs the pinned backend dependencies and a CPU PyTorch build.
4. Creates a local `.env` with a random project database password if you have no configuration yet.
5. Finds installed PostgreSQL tools or installs PostgreSQL 17 binaries using EDB's extract-only mode.
6. Initializes the project-owned cluster in `.local-postgres\data`, starts it on `127.0.0.1:55432`, and creates the `tx_user` role and `tumorxpert` database.
7. Applies all Alembic migrations, including persisted processing progress.
8. Installs the frontend dependencies, builds the frontend, starts the backend and frontend, and opens http://localhost:3000.

The project database uses port **55432** to coexist with another PostgreSQL
installation on port 5432. The application role owns only the newly created
project database. Bootstrap administrator credentials stay in the ignored
`.local-postgres` folder; application credentials stay in ignored `.env`.
Existing `.env`, `backend\.env`, database data, roles, and passwords are preserved.
`backend\.env` takes precedence over `.env`.

A fresh clone does not include the original Mac's scans, results, passwords, or
user accounts. Register an account in the app. CPU processing of a full MRI scan
can take several minutes; progress is saved by the backend and can be revisited.

To install and prepare the database without starting the app servers:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Setup-Windows.ps1 -SetupOnly
```

If setup fails, correct the error shown and run the same command again. Stop
running app servers before reinstalling dependencies or rebuilding the frontend.

## Start everything next time

Double-click `Start-TumorXpert.cmd`, or run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-TumorXpert.ps1
```

This starts the saved project database if stopped, applies migrations when
starting the backend, reuses healthy app servers, and opens the browser. Services
remain running after the launcher exits. To leave the browser closed:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-TumorXpert.ps1 -NoBrowser
```

## Separate commands for each server

Run these from the `tumorxpert` folder after setup.

**Database:** start the project database and ensure the role/database exist:

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\manage_database.py start
```

**Database plus migrations:**

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\manage_database.py migrate
```

**Backend:** start/check PostgreSQL, apply migrations, and run FastAPI in this terminal:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-backend.ps1
```

API documentation: http://127.0.0.1:8000/docs. Use one Uvicorn worker; a server
restart marks any interrupted processing run as failed so it can be retried.

**Frontend:** open another PowerShell window in the same project directory:

```powershell
npm.cmd --prefix .\frontend run start -- --hostname 127.0.0.1 --port 3000
```

Frontend: http://localhost:3000. Development mode instead of the built frontend:

```powershell
npm.cmd --prefix .\frontend run dev -- --hostname 127.0.0.1 --port 3000
```

## Stop and rebuild

To stop servers created by the all-in-one launcher:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-TumorXpert.ps1 -Stop
```

PostgreSQL remains running and saved data is preserved. Servers started manually
in separate terminals are stopped with Ctrl+C in their own terminal.

After changing frontend source, stop its server, then build and relaunch:

```powershell
npm.cmd --prefix .\frontend run build
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-TumorXpert.ps1
```

Logs are `.run\backend.log` and `.run\frontend.log`. Check database connectivity:

```powershell
.\backend\.venv\Scripts\python.exe .\scripts\manage_database.py status
```

## Use an existing PostgreSQL database

Before running setup, copy `.env.example` to `.env` and edit `POSTGRES_HOST`,
`POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` to match
your existing database. Start its normal Windows PostgreSQL service, then run
setup. An already reachable configured database is reused and migrated.
Automatic initialization applies only to the project-owned localhost:55432
cluster; the scripts do not change an unrelated installation's passwords or data.

If PostgreSQL is installed in a custom location, set its binary directory before
setup/startup:

```powershell
$env:TUMORXPERT_PG_BIN = 'C:\Program Files\PostgreSQL\17\bin'
```

For an existing project cluster, use binaries with the major version written in
`.local-postgres\data\PG_VERSION`.

Installer references: [Microsoft WinGet installation commands](https://learn.microsoft.com/en-us/windows/package-manager/winget/install),
[EDB PostgreSQL installer options, including extract-only](https://www.enterprisedb.com/docs/supported-open-source/postgresql/installing/command_line_parameters/),
and [official PostgreSQL Windows downloads](https://www.postgresql.org/download/windows/).
