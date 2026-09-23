from __future__ import annotations

import os
import secrets
import tempfile
import unittest
from pathlib import Path

from simulation_copilot.build_assets import build
from simulation_copilot.planning import PlanContractError, load_and_validate_plan
from simulation_copilot.service import CopilotService


ROOT = Path(__file__).resolve().parents[1]


class CopilotServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        build(ROOT)
        cls.service = CopilotService(ROOT)

    def test_status_uses_synthetic_data(self) -> None:
        status = self.service.status()
        self.assertEqual(status["data_policy"], "SYNTHETIC_ONLY")
        self.assertGreater(status["knowledge_chunks"], 0)
        self.assertEqual(status["experiment_cards"], 4)
        self.assertEqual(status["safety"]["solver_launch"], "HARD_BLOCKED")

    def test_grounded_diagnosis(self) -> None:
        result = self.service.diagnose("RuntimeError: No usable samples found for split test")
        self.assertEqual(result["findings"][0]["category"], "data_split_contract")
        self.assertEqual(result["assistant_summary"]["mode"], "DETERMINISTIC")
        self.assertTrue(result["sources"])
        self.assertTrue(all(source["sha256"] for source in result["sources"]))
        self.assertFalse(result["execution_boundary"]["automatic_solver_launch"])

    def test_uploaded_text_is_not_persisted(self) -> None:
        marker = "DO_NOT_" + "PERSIST_" + secrets.token_hex(12)
        before = {path: path.stat().st_mtime_ns for path in ROOT.rglob("*") if path.is_file()}
        self.service.diagnose(f"RuntimeError: {marker}")
        after = {path: path.stat().st_mtime_ns for path in ROOT.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        for path in after:
            if path.suffix in {".png", ".jpg"}:
                continue
            self.assertNotIn(marker, path.read_text(encoding="utf-8", errors="replace"))

    def test_plan_is_dry_run_only(self) -> None:
        plan = self.service.plan()
        self.assertEqual(plan["execution_mode"], "dry_run")
        self.assertFalse(plan["launch_gate"]["live_launch_allowed"])
        self.assertTrue(all(row["dry_run_enforced"] for row in plan["conditions"]))
        self.assertEqual(plan["source"], "examples/demo_plan.json")
        self.assertFalse(Path(plan["source"]).is_absolute())

    def test_plan_rejects_live_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe.json"
            path.write_text(
                '{"execution_mode":"live","budget":{"max_solver_calls":1},"commands":[{"argv":["simulator"],"solver_calls_if_live":1}]}',
                encoding="utf-8",
            )
            with self.assertRaises(PlanContractError):
                load_and_validate_plan(path)


if __name__ == "__main__":
    unittest.main()
