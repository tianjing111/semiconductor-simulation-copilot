#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 GITHUB_USERNAME" >&2
  exit 2
fi

USERNAME="$1"
if [[ ! "${USERNAME}" =~ ^[A-Za-z0-9-]+$ ]]; then
  echo "GitHub username may contain only letters, numbers and hyphens." >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

sed -i "s#YOUR_USERNAME#${USERNAME}#g" README.md docs/PUBLISHING.md
./scripts/check.sh
./scripts/update_release_manifest.sh >/dev/null

if [[ ! -d .git ]]; then
  git init -b main
fi

git add .

echo
echo "Repository prepared for review. No commit or network push was performed."
echo "Review the staged files below before committing:"
git status --short
