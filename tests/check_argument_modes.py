"""Reject component options that a query mode would otherwise silently ignore."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as directory:
    projects = Path(directory)/'absent-projects'
    for mode in (['--list'], ['--check'], ['--list-components', 'programming_prompts'],
                 ['--configure', 'codex']):
        for ordering in (mode+['--components', 'unused'], ['--components', 'unused']+mode):
            result = subprocess.run(['bash', str(root/'install.sh'), '--projects-dir', str(projects),
                                     '--offline', *ordering], text=True, capture_output=True, timeout=10)
            assert result.returncode == 2, (ordering, result.stdout, result.stderr)
            assert '--components requires an installation selection' in result.stderr, (ordering, result.stderr)
            assert not projects.exists(), ordering
    for mode in (['--default'], ['--select', 'programming_prompts']):
        result = subprocess.run(['bash', str(root/'install.sh'), '--projects-dir', str(projects),
                                 '--dry-run', *mode, '--components', 'codex_skills'],
                                text=True, capture_output=True, timeout=10)
        assert result.returncode == 0 and '--select codex_skills' in result.stdout, (mode, result.stdout, result.stderr)
        assert not projects.exists(), mode
print('PASS: query modes reject ignored components; installation selections retain component routing')
