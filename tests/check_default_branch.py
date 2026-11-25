"""Verify the live hub default branch remains master from a linked worktree."""
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
common=subprocess.check_output(['git','-C',str(root),'rev-parse','--git-common-dir'],text=True).strip()
common=(root/common).resolve()
branch=subprocess.check_output(['git','--git-dir',str(common),'symbolic-ref','--short','HEAD'],text=True).strip()
assert branch=='master',branch
print('PASS: hub default branch is master')
