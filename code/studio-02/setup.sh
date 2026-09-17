#!/usr/bin/env bash
# Studio 02 setup: checks pi is installed, downloads and prepares the corpus
# (both the single-survey corpus used by Part A/B/C, and the 13-document
# combined corpus used by context_sweep.py), and reports which model
# providers are ready to use.
#
# Usage:
#   bash setup.sh              # check only; stop with instructions if pi is missing
#   bash setup.sh --install    # also install pi globally if it is missing
#
# Re-runnable: running this twice does not re-download or re-convert any PDF
# already present, and it never touches evidence/.
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

# --- 2. Corpus: download PDF, convert to text --------------------------

ARXIV_ID="2507.13334"
PDF="corpus/${ARXIV_ID}v2.pdf"
TXT="corpus/survey.txt"

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

# --- 3. Word / token counts (survey only) -------------------------------

echo "Corpus size (survey only, corpus/survey.txt):"
python3 "$SCRIPT_DIR/lib/pi_runner.py" corpus-stats "$TXT"
echo

# --- 4. Provider availability (no secrets printed) ----------------------

echo "Provider check:"
python3 "$SCRIPT_DIR/lib/pi_runner.py" probe-providers
echo

# --- 5. Combined 13-document corpus (contract addendum v2) -------------
# Document 1 is the survey handled above (corpus/survey.txt). Documents 2-13
# are additional arXiv papers used only as bulk length and distractor text
# for the accuracy-vs-context-length sweep (context_sweep.py); none of the
# five original quiz questions depend on them. Same idempotent pattern as
# above: skip downloading/converting whatever is already present.

NOISE_IDS=(2307.03172 2310.08560 2510.04618 2404.06654 2410.10813 2210.03629 2005.11401 2304.03442 2502.05167 2504.19413 2005.14165 2403.05530)

echo "Combined corpus (13 documents for context_sweep.py):"
for id in "${NOISE_IDS[@]}"; do
  DOC_TXT="corpus/${id}.txt"
  DOC_PDF="corpus/${id}.pdf"
  if [ ! -f "$DOC_TXT" ]; then
    if [ ! -f "$DOC_PDF" ]; then
      echo "  downloading arXiv ${id}..."
      DOWNLOADED=0
      if command -v curl >/dev/null 2>&1; then
        if curl -fsSL "https://arxiv.org/pdf/${id}" -o "$DOC_PDF"; then DOWNLOADED=1; fi
      elif command -v wget >/dev/null 2>&1; then
        if wget -q "https://arxiv.org/pdf/${id}" -O "$DOC_PDF"; then DOWNLOADED=1; fi
      fi
      if [ "$DOWNLOADED" != "1" ]; then
        rm -f "$DOC_PDF"
        echo "  download of ${id} failed (no network, or arXiv unreachable)."
        echo "  Place the PDF yourself at corpus/${id}.pdf and re-run this script, or skip the"
        echo "  combined corpus and context_sweep.py for now -- setup.sh still succeeds otherwise."
        exit 1
      fi
    fi
    if ! command -v pdftotext >/dev/null 2>&1; then
      echo "  pdftotext (poppler-utils) is not installed; cannot convert ${id}.pdf."
      exit 1
    fi
    pdftotext -layout "$DOC_PDF" "$DOC_TXT"
  fi
done

python3 "$SCRIPT_DIR/lib/pi_runner.py" build-combined-corpus corpus corpus/combined.txt corpus/manifest.json
echo

# --- 6. Part B sections: ~30K-real-token chunks of combined.txt --------
# (contract addendum v2 section 7). Part B's isolate step and compaction
# demo both just glob corpus/sections/section-*.txt, so this directory is
# fully repurposed from the original ~12,000-word survey-only chunks to
# ~30,000-real-token chunks of the 13-document combined corpus; nothing
# else depends on the old chunking.

echo "Part B sections (corpus/sections/section-NN.txt, ~30,000 real tokens each):"
python3 "$SCRIPT_DIR/lib/pi_runner.py" split-sections-real-tokens corpus/combined.txt corpus/sections 30000
echo

echo "== Setup complete. Next: python3 part_a_stress.py --model <provider/id> =="
