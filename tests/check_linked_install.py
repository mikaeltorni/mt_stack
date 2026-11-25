"""Regress the hub's external public checkout boundary through its CLI."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
assert not (root/'repositories').exists(), 'hub must not embed project copies'
rows = json.loads((root/'repositories.json').read_text())
assert len(rows) == 12 and all(row['visibility']=='public' for row in rows)
with tempfile.TemporaryDirectory() as directory:
    temporary = Path(directory)
    projects = temporary/'projects with spaces'
    projects.mkdir()
    for row in rows:
        checkout = projects/row['name']
        checkout.mkdir()
        subprocess.run(['git','init','-q',str(checkout)],check=True)
        subprocess.run(['git','-C',str(checkout),'remote','add','origin',row['source']+'.git'],check=True)
        (checkout/'install.sh').write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$HUB_CALLS"\n')
    env = dict(os.environ, HUB_CALLS=str(temporary/'calls'))
    result = subprocess.run(['bash',str(root/'install.sh'),'--projects-dir',str(projects),'--select','programming_prompts'],env=env,text=True,capture_output=True)
    assert result.returncode == 0, result.stderr
    assert (temporary/'calls').read_text()=='--default\n'
    owner_installer = projects/'programming_prompts/install.sh'
    original = owner_installer.read_text()
    owner_installer.write_text(
        '#!/bin/sh\nprintf "%s %s <%s>\\n" "$INSTALLER_NO_REBOOT" "$ISC_NO_REBOOT" "$*" >> "$HUB_CALLS"\n'
    )
    (temporary/'calls').write_text('')
    commands = (
        (['--select', 'programming_prompts'], '--default'),
        (['--configure', 'programming_prompts'], ''),
    )
    for arguments, expected in commands:
        inv_env = dict(env, INSTALLER_NO_REBOOT='0', ISC_NO_REBOOT='0')
        result = subprocess.run(
            ['bash', str(root/'install.sh'), '--projects-dir', str(projects), *arguments],
            env=inv_env, text=True, capture_output=True,
        )
        assert result.returncode == 0, (arguments, result.stderr)
        assert (temporary/'calls').read_text().splitlines()[-1] == f'1 1 <{expected}>', (
            arguments, (temporary/'calls').read_text()
        )
    owner_installer.write_text(original)
    before = (temporary/'calls').read_bytes()
    for args in (['--select','unknown'],['--select',''],['--select','codex,codex'],['--projects-dir',str(root/'nested'),'--select','codex']):
        result = subprocess.run(['bash',str(root/'install.sh'),'--projects-dir',str(projects),*args],env=env,text=True,capture_output=True)
        assert result.returncode != 0, (args,result.stdout)
        assert (temporary/'calls').read_bytes()==before
    result = subprocess.run(['bash',str(root/'install.sh'),'--projects-dir',str(projects),'--select','codex','--dry-run'],env=env,text=True,capture_output=True)
    assert result.returncode==0 and str(projects/'codex') in result.stdout, result.stderr
    assert (temporary/'calls').read_bytes()==before
    subprocess.run(['git','-C',str(projects/'codex'),'remote','set-url','origin','https://github.com/mikaeltorni/notes.git'],check=True)
    result = subprocess.run(['bash',str(root/'install.sh'),'--projects-dir',str(projects),'--select','codex'],env=env,text=True,capture_output=True)
    assert result.returncode != 0 and (temporary/'calls').read_bytes()==before, result.stderr
print('PASS: public-only linked checkouts, external install routing, safe dry run, invalid names/paths/origins preserve state')

# Exercise real Git clone routing using isolated public-URL-to-local fixtures.
with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    seed = temp/'seed'
    subprocess.run(['git','init','-q','-b','master',str(seed)],check=True)
    (seed/'install.sh').write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$HUB_CALLS"\n')
    subprocess.run(['git','-C',str(seed),'add','install.sh'],check=True)
    subprocess.run(['git','-C',str(seed),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','installer fixture'],check=True)
    remote = temp/'remotes/programming_prompts.git'
    remote.parent.mkdir()
    subprocess.run(['git','clone','--bare','-q',str(seed),str(remote)],check=True)
    config = temp/'gitconfig'
    subprocess.run(['git','config','--file',str(config),'url.'+remote.parent.as_uri()+'/.insteadOf','https://github.com/mikaeltorni/'],check=True)
    projects = temp/'fresh-projects'
    env = dict(os.environ,GIT_CONFIG_GLOBAL=str(config),HUB_CALLS=str(temp/'calls'))
    result = subprocess.run(['bash',str(root/'install.sh'),'--projects-dir',str(projects),'--select','programming_prompts','--offline'],env=env,text=True,capture_output=True)
    assert result.returncode != 0 and not projects.exists(), result.stderr
    for attempt in range(2):
        result = subprocess.run(['bash',str(root/'install.sh'),'--projects-dir',str(projects),'--select','programming_prompts'],env=env,text=True,capture_output=True)
        assert result.returncode == 0, result.stderr
    assert (temp/'calls').read_text() == '--default\n--default\n'
    assert (projects/'programming_prompts/.git').is_dir()
print('PASS: fresh public-URL clone, offline rejection and unchanged checkout reuse')
