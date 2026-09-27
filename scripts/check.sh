#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
cd "${ROOT}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

"${PYTHON}" -m simulation_copilot.build_assets --root "${ROOT}"
"${PYTHON}" -m unittest discover -s tests -v
"${PYTHON}" scripts/evaluate_rag.py --root "${ROOT}" >/dev/null
"${PYTHON}" scripts/public_audit.py --root "${ROOT}"
