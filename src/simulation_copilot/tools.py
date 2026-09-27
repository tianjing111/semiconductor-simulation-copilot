from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, Callable

from .memory import ExperimentMemory
from .planning import PlanContractError, validate_plan_payload
from .qa import GroundedAnswerer
from .retrieval import sha256_file


RUN_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")
SUPPORTED_GRID_SIZES = {64, 128, 256}
ALLOWED_TOOLS = {
    "search_docs",
    "validate_config",
    "create_dry_run",
    "inspect_run",
    "summarize_results",
}


def _citation(root: Path, relative: str, section: str) -> dict[str, str]:
    path = root / relative
    return {
        "path": relative,
        "section": section,
        "sha256": sha256_file(path),
    }


class ToolRegistry:
    """Five read-only or dry-run-only tools with explicit input contracts."""

    def __init__(self, root: Path, answerer: GroundedAnswerer, memory: ExperimentMemory) -> None:
        self.root = root.resolve()
        self.answerer = answerer
        self.memory = memory
        self._handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "search_docs": self.search_docs,
            "validate_config": self.validate_config,
            "create_dry_run": self.create_dry_run,
            "inspect_run": self.inspect_run,
            "summarize_results": self.summarize_results,
        }

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in self._handlers:
            raise ValueError(f"Tool is not allowed: {name}")
        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be a JSON object")
        return self._handlers[name](arguments)

    def search_docs(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = str(arguments.get("query", "")).strip()
        if not query:
            return {"status": "NEEDS_INPUT", "errors": ["query is required"], "citations": []}
        answer = self.answerer.answer(query, mode=str(arguments.get("mode", "hybrid")))
        return {"tool": "search_docs", **answer}

    def validate_config(self, arguments: dict[str, Any]) -> dict[str, Any]:
        config = arguments.get("config")
        errors: list[str] = []
        if not isinstance(config, dict):
            return {
                "tool": "validate_config", "status": "INVALID",
                "errors": ["config must be a JSON object"], "citations": [],
            }
        task_id = config.get("task_id")
        if not isinstance(task_id, str) or not RUN_ID_PATTERN.fullmatch(task_id):
            errors.append("task_id must contain lowercase letters, digits or underscores")
        grid_size = config.get("grid_size")
        if grid_size not in SUPPORTED_GRID_SIZES:
            errors.append("grid_size must be one of 64, 128 or 256")
        budget = config.get("max_solver_calls")
        if not isinstance(budget, int) or isinstance(budget, bool) or not 1 <= budget <= 25:
            errors.append("max_solver_calls must be an integer from 1 to 25")
        conditions = config.get("conditions")
        normalized_conditions = []
        seen_ids: set[str] = set()
        if not isinstance(conditions, list) or not conditions:
            errors.append("conditions must be a non-empty list")
        else:
            for index, item in enumerate(conditions):
                if not isinstance(item, dict):
                    errors.append(f"conditions[{index}] must be an object")
                    continue
                run_id = item.get("run_id")
                dose = item.get("dose")
                focus = item.get("focus")
                calls = item.get("solver_calls_if_live", 1)
                if not isinstance(run_id, str) or not RUN_ID_PATTERN.fullmatch(run_id):
                    errors.append(f"conditions[{index}].run_id is invalid")
                elif run_id in seen_ids:
                    errors.append(f"conditions[{index}].run_id is duplicated")
                else:
                    seen_ids.add(run_id)
                if not isinstance(dose, (int, float)) or isinstance(dose, bool) or not math.isfinite(dose) or not 40 <= dose <= 50:
                    errors.append(f"conditions[{index}].dose must be within 40 to 50")
                if not isinstance(focus, (int, float)) or isinstance(focus, bool) or not math.isfinite(focus) or not -0.05 <= focus <= 0.05:
                    errors.append(f"conditions[{index}].focus must be within -0.05 to +0.05")
                if not isinstance(calls, int) or isinstance(calls, bool) or calls < 1:
                    errors.append(f"conditions[{index}].solver_calls_if_live must be a positive integer")
                normalized_conditions.append({
                    "run_id": run_id, "dose": dose, "focus": focus,
                    "solver_calls_if_live": calls,
                })
        planned_calls = sum(
            item.get("solver_calls_if_live", 0)
            for item in normalized_conditions
            if isinstance(item.get("solver_calls_if_live"), int)
        )
        if isinstance(budget, int) and not isinstance(budget, bool) and planned_calls > budget:
            errors.append("planned solver calls exceed max_solver_calls")
        citations = [
            _citation(self.root, "docs/knowledge/parameter_reference.md", "Parameter contracts"),
            _citation(self.root, "docs/knowledge/workflow_guide.md", "Validate configuration"),
        ]
        return {
            "tool": "validate_config",
            "status": "VALID" if not errors else "INVALID",
            "errors": errors,
            "planned_solver_calls": planned_calls,
            "normalized_config": {
                "task_id": task_id,
                "grid_size": grid_size,
                "max_solver_calls": budget,
                "conditions": normalized_conditions,
            } if not errors else None,
            "citations": citations,
        }

    def create_dry_run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        validation = self.validate_config(arguments)
        if validation["status"] != "VALID":
            return {
                "tool": "create_dry_run", "status": "BLOCKED_INVALID_CONFIG",
                "errors": validation["errors"], "validation": validation,
                "citations": validation["citations"],
            }
        config = validation["normalized_config"]
        commands = []
        for condition in config["conditions"]:
            commands.append({
                **condition,
                "argv": [
                    "simulator-cli", "--task-id", config["task_id"],
                    "--grid-size", str(config["grid_size"]),
                    "--dose", str(condition["dose"]),
                    "--focus", str(condition["focus"]), "--dry-run",
                ],
                "dry_run_enforced": True,
            })
        payload = {
            "plan_version": "1.0",
            "task_id": config["task_id"],
            "execution_mode": "dry_run",
            "data_policy": "synthetic_demo",
            "budget": {"max_solver_calls": config["max_solver_calls"]},
            "commands": commands,
        }
        try:
            validated = validate_plan_payload(payload, "in_memory_agent_plan")
        except PlanContractError as exc:
            return {"tool": "create_dry_run", "status": "BLOCKED", "errors": [str(exc)], "citations": []}
        return {
            "tool": "create_dry_run", "status": "DRY_RUN_READY",
            "plan": validated, "command_argv": [item["argv"] for item in commands],
            "citations": validation["citations"],
        }

    def _matching_cards(self, run_id: str) -> list[dict[str, Any]]:
        normalized = run_id.strip().lower()
        if not normalized:
            return []
        return [
            card for card in self.memory.cards
            if normalized == str(card.get("experiment_id", "")).lower()
            or normalized in str(card.get("title", "")).lower()
            or normalized in str(card.get("category", "")).lower()
        ]

    def inspect_run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        run_id = str(arguments.get("run_id", "")).strip()
        cards = self._matching_cards(run_id)
        return {
            "tool": "inspect_run",
            "status": "FOUND" if cards else ("NEEDS_INPUT" if not run_id else "NOT_FOUND"),
            "run_id": run_id,
            "results": cards[:5],
            "citations": [
                {"path": card["source"], "section": card["title"], "sha256": card["source_sha256"]}
                for card in cards[:5]
            ],
        }

    def summarize_results(self, arguments: dict[str, Any]) -> dict[str, Any]:
        inspection = self.inspect_run(arguments)
        if inspection["status"] != "FOUND":
            return {
                "tool": "summarize_results", "status": inspection["status"],
                "summary": None, "citations": inspection["citations"],
            }
        card = inspection["results"][0]
        return {
            "tool": "summarize_results",
            "status": "SUMMARY_READY",
            "summary": {
                "experiment_id": card["experiment_id"],
                "title": card["title"],
                "state": card["status"],
                "purpose": card["purpose"],
                "metrics": card["metrics"],
                "notice": "Synthetic portfolio demonstration; metrics are not scientific claims.",
            },
            "citations": inspection["citations"][:1],
        }
