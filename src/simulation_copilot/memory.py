from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .retrieval import sha256_file, tokens


def build_experiment_cards(root: Path, out_path: Path) -> dict[str, Any]:
    cards = []
    for path in sorted((root / "examples" / "experiments").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        relative = str(path.relative_to(root))
        cards.append({
            "experiment_id": hashlib.sha256(relative.encode("utf-8")).hexdigest()[:12],
            "title": payload["title"],
            "category": payload["category"],
            "status": payload["status"],
            "purpose": payload["purpose"],
            "configuration": payload["configuration"],
            "metrics": payload["metrics"],
            "source": relative,
            "source_sha256": sha256_file(path),
            "synthetic": True,
        })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(cards, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return {"card_count": len(cards), "path": str(out_path.relative_to(root))}


class ExperimentMemory:
    def __init__(self, path: Path) -> None:
        self.cards = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []

    def search(self, query: str = "", limit: int = 40) -> list[dict[str, Any]]:
        terms = tokens(query)
        rows = []
        for card in self.cards:
            haystack = json.dumps(card, ensure_ascii=True).lower()
            if terms and not all(term in haystack for term in terms):
                continue
            rows.append(card)
            if len(rows) >= max(1, min(limit, 100)):
                break
        return rows

