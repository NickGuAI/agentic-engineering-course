"""Read one fixed public source and emit acquisition metadata, without grading it.

Run: python3 retrieval-probe.py
Network and publisher responses may differ on a later run. This is an
agent-authored acquisition probe, not a student-authored evaluation harness.
"""
import datetime
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

URL = 'https://openai.com/index/scaling-storage-one-billion-users-part-one/'

with tempfile.TemporaryDirectory(prefix='studio01-http-') as temp:
    body_file = Path(temp) / 'response.body'
    result = subprocess.run(
        ['curl', '--silent', '--show-error', '--max-time', '30',
         '--proto', '=https', '--output', str(body_file),
         '--write-out', '%{http_code}', URL],
        capture_output=True, text=True, check=False,
    )
    body = body_file.read_bytes() if body_file.exists() else b''
    print(json.dumps({
        'stage': 'changed_condition_direct_http_only',
        'observed_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'source_id': 'S001', 'url': URL, 'method': 'curl HTTPS',
        'curl_exit_code': result.returncode,
        'http_status': result.stdout.strip(),
        'response_bytes': len(body),
        'response_sha256': hashlib.sha256(body).hexdigest(),
        'stderr': result.stderr.strip(),
    }))
