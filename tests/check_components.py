"""Check central discovery and component selection delegate to external owners."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

root=Path(__file__).resolve().parents[1]
rows=json.loads((root/'repositories.json').read_text())
with tempfile.TemporaryDirectory() as directory:
    temp=Path(directory)
    projects=temp/'projects'
    projects.mkdir()
    for row in rows:
        checkout=projects/row['name']
        subprocess.run(['git','init','-q',str(checkout)],check=True)
        subprocess.run(['git','-C',str(checkout),'remote','add','origin',row['source']+'.git'],check=True)
        (checkout/'install.sh').write_text('#!/bin/sh\ncase "$1" in --list-components) printf "skills\\tNative skills\\ton\\n";; *) printf "%s\\n" "$*" >> "$HUB_CALLS";; esac\n')
    env=dict(os.environ,HUB_CALLS=str(temp/'calls'))
    result=subprocess.run(['bash',str(root/'install.sh'),'--projects-dir',str(projects),'--list-components','programming_prompts'],env=env,text=True,capture_output=True)
    assert result.returncode==0 and 'skills\tNative skills' in result.stdout,result.stderr
    assert not (temp/'calls').exists()
    result=subprocess.run(['bash',str(root/'install.sh'),'--projects-dir',str(projects),'--select','programming_prompts','--components','skills'],env=env,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    assert (temp/'calls').read_text()=='--select skills\n'
    for args in (['--select','programming_prompts','--components','unknown'],['--select','programming_prompts,codex','--components','skills'],['--select','codex','--components','skills,skills']):
        result=subprocess.run(['bash',str(root/'install.sh'),'--projects-dir',str(projects),*args],env=env,text=True,capture_output=True)
        assert result.returncode!=0 and (temp/'calls').read_text()=='--select skills\n',(args,result.stdout,result.stderr)
    result=subprocess.run(['bash',str(root/'install.sh'),'--projects-dir',str(projects),'--configure','codex','--dry-run'],env=env,text=True,capture_output=True)
    assert result.returncode==0 and str(projects/'codex/install.sh') in result.stdout,result.stderr
    assert (temp/'calls').read_text()=='--select skills\n'
    result=subprocess.run(['bash',str(root/'install.sh'),'--projects-dir',str(projects),'--select','codex','--components',''],env=env,text=True,capture_output=True)
    assert result.returncode==0 and (temp/'calls').read_text()=='--select skills\n--select \n',(result.stdout,result.stderr)
print('PASS: central component discovery, exact owner selection, rejected-state preservation and owner menu preview')
