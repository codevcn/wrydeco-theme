import json
import os
import signal
import socket
import subprocess
import sys
import time
from collections import deque
from pathlib import Path
from types import SimpleNamespace

import pytest

from scraper import server_control as control


@pytest.mark.parametrize('key', ['q', 'Q', '\x03'])
def test_console_stop_keys_without_enter_and_signal_handlers_restored(tmp_path, key):
    record = control.register_server_process(tmp_path, '127.0.0.1', 5000)
    keys = deque(['x', '\xe0', 'Q'])  # Extended key's second byte is not a quit key.
    previous = signal.getsignal(signal.SIGINT)
    with control.ServerStopController(record, key_reader=lambda: keys.popleft() if keys else None) as stop:
        time.sleep(.2)
        assert not stop.requested()
        keys.append(key)
        assert stop.event.wait(2)
        assert stop.requested()
    assert signal.getsignal(signal.SIGINT) == previous


def test_stop_marker_requires_current_registration_token_and_is_removed(tmp_path):
    record = control.register_server_process(tmp_path, '127.0.0.1', 5000)
    marker = record.with_suffix('.stop')
    marker.write_text('{"token":"old-token"}', encoding='utf-8')
    assert not control.server_stop_requested(record)
    marker.write_text('incomplete JSON', encoding='utf-8')
    assert not control.server_stop_requested(record)
    token = json.loads(record.read_text())['shutdown_token']
    marker.write_text(json.dumps({'token': token}), encoding='utf-8')
    with control.ServerStopController(record) as stop:
        assert stop.requested()
    control.unregister_server_process(record)
    assert not record.exists() and not marker.exists()


def test_stop_signal_sets_event_without_raising_during_cleanup(tmp_path):
    record = control.register_server_process(tmp_path, '127.0.0.1', 5000)
    previous = signal.getsignal(signal.SIGINT)
    with control.ServerStopController(record) as stop:
        signal.getsignal(signal.SIGINT)(signal.SIGINT, None)
        signal.getsignal(signal.SIGINT)(signal.SIGINT, None)
        assert stop.requested()
    assert signal.getsignal(signal.SIGINT) == previous


@pytest.mark.parametrize('reader_fails', [False, True])
def test_console_mode_is_restored_on_exit_or_keyboard_failure(tmp_path, reader_fails):
    record = control.register_server_process(tmp_path, '127.0.0.1', 5000)
    restored = []
    kernel = SimpleNamespace(SetConsoleMode=lambda handle, mode: restored.append((handle,mode)))
    def read_key():
        if reader_fails:
            raise OSError('Console input closed')
        return 'q'
    controller = control.ServerStopController(record, key_reader=read_key)
    controller._console_mode = (kernel, 'console-handle', 7)
    with controller as stop:
        if reader_fails:
            deadline = time.monotonic()+2
            while not restored and time.monotonic()<deadline:
                time.sleep(.01)
            assert restored
            signal.getsignal(signal.SIGINT)(signal.SIGINT, None)
        assert stop.event.wait(2)
    assert restored == [('console-handle',7)]
    assert controller._console_mode is None


def registered_fixture(tmp_path, *, legacy=False):
    path = tmp_path/'.runtime'/'servers'/'99999999.json'
    path.parent.mkdir(parents=True)
    data = {'pid':99999999, 'executable':sys.executable, 'started_at':time.time()}
    if not legacy:
        data.update(shutdown_protocol=1, shutdown_token='fixture-token')
    path.write_text(json.dumps(data), encoding='utf-8')
    return path, data


def test_stale_registration_is_cleaned_without_signalling_any_process(tmp_path, monkeypatch):
    path,_ = registered_fixture(tmp_path)
    monkeypatch.setattr(control, '_registered_process_matches', lambda record: False)
    def forbidden(*args, **kwargs):
        raise AssertionError('A stale process must not be stopped')
    monkeypatch.setattr(control.subprocess, 'run', forbidden)
    monkeypatch.setattr(control.os, 'kill', forbidden)
    result = control.stop_registered_servers(tmp_path)
    assert result['stale']==[99999999] and not result['stopped'] and not path.exists()
    assert control.stop_registered_servers(tmp_path)=={'stopped':[], 'stale':[], 'failed':[], 'forced':[]}


@pytest.mark.parametrize('legacy', [False, True])
def test_unresponsive_or_legacy_server_has_bounded_force_fallback(tmp_path, monkeypatch, legacy):
    path,_ = registered_fixture(tmp_path, legacy=legacy)
    monkeypatch.setattr(control, '_registered_process_matches', lambda record: True)
    calls = []
    def force(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(control.subprocess, 'run', force)
    monkeypatch.setattr(control.os, 'kill', force)
    result = control.stop_registered_servers(tmp_path, grace_seconds=0)
    assert result['stopped']==result['forced']==[99999999] and not result['failed']
    assert len(calls)==1 and not path.exists() and not path.with_suffix('.stop').exists()


def test_replacement_registration_is_never_force_killed(tmp_path, monkeypatch):
    path,data = registered_fixture(tmp_path)
    monkeypatch.setattr(control, '_registered_process_matches', lambda record: True)
    original_write = control.atomic_write_json
    def replace(marker, payload):
        original_write(marker, payload)
        path.write_text(json.dumps({**data, 'shutdown_token':'replacement-token'}), encoding='utf-8')
    monkeypatch.setattr(control, 'atomic_write_json', replace)
    result = control.stop_registered_servers(tmp_path, grace_seconds=0)
    assert not result['forced'] and path.exists()
    assert not control.server_stop_requested(path)


@pytest.mark.skipif(os.name!='nt', reason='Windows PID identity check')
def test_reused_windows_pid_is_not_a_matching_server(tmp_path, monkeypatch):
    _,data = registered_fixture(tmp_path)
    monkeypatch.setattr(control, '_windows_process', lambda pid: {
        'ExecutablePath':sys.executable, 'CommandLine':'python -m scraper serve',
        'StartedAt':data['started_at']+1,
    })
    assert not control._registered_process_matches(data)


SERVER_FIXTURE = '''
import json, signal, sys, threading, time
from pathlib import Path
from flask import Flask
from scraper import server as server_module
from scraper import antigravity
from scraper.server_control import ServerStopController

root, port, mode = Path(sys.argv[-3]), int(sys.argv[-2]), sys.argv[-1]
root.mkdir(parents=True, exist_ok=True)
requested, stopped = [], []
class Worker:
    def __init__(self, *args, **kwargs): pass
    def recover(self): pass
    def start(self):
        if mode == 'startup-error' and self.name == 'agent': raise RuntimeError('startup fixture')
    def request_stop(self): requested.append(self.name)
    def stop(self):
        assert set(requested) == {'coordinator', 'backfill', 'agent'}
        stopped.append(self.name)
        if mode == 'ctrl-c': signal.raise_signal(signal.SIGINT)
        if mode == 'cleanup-error' and self.name == 'coordinator': raise RuntimeError('cleanup fixture')
class Coordinator(Worker): name = 'coordinator'
class Backfill(Worker): name = 'backfill'
class Agent(Worker): name = 'agent'
def app_factory(*args, **kwargs):
    app = Flask('server-stop-fixture')
    app.extensions['aeo_backfill'] = Backfill()
    app.add_url_rule('/', view_func=lambda: 'ready')
    return app
server_module.PACKAGE_ROOT = root
server_module.RunCoordinator = Coordinator
server_module.create_app = app_factory
server_module._open_dashboard = lambda url: None
antigravity.AntigravitySupervisor = Agent
key_file = root/'console-key'
if mode in {'q','cleanup-error'}:
    server_module.ServerStopController = lambda record: ServerStopController(
        record, key_reader=lambda: key_file.read_text() if key_file.exists() else None)
if mode == 'ctrl-c':
    def interrupt():
        while not key_file.exists(): time.sleep(.02)
        signal.raise_signal(signal.SIGINT)
    threading.Thread(target=interrupt, daemon=True).start()
try:
    server_module.serve('127.0.0.1', port)
finally:
    (root/'cleanup.json').write_text(json.dumps({'requested':requested,'stopped':stopped}))
'''


@pytest.mark.parametrize('mode', ['q','ctrl-c','stop-command','startup-error','cleanup-error'])
def test_real_server_lifecycle_uses_same_cleanup_and_releases_port(tmp_path, mode):
    root = tmp_path/'scraper'
    script = tmp_path/'server_fixture.py';script.write_text(SERVER_FIXTURE, encoding='utf-8')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port = sock.getsockname()[1]
    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path(__file__).resolve().parents[2])
    process = subprocess.Popen(
        [sys.executable,'-u',str(script),'-m','scraper','serve',str(root),str(port),mode],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=env, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,
    )
    try:
        if mode!='startup-error':
            deadline = time.monotonic()+15
            while time.monotonic()<deadline:
                if process.poll() is not None:
                    raise AssertionError(process.communicate())
                if list((root/'.runtime'/'servers').glob('*.json')):
                    break
                time.sleep(.02)
            else:
                raise AssertionError('Server did not register')
            if mode=='stop-command':
                result = control.stop_registered_servers(root, grace_seconds=10)
                assert result['stopped']==[process.pid] and not result['forced'] and not result['failed']
            else:
                (root/'console-key').write_text('q', encoding='utf-8')
        stdout,stderr = process.communicate(timeout=15)
        assert (process.returncode!=0)==(mode in {'startup-error','cleanup-error'}), (stdout,stderr)
        cleanup = json.loads((root/'cleanup.json').read_text())
        assert cleanup['stopped']==['coordinator','backfill','agent']
        assert not list((root/'.runtime'/'servers').glob('*'))
        with socket.socket() as sock:
            assert sock.connect_ex(('127.0.0.1',port))!=0
    finally:
        if process.poll() is None:
            process.kill();process.wait(timeout=5)


@pytest.mark.skipif(os.name!='nt', reason='Windows command launchers')
@pytest.mark.parametrize('name,arguments', [
    ('run-server.cmd',['-m','scraper','serve','--host','127.0.0.1','--port','5000']),
    ('stop-server.cmd',['-m','scraper','stop-servers']),
])
def test_cmd_launchers_resolve_own_folder_and_preserve_exit_code(tmp_path, name, arguments):
    project = Path(__file__).resolve().parents[2]
    folder = tmp_path/'launcher with spaces';folder.mkdir()
    (folder/name).write_bytes((project/name).read_bytes())
    stub = folder/'record_python.py'
    stub.write_text("import os,sys,json\nfrom pathlib import Path\n"
                    "Path('launch.json').write_text(json.dumps({'cwd':os.getcwd(),'args':sys.argv[1:]}))\n"
                    "raise SystemExit(7)\n", encoding='utf-8')
    (folder/'python.cmd').write_text(f'@"{sys.executable}" "{stub}" %*\r\n@exit /b %errorlevel%\r\n')
    env = os.environ.copy();env['PATH'] = str(folder)+os.pathsep+env['PATH']
    result = subprocess.run([os.environ.get('COMSPEC','cmd.exe'),'/d','/c',str(folder/name)],
                            cwd=tmp_path, env=env, capture_output=True, timeout=15)
    assert result.returncode==7, (result.stdout,result.stderr)
    launch = json.loads((folder/'launch.json').read_text())
    assert Path(launch['cwd'])==folder and launch['args']==arguments
