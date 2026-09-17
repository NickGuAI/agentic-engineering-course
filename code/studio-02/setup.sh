#!/usr/bin/env bash
# Studio 02 setup: checks pi is installed, downloads and prepares the corpus,
# and reports which model providers are ready to use.
#
# Usage:
#   bash setup.sh              # check only; stop with instructions if pi is missing
#   bash setup.sh --install    # also install pi globally if it is missing
#
# Re-runnable: running this twice does not re-download the PDF or re-split the
# corpus unless corpus/survey.txt is missing, and it never touches evidence/.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

INSTALL=0
for arg in "$@"; do
  case "$arg" in
    --install) INSTALL=1 ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

echo "== Studio 02 setup =="
echo

# --- 1. Node and pi -----------------------------------------------------

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
  if [ "$INSTALL" = "1" ]; then
    echo "pi not found. Installing @earendil-works/pi-coding-agent globally..."
    npm install -g --ignore-scripts @earendil-works/pi-coding-agent
    echo "pi: $(pi --version)"
  else
    echo "pi is not installed."
    echo "Install it with:"
    echo "  npm install -g --ignore-scripts @earendil-works/pi-coding-agent"
    echo "Or re-run this script as: bash setup.sh --install"
    exit 1
  fi
fi
echo

# --- 2. Corpus: download PDF, convert to text, split into sections -----

ARXIV_ID="2507.13334"
PDF="corpus/${ARXIV_ID}v2.pdf"
TXT="corpus/survey.txt"

mkdir -p corpus/sections

if [ ! -f "$TXT" ]; then
  if [ ! -f "$PDF" ]; then
    echo "Downloading arXiv ${ARXIV_ID} (A Survey of Context Engineering for Large Language Models)..."
    DOWNLOADED=0
    if command -v curl >/dev/null 2>&1; then
      if curl -fsSL "https://arxiv.org/pdf/${ARXIV_ID}v2" -o "$PDF"; then DOWNLOADED=1; fi
    elif command -v wget >/dev/null 2>&1; then
      if wget -q "https://arxiv.org/pdf/${ARXIV_ID}v2" -O "$PDF"; then DOWNLOADED=1; fi
    fi
    if [ "$DOWNLOADED" != "1" ]; then
      rm -f "$PDF"
      echo "Download failed (no network, or arXiv unreachable)."
      echo "Place any long plain-text corpus at corpus/survey.txt yourself and re-run this script."
      exit 1
    fi
  fi

  if ! command -v pdftotext >/dev/null 2>&1; then
    echo "pdftotext (poppler-utils) is not installed and is needed to convert the PDF."
    echo "Install it (e.g. 'sudo apt-get install poppler-utils' or 'brew install poppler'),"
    echo "or place any long plain-text corpus at corpus/survey.txt yourself and re-run."
    exit 1
  fi

  echo "Converting PDF to text with pdftotext..."
  pdftotext -layout "$PDF" "$TXT"
fi

if [ ! -f "$TXT" ]; then
  echo "corpus/survey.txt is still missing. Place any long plain-text corpus there and re-run."
  exit 1
fi

echo "Splitting corpus into ~12,000-word sections (corpus/sections/section-NN.txt)..."
python3 "$SCRIPT_DIR/lib/pi_runner.py" split-sections "$TXT" corpus/sections 12000
echo

# --- 3. Word / token counts ---------------------------------------------

echo "Corpus size:"
python3 "$SCRIPT_DIR/lib/pi_runner.py" corpus-stats "$TXT" corpus/sections
echo

# --- 4. Provider availability (no secrets printed) ----------------------

echo "Provider check:"
python3 "$SCRIPT_DIR/lib/pi_runner.py" probe-providers
echo

echo "== Setup complete. Next: python3 part_a_stress.py --model <provider/id> =="
