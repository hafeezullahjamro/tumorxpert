"""Fresh-clone Windows setup; keep installation and existing data repeatable."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

from runtime_tools import npm_command

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local-postgres"


def run(command, *, cwd=ROOT):
    subprocess.run([str(item) for item in command], cwd=cwd, check=True)


def refresh_path():
    import winreg
    entries = [os.environ.get("PATH", "")]
    for hive, key in ((winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                      (winreg.HKEY_CURRENT_USER, "Environment")):
        try:
            with winreg.OpenKey(hive, key) as registry:
                entries.append(os.path.expandvars(winreg.QueryValueEx(registry, "Path")[0]))
        except FileNotFoundError:
            pass
    entries.extend([str(Path(os.environ["ProgramFiles"]) / "nodejs"),
                    str(Path(os.environ["ProgramFiles"]) / "Git/cmd")])
    os.environ["PATH"] = os.pathsep.join(entries)


def install(package, *, override=None):
    winget = shutil.which("winget")
    if not winget:
        raise RuntimeError("Install Microsoft's App Installer (WinGet), then rerun setup.")
    command = [winget, "install", "--id", package, "--exact", "--silent", "--accept-package-agreements", "--accept-source-agreements"]
    if override:
        command.extend(["--override", override])
    run(command)
    refresh_path()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup-only", action="store_true")
    options = parser.parse_args()
    if os.name != "nt":
        raise RuntimeError("This setup command is for Windows. See README.md for macOS setup.")
    refresh_path()
    import socket
    for port in (3000, 8000, int(os.environ.get("FRONTEND_PORT", "3000"))):
        with socket.socket() as connection:
            if connection.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError("An app server is running. Stop it before setup with Start-TumorXpert.ps1 -Stop, then rerun setup.")
    node = shutil.which("node")
    if not node or int(subprocess.check_output([node, "--version"], text=True).strip().lstrip("v").split(".")[0]) < 20:
        install("OpenJS.NodeJS.LTS")
    npm = shutil.which("npm.cmd")
    if not npm:
        raise RuntimeError("Node.js/npm was not found after installation. Reopen PowerShell and rerun setup.")
    git = shutil.which("git")
    if not git:
        install("Git.Git")
        git = shutil.which("git")
    if not git:
        raise RuntimeError("Git is missing; reopen PowerShell and rerun setup.")
    if subprocess.run([git, "lfs", "version"], capture_output=True).returncode:
        install("GitHub.GitLFS")
    run([git, "lfs", "install", "--local"])
    run([git, "lfs", "pull"])
    for path in (ROOT / "all best models").rglob("*.pth"):
        with path.open("rb") as stream:
            if stream.read(80).startswith(b"version https://git-lfs.github.com/spec/v1"):
                raise RuntimeError(f"Model weights are still LFS pointers: {path.name}. Run git lfs pull.")
    python = ROOT / "backend/.venv/Scripts/python.exe"
    if not python.exists():
        run([sys.executable, "-m", "venv", ROOT / "backend/.venv"])
    run([python, "-m", "pip", "install", "--upgrade", "pip"])
    # A fixed CPU build matches the bundled model code and avoids a CUDA install.
    run([python, "-m", "pip", "install", "torch==2.2.2", "--index-url", "https://download.pytorch.org/whl/cpu"])
    run([python, "-m", "pip", "install", "-r", ROOT / "backend/requirements.txt", "-c", ROOT / "backend/constraints.txt"])
    run([python, "-m", "pip", "check"])
    if not (ROOT / ".env").exists() and not (ROOT / "backend/.env").exists():
        config = (ROOT / ".env.example").read_text()
        config = config.replace("POSTGRES_PORT=5432", "POSTGRES_PORT=55432")
        config = config.replace("POSTGRES_PASSWORD=tx_password", "POSTGRES_PASSWORD=" + secrets.token_hex(24))
        config += "\nINFERENCE_DEVICE=cpu\n"
        (ROOT / ".env").write_text(config)
    # An accessible external DB needs no local PostgreSQL installation.
    healthy = subprocess.run([str(python), str(ROOT / "scripts/manage_database.py"), "status"], capture_output=True).returncode == 0
    if not healthy:
        probe = subprocess.run([str(python), "-c", "import sys; sys.path.insert(0, 'scripts'); from manage_database import find_pg_bin; print(find_pg_bin())"], cwd=ROOT, capture_output=True)
        if probe.returncode:
            LOCAL.mkdir(exist_ok=True)
            import winreg
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64") as runtime:
                    runtime_installed = winreg.QueryValueEx(runtime, "Installed")[0] == 1
            except FileNotFoundError:
                runtime_installed = False
            if not runtime_installed:
                install("Microsoft.VCRedist.2015+.x64")
            # EDB's supported extract-only mode installs binaries, not a second service.
            override = subprocess.list2cmdline(["--mode", "unattended", "--extract-only", "1", "--prefix", str(LOCAL / "pgsql"), "--disable-components", "pgAdmin,stackbuilder"])
            version_file = LOCAL / "data/PG_VERSION"
            major = version_file.read_text().strip() if version_file.exists() else "17"
            if major not in {"14", "15", "16", "17", "18"}:
                raise RuntimeError("Install PostgreSQL binaries matching the existing PG_VERSION before setup.")
            install("PostgreSQL.PostgreSQL." + major, override=override)
    run([python, ROOT / "scripts/manage_database.py", "migrate"])
    run(npm_command("ci"), cwd=ROOT / "frontend")
    # Never overwrite .next under a running frontend.
    import socket
    with socket.socket() as connection:
        if connection.connect_ex(("127.0.0.1", int(os.environ.get("FRONTEND_PORT", "3000")))) == 0:
            raise RuntimeError("Setup completed through database migration, but the frontend is running. Stop it before rebuilding, then rerun Setup-Windows.ps1.")
    os.environ.setdefault("NEXT_TELEMETRY_DISABLED", "1")
    bind = json.loads(subprocess.check_output([str(python), "-c", "import json; from app.core.config import get_settings; s=get_settings(); print(json.dumps({'host':s.backend_host,'port':s.backend_port}))"], cwd=ROOT / "backend", text=True))
    client_host = "127.0.0.1" if bind["host"] in {"0.0.0.0", "::"} else bind["host"]
    os.environ.setdefault("API_BACKEND_URL", f"http://{client_host}:{bind['port']}")
    run(npm_command("run", "build"), cwd=ROOT / "frontend")
    print("Windows setup complete. Database credentials are in .env or backend/.env; register an account in the app.", flush=True)
    if not options.setup_only:
        run([python, ROOT / "scripts/local-services.py", "start", "--production", "--open-browser"])


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
