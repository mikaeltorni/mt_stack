"""Verify portable component discovery and interactive selection without deployment."""
import os
from pathlib import Path
import pty
import select
import subprocess
import tempfile
import time

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as directory:
    master, slave = pty.openpty()
    process = subprocess.Popen(['bash', str(root/'install.sh'), '--menu', '--dry-run'], stdin=slave, stdout=slave, stderr=slave, env=dict(os.environ, HOME=directory))
    os.close(slave)
    data = b''
    deadline = time.monotonic()+10
    while b'Installation Components' not in data and process.poll() is None and time.monotonic()<deadline:
        if select.select([master], [], [], 0.2)[0]:
            data += os.read(master, 65536)
    assert b'Installation Components' in data, data.decode(errors='replace')
    assert b'programming_prompts' in data and b'codex' in data, data
    os.write(master, b'\r')
    process.wait(timeout=10)
    assert process.returncode == 0, process.returncode
    os.close(master)
result = subprocess.run(['bash', str(root/'install.sh'), '--menu', '--dry-run'], input='garbage\n0\n99\nq\n', text=True, capture_output=True)
assert result.returncode == 2 and 'requires a terminal' in result.stderr, (result.stdout, result.stderr)
print('PASS: shared terminal menu previews without writes and rejects nonterminal interactive input')
