"""Start the configured project database, provisioning only a new owned cluster."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import get_settings
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

LOCAL = ROOT / ".local-postgres"
DATA = LOCAL / "data"
LOCAL_PORT = 55432


def find_pg_bin():
    suffix = ".exe" if os.name == "nt" else ""
    candidates = []
    if os.environ.get("TUMORXPERT_PG_BIN"):
        candidates.append(Path(os.environ["TUMORXPERT_PG_BIN"]))
    candidates.append(LOCAL / "pgsql/bin")
    if os.name == "nt":
        base = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "PostgreSQL"
        if base.exists():
            candidates.extend(sorted(base.glob("*/bin"), reverse=True))
    else:
        for version in ("18", "17", "16", "15", "14"):
            candidates.extend([Path(f"/Library/PostgreSQL/{version}/bin"),
                               Path(f"/opt/homebrew/opt/postgresql@{version}/bin"),
                               Path(f"/usr/local/opt/postgresql@{version}/bin")])
    located = shutil.which("pg_ctl")
    if located:
        candidates.append(Path(located).parent)
    required = (DATA / "PG_VERSION").read_text().strip() if (DATA / "PG_VERSION").exists() else None
    for candidate in candidates:
        executable = candidate / f"pg_ctl{suffix}"
        if not executable.is_file():
            continue
        version = subprocess.check_output([str(executable), "--version"], text=True).split()[-1].split(".")[0]
        if required is None or version == required:
            return candidate
    raise RuntimeError("PostgreSQL binaries are missing or their major version does not match this cluster. Run Setup-Windows.ps1, or set TUMORXPERT_PG_BIN to the correct PostgreSQL bin directory.")


def reachable(url):
    engine = create_engine(url, connect_args={"connect_timeout": 5} if url.get_backend_name() == "postgresql" else {})
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        engine.dispose()


def execute(command):
    subprocess.run([str(item) for item in command], check=True)


def ensure_database():
    settings = get_settings()
    url = make_url(settings.database_url)
    if reachable(url):
        print(f"Database ready at {url.host}:{url.port or 5432}/{url.database}.", flush=True)
        return
    if url.get_backend_name() != "postgresql" or url.host not in {"localhost", "127.0.0.1"} or url.port != LOCAL_PORT:
        raise RuntimeError("The configured database is unreachable. Start your existing PostgreSQL service and check .env. Automatic cluster creation is reserved for this project's localhost:55432 database.")
    binaries = find_pg_bin()
    suffix = ".exe" if os.name == "nt" else ""
    pg_ctl = binaries / f"pg_ctl{suffix}"
    LOCAL.mkdir(exist_ok=True)
    bootstrap_path = LOCAL / "bootstrap.json"
    if not (DATA / "PG_VERSION").exists():
        if DATA.exists() and any(DATA.iterdir()):
            raise RuntimeError("Refusing to initialize a nonempty PostgreSQL data folder without PG_VERSION.")
        with socket.socket() as connection:
            if connection.connect_ex(("127.0.0.1", LOCAL_PORT)) == 0:
                raise RuntimeError("Port 55432 is occupied. Check .env; no existing server or database was changed.")
        credentials = dict(user="tx_admin", password=secrets.token_hex(24))
        bootstrap_path.write_text(json.dumps(credentials))
        bootstrap_path.chmod(0o600)
        with tempfile.TemporaryDirectory(prefix="tumorxpert-init-") as temporary:
            password_file = Path(temporary) / "password"
            password_file.write_text(credentials["password"] + "\n")
            password_file.chmod(0o600)
            execute([binaries / f"initdb{suffix}", "-D", DATA, "-U", credentials["user"],
                     "--pwfile", password_file, "--auth-host=scram-sha-256", "--auth-local=scram-sha-256",
                     "--encoding=UTF8", "--locale=C"])
    status = subprocess.run([str(pg_ctl), "-D", str(DATA), "status"], capture_output=True)
    if status.returncode != 0:
        execute([pg_ctl, "-D", DATA, "-l", LOCAL / "postgres.log", "-o", f"-h 127.0.0.1 -p {LOCAL_PORT}", "-w", "start"])
    if reachable(url):
        print("Project PostgreSQL is ready.", flush=True)
        return
    if not bootstrap_path.exists():
        raise RuntimeError("The existing cluster started, but the configured database credentials did not connect. Check .env; existing roles and passwords were preserved.")
    import psycopg
    from psycopg import sql
    credentials = json.loads(bootstrap_path.read_text())
    with psycopg.connect(host="127.0.0.1", port=LOCAL_PORT, dbname="postgres", user=credentials["user"],
                         password=credentials["password"], autocommit=True, connect_timeout=5) as connection:
        if not connection.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (url.username,)).fetchone():
            connection.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(sql.Identifier(url.username), sql.Literal(url.password)))
        if not connection.execute("SELECT 1 FROM pg_database WHERE datname=%s", (url.database,)).fetchone():
            connection.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(url.database), sql.Identifier(url.username)))
    if not reachable(url):
        raise RuntimeError("PostgreSQL is running, but the configured role/database cannot connect. Verify .env credentials.")
    print(f"Project role and database ready: {url.username}, {url.database}.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "migrate", "status"))
    action = parser.parse_args().action
    if action == "status":
        if not reachable(make_url(get_settings().database_url)):
            return 1
        print("Configured database is reachable.")
        return 0
    ensure_database()
    if action == "migrate":
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT / "backend", check=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
