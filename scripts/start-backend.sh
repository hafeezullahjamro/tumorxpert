#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

VENV_PYTHON=""
for candidate in "$BACKEND_DIR/.venv/bin/python" "$BACKEND_DIR/.venv-mac/bin/python"; do
  if [[ -x "$candidate" ]]; then
    VENV_PYTHON="$candidate"
    break
  fi
done
if [[ -z "$VENV_PYTHON" ]]; then
  echo "Create a backend environment first: python3 -m venv backend/.venv"
  echo "Then install: backend/.venv/bin/python -m pip install -r backend/requirements.txt -c backend/constraints.txt"
  exit 1
fi

cd "$BACKEND_DIR"
# Use the app's dotenv parser so paths with spaces and DATABASE_URL work too.
IFS=$'\t' read -r BACKEND_HOST BACKEND_PORT POSTGRES_HOST POSTGRES_PORT POSTGRES_USER < <(
  "$VENV_PYTHON" - <<'PY'
from app.core.config import get_settings
from sqlalchemy.engine import make_url
s = get_settings()
url = make_url(s.database_url)
print(s.backend_host, s.backend_port, url.host or "localhost", url.port or 5432, url.username or "postgres", sep="\t")
PY
)

find_pg_bin() {
  if command -v pg_isready >/dev/null 2>&1; then
    dirname "$(command -v pg_isready)"
    return 0
  fi

  local candidates=(
    "/Library/PostgreSQL/18/bin"
    "/Library/PostgreSQL/17/bin"
    "/opt/homebrew/opt/postgresql@18/bin"
    "/opt/homebrew/opt/postgresql@17/bin"
    "/usr/local/opt/postgresql@18/bin"
    "/usr/local/opt/postgresql@17/bin"
  )

  for bin_dir in "${candidates[@]}"; do
    if [[ -x "$bin_dir/pg_isready" ]]; then
      echo "$bin_dir"
      return 0
    fi
  done

  return 1
}

if ! PG_BIN="$(find_pg_bin)"; then
  echo "PostgreSQL client tools not found (pg_isready missing)."
  echo "Install PostgreSQL tools or add them to PATH, then rerun."
  exit 1
fi

PG_ISREADY="$PG_BIN/pg_isready"
PG_CTL="$PG_BIN/pg_ctl"

if ! "$PG_ISREADY" -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" >/dev/null 2>&1; then
  LOCAL_DATA_DIR="$ROOT_DIR/.local-postgres/data"
  if [[ ( "$POSTGRES_HOST" == "localhost" || "$POSTGRES_HOST" == "127.0.0.1" ) && "$POSTGRES_PORT" == "55432" && -d "$LOCAL_DATA_DIR" && -x "$PG_CTL" ]]; then
    echo "Postgres is down. Starting project-local Postgres on port 55432..."
    "$PG_CTL" -D "$LOCAL_DATA_DIR" -l "$ROOT_DIR/.local-postgres/postgres.log" -o "-p 55432" start >/dev/null
  fi
fi

if ! "$PG_ISREADY" -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" >/dev/null 2>&1; then
  echo "Postgres is not accepting connections at $POSTGRES_HOST:$POSTGRES_PORT"
  echo "Start your Postgres server/service first, then rerun this command."
  exit 1
fi

if ! "$VENV_PYTHON" -c 'import alembic, uvicorn' >/dev/null 2>&1; then
  echo "Backend virtual environment exists but tools are missing."
  echo "Install deps with: $VENV_PYTHON -m pip install -r requirements.txt -c constraints.txt"
  exit 1
fi

echo "Applying migrations..."
"$VENV_PYTHON" -m alembic upgrade head

echo "Starting backend on http://$BACKEND_HOST:$BACKEND_PORT"
exec "$VENV_PYTHON" -m uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
