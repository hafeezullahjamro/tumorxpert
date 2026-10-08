"""Start the local app detached, with logs and reproducible stop/restart commands."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / ".run"


def listening(port: int) -> bool:
    with socket.socket() as connection:
        connection.settimeout(1)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def config() -> dict:
    for environment in (".venv", ".venv-mac"):
        python = ROOT / "backend" / environment / "bin/python"
        if python.exists() and os.access(python, os.X_OK):
            output = subprocess.check_output(
                [str(python), "-c", "from app.core.config import get_settings; import json; s=get_settings(); print(json.dumps({'host':s.backend_host,'port':s.backend_port}))"],
                cwd=ROOT / "backend", text=True,
            )
            return json.loads(output)
    raise RuntimeError("Backend Python environment is missing; see README.md.")


def start() -> None:
    settings = config()
    frontend_port = int(os.environ.get("FRONTEND_PORT", "3000"))
    backend_url = f"http://{settings['host']}:{settings['port']}"
    production = "--production" in sys.argv
    npm = shutil.which("npm")
    if not npm or not (ROOT / "frontend/node_modules/next").exists():
        raise RuntimeError("Install frontend dependencies with: cd frontend && npm ci")
    if production and not (ROOT / "frontend/.next/BUILD_ID").is_file():
        raise RuntimeError("Build the frontend first: cd frontend && npm run build")
    RUN.mkdir(exist_ok=True)
    services = (
        ("backend", settings["port"], ["bash", str(ROOT / "scripts/start-backend.sh")], ROOT, backend_url + "/health"),
        ("frontend", frontend_port, [npm, "run", "start" if production else "dev", "--", "--hostname", "127.0.0.1", "--port", str(frontend_port)], ROOT / "frontend", f"http://127.0.0.1:{frontend_port}/auth/login"),
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
        environment = os.environ.copy()
        environment.setdefault("API_BACKEND_URL", backend_url)
        environment.setdefault("NEXT_TELEMETRY_DISABLED", "1")
        environment.setdefault("OMP_NUM_THREADS", "2")
        environment.setdefault("MKL_NUM_THREADS", "2")
        environment.setdefault("ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS", "2")
        with (RUN / f"{name}.log").open("a") as log:
            process = subprocess.Popen(command, cwd=directory, env=environment, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
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


def stop() -> None:
    for name in ("frontend", "backend"):
        pid_file = RUN / f"{name}.pid"
        if not pid_file.exists():
            continue
        pid = int(pid_file.read_text())
        try:
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
        finally:
            pid_file.unlink(missing_ok=True)
    print("PostgreSQL remains running; saved data is preserved.")


if __name__ == "__main__":
    try:
        stop() if len(sys.argv) > 1 and sys.argv[1] == "stop" else start()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
