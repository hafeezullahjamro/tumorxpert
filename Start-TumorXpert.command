#!/usr/bin/env bash
set -euo pipefail

# Finder can launch this file without the PATH used by an interactive shell.
export PATH="/opt/homebrew/bin:/usr/local/bin:/Library/Frameworks/Python.framework/Versions/Current/bin:$PATH"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

trap 'status=$?; if [[ $status -ne 0 && -t 0 ]]; then printf "\nStartup failed. Press Return to close this window. "; read -r _; fi' EXIT

OPTIONS=(--production --build-if-needed --open-browser)
for argument in "$@"; do
  case "$argument" in
    --no-browser) OPTIONS=(--production --build-if-needed) ;;
    --help|-h)
      printf 'Usage: ./Start-TumorXpert.command [--no-browser]\nStarts PostgreSQL, the backend, and the frontend; opens TumorXpert in your browser.\n'
      exit 0
      ;;
    *) printf 'Unknown option: %s\n' "$argument" >&2; exit 1 ;;
  esac
done

if ! command -v python3 >/dev/null 2>&1; then
  printf 'Python 3 is required. See README.md for setup instructions.\n' >&2
  exit 1
fi

printf 'Starting TumorXpert...\n'
bash "$ROOT_DIR/scripts/start.sh" "${OPTIONS[@]}"
