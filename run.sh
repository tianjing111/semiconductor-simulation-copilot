#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8765}"

python_is_compatible() {
  "$1" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' >/dev/null 2>&1
}

if ! python_is_compatible "${PYTHON}"; then
  configured_python="${PYTHON}"
  PYTHON=""
  for candidate in python3.11 python3.12 python3; do
    if python_is_compatible "${candidate}"; then
      PYTHON="${candidate}"
      break
    fi
  done
  if [[ -z "${PYTHON}" ]]; then
    echo "Python 3.11+ is required; '${configured_python}' is unavailable or incompatible." >&2
    exit 1
  fi
  echo "Using ${PYTHON}; configured interpreter '${configured_python}' is unavailable or incompatible." >&2
fi

cd "${ROOT}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

if [[ ! -s data/knowledge_index.jsonl || ! -s data/experiment_cards.json ]]; then
  "${PYTHON}" -m simulation_copilot.build_assets --root "${ROOT}"
fi

exec "${PYTHON}" -m simulation_copilot.server --root "${ROOT}" --host "${HOST}" --port "${PORT}"
