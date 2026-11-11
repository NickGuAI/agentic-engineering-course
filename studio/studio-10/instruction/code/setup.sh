#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [[ $# -gt 1 || ( $# -eq 1 && $1 != --dry-run ) ]]; then
  echo 'Usage: bash setup.sh [--dry-run]' >&2
  exit 2
fi
python_bin="${PYTHON:-python3.12}"
venv_dir="${VENV_DIR:-.venv}"
if [[ ${1:-} == --dry-run ]]; then
  printf '%q -m venv %q\n' "$python_bin" "$venv_dir"
  printf '%q -m pip install -r requirements.txt\n' "$venv_dir/bin/python"
  exit 0
fi
"$python_bin" -m venv "$venv_dir"
"$venv_dir/bin/python" -m pip install -r requirements.txt
printf 'Activate with: source %q/bin/activate\n' "$venv_dir"
