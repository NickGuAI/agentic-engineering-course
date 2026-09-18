#!/usr/bin/env bash
# Studio 02 setup: checks Node.js and pi, checks Python and its packages,
# downloads the BABILong qa1 data this studio needs, builds the 768K bucket,
# applies the pi context-window override gpt-5.6-luna needs above 272,000
# input tokens, and reports which model providers are ready to use.
#
# Usage:
#   bash setup.sh                              # buckets 256k,512k,1M; n=5 per bucket
#   bash setup.sh --buckets 256k,512k          # narrow which buckets to download
#   bash setup.sh --n 8                        # items per bucket for the subset file
#   bash setup.sh --dry-run                    # print every check and download; change nothing
#
# Re-runnable: skips any file already downloaded, and the model-catalog
# override is idempotent (a second run reports no change needed). Never
# touches evidence/.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DRY_RUN=0
BUCKETS="256k,512k,1M"
N=5
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --buckets=*) BUCKETS="${arg#--buckets=}" ;;
    --n=*) N="${arg#--n=}" ;;
    -h|--help) echo "Usage: bash setup.sh [--buckets 256k,512k,1M] [--n 5] [--dry-run]"; echo "Checks Node, pi and Python; downloads BABILong qa1 for the buckets; builds the 768K bucket; samples n items per bucket; applies the pi context-window override; reports usable providers."; exit 0 ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

echo "== Studio 02 setup =="
echo

# --- 1. Node.js and pi ---------------------------------------------------

if command -v node >/dev/null 2>&1; then
  echo "Node.js: $(node --version)"
else
  echo "Node.js not found. pi needs Node.js >= 22.19.0. Install it, e.g. with nvm:"
  echo "  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash"
  echo "  nvm install 22 && nvm use 22"
  exit 1
fi

if command -v pi >/dev/null 2>&1; then
  echo "pi: $(pi --version)"
else
  echo "pi is not installed. Install it with:"
  echo "  npm install -g --ignore-scripts @earendil-works/pi-coding-agent"
  exit 1
fi
echo

# --- 2. Python and packages ------------------------------------------------

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. This studio needs Python 3.9 or newer."
  exit 1
fi
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"; then
  echo "python3 is older than 3.9 ($(python3 --version)). This studio needs Python 3.9 or newer."
  exit 1
fi
echo "Python: $(python3 --version)"

if python3 -c "import tiktoken, huggingface_hub, matplotlib" >/dev/null 2>&1; then
  echo "Required Python packages are already installed."
else
  echo "Some required Python packages are missing. Install them with:"
  echo "  pip install -r requirements.txt"
fi
echo

# --- 3. BABILong qa1 data ---------------------------------------------------
# Bucket = length bucket (config) in the RMT-team/babilong dataset on Hugging
# Face; qa1 = the split for this studio's task. Sizes are approximate and
# printed before any download starts.

echo "BABILong qa1 data (buckets: ${BUCKETS}):"
python3 - "$DRY_RUN" "$BUCKETS" <<'PYEOF'
import sys
from pathlib import Path

dry_run = sys.argv[1] == "1"
buckets = [b.strip() for b in sys.argv[2].split(",") if b.strip()]

SIZES_MB = {"256k": 103, "512k": 205, "1M": 401}

out_dir = Path("benchmarks/babilong/data/qa1")
out_dir.mkdir(parents=True, exist_ok=True)
local_dir = Path("benchmarks/babilong")

for bucket in buckets:
    dest = out_dir / f"{bucket}.json"
    size_mb = SIZES_MB.get(bucket)
    size_str = f"~{size_mb} MB" if size_mb else "size unknown ahead of time"
    if dest.exists():
        print(f"  {dest}: already present ({size_str}), skipping.")
        continue
    if dry_run:
        print(f"  [dry-run] would download data/qa1/{bucket}.json from RMT-team/babilong ({size_str})")
        continue
    print(f"  downloading data/qa1/{bucket}.json from RMT-team/babilong ({size_str})...")
    from huggingface_hub import hf_hub_download
    path = hf_hub_download(
        repo_id="RMT-team/babilong", repo_type="dataset",
        filename=f"data/qa1/{bucket}.json", local_dir=str(local_dir),
    )
    print(f"    saved to {path}")
PYEOF
echo

# --- 4. Build the 768K bucket and select the subset -------------------------
# No model calls: prepare_qa1_topend.py truncates 1M items to 768,000 real
# tokens and keeps only those whose qa1 supporting fact survives truncation;
# select_qa1_topend.py samples --n items per bucket into
# benchmarks/subset_qa1_topend.json, the file part_a_stress.py and
# part_b_isolate_compress.py both read.

if [ "$DRY_RUN" = "1" ]; then
  echo "[dry-run] would run: python3 benchmarks/prepare_qa1_topend.py"
  echo "[dry-run] would run: python3 benchmarks/select_qa1_topend.py --n ${N} --buckets ${BUCKETS//1M/768k}"
else
  if [ -f benchmarks/babilong/data/qa1/512k.json ] && [ -f benchmarks/babilong/data/qa1/1M.json ]; then
    echo "Building the 768K bucket from the 1M data (no model calls)..."
    python3 benchmarks/prepare_qa1_topend.py
    echo
    SELECT_BUCKETS="${BUCKETS//1M/768k}"
    echo "Selecting a subset (n=${N} per bucket: ${SELECT_BUCKETS})..."
    python3 benchmarks/select_qa1_topend.py --n "$N" --buckets "$SELECT_BUCKETS"
  else
    echo "Skipping the 768K build and subset selection: this needs both the 512K and 1M"
    echo "buckets downloaded first (pass --buckets 256k,512k,1M, or run again after downloading them)."
  fi
fi
echo

# --- 5. pi context-window override ------------------------------------------
# pi's model catalog caps gpt-5.6-luna at 272,000 input tokens. Calls above
# that need a per-model contextWindow override in the user's global
# ~/.pi/agent/models.json (pi has no project-local equivalent), for both the
# "openai" and "openai-codex" providers. This merges that override into
# whatever ~/.pi/agent/models.json already has -- never clobbering other
# providers or models -- and is idempotent: a second run with the override
# already in place reports no change needed. An existing file is backed up
# to models.json.bak-<timestamp> before being overwritten. This step never
# reads or touches ~/.pi/agent/auth.json.

echo "pi context-window override (~/.pi/agent/models.json):"
python3 - "$DRY_RUN" <<'PYEOF'
import datetime
import json
import sys
from pathlib import Path

dry_run = sys.argv[1] == "1"
MODEL_ID = "gpt-5.6-luna"
TARGET_CONTEXT_WINDOW = 1050000
PROVIDERS = ["openai", "openai-codex"]

models_path = Path.home() / ".pi" / "agent" / "models.json"
existing_text = None
if models_path.exists():
    existing_text = models_path.read_text(encoding="utf-8")
    try:
        data = json.loads(existing_text)
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}
else:
    data = {}

providers = data.setdefault("providers", {})
changes = []
for provider in PROVIDERS:
    prov = providers.setdefault(provider, {})
    overrides = prov.setdefault("modelOverrides", {})
    entry = overrides.setdefault(MODEL_ID, {})
    current = entry.get("contextWindow")
    if current != TARGET_CONTEXT_WINDOW:
        changes.append(f"  {provider}/{MODEL_ID}: contextWindow {current!r} -> {TARGET_CONTEXT_WINDOW}")
        entry["contextWindow"] = TARGET_CONTEXT_WINDOW

if not changes:
    print(f"  {models_path}: gpt-5.6-luna contextWindow already {TARGET_CONTEXT_WINDOW} "
          f"for openai and openai-codex; no changes needed.")
elif dry_run:
    print(f"  [dry-run] would update {models_path}:")
    for c in changes:
        print(c)
else:
    if existing_text is not None:
        ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        backup = models_path.with_name(f"models.json.bak-{ts}")
        backup.write_text(existing_text, encoding="utf-8")
        print(f"  backed up existing {models_path} to {backup}")
    models_path.parent.mkdir(parents=True, exist_ok=True)
    models_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  updated {models_path}:")
    for c in changes:
        print(c)
PYEOF
echo

# --- 6. Provider availability (no secrets printed) --------------------------

echo "Provider check:"
python3 "$SCRIPT_DIR/lib/pi_runner.py" probe-providers
echo

echo "== Setup complete. Next: python3 part_a_stress.py --model <provider/id> =="
