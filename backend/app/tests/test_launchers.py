"""Platform command checks without installing tools or touching live services."""
import importlib.util
import io
import os
from pathlib import Path
import sys
from types import SimpleNamespace

SCRIPTS = Path(__file__).resolve().parents[3] / 'scripts'


def load(name):
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), SCRIPTS / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_windows_npm_uses_node_directly_for_paths_with_spaces(tmp_path, monkeypatch):
    runtime = load('runtime_tools')
    directory = tmp_path / 'Node installation with spaces'
    cli = directory / 'node_modules/npm/bin/npm-cli.js'
    cli.parent.mkdir(parents=True)
    cli.write_text('')
    node = directory / 'node.exe'
    monkeypatch.setattr(runtime, 'os', SimpleNamespace(name='nt'))
    monkeypatch.setattr(runtime.shutil, 'which', lambda name: str(directory / 'npm.cmd') if name == 'npm.cmd' else str(node))
    project = tmp_path / 'Project with spaces/frontend'
    command = runtime.npm_command('--prefix', project, 'run', 'start')
    assert command == [str(node), str(cli), '--prefix', str(project), 'run', 'start']
    assert all('cmd.exe' not in part for part in command)


def test_windows_startup_prepares_database_and_migrates_before_server_launch(tmp_path, monkeypatch):
    launcher = load('local-services')
    root = tmp_path / 'Project with spaces'
    (root / 'frontend/node_modules/next').mkdir(parents=True)
    (root / 'frontend/.next').mkdir()
    (root / 'frontend/.next/BUILD_ID').write_text('verified-build')
    run = root / '.run'
    run.mkdir()
    python = root / 'backend/.venv/Scripts/python.exe'
    monkeypatch.setattr(launcher, 'ROOT', root)
    monkeypatch.setattr(launcher, 'RUN', run)
    monkeypatch.setattr(launcher, 'os', SimpleNamespace(name='nt', environ=os.environ.copy()))
    monkeypatch.setattr(launcher, 'config', lambda: dict(host='127.0.0.1', port=8000))
    monkeypatch.setattr(launcher, 'backend_python', lambda _: python)
    monkeypatch.setattr(launcher, 'npm_command', lambda *args: ['node.exe', 'npm-cli.js', *map(str, args)])
    monkeypatch.setattr(launcher, 'listening', lambda _: False)
    monkeypatch.setattr(launcher.sys, 'argv', ['local-services.py', 'start', '--production', '--open-browser'])
    monkeypatch.setattr(launcher.subprocess, 'CREATE_NO_WINDOW', 0x08000000, raising=False)
    monkeypatch.setattr(launcher.subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x200, raising=False)
    events = []
    monkeypatch.setattr(launcher.subprocess, 'run', lambda command, **kwargs: events.append(('run', command)))
    def spawn(command, **options):
        events.append(('spawn', command, options))
        return SimpleNamespace(pid=100 + len(events), poll=lambda: None)
    monkeypatch.setattr(launcher.subprocess, 'Popen', spawn)
    class Response(io.BytesIO):
        status = 200
    monkeypatch.setattr(launcher, 'urlopen', lambda *args, **kwargs: Response(b'{"status":"ok"}'))
    monkeypatch.setattr(launcher.webbrowser, 'open', lambda url: events.append(('browser', url)))
    launcher.start()
    assert events[0][1] == [str(python), str(root / 'scripts/manage_database.py'), 'start']
    assert events[1][1] == [str(python), '-m', 'alembic', 'upgrade', 'head']
    assert events[2][0] == events[3][0] == 'spawn'
    assert events[2][1][:4] == [str(python), '-m', 'uvicorn', 'app.main:app']
    assert str(root / 'frontend') in events[3][1]
    assert events[2][2]['start_new_session'] is False
    assert events[2][2]['creationflags'] == 0x08000200
    assert events[-1] == ('browser', 'http://localhost:3000')


def test_stop_permission_probe_distinguishes_exited_and_live_groups(tmp_path, monkeypatch):
    import pytest
    launcher = load('local-services')
    run = tmp_path / '.run'
    run.mkdir()
    pid_file = run / 'backend.pid'
    monkeypatch.setattr(launcher, 'ROOT', tmp_path)
    monkeypatch.setattr(launcher, 'RUN', run)
    def signal_group(pid, signal):
        if signal == 0:
            raise PermissionError('group probe denied')
    monkeypatch.setattr(launcher, 'os', SimpleNamespace(name='posix', killpg=signal_group))
    group_exists = False
    def process_info(command, **kwargs):
        if command[0] == 'lsof':
            return 'n' + str(tmp_path)
        if '-axo' in command:
            return '12345 S\n' if group_exists else ''
        return 'python ' + str(tmp_path)
    monkeypatch.setattr(launcher.subprocess, 'check_output', process_info)
    pid_file.write_text('12345')
    launcher.stop(('backend',))
    assert not pid_file.exists()
    group_exists = True
    pid_file.write_text('12345')
    with pytest.raises(RuntimeError, match='remains recorded'):
        launcher.stop(('backend',))
    assert pid_file.read_text() == '12345'
