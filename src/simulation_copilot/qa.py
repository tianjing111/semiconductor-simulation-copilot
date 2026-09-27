from __future__ import annotations

from typing import Any

from .retrieval import EvidenceIndex, tokens


VAGUE_QUESTIONS = {
    "can i run it",
    "is the result okay",
    "is this valid",
    "what should i do",
    "why did it fail",
    "why was it rejected",
    "what went wrong",
    "why did this not pass",
}
PROHIBITED_CLAIM_TERMS = ("guarantee", "production yield")


def citation(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": source["path"],
        "section": source["section"],
        "sha256": source["sha256"],
        "chunk_id": source["chunk_id"],
    }


class GroundedAnswerer:
    """Evidence-first QA with explicit abstention and conflict states."""

    def __init__(self, index: EvidenceIndex) -> None:
        self.index = index

    def answer(self, question: str, mode: str = "hybrid", limit: int = 5) -> dict[str, Any]:
        question = question.strip()
        if not question:
            raise ValueError("Question is required")
        normalized = " ".join(question.lower().rstrip("?.!").split())
        if normalized in VAGUE_QUESTIONS or len(tokens(question)) < 2:
            return {
                "status": "CLARIFICATION_REQUIRED",
                "answer": "The request lacks a parameter, error signature, task state or acceptance rule to inspect.",
                "citations": [],
                "retrieval": [],
            }
        raw_results = self.index.search(question, limit=12, mode=mode)
        if any(term in normalized for term in PROHIBITED_CLAIM_TERMS):
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "answer": "Synthetic demonstration evidence cannot support a production guarantee.",
                "citations": [],
                "retrieval": raw_results[:limit],
            }
        results = [
            item for item in raw_results
            if item["path"].startswith("docs/knowledge/")
        ]
        query_identifiers = {term for term in tokens(question) if "_" in term}
        parameter_intent = any(
            term in normalized for term in ("accepted", "allowed", "how large", "mean", "range", "supported", "valid")
        )

        def priority(item: dict[str, Any]) -> tuple[bool, bool, float, bool, float]:
            matched = set(item.get("matched_terms", []))
            parameter_contract = (
                parameter_intent
                and bool(query_identifiers & matched)
                and item["path"].endswith("parameter_reference.md")
            )
            identifier_match = bool(query_identifiers & matched)
            return (
                parameter_contract,
                identifier_match,
                float(item.get("query_coverage", 0.0)),
                int(item.get("heading_level", 0)) >= 2,
                float(item.get("score", 0.0)),
            )

        results = sorted(results, key=priority, reverse=True)[:limit]
        strong_identifier = bool(results) and bool(query_identifiers & set(results[0].get("matched_terms", [])))
        strong_specific_section = bool(results) and (
            int(results[0].get("heading_level", 0)) >= 2
            and float(results[0].get("score", 0.0)) >= 0.7
        )
        if not results or (
            results[0].get("query_coverage", 0.0) < 0.34
            and not strong_identifier
            and not strong_specific_section
        ):
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "answer": "The public knowledge base does not contain enough evidence to answer this question.",
                "citations": [],
                "retrieval": results,
            }
        deprecated = [item for item in results if item["path"].endswith("deprecated_notes.md")]
        canonical = [item for item in results if not item["path"].endswith("deprecated_notes.md")]
        conflict_requested = any(
            term in normalized for term in ("old", "deprecated", "disagree", "shortcut", "canonical")
        )
        if deprecated and canonical and conflict_requested:
            sources = [canonical[0], deprecated[0]]
            return {
                "status": "CONFLICTING_EVIDENCE",
                "answer": (
                    "The retrieved sources contain a deprecated statement and a canonical rule. "
                    f"Use {canonical[0]['path']} / {canonical[0]['section']} and treat the deprecated note as non-authoritative."
                ),
                "citations": [citation(item) for item in sources],
                "retrieval": results,
            }
        primary = results[0]
        return {
            "status": "ANSWERED",
            "answer": primary["excerpt"],
            "citations": [citation(primary)],
            "retrieval": results,
        }
