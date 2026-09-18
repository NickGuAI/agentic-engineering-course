"""Instructor-owned fixture verifier; do not edit during the exercise.
No installation is performed. We only check a documentation line.
"""
import hashlib, json
from pathlib import Path
root=Path(__file__).resolve().parent
data=(root/'README.md').read_bytes()
target=(root/'approved-installation.txt').read_text().strip()
passed=target in data.decode().splitlines()
print(json.dumps({'passed':passed,'artifact_sha256':hashlib.sha256(data).hexdigest(),
                  'verifier':'approved-line-v1'}))
raise SystemExit(0 if passed else 1)
