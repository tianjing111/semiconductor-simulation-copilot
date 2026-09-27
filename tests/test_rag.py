from __future__ import annotations

import unittest
from pathlib import Path

from simulation_copilot.build_assets import build
from simulation_copilot.service import CopilotService


ROOT = Path(__file__).resolve().parents[1]


class RagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        build(ROOT)
        cls.service = CopilotService(ROOT)

    def test_retrieval_modes_return_section_provenance(self) -> None:
        for mode in ("keyword", "tfidf", "hybrid"):
            with self.subTest(mode=mode):
                results = self.service.search("accepted dose range", mode=mode)
                self.assertTrue(results)
                self.assertTrue(all(item["section"] for item in results))
                self.assertTrue(all(item["sha256"] for item in results))
                self.assertTrue(all(item["retrieval_mode"] == mode for item in results))

    def test_grounded_answer_has_expected_citation(self) -> None:
        result = self.service.ask("What signed focus values are valid in the public demonstration?")
        self.assertEqual(result["status"], "ANSWERED")
        self.assertEqual(result["citations"][0]["path"], "docs/knowledge/parameter_reference.md")
        self.assertEqual(result["citations"][0]["section"], "Focus")

    def test_ambiguous_question_requests_clarification(self) -> None:
        result = self.service.ask("Why did it fail?")
        self.assertEqual(result["status"], "CLARIFICATION_REQUIRED")
        self.assertFalse(result["citations"])

    def test_out_of_scope_question_abstains(self) -> None:
        result = self.service.ask("What chamber pressure should I use for plasma etching?")
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")
        self.assertFalse(result["citations"])

    def test_conflicting_sources_are_reported(self) -> None:
        result = self.service.ask("Which focus range is authoritative when the deprecated note disagrees?")
        self.assertEqual(result["status"], "CONFLICTING_EVIDENCE")
        paths = {item["path"] for item in result["citations"]}
        self.assertEqual(paths, {
            "docs/knowledge/parameter_reference.md",
            "docs/knowledge/deprecated_notes.md",
        })


if __name__ == "__main__":
    unittest.main()
