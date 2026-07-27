"""Unit tests for the deterministic consensus policy."""

import unittest

from orchestrator import AgentVerdict, confidence, decide


class ConsensusPolicyTests(unittest.TestCase):
    def pass_verdict(self, agent: str = "performance") -> AgentVerdict:
        return AgentVerdict(
            agent=agent,
            verdict="PASS",
            severity="info",
            risk=None,
            hard_rules_passed=2,
            hard_rules_total=2,
        )

    def warn_verdict(self) -> AgentVerdict:
        return AgentVerdict(
            agent="reliability",
            verdict="WARN",
            severity="warning",
            risk="La recuperación ante fallos debe probarse antes del despliegue.",
            hard_rules_passed=1,
            hard_rules_total=1,
        )

    def security_blocker(self) -> AgentVerdict:
        return AgentVerdict(
            agent="security",
            verdict="FAIL",
            severity="blocker",
            risk="Falta cifrado para los datos almacenados.",
            hard_rules_passed=0,
            hard_rules_total=1,
        )

    def test_security_or_cost_blocker_requests_reproposal_before_final_round(
        self,
    ) -> None:
        self.assertEqual(
            decide([self.pass_verdict(), self.security_blocker()], round=0),
            "re_propose",
        )
        cost_blocker = AgentVerdict(
            agent="cost",
            verdict="FAIL",
            severity="blocker",
            risk="El coste mensual supera el presupuesto aprobado.",
            hard_rules_passed=0,
            hard_rules_total=1,
        )
        self.assertEqual(decide([cost_blocker], round=1), "re_propose")

    def test_blocker_at_second_round_forces_delivery(self) -> None:
        self.assertEqual(
            decide([self.security_blocker()], round=2), "force_deliver"
        )

    def test_only_warnings_converge(self) -> None:
        self.assertEqual(decide([self.warn_verdict()], round=0), "converge")

    def test_confidence_is_deterministic_and_uses_all_required_factors(self) -> None:
        verdicts = [self.pass_verdict(), self.warn_verdict()]
        self.assertEqual(confidence(verdicts), 75)
        self.assertEqual(confidence(verdicts), confidence(verdicts))

    def test_empty_verdicts_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            decide([], round=0)

    def test_non_actionable_fail_is_rejected_at_model_boundary(self) -> None:
        with self.assertRaises(ValueError):
            AgentVerdict(
                agent="reliability",
                verdict="FAIL",
                severity="blocker",
                risk="No hay plan de recuperación.",
                hard_rules_passed=0,
                hard_rules_total=1,
            )


if __name__ == "__main__":
    unittest.main()
