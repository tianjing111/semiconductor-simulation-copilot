#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from simulation_copilot.build_assets import build
from simulation_copilot.service import CopilotService


MODES = ("keyword", "tfidf", "hybrid")


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            case = json.loads(line)
            if not all(key in case for key in ("id", "category", "question", "expected_status", "expected_sources")):
                raise ValueError(f"Incomplete case at line {line_number}")
            cases.append(case)
    if len(cases) != 40:
        raise ValueError(f"Expected 40 frozen cases, found {len(cases)}")
    return cases


def identity(item: dict[str, Any]) -> tuple[str, str]:
    return str(item.get("path", "")), str(item.get("section", ""))


def evaluate(root: Path) -> dict[str, Any]:
    build(root)
    cases = load_cases(root / "benchmarks" / "rag" / "questions.jsonl")
    service = CopilotService(root)
    retrieval_cases = [case for case in cases if case["expected_sources"]]
    retrieval = {}
    case_rows: dict[str, dict[str, Any]] = {case["id"]: {"case": case, "retrieval": {}} for case in cases}
    for mode in MODES:
        hits = 0
        reciprocal_ranks = []
        for case in retrieval_cases:
            results = service.search(case["question"], limit=5, mode=mode)
            expected = {identity(item) for item in case["expected_sources"]}
            observed = [identity(item) for item in results]
            hit = expected.issubset(set(observed))
            hits += int(hit)
            ranks = [observed.index(item) + 1 for item in expected if item in observed]
            reciprocal_rank = 1 / min(ranks) if ranks else 0.0
            reciprocal_ranks.append(reciprocal_rank)
            case_rows[case["id"]]["retrieval"][mode] = {
                "hit_at_5": hit,
                "reciprocal_rank": reciprocal_rank,
                "top_5": [
                    {"path": item["path"], "section": item["section"], "score": item["score"]}
                    for item in results
                ],
            }
        retrieval[mode] = {
            "case_count": len(retrieval_cases),
            "recall_at_5": hits / len(retrieval_cases),
            "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks),
        }

    status_correct = citation_supported = citation_cases = 0
    abstention_correct = abstention_cases = 0
    conflict_correct = conflict_cases = 0
    for case in cases:
        answer = service.ask(case["question"], mode="hybrid")
        correct = answer["status"] == case["expected_status"]
        status_correct += int(correct)
        expected = {identity(item) for item in case["expected_sources"]}
        cited = {identity(item) for item in answer["citations"]}
        citation_ok = expected.issubset(cited) if expected else not cited
        if case["expected_sources"]:
            citation_cases += 1
            citation_supported += int(citation_ok)
        if case["category"] in {"ambiguous", "out_of_scope"}:
            abstention_cases += 1
            abstention_correct += int(correct and not answer["citations"])
        if case["category"] == "conflict":
            conflict_cases += 1
            conflict_correct += int(correct and citation_ok)
        case_rows[case["id"]]["answer"] = {
            "observed_status": answer["status"],
            "status_correct": correct,
            "citation_supported": citation_ok,
            "citations": answer["citations"],
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "protocol": "benchmarks/rag/README.md",
        "question_file": "benchmarks/rag/questions.jsonl",
        "question_count": len(cases),
        "retrieval": retrieval,
        "answering": {
            "status_accuracy": status_correct / len(cases),
            "citation_support_rate": citation_supported / citation_cases,
            "abstention_accuracy": abstention_correct / abstention_cases,
            "conflict_detection_accuracy": conflict_correct / conflict_cases,
        },
        "cases": list(case_rows.values()),
    }


def markdown_report(result: dict[str, Any]) -> str:
    lines = [
        "# RAG Evaluation Report",
        "",
        "This report is generated from the frozen synthetic 40-question benchmark.",
        "It is a regression result, not a production-quality claim.",
        "",
        "## Retrieval",
        "",
        "| Mode | Cases | Recall@5 | MRR |",
        "| --- | ---: | ---: | ---: |",
    ]
    for mode in MODES:
        metric = result["retrieval"][mode]
        lines.append(f"| {mode} | {metric['case_count']} | {metric['recall_at_5']:.3f} | {metric['mrr']:.3f} |")
    answering = result["answering"]
    lines.extend([
        "",
        "## Grounded answering",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Status accuracy | {answering['status_accuracy']:.3f} |",
        f"| Citation support rate | {answering['citation_support_rate']:.3f} |",
        f"| Abstention accuracy | {answering['abstention_accuracy']:.3f} |",
        f"| Conflict detection accuracy | {answering['conflict_detection_accuracy']:.3f} |",
        "",
        "## Failed cases",
        "",
    ])
    failures = []
    for row in result["cases"]:
        retrieval_failed = not row["retrieval"].get("hybrid", {}).get("hit_at_5", True)
        answer_failed = not row["answer"]["status_correct"] or not row["answer"]["citation_supported"]
        if retrieval_failed or answer_failed:
            failures.append(row)
    if not failures:
        lines.append("No failures on the frozen public regression set.")
    else:
        lines.append("| Case | Expected | Observed | Hybrid retrieval | Citation |")
        lines.append("| --- | --- | --- | --- | --- |")
        for row in failures:
            case = row["case"]
            answer = row["answer"]
            retrieval_ok = row["retrieval"].get("hybrid", {}).get("hit_at_5", "n/a")
            lines.append(
                f"| {case['id']} | {case['expected_status']} | {answer['observed_status']} | "
                f"{retrieval_ok} | {answer['citation_supported']} |"
            )
    lines.extend([
        "",
        "Full per-case outputs are available in `results.json`.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate public RAG retrieval and grounded answering")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out-dir", type=Path, default=Path("benchmarks/rag/reports"))
    args = parser.parse_args()
    root = args.root.resolve()
    out_dir = args.out_dir if args.out_dir.is_absolute() else root / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    result = evaluate(root)
    (out_dir / "results.json").write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (out_dir / "REPORT.md").write_text(markdown_report(result), encoding="utf-8")
    print(markdown_report(result))


if __name__ == "__main__":
    main()
