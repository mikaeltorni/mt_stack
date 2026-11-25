#!/usr/bin/env bash
# Public stack entrypoint; all parsing and installation routing lives in stack.py.
set -euo pipefail
if [[ ${EUID} == 0 && -n ${SUDO_USER:-} && $SUDO_USER != root ]]; then
  exec sudo -H -u "$SUDO_USER" bash "$0" "$@"
fi
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/stack.py" "$@"
