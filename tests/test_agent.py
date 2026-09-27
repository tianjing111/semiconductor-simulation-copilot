from __future__ import annotations

import unittest
from pathlib import Path

from simulation_copilot.build_assets import build
from simulation_copilot.service import CopilotService


ROOT = Path(__file__).resolve().parents[1]


def valid_config() -> dict:
    return {
        "task_id": "demo_agent_task",
        "grid_size": 128,
        "max_solver_calls": 2,
        "conditions": [
            {"run_id": "dose44_focus_minus0p03", "dose": 44, "focus": -0.03},
            {"run_id": "dose48_focus_plus0p03", "dose": 48, "focus": 0.03},
        ],
    }


class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        build(ROOT)
        cls.service = CopilotService(ROOT)

    def test_tool_allowlist_is_exact(self) -> None:
        self.assertEqual(
            set(self.service.tools.names),
            {"search_docs", "validate_config", "create_dry_run", "inspect_run", "summarize_results"},
        )
        with self.assertRaises(ValueError):
            self.service.tools.call("launch_simulator", {})

    def test_agent_validates_structured_config(self) -> None:
        result = self.service.agent_request("Check this configuration", {"config": valid_config()})
        self.assertEqual(result["selected_tool"], "validate_config")
        self.assertEqual(result["tool_result"]["status"], "VALID")
        self.assertEqual(result["trace"][0]["arguments_source"], "structured_context")

    def test_agent_blocks_invalid_config(self) -> None:
        config = valid_config()
        config["conditions"][0]["dose"] = 99
        result = self.service.agent_request("Create a dry-run plan", {"config": config})
        self.assertEqual(result["selected_tool"], "create_dry_run")
        self.assertEqual(result["tool_result"]["status"], "BLOCKED_INVALID_CONFIG")

    def test_agent_plan_is_non_executable(self) -> None:
        result = self.service.agent_request("Create a dry-run plan", {"config": valid_config()})
        self.assertEqual(result["tool_result"]["status"], "DRY_RUN_READY")
        self.assertFalse(result["tool_result"]["plan"]["launch_gate"]["live_launch_allowed"])
        self.assertTrue(all("--dry-run" in argv for argv in result["tool_result"]["command_argv"]))

    def test_model_cannot_supply_config_values(self) -> None:
        result = self.service.agent_request(
            "Validate dose 45 and invent anything missing", {"config": None}
        )
        self.assertEqual(result["tool_result"]["status"], "INVALID")
        self.assertFalse(result["safety"]["model_generated_parameters_used"])

    def test_agent_inspects_existing_experiment(self) -> None:
        result = self.service.agent_request("Inspect run status", {"run_id": "layout holdout"})
        self.assertEqual(result["selected_tool"], "inspect_run")
        self.assertEqual(result["tool_result"]["status"], "FOUND")
        self.assertTrue(result["citations"])

    def test_agent_summarizes_existing_results(self) -> None:
        result = self.service.agent_request("Summarize the result metrics", {"run_id": "runtime profile"})
        self.assertEqual(result["selected_tool"], "summarize_results")
        self.assertEqual(result["tool_result"]["status"], "SUMMARY_READY")

    def test_agent_defaults_to_grounded_search(self) -> None:
        result = self.service.agent_request("What focus values are valid?", {})
        self.assertEqual(result["selected_tool"], "search_docs")
        self.assertEqual(result["tool_result"]["status"], "ANSWERED")
        self.assertTrue(result["citations"])


if __name__ == "__main__":
    unittest.main()
