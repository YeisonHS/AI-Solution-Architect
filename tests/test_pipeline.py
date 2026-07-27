"""End-to-end tests for the bounded consensus pipeline."""

import unittest

from orchestrator import AgentVerdict, run_consensus


def pass_verdict() -> AgentVerdict:
    return AgentVerdict(
        agent="performance",
        verdict="PASS",
        severity="info",
        risk=None,
        hard_rules_passed=1,
        hard_rules_total=1,
    )


def warn_verdict(risk: str = "Falta validar la recuperación ante fallos.") -> AgentVerdict:
    return AgentVerdict(
        agent="reliability",
        verdict="WARN",
        severity="warning",
        risk=risk,
        hard_rules_passed=1,
        hard_rules_total=1,
    )


def blocker(risk: str = "Falta cifrado en reposo.") -> AgentVerdict:
    return AgentVerdict(
        agent="security",
        verdict="FAIL",
        severity="blocker",
        risk=risk,
        hard_rules_passed=0,
        hard_rules_total=1,
    )


class ConsensusPipelineTests(unittest.TestCase):
    def test_converges_and_delivers_once_with_unique_accepted_risks(self) -> None:
        calls = {"architect": 0, "board": 0, "adr": []}

        def architect(context, rejected):
            calls["architect"] += 1
            self.assertEqual(rejected, ())
            return {"version": 1, "context_id": context["id"]}

        def review_board(context, candidate):
            calls["board"] += 1
            self.assertEqual(context["id"], "problem-1")
            self.assertEqual(candidate["version"], 1)
            return [warn_verdict("Riesgo operativo."), warn_verdict("Riesgo operativo.")]

        def adr(result):
            calls["adr"].append(result)

        result = run_consensus({"id": "problem-1"}, architect, review_board, adr)

        self.assertEqual(calls["architect"], 1)
        self.assertEqual(calls["board"], 1)
        self.assertEqual(len(calls["adr"]), 1)
        self.assertEqual(result.round_reached, 0)
        self.assertFalse(result.forced)
        self.assertEqual(result.accepted_risks, ["Riesgo operativo."])
        self.assertEqual(result.unresolved_risks, [])
        self.assertEqual(result.rejected, [])

    def test_reproposal_records_rejection_and_isolates_adapter_mutations(self) -> None:
        context = {"id": "problem-2", "nested": {"source": "caller"}}
        received_rejections = []
        delivered = []
        candidates = iter([{"version": 1, "nested": {"value": "old"}}, {"version": 2}])

        def architect(adapter_context, rejected):
            adapter_context["nested"]["source"] = "architect"
            if rejected:
                received_rejections.append(rejected)
                rejected[0]["candidate"]["nested"]["value"] = "tampered"
            return next(candidates)

        board_calls = 0

        def review_board(adapter_context, candidate):
            nonlocal board_calls
            board_calls += 1
            candidate["nested"] = {"value": "board-tampered"}
            if board_calls == 1:
                return [blocker("Primera razón.")]
            return [pass_verdict(), warn_verdict("Riesgo aceptado.")]

        def adr(result):
            result.architecture["version"] = 999
            delivered.append(result)

        result = run_consensus(context, architect, review_board, adr)

        self.assertEqual(context["nested"]["source"], "caller")
        self.assertEqual(result.architecture, {"version": 2})
        self.assertEqual(result.round_reached, 1)
        self.assertEqual(result.rejected[0]["rejected_round"], 0)
        self.assertEqual(result.rejected[0]["candidate"], {"version": 1, "nested": {"value": "old"}})
        self.assertEqual(result.rejected[0]["reasons"], ["Primera razón."])
        self.assertEqual(result.accepted_risks, ["Riesgo aceptado."])
        self.assertEqual(len(received_rejections), 1)
        self.assertEqual(delivered[0].architecture["version"], 999)

    def test_persistent_blockers_force_delivery_after_two_reproposals(self) -> None:
        generated = []
        delivered = []

        def architect(context, rejected):
            generated.append(len(rejected))
            return {"version": len(generated)}

        def review_board(context, candidate):
            return [blocker("Bloqueo {}.".format(candidate["version"]))]

        def adr(result):
            delivered.append(result)

        result = run_consensus({}, architect, review_board, adr)

        self.assertEqual(generated, [0, 1, 2])
        self.assertTrue(result.forced)
        self.assertEqual(result.round_reached, 2)
        self.assertEqual(result.architecture, {"version": 3})
        self.assertEqual(result.unresolved_risks, ["Bloqueo 3."])
        self.assertEqual(
            [entry["rejected_round"] for entry in result.rejected], [0, 1]
        )
        self.assertEqual(len(delivered), 1)

    def test_adapter_errors_propagate_without_adr_delivery(self) -> None:
        delivered = []

        def failing_board(context, candidate):
            raise RuntimeError("board unavailable")

        with self.assertRaisesRegex(RuntimeError, "board unavailable"):
            run_consensus(
                {},
                lambda context, rejected: {"version": 1},
                failing_board,
                lambda result: delivered.append(result),
            )
        self.assertEqual(delivered, [])


if __name__ == "__main__":
    unittest.main()
