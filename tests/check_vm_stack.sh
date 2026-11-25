#!/usr/bin/env bash
# Exercise real external owners on a disposable Ubuntu GNOME VM.
set -euo pipefail
if [[ ${MT_STACK_VM_TEST:-} != 1 ]]; then
  printf 'Run only inside the test VM with MT_STACK_VM_TEST=1.\n' >&2
  exit 2
fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECTS="${MT_STACK_PROJECTS_DIR:-$HOME/projects}"
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/run/user/$(id -u)/gdm/Xauthority}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"
export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
# Keep repeated native verification on the same bounded build profile.
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-2}"
export CARGO_PROFILE_RELEASE_DEBUG="${CARGO_PROFILE_RELEASE_DEBUG:-0}"
owners=(programming_prompts codex linux_automatic_window_tiling linux_taskbar_window_count linux_taskbar_monitor)
case ${1:-discovery} in
  discovery)
    bash "$ROOT/tests/run_tests.sh"
    python3 "$ROOT/tests/check_vm_menus.py"
    bash "$ROOT/install.sh" --check
    for owner in "${owners[@]}"; do
      bash "$ROOT/install.sh" --projects-dir "$PROJECTS" --offline --list-components "$owner"
      bash "$PROJECTS/$owner/install.sh" --export-selection
      if bash "$PROJECTS/$owner/install.sh" --select __invalid_vm_component__; then
        printf 'Invalid component accepted: %s\n' "$owner" >&2
        exit 1
      fi
    done
    ;;
  install-desktop)
    for attempt in 1 2; do
      printf 'Real desktop and skills install: attempt %s\n' "$attempt"
      bash "$ROOT/install.sh" --projects-dir "$PROJECTS" --offline --select programming_prompts,linux_automatic_window_tiling,linux_taskbar_window_count,linux_taskbar_monitor
    done
    ;;
  install-all)
    bash "$ROOT/install.sh" --projects-dir "$PROJECTS" --offline --select programming_prompts,codex,linux_automatic_window_tiling,linux_taskbar_window_count,linux_taskbar_monitor
    ;;
  install-codex)
    for attempt in 1 2; do
      printf 'Real Codex source build and install: attempt %s\n' "$attempt"
      bash "$ROOT/install.sh" --projects-dir "$PROJECTS" --offline --select codex
    done
    ;;
  installed)
    python3 - "$PROJECTS/programming_prompts" <<'PY'
from pathlib import Path
import sys
import json
import hashlib
import subprocess
source = Path(sys.argv[1])
skills = sorted(source.glob('plugins/*/skills/*/SKILL.md')) + sorted(source.glob('skills/*/SKILL.md')) + sorted(source.glob('dispatch-skills/*/SKILL.md'))
assert skills, 'No source skills discovered'
for harness in ('.agents', '.claude'):
    for skill in skills:
        target = Path.home()/harness/'skills'/('mt-stack-'+skill.parent.name)/'SKILL.md'
        assert target.read_bytes() == skill.read_bytes(), str(target)
print(f'PASS: {len(skills)} exact native skills in each harness')
for owner in ('programming_prompts', 'codex', 'linux_automatic_window_tiling', 'linux_taskbar_window_count', 'linux_taskbar_monitor'):
    installer = source.parent/owner/'install.sh'
    listing = subprocess.check_output(['bash', str(installer), '--list-components'], text=True)
    required = {line.split('\t')[0] for line in listing.splitlines() if line.split('\t')[2] == 'on'}
    detected = dict(line.split('\t') for line in subprocess.check_output(['bash', str(installer), '--detect'], text=True).splitlines())
    assert required and all(detected.get(component) in ('1', 'installed') for component in required), (owner, required, detected)
    print(f'PASS: {owner} detects every default component as installed')
receipt = json.loads((Path.home()/'.local/state/codex-fork/installed.json').read_text())
for name in ('codex', 'codex-code-mode-host'):
    binary = Path.home()/'.local/bin'/name
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == receipt[name], name
PY
    for uuid in automatic-window-tiling@local workspace-window-count@local Resource_Monitor@Ory0n; do
      information="$(LC_ALL=C gnome-extensions info "$uuid")"
      printf '%s\n' "$information"
      [[ $information == *'State: ACTIVE'* ]]
    done
    [[ $(gsettings get org.gnome.shell disable-user-extensions) == false ]]
    [[ $(command -v codex) == "$HOME/.local/bin/codex" ]]
    [[ $(command -v codex-code-mode-host) == "$HOME/.local/bin/codex-code-mode-host" ]]
    codex --version
    codex --help
    codex-code-mode-host --help
    python3 "$ROOT/tests/check_vm_code_mode.py"
    env PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin bash -lc 'set -e; test "$(command -v codex)" = "$HOME/.local/bin/codex"; test "$(command -v codex-code-mode-host)" = "$HOME/.local/bin/codex-code-mode-host"; codex --version'
    ;;
  *)
    printf 'Usage: MT_STACK_VM_TEST=1 bash tests/check_vm_stack.sh [discovery|install-desktop|install-codex|install-all|installed]\n' >&2
    exit 2
    ;;
esac
printf 'PASS: VM phase %s\n' "${1:-discovery}"
