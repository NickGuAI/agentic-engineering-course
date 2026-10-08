#!/usr/bin/env python3
"""Offline, source-pinned study digest assembled by local Codex; no runtime LLM."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def run(input_dir, output_dir):
    input_dir, output_dir = input_dir.resolve(), output_dir.resolve()
    if not input_dir.is_relative_to(ROOT) or not output_dir.is_relative_to(ROOT / 'outputs'):
        raise ValueError('Inputs must stay in student folder; outputs must stay in its outputs directory')
    output_dir.mkdir(parents=True, exist_ok=False)
    def event(kind, **details):
        with (output_dir / 'trace.jsonl').open('a') as f:
            f.write(json.dumps({'time_utc': datetime.now(timezone.utc).isoformat(), 'event': kind, **details}) + '\n')
    event('start', runner='offline deterministic renderer', inputs=str(input_dir.relative_to(ROOT)))
    manifest = json.loads((ROOT / 'sources.json').read_text())
    sources = {}
    for name, meta in manifest['sources'].items():
        p = input_dir / name
        if not p.is_file():
            event('stop', reason='missing_input', file=name)
            (output_dir / 'result.json').write_text(json.dumps({'status':'blocked','reason':'missing_input','file':name}, indent=2)+'\n')
            return 2
        content = p.read_bytes()
        if sha(content) != meta['sha256']:
            event('stop', reason='source_changed', file=name, observed_sha256=sha(content))
            (output_dir / 'result.json').write_text(json.dumps({'status':'blocked','reason':'source_changed','file':name}, indent=2)+'\n')
            return 2
        sources[name] = content.decode()
        event('source_verified', file=name, sha256=sha(content))
    def cite(name, phrase):
        lines = sources[name].splitlines()
        matches = [i+1 for i,line in enumerate(lines) if phrase in line]
        if len(matches)!=1:
            raise ValueError('Ambiguous or missing citation: '+phrase)
        line=matches[0]
        return '['+name+':'+str(line)+']('+manifest['sources'][name]['url']+'#L'+str(line)+')'
    c=lambda phrase: cite('Studio01.md', phrase)
    w=lambda phrase: cite('workspace.md', phrase)
    p=lambda phrase: cite('course-prep.md', phrase)
    text=f'''# Studio 01 study digest

Generated from pinned public materials. This is an AI-assisted learning artifact, not the student's personal explanation.

## The workflow

```text
FRAME              RUN & INSPECT        CHANGE & EXPLAIN
four-field card -> bounded local run -> change one condition
                       |                        |
                 output + trace        compare evidence -> correct or stop
```

The workshop follows these three phases. {c('## 1. Frame')} {c('## 2. Run & Inspect')} {c('## 3. Change & Explain')}

## What to do

| Step | Concrete action | Evidence to retain |
|---|---|---|
| Define | Choose Research Update or Course Assistant and fill the delegation card | Completed card |
| Execute | Run local Codex or Claude Code using your own account | Output and execution trace |
| Perturb | Change one condition, inspect the result, then correct or stop | Before/after comparison |

Sources: {c('Research Update:')} {c('Course Assistant:')} {c('Run local Codex')} {c('Change one condition')}

### Keep the delegation precise

Use exactly **Task, Context, Success criteria, Restrictions**. {w('exactly four fields')}

Learning example (assistant-created, not a course requirement): “Turn these three files into a study digest; every requirement needs a source; if one file is missing, report the missing filename and stop.” This is more testable than “help me study” because a reader can check both success and refusal to proceed.

### Submission checklist

- Keep work directly under `studio/<username-or-team>/`, not a `studio-01` subfolder. {w('Do not create a')}
- Preserve code, outputs, and the completed card. {c('Preserve all code')}
- Each student personally writes a separate `explanation-<username>.md`, without AI-generated text. {w('by hand (no AI-generated text)')}
- Use a dedicated non-main working branch and a PR to the course repository's `main`. {w('dedicated non-main')} {w('Open a PR targeting')}
- Delete the working branch only after confirming a successful merge; preserve unmerged work. {w('After confirming a successful merge')}
- Check CourseWorks for official submission instructions and deadlines. No deadline is supplied by these inputs. {w('CourseWorks remains')}

## Preparation check

The listed accounts are GitHub, ChatGPT, Gemini, and Tavily. {p('**GitHub**:')} {p('**ChatGPT**:')} {p('**Gemini**:')} {p('**Tavily**:')}

Python 3.11+ and Git are required; no GPU is required. {p('Ensure you have Python')}
The preparation guide says there is no coding assignment *before the first class*. This does not waive the separate Studio 01 deliverables. {p('Before our first class')}

## Self-check (assistant-created study questions)

1. Why is an output alone insufficient to understand an agent run?
2. What should happen if one required source is missing?
3. Which part of this studio must not be written by the agent?

<details><summary>Check your understanding</summary>

1. The trace shows what inputs and checks produced the output, so a plausible-looking result can be inspected rather than trusted blindly. This is a learning interpretation of Run & Inspect.
2. In this assistant's delegation contract, stop and name the missing input. The workshop itself also allows a responsible stop; this specific behavior is our implementation choice.
3. The student's separate personal explanation. Inspect the evidence and write it yourself.

</details>

## Scope and uncertainty

This small offline renderer is intentionally limited to these pinned Studio 01 materials. It does not claim to summarize lectures not provided, infer grades, discover deadlines, or measure LLM quality. Updating a source requires reviewing the content and its citation phrases before updating the pin; blindly accepting new hashes is not a correction.
'''
    digest=text.encode()
    (output_dir/'digest.md').write_bytes(digest)
    result={'status':'success','source_count':len(sources),'digest_sha256':sha(digest),'network_calls':0}
    (output_dir/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    event('digest_written',sha256=sha(digest),bytes=len(digest))
    event('complete',status='success')
    return 0

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,default=ROOT/'inputs')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    raise SystemExit(run(args.inputs,args.out))
