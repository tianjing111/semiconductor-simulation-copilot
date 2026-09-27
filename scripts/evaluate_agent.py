#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

from simulation_copilot.service import CopilotService


FAMILY_TO_TOOL = {
    "knowledge": "search_docs",
    "validate": "validate_config",
    "plan": "create_dry_run",
    "inspect": "inspect_run",
    "summarize": "summarize_results",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def context_for(task: dict[str, Any], fixtures: dict[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {"run_id": task.get("run_id", "")}
    if task.get("fixture"):
        context["config"] = fixtures[task["fixture"]]
    return context


def tool_arguments(tool: str, task: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    if tool == "search_docs":
        return {"query": task["prompt"], "mode": "hybrid"}
    if tool in {"validate_config", "create_dry_run"}:
        return {"config": context.get("config")}
    return {"run_id": context.get("run_id", "")}


def evaluate(root: Path) -> dict[str, Any]:
    benchmark = root / "benchmarks" / "agent"
    tasks = read_jsonl(benchmark / "tasks.jsonl")
    fixtures = json.loads((benchmark / "fixtures.json").read_text(encoding="utf-8"))
    service = CopilotService(root)
    policies: dict[str, list[dict[str, Any]]] = {
        "fixed_dispatch": [],
        "bounded_router_no_rag": [],
        "bounded_router_rag": [],
    }
    for task in tasks:
        context = context_for(task, fixtures)
        fixed_tool = FAMILY_TO_TOOL[task["family"]]
        fixed_result = service.tools.call(fixed_tool, tool_arguments(fixed_tool, task, context))
        policies["fixed_dispatch"].append({
            "id": task["id"], "selected_tool": fixed_tool,
            "observed_status": fixed_result["status"],
            "citation_count": len(fixed_result.get("citations", [])), "tool_calls": 1,
        })
        selected = service.agent.planner.deterministic(task["prompt"])
        if selected == "search_docs":
            no_rag = {"status": "EVIDENCE_DISABLED", "citations": []}
        else:
            no_rag = service.tools.call(selected, tool_arguments(selected, task, context))
        policies["bounded_router_no_rag"].append({
            "id": task["id"], "selected_tool": selected,
            "observed_status": no_rag["status"],
            "citation_count": len(no_rag.get("citations", [])), "tool_calls": 1,
        })
        agent_result = service.agent_request(task["prompt"], context)
        policies["bounded_router_rag"].append({
            "id": task["id"], "selected_tool": agent_result["selected_tool"],
            "observed_status": agent_result["tool_result"]["status"],
            "citation_count": len(agent_result.get("citations", [])),
            "tool_calls": len(agent_result["trace"]),
        })

    summaries = {}
    details = {}
    for name, rows in policies.items():
        enriched = []
        for task, row in zip(tasks, rows):
            tool_correct = row["selected_tool"] == task["expected_tool"]
            status_correct = row["observed_status"] == task["expected_status"]
            citation_supported = not task["requires_citation"] or row["citation_count"] > 0
            enriched.append({
                **row,
                "expected_tool": task["expected_tool"],
                "expected_status": task["expected_status"],
                "requires_citation": task["requires_citation"],
                "tool_correct": tool_correct,
                "status_correct": status_correct,
                "citation_supported": citation_supported,
            })
        citation_rows = [row for row in enriched if row["requires_citation"]]
        summaries[name] = {
            "task_count": len(enriched),
            "tool_selection_accuracy": mean(row["tool_correct"] for row in enriched),
            "expected_status_accuracy": mean(row["status_correct"] for row in enriched),
            "citation_support_rate": mean(row["citation_supported"] for row in citation_rows),
            "unsafe_tool_calls": sum(row["selected_tool"] not in service.tools.names for row in enriched),
            "mean_tool_calls": mean(row["tool_calls"] for row in enriched),
        }
        details[name] = enriched
    return {
        "benchmark": "synthetic_bounded_tool_use_v1",
        "task_count": len(tasks),
        "policy_summaries": summaries,
        "per_task": details,
        "limitations": [
            "The benchmark is a deterministic public regression set, not a production workload.",
            "The optional OpenAI-compatible planner is not scored without a configured endpoint.",
            "Fixed dispatch receives the explicit task family and is an intentionally strong baseline.",
        ],
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# Bounded Tool-Use Evaluation",
        "",
        "This generated report covers a frozen synthetic 30-task regression set.",
        "It does not measure production autonomy or semiconductor expertise.",
        "",
        "| Policy | Tasks | Tool selection | Expected status | Citation support | Unsafe calls | Mean calls |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, metrics in result["policy_summaries"].items():
        lines.append(
            f"| {name} | {metrics['task_count']} | {metrics['tool_selection_accuracy']:.3f} | "
            f"{metrics['expected_status_accuracy']:.3f} | {metrics['citation_support_rate']:.3f} | "
            f"{metrics['unsafe_tool_calls']} | {metrics['mean_tool_calls']:.2f} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The fixed workflow remains a strong option when intent is already structured.",
        "Natural-language routing does not replace deterministic validation. Retrieval",
        "adds source support to open-ended knowledge requests, while all parameter and",
        "safety decisions remain in code.",
        "",
        "## Limitations",
        "",
        *[f"- {item}" for item in result["limitations"]],
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate bounded public tool use")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    result = evaluate(root)
    report_dir = root / "benchmarks" / "agent" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "results.json").write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    write_report(result, report_dir / "REPORT.md")
    print(json.dumps(result["policy_summaries"], indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
