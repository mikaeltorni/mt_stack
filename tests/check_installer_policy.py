"""Require the shared installer protocol at the hub's admission boundary."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
text = (root / 'AGENTS.md').read_text()
for requirement in ('## Installer framework contract', '--list-components', '--select', '--uninstall', '--reconfigure', '--detect', '--export-selection', 'same operations', 'generated', 'private download'):
    assert requirement in text, requirement
assert 'Never push' in text and 'private candidates' in text
print('PASS: framework compatibility, menu/CLI parity and private-public boundary documented')
