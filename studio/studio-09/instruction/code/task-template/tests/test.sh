#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
# No reward is written when the API or verifier fails: Harbor records an error.
python /tests/judge.py
