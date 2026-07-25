"""Tests for the scripted AI Solution Architect debate (spec §10)."""

import unittest

from architect import Constraints, HardwareProfile, ProblemContext
from architect.decision import run_review, serialize_adr


def demo_context() -> ProblemContext:
    return ProblemContext(
        description="Chatbot sobre 5.000 PDFs que cambian cada semana, presupuesto bajo.",
        hardware=HardwareProfile(
            cpu_cores=10, ram_gb=16, has_gpu=False, unified_memory=True
        ),
        constraints=Constraints(
            monthly_budget_usd=200,
            privacy="private_cloud",
            data_changes_frequently=True,
        ),
        knowledge_base_docs=5000,
    )


class ScriptedDebateTests(unittest.TestCase):
    def test_fine_tuning_is_rejected_and_rag_wins(self) -> None:
        adr = run_review(demo_context())
        self.assertEqual(adr.recommendation.strategy, "rag")
        self.assertFalse(adr.forced)
        rejected = [alt.strategy for alt in adr.rejected_alternatives]
        self.assertIn("fine_tuning", rejected)

    def test_rejected_fine_tuning_cites_cost_fail(self) -> None:
        adr = run_review(demo_context())
        fine_tuning = next(
            alt for alt in adr.rejected_alternatives if alt.strategy == "fine_tuning"
        )
        self.assertIn("cost FAIL", fine_tuning.board_summary)
        self.assertTrue(any("presupuesto" in reason for reason in fine_tuning.reasons))

    def test_confidence_is_calculated_and_bounded(self) -> None:
        adr = run_review(demo_context())
        self.assertGreaterEqual(adr.confidence, 0)
        self.assertLessEqual(adr.confidence, 100)
        # RAG with a clean board should be highly confident.
        self.assertGreaterEqual(adr.confidence, 80)

    def test_serialized_adr_has_matrix_and_rejected(self) -> None:
        data = serialize_adr(demo_context(), run_review(demo_context()))
        techniques = {row["technique"] for row in data["capability_matrix"]}
        self.assertEqual(techniques, {"rag", "agents", "lora", "fine_tuning"})
        self.assertEqual(data["recommendation"]["strategy"], "rag")
        self.assertTrue(data["rejected_alternatives"])
        self.assertIsInstance(data["recommendation"]["estimated_monthly_usd"], float)


if __name__ == "__main__":
    unittest.main()
