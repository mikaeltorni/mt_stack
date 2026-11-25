#!/usr/bin/env bash
# Test hub orchestration using external fixtures, without installing desktop software.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3 tests/check_linked_install.py
python3 tests/check_menus.py
python3 tests/check_components.py
python3 tests/check_argument_modes.py
python3 tests/check_default_branch.py
python3 tests/check_installer_policy.py
python3 tests/check_shared_menu.py
python3 tests/check_lifecycle.py
python3 tests/check_workstation.py
python3 tests/check_workstation_fetch.py
bash -n install.sh tests/run_tests.sh
