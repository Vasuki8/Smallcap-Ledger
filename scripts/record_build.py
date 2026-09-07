"""Commit a compact, meaningful collection audit after each scheduled build."""
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
report=json.loads((ROOT/'site/data/status.json').read_text())
target=ROOT/'deployment/update-status.json';target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps({'built_at':report['server_time'],'counts':report['counts'],'recent_jobs':[{k:j[k] for k in ('kind','started_at','finished_at','status')} for j in report['jobs'][:4]],'schedule':report['hosting']},indent=2)+'\n')
def git(*args,check=True):return subprocess.run(['git',*args],cwd=ROOT,check=check)
git('config','user.name','github-actions[bot]');git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
git('add','deployment/update-status.json')
if git('diff','--cached','--quiet',check=False).returncode:
    git('commit','-m','Record daily collection status [skip ci]')
    git('pull','--rebase','origin','main')
    git('push','origin','HEAD:main')
