"""Compare real shared terminal selections with exact programmatic installation."""
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def wait_for(master, process, needle, output):
    """Read terminal output until the requested menu text appears.

    Parameters: master - PTY reader; process - fixture child; needle - expected bytes; output - prior terminal bytes.
    Returns: accumulated terminal bytes after the expected text arrives.
    """
    print(f'master={master} process={process!r} needle={needle!r} output={output!r}')
    deadline = time.monotonic() + 8
    while needle not in output and process.poll() is None and time.monotonic() < deadline:
        if select.select([master], [], [], .1)[0]:
            try:
                output += os.read(master, 65536)
            except OSError:
                break
    assert needle in output, (needle, output.decode(errors='replace'))
    print(output)
    return output


def run_menu(projects, env, steps, extra=()):
    """Drive a real multi-selection terminal without installing desktop software.

    Parameters: projects - isolated registered owners; env - fixture state; steps - expected text and input pairs; extra - additional public installer options.
    Returns: the completed child exit status and terminal output.
    """
    print(f'projects={projects} env={env!r} steps={steps!r} extra={extra!r}')
    master, slave = pty.openpty()
    process = subprocess.Popen(['bash', str(ROOT/'install.sh'), '--menu', '--offline', '--projects-dir', str(projects), *extra], stdin=slave, stdout=slave, stderr=slave, env=env)
    os.close(slave)
    output = b''
    try:
        for expected, keys in steps:
            output = wait_for(master, process, expected, b'')
            os.write(master, keys)
        deadline = time.monotonic() + 10
        while process.poll() is None and time.monotonic() < deadline:
            if select.select([master], [], [], .1)[0]:
                try:
                    output += os.read(master, 65536)
                except OSError:
                    break
        process.wait(timeout=2)
        result = process.returncode, output
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
        os.close(master)
    print(result)
    return result


with tempfile.TemporaryDirectory(prefix='stack menu ') as directory:
    temporary = Path(directory)
    projects = temporary / 'projects'
    projects.mkdir()
    manifest = json.loads((ROOT/'repositories.json').read_text())
    for row in manifest:
        owner = projects / row['name']
        subprocess.run(['git', 'init', '-q', str(owner)], check=True)
        subprocess.run(['git', '-C', str(owner), 'remote', 'add', 'origin', row['source']+'.git'], check=True)
        (owner/'install.sh').write_text('''#!/bin/bash
set -eu
case "${1:-}" in
 --list-components) printf 'alpha\\tAlpha component\\ton\\n beta\\tBeta component\\toff\\n' | sed 's/^ //' ;;
 --detect) if [[ $(basename "$PWD") == codex ]]; then printf 'alpha\\t0\\nbeta\\t0\\n'; else printf 'alpha\\tabsent\\nbeta\\tabsent\\n'; fi ;;
 --list-configurable-components) printf 'beta\\n' ;;
 --list-select-configure-components|--list-component-config-values) : ;;
 --configure-component) [[ "$2" == beta ]]; printf '%s:beta\\n' "$(basename "$PWD")" >> "$HUB_CONFIG_CALLS"; printf 'Configured beta\\n' ;;
 --select) printf '%s:%s:%s\\n' "$(basename "$PWD")" "$1" "$2" >> "$HUB_CALLS" ;;
 --default) printf '%s:--select:alpha\\n' "$(basename "$PWD")" >> "$HUB_CALLS" ;;
 *) printf 'unexpected fixture action: %s\\n' "$*" >&2; exit 91 ;;
esac
''')
    calls = temporary / 'calls'
    env = dict(PATH=os.environ['PATH'], USER=os.environ.get('USER','mk'), HOME=str(temporary/'home'), HUB_CALLS=str(calls), HUB_CONFIG_CALLS=str(temporary/'configured'), TERM='xterm', LANG='C.UTF-8')
    # First owner: deselect alpha and select beta. Second owner: select alpha.
    code, output = run_menu(projects, env, [
        (b'Installation Components', b'\x1b[C'),
        (b'Alpha component', b' \x1b[B '),
        (b'Beta component', b'\x1b[D'),
        (b'Installation Components', b'\x1b[B \x1b[C'),
        (b'Alpha component', b'\x1b[D'),
        (b'Installation Components', b'\r'),
    ])
    assert code == 0, output
    expected = 'programming_prompts:--select:beta\ncodex:--select:alpha\n'
    assert calls.read_text() == expected, calls.read_text()
    calls.unlink()
    result = subprocess.run(['bash', str(ROOT/'install.sh'), '--offline', '--projects-dir', str(projects), '--select', 'programming_prompts,codex', '--components', 'programming_prompts=beta', '--components', 'codex=alpha'], env=env, text=True, capture_output=True)
    assert result.returncode == 0 and calls.read_text() == expected, (result.stdout, result.stderr)
    before = calls.read_bytes()
    result = subprocess.run(['bash', str(ROOT/'install.sh'), '--offline', '--projects-dir', str(projects), '--select', 'programming_prompts,codex', '--components', 'programming_prompts=alpha', '--components', 'codex=unknown'], env=env, text=True, capture_output=True)
    assert result.returncode == 2 and calls.read_bytes() == before, (result.stdout, result.stderr)
    for assignment in (
        ['--components','programming_prompts=alpha','--components','programming_prompts=beta'],
        ['--components','programming_prompts=alpha,alpha'],
        ['--components','missing=alpha'],
        ['--components','=alpha'],
        ['--components','alpha'],
    ):
        result = subprocess.run(['bash',str(ROOT/'install.sh'),'--offline','--projects-dir',str(projects),'--select','programming_prompts,codex',*assignment],env=env,text=True,capture_output=True)
        assert result.returncode == 2 and calls.read_bytes() == before,(assignment,result.stdout,result.stderr)
    code, output = run_menu(projects, env, [
        (b'Installation Components', b'\x1b[C'),
        (b'Alpha component', b'\x1b[B\x1b[C'),
        (b'Configured beta', b'\x1b[D'),
        (b'Installation Components', b'q'),
    ])
    assert code == 0 and calls.read_bytes() == before, output
    configured = temporary / 'configured'
    assert configured.read_text() == 'programming_prompts:beta\n'
    configured.unlink()
    code, output = run_menu(projects, env, [
        (b'Installation Components', b'\x1b[C'),
        (b'Alpha component', b'\x1b[B\x1b[C'),
        (b'--configure-component', b'\x1b[D'),
        (b'Installation Components', b'q'),
    ], ('--dry-run',))
    assert code == 0 and not configured.exists() and calls.read_bytes() == before, output
    code, output = run_menu(projects, env, [(b'Installation Components', b' \r')])
    assert code == 0 and calls.read_bytes() == before, output
    code, output = run_menu(projects, env, [(b'Installation Components', b'q')])
    assert code == 0 and calls.read_bytes() == before, output
print('PASS: shared nested multi-selection, exact multi-owner CLI parity, cancellation and whole-plan validation')
