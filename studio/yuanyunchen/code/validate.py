#!/usr/bin/env python3
"""Check real output provenance and failure boundaries independently of rendering."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'sources.json').read_text())
checks={}
checks['source_hashes_match']=all(hashlib.sha256((ROOT/'inputs'/n).read_bytes()).hexdigest()==v['sha256'] for n,v in manifest['sources'].items())
digest=(ROOT/'outputs/baseline/digest.md').read_text()
citations=re.findall(r'\[([^\]:]+):(\d+)\]\(([^)]+)\)',digest)
checks['all_citations_resolve']=bool(citations) and all(n in manifest['sources'] and url==manifest['sources'][n]['url']+'#L'+line and 1<=int(line)<=len((ROOT/'inputs'/n).read_text().splitlines()) for n,line,url in citations)
checks['card_exactly_four_fields']=re.findall(r'^## (.+)$',(ROOT/'delegation-card.md').read_text(),re.M)==['Task','Context','Success criteria','Restrictions']
checks['missing_input_has_no_digest']=not (ROOT/'outputs/missing-input/digest.md').exists()
checks['recovery_matches_baseline']=(ROOT/'outputs/baseline/digest.md').read_bytes()==(ROOT/'outputs/recovered/digest.md').read_bytes()
# Authorship is not inferable from file existence; only check honest disclosure.
checks['reflection_draft_disclosed']='AI-assisted draft; this does not fulfill' in (ROOT/'explanation-yuanyunchen.md').read_text()
runner=ROOT/'code/course_assistant.py'
with tempfile.TemporaryDirectory(dir=ROOT/'outputs',prefix='validation-') as tmp:
    tmp=Path(tmp); inputs=tmp/'inputs';shutil.copytree(ROOT/'inputs',inputs)
    with (inputs/'Studio01.md').open('a') as f:f.write('\nUnexpected source update\n')
    changed=subprocess.run([sys.executable,str(runner),'--inputs',str(inputs),'--out',str(tmp/'changed')],capture_output=True)
    result=json.loads((tmp/'changed/result.json').read_text())
    checks['changed_source_stops']=changed.returncode==2 and result['reason']=='source_changed' and not (tmp/'changed/digest.md').exists()
    stale=tmp/'existing';stale.mkdir();(stale/'digest.md').write_text('old artifact')
    reused=subprocess.run([sys.executable,str(runner),'--out',str(stale)],capture_output=True)
    checks['existing_run_rejected']=reused.returncode!=0 and (stale/'digest.md').read_text()=='old artifact'
report={'checks':checks,'citation_count':len(citations),'passed':all(checks.values()),'scope':'Technical evidence only; does not verify student authorship or complete submission.'}
(ROOT/'outputs/validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
