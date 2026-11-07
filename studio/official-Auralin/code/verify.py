#!/usr/bin/env python3
"""Run offline checks and export reviewed local run evidence for the studio folder."""
import io
import json
from pathlib import Path
import re
import sys
import unittest

import agent


def main():
    output = agent.ROOT / 'outputs/verification'
    suite = unittest.defaultTestLoader.discover(str(agent.ROOT / 'code/tests'))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    agent.atomic(output / 'tests.txt', stream.getvalue())
    agent.write_json(output / 'checks.json', dict(at=agent.now(), passed=result.wasSuccessful(),
                     tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                     evidence='Synthetic fixtures validate harness behavior, not model quality.'))
    print(stream.getvalue())
    for run_id in sys.argv[1:]:
        if not re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{8}', run_id):
            raise ValueError('Invalid run ID')
        run = agent.ROOT / 'outputs/live/runs' / run_id
        record = json.loads((run / 'result.json').read_text())
        record['digest'] = run_id + '.md'
        record['model_called'] = (run / 'model-trace.jsonl').exists()
        if record['model_called']:
            model_events = [json.loads(line) for line in (run / 'model-trace.jsonl').read_text().splitlines()]
            record['model_item_types'] = [e['item']['type'] for e in model_events if e['type'] == 'item.completed']
            record['model_usage'] = [e.get('usage') for e in model_events if e['type'] == 'turn.completed']
        agent.write_json(output / (run_id + '.json'), record)
        agent.atomic(output / (run_id + '.md'), (run / 'digest.md').read_text())
        agent.atomic(output / (run_id + '.jsonl'), (run / 'trace.jsonl').read_text())
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
