"""Check the opt-in workstation installer through the hub CLI."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
base = 'linux_installations_setup'
desktop = 'linux_configuration_setup'
base_components = 'git,curl,gpg,jq,tmux,gnome_tooling,build_tools,python_runtime,desktop_utils,terminal'
desktop_components = 'clock_calendar,dark_mode,terminal_theme,kitty_defaults,tmux_defaults'
expected = (
    (base, base_components),
    (desktop, desktop_components),
    ('linux_task_workspaces', 'task_workspaces'),
    ('linux_active_monitor_placement', 'active_monitor_placement'),
    ('linux_monitor_window_hotkeys', 'monitor_window_hotkeys'),
    ('linux_hotkey_setup', 'screenshot,workspace_behavior,workspace_switch_1,workspace_switch_2,workspace_switch_3,workspace_switch_4,workspace_switch_5,workspace_switch_6,workspace_switch_7,workspace_switch_8,workspace_move_modifier,window_placement_tiling'),
    ('linux_workspaces_setup', 'workspace_send_mode,workspace_popup'),
    ('linux_hotkey_window_tools', 'move_hotkey,resize_hotkey,open_kitty_sort_hotkey'),
    ('linux_automatic_window_tiling', 'keybinding,per_app_widths,portrait_stacking'),
    ('linux_taskbar_window_count', 'badge_position,count_threshold,workspace_scope,badge_appearance'),
    ('linux_taskbar_monitor', 'rm_refresh_interval,rm_gradient_colors,rm_vram,rm_per_disk,rm_panel_spacing,rm_hide_eth_icon,rm_process_popup'),
    ('linux_programming_setup', 'cursor,cursor_extensions,cursor_skills'),
    ('linux_window_selection_indicator', 'outline'),
    ('linux_codex_claude_code_setup', ''),
    ('agent_command_center', ''),
)

with tempfile.TemporaryDirectory() as directory:
    sandbox = Path(directory)
    projects = sandbox / 'projects'
    bin_dir = sandbox / 'bin'
    bin_dir.mkdir()
    calls = sandbox / 'calls'
    receipt_paths = sandbox / 'receipt-paths'
    sudo = bin_dir / 'sudo'
    sudo.write_text('#!/bin/sh\n[ "$1" = "--" ] && shift\nexport HUB_ELEVATED=yes\nexec "$@"\n')
    sudo.chmod(0o755)
    environment = dict(os.environ, PATH=str(bin_dir) + ':' + os.environ['PATH'], HUB_CALLS=str(calls),
                       HUB_RECEIPT_PATHS=str(receipt_paths), ISC_RECEIPT_DIR=str(sandbox / 'user-receipts'),
                       HUB_PROJECTS=str(projects), HUB_REPOS=' '.join(owner for owner, _ in expected))
    command = ['bash', str(root / 'install.sh'), '--projects-dir', str(projects)]
    listed = subprocess.run(command + ['--workstation', '--list'], env=environment, text=True, capture_output=True, timeout=10)
    assert listed.returncode == 0, listed.stderr
    assert [line.split('\t')[0] for line in listed.stdout.splitlines()] == [owner for owner, _ in expected], listed.stdout
    public = subprocess.run(command + ['--list'], env=environment, text=True, capture_output=True, timeout=10)
    assert public.returncode == 0 and base not in public.stdout and desktop not in public.stdout, public.stdout
    missing = subprocess.run(command + ['--workstation', '--default', '--dry-run'], env=environment, text=True, capture_output=True, timeout=10)
    assert missing.returncode == 2 and base in missing.stderr and not projects.exists(), missing.stderr
    for owner, components in expected:
        checkout = projects / owner
        subprocess.run(['git', 'init', '-q', str(checkout)], check=True)
        subprocess.run(['git', '-C', str(checkout), 'remote', 'add', 'origin', f'https://github.com/mikaeltorni/{owner}.git'], check=True)
        metadata = ''.join(f"{name}\\t{name}\\ton\\n" for name in (*filter(None, components.split(',')), 'optional'))
        context_check = (
            '''
case "$*" in
  "--select cursor_extensions,cursor_skills"|--detect)
    test "$PROJECTS_DIR" = "$HUB_PROJECTS" &&
      test "$PROGRAMMING_PROMPTS_DIR" = "$HUB_PROJECTS/programming_prompts" &&
      test "$CURSOR_SKILLS_REPOS" = "$HUB_REPOS" || exit 14 ;;
esac
''' if owner == 'linux_programming_setup' else ''
        )
        detection = 'printf "cursor_skills\\tinstalled\\n"' if context_check else ':'
        (checkout / 'install.sh').write_text(
            '#!/bin/sh\n' + context_check + 'case "$1" in\n'
            f'--list-components) printf "{metadata}" ;;\n'
            f'--detect) {detection} ;;\n'
            '*) printf "%s %s %s %s\\n" "${PWD##*/}" "${HUB_ELEVATED:-no}" "$INSTALLER_NO_REBOOT" "$*" >> "$HUB_CALLS"; printf "%s\\n" "$ISC_RECEIPT_DIR" >> "$HUB_RECEIPT_PATHS" ;;\nesac\n'
        )
    preview = subprocess.run(command + ['--workstation', '--default', '--dry-run'], env=environment, text=True, capture_output=True, timeout=10)
    assert preview.returncode == 0 and not calls.exists(), preview.stderr
    assert preview.stdout.splitlines()[0].startswith('sudo -- env '), preview.stdout
    assert len(preview.stdout.splitlines()) == 1 + sum(bool(components) for _, components in expected), preview.stdout
    exported = subprocess.run(command + ['--workstation', '--export-selection'], env=environment, text=True, capture_output=True, timeout=10)
    assert exported.returncode == 0, exported.stderr
    defaults = json.loads(exported.stdout)['repos']
    assert defaults['agent_command_center'] == {
        'enabled': 0, 'components': {'optional': {'on': 1, 'uninstall': 0}},
    }, defaults['agent_command_center']
    detected = subprocess.run(command + ['--workstation', '--detect'], env=environment, text=True, capture_output=True, timeout=10)
    assert detected.returncode == 0, detected.stderr
    assert 'linux_programming_setup\tcursor_skills\tinstalled' in detected.stdout, detected.stdout
    applied = subprocess.run(command + ['--workstation', '--default'], env=environment, text=True, capture_output=True, timeout=10)
    assert applied.returncode == 0, applied.stderr
    expected_calls = []
    for owner, components in expected:
        if owner == 'linux_programming_setup':
            expected_calls.extend((
                f'{owner} yes 1 --select cursor',
                f'{owner} no 1 --select cursor_extensions,cursor_skills',
            ))
        elif components:
            expected_calls.append(f"{owner} {'yes' if owner == base else 'no'} 1 --select {components}")
    assert calls.read_text().splitlines() == expected_calls, calls.read_text()
    assert receipt_paths.read_text().splitlines() == [
        '/var/lib/mt-stack/receipts' if ' yes ' in call else str(sandbox / 'user-receipts')
        for call in expected_calls
    ], receipt_paths.read_text()
    calls.unlink()
    reject = subprocess.run(command + ['--workstation', '--default', '--components', f'{desktop}=unknown'], env=environment, text=True, capture_output=True, timeout=10)
    assert reject.returncode == 2 and not calls.exists(), reject.stderr
    apply = subprocess.run(command + ['--workstation', '--select', f'{desktop},{base}'], env=environment, text=True, capture_output=True, timeout=10)
    assert apply.returncode == 0, apply.stderr
    assert calls.read_text().splitlines() == [
        f'{base} yes 1 --select {base_components}',
        f'{desktop} no 1 --select {desktop_components}',
    ], calls.read_text()
    configured = subprocess.run(command + ['--workstation', '--list-components', desktop], env=environment, text=True, capture_output=True, timeout=10)
    assert configured.returncode == 0 and 'tmux_defaults\t' in configured.stdout, configured.stderr
    override = subprocess.run(command + ['--workstation', '--select', desktop, '--components', 'optional'], env=environment, text=True, capture_output=True, timeout=10)
    assert override.returncode == 0 and calls.read_text().splitlines()[-1] == f'{desktop} no 1 --select optional', override.stderr
    agents = subprocess.run(command + ['--workstation', '--select', 'agent_command_center,linux_codex_claude_code_setup'], env=environment, text=True, capture_output=True, timeout=10)
    assert agents.returncode == 0, agents.stderr
    assert calls.read_text().splitlines()[-2:] == [
        'linux_codex_claude_code_setup no 1 --default',
        'agent_command_center no 1 --default',
    ], calls.read_text()
print('PASS: workstation profile isolation, ordering, checkout validation, privilege and component dispatch')
