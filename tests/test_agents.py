"""Tests for the deterministic Review Board agents."""

import unittest

from orchestrator import cost_agent, reliability_agent, review_board, security_agent


class SecurityAgentTests(unittest.TestCase):
    def test_full_controls_pass(self) -> None:
        verdict = security_agent(
            {"encryption_at_rest": True, "authentication": True, "public_network": False}
        )
        self.assertEqual(verdict.verdict, "PASS")
        self.assertEqual(verdict.hard_rules_passed, 3)

    def test_missing_encryption_blocks(self) -> None:
        verdict = security_agent(
            {"encryption_at_rest": False, "authentication": True}
        )
        self.assertTrue(verdict.is_blocker)
        self.assertIn("cifra", verdict.risk)

    def test_public_without_auth_blocks_two_rules(self) -> None:
        verdict = security_agent(
            {"encryption_at_rest": True, "authentication": False, "public_network": True}
        )
        self.assertTrue(verdict.is_blocker)
        self.assertEqual(verdict.hard_rules_passed, 1)

    def test_missing_attribute_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            security_agent({"authentication": True})


class CostAgentTests(unittest.TestCase):
    def test_no_budget_is_pass(self) -> None:
        self.assertEqual(cost_agent({}, {"monthly_cost_usd": 500}).verdict, "PASS")

    def test_over_budget_blocks(self) -> None:
        verdict = cost_agent({"budget_usd": 100}, {"monthly_cost_usd": 150})
        self.assertTrue(verdict.is_blocker)

    def test_near_budget_warns(self) -> None:
        verdict = cost_agent({"budget_usd": 100}, {"monthly_cost_usd": 90})
        self.assertEqual(verdict.verdict, "WARN")

    def test_within_budget_passes(self) -> None:
        verdict = cost_agent({"budget_usd": 100}, {"monthly_cost_usd": 50})
        self.assertEqual(verdict.verdict, "PASS")


class ReliabilityAgentTests(unittest.TestCase):
    def test_backups_pass(self) -> None:
        self.assertEqual(reliability_agent({"has_backups": True}).verdict, "PASS")

    def test_missing_backups_warns_without_blocking(self) -> None:
        verdict = reliability_agent({"has_backups": False})
        self.assertEqual(verdict.verdict, "WARN")
        self.assertFalse(verdict.is_blocker)


class ReviewBoardTests(unittest.TestCase):
    def test_board_returns_three_agents(self) -> None:
        verdicts = review_board(
            {"budget_usd": 200},
            {
                "encryption_at_rest": True,
                "authentication": True,
                "public_network": False,
                "has_backups": True,
                "monthly_cost_usd": 100,
            },
        )
        self.assertEqual([v.agent for v in verdicts], ["security", "cost", "reliability"])
        self.assertTrue(all(v.verdict == "PASS" for v in verdicts))


if __name__ == "__main__":
    unittest.main()
