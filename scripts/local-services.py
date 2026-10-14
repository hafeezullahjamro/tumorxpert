"""Start the local app detached, with logs and reproducible stop/restart commands."""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import webbrowser
from urllib.request import urlopen

from runtime_tools import backend_python, npm_command

if os.name == "nt":
    import msvcrt
else:
    import fcntl

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / ".run"


def listening(port: int) -> bool:
    with socket.socket() as connection:
        connection.settimeout(1)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def config() -> dict:
    python = backend_python(ROOT)
    output = subprocess.check_output(
        [str(python), "-c", "from app.core.config import get_settings; import json; s=get_settings(); print(json.dumps({'host':s.backend_host,'port':s.backend_port}))"],
        cwd=ROOT / "backend", text=True,
    )
    return json.loads(output)


def start() -> None:
    settings = config()
    frontend_port = int(os.environ.get("FRONTEND_PORT", "3000"))
    client_host = "127.0.0.1" if settings["host"] in {"0.0.0.0", "::"} else settings["host"]
    backend_url = f"http://{client_host}:{settings['port']}"
    python = backend_python(ROOT)
    production = "--production" in sys.argv
    if not (ROOT / "frontend/node_modules/next").exists():
        raise RuntimeError("Install frontend dependencies with: cd frontend && npm ci")
    environment = os.environ.copy()
    environment.setdefault("API_BACKEND_URL", backend_url)
    environment.setdefault("NEXT_TELEMETRY_DISABLED", "1")
    environment.setdefault("OMP_NUM_THREADS", "2")
    environment.setdefault("MKL_NUM_THREADS", "2")
    environment.setdefault("ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS", "2")
    # Check the database even when the API server is already running.
    prepare_database = ([str(python), str(ROOT / "scripts/manage_database.py"), "start"] if os.name == "nt"
                        else ["bash", str(ROOT / "scripts/start-backend.sh"), "--check-database"])
    subprocess.run(
        prepare_database,
        cwd=ROOT, env=environment, check=True,
    )
    if production and not (ROOT / "frontend/.next/BUILD_ID").is_file():
        if "--build-if-needed" not in sys.argv:
            raise RuntimeError("Build the frontend first: cd frontend && npm run build")
        if listening(frontend_port):
            raise RuntimeError("The frontend is running without a production build. Stop it with ./scripts/stop.sh before building.")
        print("Building the frontend for its first production launch...", flush=True)
        subprocess.run(npm_command("run", "build"), cwd=ROOT / "frontend", env=environment, check=True)
    backend_command = ([str(python), "-m", "uvicorn", "app.main:app", "--host", settings["host"], "--port", str(settings["port"])]
                       if os.name == "nt" else ["bash", str(ROOT / "scripts/start-backend.sh")])
    services = (
        ("backend", settings["port"], backend_command, ROOT / "backend" if os.name == "nt" else ROOT, backend_url + "/health"),
        ("frontend", frontend_port, npm_command("--prefix", ROOT / "frontend", "run", "start" if production else "dev", "--", "--hostname", "127.0.0.1", "--port", str(frontend_port)), ROOT / "frontend", f"http://127.0.0.1:{frontend_port}/auth/login"),
    )
    for name, port, command, directory, health in services:
        if listening(port):
            try:
                with urlopen(health, timeout=10) as response:
                    if response.status != 200:
                        raise RuntimeError(f"Unexpected response on port {port}")
                    if name == "backend" and json.load(response).get("status") != "ok":
                        raise RuntimeError(f"Port {port} belongs to a different application")
            except Exception as error:
                raise RuntimeError(f"Port {port} is occupied and {name} is not healthy: {error}") from error
            print(f"{name.capitalize()} already running on port {port}.")
            continue
        if name == "backend" and os.name == "nt":
            subprocess.run([str(python), "-m", "alembic", "upgrade", "head"], cwd=ROOT / "backend", env=environment, check=True)
        with (RUN / f"{name}.log").open("a") as log:
            process = subprocess.Popen(command, cwd=directory, env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=os.name != "nt",
                                       creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW) if os.name == "nt" else 0)
        (RUN / f"{name}.pid").write_text(str(process.pid))
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"{name} exited. Read {RUN / (name + '.log')}")
            try:
                with urlopen(health, timeout=3) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError(f"{name} did not become ready. Read {RUN / (name + '.log')}")
        print(f"{name.capitalize()} ready on port {port}.", flush=True)
    print(f"Open http://localhost:{frontend_port}")
    print(f"Backend docs: {backend_url}/docs")
    print(f"Logs: {RUN}")
    if "--open-browser" in sys.argv:
        webbrowser.open(f"http://localhost:{frontend_port}")


def stop(names=("frontend", "backend")) -> None:
    for name in names:
        pid_file = RUN / f"{name}.pid"
        if not pid_file.exists():
            continue
        pid = int(pid_file.read_text())
        remove_record = True
        try:
            if os.name == "nt":
                raw = subprocess.check_output(["powershell.exe", "-NoProfile", "-Command", f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}').CommandLine"], text=True).strip()
                if str(ROOT).casefold() not in raw.casefold():
                    print(f"Skipping reused PID {pid}.")
                    continue
                result = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"])
                if result.returncode != 0:
                    remove_record = False
                    raise RuntimeError(f"Unable to stop {name}; PID {pid} remains recorded. Check process permissions.")
                print(f"Stopped {name}.")
                continue
            # Confirm the recorded PID still belongs to this project's process.
            command = subprocess.check_output(["ps", "-p", str(pid), "-o", "command="], text=True).strip()
            directory = subprocess.check_output(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"], text=True)
            if str(ROOT) not in command and str(ROOT) not in directory:
                print(f"Skipping reused PID {pid}.")
                continue
            os.killpg(pid, signal.SIGTERM)
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                try:
                    os.killpg(pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.2)
            else:
                # Only terminate the process group already verified above.
                os.killpg(pid, signal.SIGKILL)
            print(f"Stopped {name}.")
        except (ProcessLookupError, subprocess.CalledProcessError):
            pass
        except PermissionError:
            # macOS can deny a group probe after the last owned process exits.
            # Check actual group members before treating that as a stop failure.
            members = subprocess.check_output(["ps", "-axo", "pgid=,stat="], text=True)
            live = [line.split() for line in members.splitlines() if line.split() and line.split()[0] == str(pid)]
            if any(not fields[1].startswith("Z") for fields in live):
                remove_record = False
                raise RuntimeError(f"Unable to stop {name}; PID {pid} remains recorded. Check process permissions.") from None
            print(f"Stopped {name}.")
        finally:
            if remove_record:
                pid_file.unlink(missing_ok=True)
    print("PostgreSQL remains running; saved data is preserved.")


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1 and sys.argv[1] in {"stop", "stop-frontend"}:
            stop(("frontend",) if sys.argv[1] == "stop-frontend" else ("frontend", "backend"))
        else:
            RUN.mkdir(exist_ok=True)
            with (RUN / "launcher.lock").open("a+b") as lock:
                try:
                    if os.name == "nt":
                        lock.seek(0, os.SEEK_END)
                        if lock.tell() == 0:
                            lock.write(b"0")
                            lock.flush()
                        lock.seek(0)
                        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    raise RuntimeError("TumorXpert startup is already in progress. Wait for the other launcher to finish.") from None
                start()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
