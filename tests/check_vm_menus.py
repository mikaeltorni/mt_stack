"""Open and cancel every real external owner's selection menu on a VM terminal."""
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import time

assert os.environ.get('MT_STACK_VM_TEST') == '1', 'Run only inside the disposable test VM'
root = Path(__file__).resolve().parents[1]
owners = ('programming_prompts', 'codex', 'linux_automatic_window_tiling',
          'linux_taskbar_window_count', 'linux_taskbar_monitor')
environment = dict(os.environ, TERM='xterm-256color')
for owner in owners:
    master, slave = pty.openpty()
    process = subprocess.Popen(['bash', str(root/'install.sh'), '--offline', '--configure', owner],
                               stdin=slave, stdout=slave, stderr=slave, env=environment, start_new_session=True)
    os.close(slave)
    data = b''
    deadline = time.monotonic()+45
    try:
        while time.monotonic() < deadline and process.poll() is None:
            if select.select([master], [], [], 0.2)[0]:
                try:
                    data += os.read(master, 65536)
                except OSError:
                    break
            if b'cancel' in data.lower() or b'Selection [q]:' in data or b'Configure components' in data:
                break
        assert b'cancel' in data.lower() or b'Selection [q]:' in data or b'Configure components' in data, (owner, data.decode(errors='replace'))
        os.write(master, b'q\n')
        process.wait(timeout=10)
        while select.select([master], [], [], 0)[0]:
            try:
                data += os.read(master, 65536)
            except OSError:
                break
        assert process.returncode == 0, (owner, process.returncode, data.decode(errors='replace'))
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)
        os.close(master)
    print(f'PASS: {owner} real component menu opens and cancels through the hub')
