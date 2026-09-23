#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

find . -type f \
  -not -path './.git/*' \
  -not -path './data/*' \
  -not -path '*/__pycache__/*' \
  -not -name 'PUBLIC_RELEASE_MANIFEST.sha256' \
  -print0 \
  | sort -z \
  | xargs -0 sha256sum \
  > PUBLIC_RELEASE_MANIFEST.sha256

sha256sum -c PUBLIC_RELEASE_MANIFEST.sha256

