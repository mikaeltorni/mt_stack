"""Check uniform hub lifecycle commands using isolated public owner fixtures."""
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
rows = json.loads((ROOT/'repositories.json').read_text())
with tempfile.TemporaryDirectory(prefix='hub lifecycle ') as directory:
    temporary = Path(directory)
    projects = temporary/'projects'
    projects.mkdir()
    calls = temporary/'calls'
    home = temporary/'home'
    home.mkdir()
    for row in rows:
        checkout = projects/row['name']
        subprocess.run(['git', 'init', '-q', str(checkout)], check=True)
        subprocess.run(['git', '-C', str(checkout), 'remote', 'add', 'origin', row['source']+'.git'], check=True)
        shutil.copytree(ROOT/'.installer-support', checkout/'.installer-support', ignore=shutil.ignore_patterns('__pycache__', '.log'))
        (checkout/'install.sh').write_text('''#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/.installer-support/bootstrap.sh"
isc_activate_components
ISC_REPO_NAME="${SCRIPT_DIR##*/}"
# Apply an isolated fixture component.
# Parameters: none. Returns: zero.
apply_component() { printf 'parameters=none\\n0\\n' >&2; }
# Reverse an isolated fixture component.
# Parameters: none. Returns: zero.
remove_component() { printf 'parameters=none\\n0\\n' >&2; }
ISC_COMPONENTS=("alpha|Alpha|on|apply_component||remove_component" "beta|Beta|off|apply_component||remove_component")
case "${1:-}" in
 --select|--select=*|--uninstall|--uninstall=*|--reconfigure|--reconfigure=*|--default|--all)
  printf '%s:%s\\n' "$ISC_REPO_NAME" "$*" >> "$OWNER_CALLS" ;;
esac
component_main "$@"
''')
    env = dict(PATH=os.environ['PATH'], HOME=str(home), USER=os.environ.get('USER', 'mk'),
               OWNER_CALLS=str(calls), XDG_STATE_HOME=str(temporary/'state'),
               XDG_CACHE_HOME=str(temporary/'cache'), TERM='xterm')
    public = ['bash', str(ROOT/'install.sh'), '--projects-dir', str(projects), '--offline']
    result = subprocess.run([*public, '--detect'], env=env, text=True, capture_output=True)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert set(result.stdout.splitlines()) == {row['name']+'\t'+component+'\tabsent' for row in rows for component in ('alpha', 'beta')}, result.stdout
    assert not calls.exists()
    result = subprocess.run([*public, '--export-selection'], env=env, text=True, capture_output=True)
    assert result.returncode == 0, (result.stdout, result.stderr)
    document = json.loads(result.stdout)
    assert document['scope'] == 'master' and document['schema_version'] == 1, document
    assert set(document['repos']) == {row['name'] for row in rows}, document
    for row in rows:
        record = document['repos'][row['name']]
        assert record['enabled'] == int(row['default']), (row, record)
        assert record['components']['alpha']['on'] == 1 and record['components']['beta']['on'] == 0, record
    assert not calls.exists()
    result = subprocess.run([*public, '--all'], env=env, text=True, capture_output=True)
    assert result.returncode == 0, (result.stdout, result.stderr)
    expected = ''.join(row['name']+':--all\n' for row in rows)
    assert calls.read_text() == expected, calls.read_text()
    for arguments, additions in (
        (['--all', '--components', 'codex=alpha'], ''.join(row['name'] + (':--select alpha\n' if row['name'] == 'codex' else ':--all\n') for row in rows)),
        (['--uninstall', 'programming_prompts,codex', '--components', 'programming_prompts=alpha', '--components', 'codex=beta'], 'programming_prompts:--uninstall alpha\ncodex:--uninstall beta\n'),
        (['--reconfigure', 'codex', '--components', 'alpha'], 'codex:--reconfigure alpha\n'),
        (['--reconfigure', 'codex'], 'codex:--reconfigure alpha\n'),
        (['--reconfigure', 'programming_prompts,codex', '--components', 'programming_prompts=beta', '--components', 'codex=alpha'], 'programming_prompts:--reconfigure beta\ncodex:--reconfigure alpha\n'),
        (['--reconfigure', 'codex', '--components', ''], 'codex:--reconfigure \n'),
        (['--uninstall', 'programming_prompts'], 'programming_prompts:--uninstall beta\n'),
        (['--uninstall', 'programming_prompts'], ''),
        (['--uninstall', 'codex', '--components', ''], 'codex:--uninstall \n'),
    ):
        result = subprocess.run([*public, *arguments], env=env, text=True, capture_output=True)
        assert result.returncode == 0, (arguments, result.stdout, result.stderr)
        expected += additions
        assert calls.read_text() == expected, (arguments, calls.read_text())
    result = subprocess.run([*public, '--detect'], env=env, text=True, capture_output=True)
    assert result.returncode == 0, (result.stdout, result.stderr)
    states = {tuple(line.split('\t')[:2]): line.split('\t')[2] for line in result.stdout.splitlines()}
    assert states['programming_prompts', 'alpha'] == states['programming_prompts', 'beta'] == 'absent', states
    assert states['codex', 'alpha'] == 'installed' and states['codex', 'beta'] == 'absent', states
    for arguments in (
        ['--uninstall', 'programming_prompts,codex', '--components', 'programming_prompts=alpha', '--components', 'codex=unknown'],
        ['--reconfigure', 'codex', '--components', 'alpha,alpha'],
        ['--uninstall'], ['--reconfigure'], ['--all', '--default'],
        ['--detect', '--components', 'alpha'], ['--export-selection', '--components', 'alpha'],
        ['--uninstall', 'unknown'], ['--reconfigure', 'codex,codex'],
        ['--uninstall', 'codex', '--components', 'alpha,,beta'],
        ['--select', 'codex,'], ['--select', 'codex codex'],
        ['--list-components', ''],
    ):
        result = subprocess.run([*public, *arguments], env=env, text=True, capture_output=True)
        assert result.returncode == 2, (arguments, result.stdout, result.stderr)
        assert calls.read_text() == expected, (arguments, calls.read_text())
    for arguments in (['--uninstall', 'codex', '--components', 'alpha'], ['--reconfigure', 'codex', '--components', 'alpha'], ['--all']):
        result = subprocess.run([*public, *arguments, '--dry-run'], env=env, text=True, capture_output=True)
        assert result.returncode == 0, (arguments, result.stdout, result.stderr)
        assert calls.read_text() == expected, arguments
    # Malformed owner replies must fail as clean protocol errors without mutations.
    installer = projects/'codex/install.sh'
    original = installer.read_text()
    for flag, reply in (('--detect', 'unknown\tinstalled\n'), ('--list-components', 'bad component\tInvalid\ton\n')):
        guard = 'if [[ "${1:-}" == ' + flag + ' ]]; then printf %s ' + shlex.quote(reply) + '; exit 0; fi\n'
        installer.write_text(original.replace('component_main "$@"', guard + 'component_main "$@"'))
        result = subprocess.run([*public, '--detect'], env=env, text=True, capture_output=True)
        assert result.returncode == 2 and 'Traceback' not in result.stderr, (flag, result.stdout, result.stderr)
        assert calls.read_text() == expected, flag
        installer.write_text(original)
print('PASS: hub detect/export, complete selection, reconfigure/removal, dry-run and rejection preserve owner state')
