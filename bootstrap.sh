#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash bootstrap.sh [repo-name]

Creates your own private copy of the course repo on GitHub, invites your
teammates as collaborators, and prints the URL plus next steps.

Arguments:
  repo-name   Name for your private repo (default: agentic-engineering-course)

Options:
  -h, --help  Show this help message and exit
EOF
}

REPO_NAME="agentic-engineering-course"

for arg in "$@"; do
  case "$arg" in
    -h|--help)
      usage
      exit 0
      ;;
  esac
done

if [ "$#" -gt 0 ]; then
  REPO_NAME="$1"
fi

echo "==> Checking required tools (git, gh)..."
command -v git >/dev/null 2>&1 || { echo "error: git is required but not found" >&2; exit 1; }
command -v gh  >/dev/null 2>&1 || { echo "error: gh (GitHub CLI) is required but not found" >&2; exit 1; }

echo "==> Checking GitHub CLI authentication..."
if ! gh auth status >/dev/null 2>&1; then
  echo "run: gh auth login"
  exit 1
fi

echo "==> Locating the course repo..."
IN_COURSE_CLONE=false
if TOPLEVEL="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  if git -C "$TOPLEVEL" remote -v 2>/dev/null | grep -q "NickGuAI/agentic-engineering-course"; then
    IN_COURSE_CLONE=true
  fi
fi

if [ "$IN_COURSE_CLONE" = true ]; then
  echo "    already inside a clone of the course repo; using it."
  cd "$TOPLEVEL"
else
  echo "    cloning the course repo into ./$REPO_NAME ..."
  git clone https://github.com/NickGuAI/agentic-engineering-course.git "$REPO_NAME"
  cd "$REPO_NAME"
fi

echo "==> Setting up the 'upstream' remote..."
if git remote | grep -qx "upstream"; then
  echo "    'upstream' remote already exists; leaving it as-is."
else
  git remote rename origin upstream
  echo "    renamed 'origin' to 'upstream'."
fi

echo "==> Creating your private GitHub repo..."
ORIGIN_IS_PRIVATE=false
if git remote | grep -qx "origin"; then
  if PRIVATE="$(gh repo view --json isPrivate -q .isPrivate 2>/dev/null)" && [ "$PRIVATE" = "true" ]; then
    ORIGIN_IS_PRIVATE=true
  fi
fi

if [ "$ORIGIN_IS_PRIVATE" = true ]; then
  echo "    'origin' already points to a private repo; pushing instead of creating."
  git push -u origin HEAD
else
  gh repo create "$REPO_NAME" --private --source=. --remote=origin --push
fi

echo "==> Inviting teammates as collaborators..."
for id in NickGuAI arielbenavi thevoid12; do
  if gh api -X PUT "repos/{owner}/{repo}/collaborators/$id" -f permission=push >/dev/null 2>&1; then
    echo "    ok: $id"
  else
    echo "    skipped: $id (invite failed; note the owner cannot invite themself)"
  fi
done

REPO_URL="$(gh repo view --json url -q .url)"
echo ""
echo "$REPO_URL"
echo "Add your teammates: Settings > Collaborators"
echo "Course materials sync daily via GitHub Actions; run 'git pull upstream main' to sync now."
