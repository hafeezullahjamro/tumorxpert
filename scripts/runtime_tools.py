"""Paths and process commands shared by macOS and Windows launchers."""
import os
from pathlib import Path
import shutil


def backend_python(root):
    candidates = [root / 'backend/.venv/Scripts/python.exe', root / 'backend/.venv/bin/python',
                  root / 'backend/.venv-mac/bin/python']
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise RuntimeError('Backend environment is missing. Run Setup-Windows.ps1 on Windows or follow README.md on macOS.')


def npm_command(*arguments):
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not npm:
        raise RuntimeError('Node.js/npm is missing. Install Node.js LTS and reopen your terminal.')
    if os.name != 'nt':
        return [npm, *map(str, arguments)]
    # Run Node directly: Windows batch-file quoting otherwise breaks paths with spaces.
    node = shutil.which('node')
    cli = Path(npm).parent / 'node_modules/npm/bin/npm-cli.js'
    if not node or not cli.is_file():
        raise RuntimeError('The npm CLI was not found beside npm.cmd. Repair your Node.js installation.')
    return [node, str(cli), *map(str, arguments)]
