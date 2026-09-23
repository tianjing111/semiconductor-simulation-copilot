from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_./+-]{2,}")
STOP_WORDS = {"and", "are", "for", "from", "into", "not", "the", "this", "that", "was", "with"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text) if token.lower() not in STOP_WORDS]


def chunks(text: str, size: int = 1800, overlap: int = 220) -> Iterable[str]:
    text = text.replace("\x00", " ").strip()
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = max(text.rfind("\n\n", start, end), text.rfind("\n", start, end))
            if boundary > start + size // 2:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            yield chunk
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)


def build_index(root: Path, out_path: Path) -> dict[str, Any]:
    roots = [root / "docs", root / "examples", root / "src"]
    files = []
    for source_root in roots:
        if source_root.is_dir():
            files.extend(path for path in source_root.rglob("*") if path.is_file())
    files = sorted(path for path in files if path.suffix.lower() in {".md", ".txt", ".log", ".json", ".yaml", ".py"})
    rows = []
    for path in files:
        if path.stat().st_size > 2 * 1024 * 1024:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        sha = sha256_file(path)
        relative = str(path.relative_to(root))
        source_type = "synthetic_log" if "examples/logs" in relative else (
            "documentation" if path.suffix == ".md" else "project_source"
        )
        for index, chunk in enumerate(chunks(text)):
            rows.append({
                "chunk_id": f"{sha[:12]}:{index}",
                "path": relative,
                "title": path.stem.replace("_", " ").replace("-", " ").title(),
                "source_type": source_type,
                "sha256": sha,
                "text": chunk,
            })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(json.dumps(row, ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")
    return {"source_count": len(files), "chunk_count": len(rows), "path": str(out_path.relative_to(root))}


class EvidenceIndex:
    def __init__(self, path: Path) -> None:
        self.rows = []
        if path.is_file():
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(row, dict):
                        self.rows.append(row)

    def search(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        query_terms = list(dict.fromkeys(tokens(query)))[:32]
        if not query_terms:
            return []
        scored = []
        for row in self.rows:
            text = str(row.get("text", ""))
            lowered = text.lower()
            path_text = f"{row.get('path', '')} {row.get('title', '')}".lower()
            matched = [term for term in query_terms if term in lowered or term in path_text]
            if not matched:
                continue
            score = sum(min(4, lowered.count(term)) + (3 if term in path_text else 0) + 1 / math.sqrt(len(term)) for term in matched)
            positions = [lowered.find(term) for term in matched if lowered.find(term) >= 0]
            start = max(0, (min(positions) if positions else 0) - 140)
            excerpt = re.sub(r"\s+", " ", text[start:start + 620]).strip()
            scored.append({
                "score": round(score, 3), "title": row.get("title"), "path": row.get("path"),
                "source_type": row.get("source_type"), "sha256": row.get("sha256"),
                "matched_terms": matched[:8], "excerpt": excerpt,
            })
        scored.sort(key=lambda item: (-item["score"], item["path"]))
        unique, seen = [], set()
        for item in scored:
            if item["path"] in seen:
                continue
            seen.add(item["path"])
            unique.append(item)
            if len(unique) >= max(1, min(limit, 12)):
                break
        return unique

