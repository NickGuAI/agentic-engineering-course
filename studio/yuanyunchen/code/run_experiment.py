#!/usr/bin/env python3
"""Reproduce a baseline, missing-source stop, and corrected run, with assertions."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'
runner=ROOT/'code/course_assistant.py'
missing=OUT/'missing-inputs'
missing.mkdir(exist_ok=False)
for name in ['Studio01.md','course-prep.md']:
    shutil.copy2(ROOT/'inputs'/name,missing/name)

def invoke(label,inputs):
    cmd=[sys.executable,str(runner),'--inputs',str(inputs),'--out',str(OUT/label)]
    p=subprocess.run(cmd,text=True,capture_output=True)
    (OUT/(label+'-process.json')).write_text(json.dumps({'command':['python3','code/course_assistant.py','--inputs',str(inputs.relative_to(ROOT)),'--out','outputs/'+label], 'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr},indent=2)+'\n')
    return p.returncode

assert invoke('missing-input',missing)==2
blocked=json.loads((OUT/'missing-input/result.json').read_text())
assert blocked=={'status':'blocked','reason':'missing_input','file':'workspace.md'}
assert not (OUT/'missing-input/digest.md').exists()
# Evidence-led correction: restore the one file identified by the blocked result,
# from the pinned source snapshot, then rerun the same job.
shutil.copy2(ROOT/'inputs'/blocked['file'],missing/blocked['file'])
assert invoke('recovered',missing)==0
assert (OUT/'baseline/digest.md').read_bytes()==(OUT/'recovered/digest.md').read_bytes()
# Preserve the perturbed input condition as well as the corrected run evidence.
(missing/'workspace.md').unlink()
comparison={
    'baseline':json.loads((OUT/'baseline/result.json').read_text()),
    'perturbation':'Removed workspace.md from a separate copy of the declared inputs.',
    'observed':blocked,
    'correction':'Restored only workspace.md from the source-pinned original; no verifier or source pin was changed.',
    'recovered':json.loads((OUT/'recovered/result.json').read_text()),
    'checks':{'missing_run_nonzero':True,'no_digest_on_failure':True,'recovery_success':True,'recovered_digest_equals_baseline':True},
    'authorship':'Machine-generated experiment evidence, not the student personal explanation.'
}
(OUT/'comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
print(json.dumps(comparison,indent=2))
