"""Verify explicit workstation fetch uses Git authentication and reuses checkouts."""
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
owner = 'linux_configuration_setup'
with tempfile.TemporaryDirectory() as directory:
    sandbox = Path(directory)
    seed = sandbox / 'seed'
    remotes = sandbox / 'remotes'
    remotes.mkdir()
    projects = sandbox / 'workstation'
    subprocess.run(['git', 'init', '-qb', 'owner-default', str(seed)], check=True)
    (seed / 'install.sh').write_text('#!/bin/sh\ncase "$1" in\n--list-components) printf "clock_calendar\\tClock\\ton\\ndark_mode\\tTheme\\ton\\nterminal_theme\\tTerminal\\ton\\nkitty_defaults\\tKitty\\ton\\ntmux_defaults\\tTmux\\ton\\n";;\nesac\n')
    subprocess.run(['git', '-C', str(seed), 'add', 'install.sh'], check=True)
    subprocess.run(['git', '-C', str(seed), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'owner fixture'], check=True)
    subprocess.run(['git', 'clone', '--bare', '-q', str(seed), str(remotes / f'{owner}.git')], check=True)
    config = sandbox / 'gitconfig'
    subprocess.run(['git', 'config', '--file', str(config), f'url.{remotes.as_uri()}/.insteadOf', 'https://github.com/mikaeltorni/'], check=True)
    environment = dict(os.environ, GIT_CONFIG_GLOBAL=str(config))
    command = ['bash', str(root / 'install.sh'), '--projects-dir', str(projects), '--list-components', owner]
    for flags in (['--workstation'], ['--fetch'], ['--workstation', '--fetch', '--offline']):
        rejected = subprocess.run(command + flags, env=environment, capture_output=True, text=True, timeout=10)
        assert rejected.returncode == 2 and not projects.exists(), (flags, rejected.stderr)
    preview = subprocess.run(command + ['--workstation', '--fetch', '--dry-run'], env=environment, capture_output=True, text=True, timeout=10)
    assert preview.returncode == 0 and not projects.exists(), preview.stderr
    assert 'git clone' in preview.stdout and 'credential.helper=' not in preview.stdout, preview.stdout
    fetched = subprocess.run(command + ['--workstation', '--fetch'], env=environment, capture_output=True, text=True, timeout=10)
    assert fetched.returncode == 0 and fetched.stdout.startswith('clock_calendar\tClock\ton\n'), (fetched.stdout, fetched.stderr)
    checkout = projects / owner
    branch = subprocess.check_output(['git', '-C', str(checkout), 'branch', '--show-current'], text=True).strip()
    assert branch == 'owner-default', branch
    reused = subprocess.run(command + ['--workstation', '--offline'], env=environment, capture_output=True, text=True, timeout=10)
    assert reused.returncode == 0 and reused.stdout.startswith('clock_calendar\t'), reused.stderr
print('PASS: explicit fresh workstation clone, inherited Git authentication, default branch and offline reuse')
