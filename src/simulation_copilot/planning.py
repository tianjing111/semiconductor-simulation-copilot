from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PlanContractError(ValueError):
    pass


def load_and_validate_plan(path: Path, source_label: str | None = None) -> dict[str, Any]:
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan.get("execution_mode") != "dry_run":
        raise PlanContractError("Only dry-run plans are accepted")
    commands = plan.get("commands")
    if not isinstance(commands, list) or not commands:
        raise PlanContractError("Plan must contain commands")
    planned_calls = 0
    for command in commands:
        argv = command.get("argv")
        if not isinstance(argv, list) or "--dry-run" not in argv:
            raise PlanContractError("Every command must enforce --dry-run")
        if command.get("dry_run_enforced") is not True:
            raise PlanContractError("Dry-run enforcement flag is missing")
        planned_calls += int(command.get("solver_calls_if_live", 0))
    budget = plan.get("budget", {})
    if planned_calls > int(budget.get("max_solver_calls", -1)):
        raise PlanContractError("Planned solver calls exceed the declared budget")
    return {
        "available": True,
        "task_id": plan.get("task_id"),
        "execution_mode": "dry_run",
        "validation": "PASS",
        "budget": {**budget, "planned_solver_calls": planned_calls},
        "launch_gate": {"state": "HARD_BLOCKED", "live_launch_allowed": False},
        "conditions": [
            {
                "run_id": command.get("run_id"), "dose": command.get("dose"),
                "focus": command.get("focus"), "solver_calls_if_live": command.get("solver_calls_if_live"),
                "dry_run_enforced": command.get("dry_run_enforced"),
            }
            for command in commands
        ],
        "source": source_label or path.name,
    }
