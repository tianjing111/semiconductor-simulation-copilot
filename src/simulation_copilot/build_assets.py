from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .memory import build_experiment_cards
from .retrieval import build_index


def build(root: Path) -> dict:
    data_dir = root / "data"
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "knowledge": build_index(root, data_dir / "knowledge_index.jsonl"),
        "experiments": build_experiment_cards(root, data_dir / "experiment_cards.json"),
        "data_policy": "Synthetic public demo data only",
    }
    (data_dir / "asset_manifest.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build public demo assets")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(build(args.root.resolve()), indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()

