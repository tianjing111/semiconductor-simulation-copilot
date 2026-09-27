from __future__ import annotations

from pathlib import Path
from typing import Any

from .diagnostics import diagnose_text
from .generation import GroundedGenerator
from .memory import ExperimentMemory
from .planning import load_and_validate_plan
from .qa import GroundedAnswerer
from .retrieval import EvidenceIndex


class CopilotService:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.index = EvidenceIndex(self.root / "data" / "knowledge_index.jsonl")
        self.answerer = GroundedAnswerer(self.index)
        self.memory = ExperimentMemory(self.root / "data" / "experiment_cards.json")
        self.generator = GroundedGenerator()

    def status(self) -> dict[str, Any]:
        return {
            "product": "Semiconductor Process Simulation Copilot",
            "mode": "READ_ONLY_PUBLIC_DEMO",
            "generation_mode": self.generator.mode,
            "knowledge_chunks": len(self.index.rows),
            "experiment_cards": len(self.memory.cards),
            "data_policy": "SYNTHETIC_ONLY",
            "safety": {
                "solver_launch": "HARD_BLOCKED",
                "task_planning": "DRY_RUN_ONLY",
                "uploaded_log_persistence": "DISABLED",
            },
        }

    def search(self, query: str, limit: int = 6, mode: str = "hybrid") -> list[dict[str, Any]]:
        return self.index.search(query, limit, mode)

    def ask(self, question: str, mode: str = "hybrid") -> dict[str, Any]:
        return self.answerer.answer(question, mode=mode)

    def experiments(self, query: str = "", limit: int = 40) -> list[dict[str, Any]]:
        return self.memory.search(query, limit)

    def diagnose(self, text: str) -> dict[str, Any]:
        text = text.strip()
        if not text:
            raise ValueError("Log text is required")
        if len(text.encode("utf-8")) > 2 * 1024 * 1024:
            raise ValueError("Log text exceeds the 2 MiB in-memory limit")
        result = diagnose_text(text, source="browser_upload")
        sources_by_path = {}
        for finding in result["findings"]:
            evidence = finding["evidence"]["text"]
            for source in self.search(f"{finding['category']} {finding['message']} {evidence}", 4):
                sources_by_path[source["path"]] = source
        sources = list(sources_by_path.values())[:8]
        return {
            "status": "DIAGNOSIS_READY",
            "privacy": "Input was analyzed in memory and was not persisted.",
            "finding_count": result["finding_count"],
            "findings": result["findings"],
            "assistant_summary": self.generator.summarize(result["findings"], sources),
            "sources": sources,
            "execution_boundary": {
                "automatic_solver_launch": False,
                "dry_run_planning": True,
                "human_approval_required": True,
            },
        }

    def plan(self) -> dict[str, Any]:
        return load_and_validate_plan(
            self.root / "examples" / "demo_plan.json",
            source_label="examples/demo_plan.json",
        )
