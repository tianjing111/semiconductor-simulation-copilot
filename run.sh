#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8765}"

cd "${ROOT}"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

if [[ ! -s data/knowledge_index.jsonl || ! -s data/experiment_cards.json ]]; then
  "${PYTHON}" -m simulation_copilot.build_assets --root "${ROOT}"
fi

exec "${PYTHON}" -m simulation_copilot.server --root "${ROOT}" --host "${HOST}" --port "${PORT}"

