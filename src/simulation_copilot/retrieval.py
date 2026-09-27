from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_./+-]{2,}")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
STOP_WORDS = {
    "a", "an", "and", "are", "be", "can", "did", "do", "does", "for", "from",
    "how", "i", "in", "into", "is", "it", "may", "my", "not", "of", "on", "or",
    "public", "demo", "demonstration", "should", "synthetic", "the", "this", "that",
    "to", "was", "what", "when", "which", "why", "with", "would",
}


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


def section_chunks(path: Path, text: str) -> Iterable[tuple[str, int, str]]:
    """Split Markdown on headings, then apply bounded chunks within a section."""
    if path.suffix.lower() != ".md":
        yield from (("Document", 0, chunk) for chunk in chunks(text))
        return
    section = "Document"
    heading_level = 0
    lines: list[str] = []

    def flush() -> Iterable[tuple[str, int, str]]:
        body = "\n".join(lines).strip()
        if body:
            yield from ((section, heading_level, chunk) for chunk in chunks(body))

    for line in text.splitlines():
        match = HEADING_PATTERN.match(line)
        if match:
            yield from flush()
            section = match.group(2).strip()
            heading_level = len(match.group(1))
            lines = [line]
        else:
            lines.append(line)
    yield from flush()


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
        for index, (section, heading_level, chunk) in enumerate(section_chunks(path, text)):
            rows.append({
                "chunk_id": f"{sha[:12]}:{index}",
                "path": relative,
                "title": path.stem.replace("_", " ").replace("-", " ").title(),
                "section": section,
                "heading_level": heading_level,
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
        self._document_tokens: list[list[str]] = []
        document_frequency: Counter[str] = Counter()
        for row in self.rows:
            document_tokens = tokens(
                f"{row.get('path', '')} {row.get('title', '')} "
                f"{row.get('section', '')} {row.get('text', '')}"
            )
            self._document_tokens.append(document_tokens)
            document_frequency.update(set(document_tokens))
        count = max(1, len(self.rows))
        self._idf = {
            term: math.log((count + 1) / (frequency + 1)) + 1
            for term, frequency in document_frequency.items()
        }

    def _keyword_scores(self, query_terms: list[str]) -> tuple[dict[int, float], dict[int, list[str]]]:
        scores: dict[int, float] = {}
        matches: dict[int, list[str]] = {}
        for index, row in enumerate(self.rows):
            lowered = str(row.get("text", "")).lower()
            metadata = f"{row.get('path', '')} {row.get('title', '')} {row.get('section', '')}".lower()
            matched = [term for term in query_terms if term in lowered or term in metadata]
            if not matched:
                continue
            scores[index] = sum(
                self._idf.get(term, 1.0)
                * (min(4, lowered.count(term)) + (1.25 if term in metadata else 0) + 0.2)
                for term in matched
            )
            matches[index] = matched
        return scores, matches

    def _tfidf_scores(self, query_terms: list[str]) -> dict[int, float]:
        query_counts = Counter(query_terms)
        query_weights = {
            term: count * self._idf.get(term, math.log(len(self.rows) + 1) + 1)
            for term, count in query_counts.items()
        }
        query_norm = math.sqrt(sum(weight * weight for weight in query_weights.values()))
        if query_norm == 0:
            return {}
        scores = {}
        for index, document_tokens in enumerate(self._document_tokens):
            counts = Counter(document_tokens)
            document_weights = {term: count * self._idf[term] for term, count in counts.items()}
            dot = sum(query_weights.get(term, 0.0) * weight for term, weight in document_weights.items())
            if dot <= 0:
                continue
            document_norm = math.sqrt(sum(weight * weight for weight in document_weights.values()))
            if document_norm:
                scores[index] = dot / (query_norm * document_norm)
        return scores

    @staticmethod
    def _normalized(scores: dict[int, float]) -> dict[int, float]:
        maximum = max(scores.values(), default=0.0)
        return {index: score / maximum for index, score in scores.items()} if maximum else {}

    def search(self, query: str, limit: int = 6, mode: str = "hybrid") -> list[dict[str, Any]]:
        query_terms = list(dict.fromkeys(tokens(query)))[:32]
        if not query_terms:
            return []
        if mode not in {"keyword", "tfidf", "hybrid"}:
            raise ValueError("Retrieval mode must be keyword, tfidf or hybrid")
        keyword, matches = self._keyword_scores(query_terms)
        tfidf = self._tfidf_scores(query_terms)
        if mode == "keyword":
            combined = keyword
        elif mode == "tfidf":
            combined = tfidf
        else:
            keyword_normalized = self._normalized(keyword)
            tfidf_normalized = self._normalized(tfidf)
            combined = {
                index: 0.45 * keyword_normalized.get(index, 0.0) + 0.55 * tfidf_normalized.get(index, 0.0)
                for index in set(keyword_normalized) | set(tfidf_normalized)
            }
        scored = []
        for index, score in combined.items():
            row = self.rows[index]
            text = str(row.get("text", ""))
            lowered = text.lower()
            matched = matches.get(index, [term for term in query_terms if term in lowered])
            positions = [lowered.find(term) for term in matched if lowered.find(term) >= 0]
            start = max(0, (min(positions) if positions else 0) - 140)
            excerpt = re.sub(r"\s+", " ", text[start:start + 620]).strip()
            scored.append({
                "score": round(score, 6), "retrieval_mode": mode,
                "query_coverage": round(len(set(matched)) / len(query_terms), 6),
                "chunk_id": row.get("chunk_id"), "title": row.get("title"),
                "section": row.get("section", "Document"), "path": row.get("path"),
                "heading_level": row.get("heading_level", 0),
                "source_type": row.get("source_type"), "sha256": row.get("sha256"),
                "matched_terms": matched[:8], "excerpt": excerpt,
            })
        scored.sort(key=lambda item: (-item["score"], item["path"], item["section"]))
        unique, seen = [], set()
        for item in scored:
            identity = item["chunk_id"] or (item["path"], item["section"])
            if identity in seen:
                continue
            seen.add(identity)
            unique.append(item)
            if len(unique) >= max(1, min(limit, 12)):
                break
        return unique
