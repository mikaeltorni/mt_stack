"""Apply one real component from each non-Codex owner's interactive menu."""
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import time

assert os.environ.get('MT_STACK_VM_TEST') == '1', 'Run only inside the disposable test VM'
root = Path(__file__).resolve().parents[1]
owners = {'programming_prompts': 'codex_skills', 'linux_automatic_window_tiling': 'per_app_widths',
          'linux_taskbar_window_count': 'badge_position', 'linux_taskbar_monitor': 'rm_refresh_interval'}
environment = dict(os.environ, TERM='xterm-256color')
for owner, component in owners.items():
    master, slave = pty.openpty()
    process = subprocess.Popen(['bash', str(root/'install.sh'), '--offline', '--configure', owner],
                               stdin=slave, stdout=slave, stderr=slave, env=environment, start_new_session=True)
    os.close(slave)
    data = b''
    applied = discarded = uninstall_answered = False
    deadline = time.monotonic()+60
    try:
        while time.monotonic()<deadline and process.poll() is None:
            if select.select([master], [], [], 0.2)[0]:
                try:
                    data += os.read(master, 65536)
                except OSError:
                    break
            if not applied:
                if owner == 'linux_taskbar_window_count' and b'IDs to install or reconfigure' in data:
                    os.write(master, component.encode()+b'\n')
                    applied = True
                elif b'[enter] apply' in data:
                    os.write(master, (b'\x1b[B' if owner == 'linux_automatic_window_tiling' else b'')+b' \n')
                    applied = True
            if owner == 'linux_taskbar_window_count' and not uninstall_answered and b'IDs to uninstall' in data:
                os.write(master, b'\n')
                uninstall_answered = True
            if not discarded and b'Choice [1/2/3]' in data:
                os.write(master, b'3\n')
                discarded = True
        process.wait(timeout=5)
        while select.select([master], [], [], 0)[0]:
            try:
                data += os.read(master, 65536)
            except OSError:
                break
        assert applied and process.returncode == 0, (owner, process.returncode, data.decode(errors='replace'))
        assert b'Installing component:' in data and ('('+component+')').encode() in data, (owner, data.decode(errors='replace'))
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)
        os.close(master)
    print(f'PASS: {owner} menu applies {component} through the hub')
