"""Tests for classic ML problem families (regression, clustering, forecasting)."""

import unittest

from architect import Constraints, HardwareProfile, ProblemContext
from architect.decision import run_review, serialize_adr


def context(description, task=None, budget=None, rows=None):
    return ProblemContext(
        description=description,
        hardware=HardwareProfile(cpu_cores=8, ram_gb=16, unified_memory=True),
        constraints=Constraints(monthly_budget_usd=budget),
        task=task,
        dataset_labeled=True,
        dataset_rows=rows,
    )


class ClassicFamiliesTests(unittest.TestCase):
    def test_predict_value_detects_regression(self) -> None:
        data = serialize_adr(
            context("Quiero predecir el precio de una casa con datos etiquetados"),
            run_review(context("Quiero predecir el precio de una casa con datos etiquetados")),
        )
        self.assertEqual(data["problem"]["family"], "regression")
        keys = [t["key"] for t in data["technique_options"]]
        self.assertIn("gradient_boosting", keys)
        self.assertIn("linear_regression", keys)
        # Recommended technique is flagged.
        self.assertTrue(data["technique_options"][0]["recommended"])

    def test_explicit_clustering_task(self) -> None:
        ctx = context("Agrupar clientes", task="clustering")
        data = serialize_adr(ctx, run_review(ctx))
        self.assertEqual(data["problem"]["family"], "clustering")
        keys = [t["key"] for t in data["technique_options"]]
        self.assertIn("kmeans", keys)

    def test_deployment_options_have_costs(self) -> None:
        ctx = context("Predecir demanda", task="regression", budget=100)
        data = serialize_adr(ctx, run_review(ctx))
        self.assertTrue(data["deployment_options"])
        for option in data["deployment_options"]:
            self.assertIn("estimated_monthly_usd", option)
            self.assertIn("best_for", option)
            self.assertIsInstance(option["within_budget"], bool)

    def test_regression_recommends_and_fits_budget(self) -> None:
        ctx = context("Predecir ventas", task="regression", budget=100, rows=5000)
        data = serialize_adr(ctx, run_review(ctx))
        self.assertEqual(data["recommendation"]["strategy"], "gradient_boosting")
        self.assertIsNotNone(data["recommendation"]["deploy_target"])
        self.assertLessEqual(data["recommendation"]["estimated_monthly_usd"], 100)
        self.assertFalse(data["forced"])

    def test_forecasting_family_detected_from_keywords(self) -> None:
        ctx = context("Pronóstico de la demanda semanal de ventas")
        data = serialize_adr(ctx, run_review(ctx))
        self.assertEqual(data["problem"]["family"], "forecasting")

    def test_adr_includes_evaluation_per_family(self) -> None:
        from architect.catalog import FAMILY_LABELS

        for family in FAMILY_LABELS:
            ctx = context("caso", task=family, budget=5000)
            data = serialize_adr(ctx, run_review(ctx))
            ev = data["evaluation"]
            self.assertTrue(ev["metrics"] and ev["validation"] and ev["pitfalls"])
            self.assertTrue(ev["baseline"])

    def test_regression_metrics_present(self) -> None:
        ctx = context("predecir precio", task="regression")
        data = serialize_adr(ctx, run_review(ctx))
        names = [m["name"] for m in data["evaluation"]["metrics"]]
        self.assertIn("RMSE", names)

    def test_forecasting_validation_mentions_temporal(self) -> None:
        ctx = context("pronóstico de demanda", task="forecasting")
        data = serialize_adr(ctx, run_review(ctx))
        joined = " ".join(data["evaluation"]["validation"]).lower()
        self.assertIn("temporal", joined)

    def test_interpretability_prefers_simpler_technique(self) -> None:
        from architect import Constraints, HardwareProfile, ProblemContext

        ctx = ProblemContext(
            description="predecir precio",
            hardware=HardwareProfile(cpu_cores=8, ram_gb=16, unified_memory=True),
            constraints=Constraints(interpretability_required=True),
            task="regression",
        )
        data = serialize_adr(ctx, run_review(ctx))
        recommended = next(t for t in data["technique_options"] if t["recommended"])
        self.assertEqual(recommended["complexity"], "baja")
        self.assertEqual(data["recommendation"]["strategy"], "linear_regression")

    def test_serving_mode_batch_selects_batch_transform(self) -> None:
        from architect import Constraints, HardwareProfile, ProblemContext

        ctx = ProblemContext(
            description="predecir precio",
            hardware=HardwareProfile(cpu_cores=8, ram_gb=16, unified_memory=True),
            constraints=Constraints(serving_mode="batch"),
            task="regression",
        )
        data = serialize_adr(ctx, run_review(ctx))
        self.assertEqual(data["recommendation"]["deploy_target"], "batch_transform")

    def test_catalog_depth_and_invariants(self) -> None:
        from architect.catalog import FAMILY_LABELS, techniques_for

        for family in FAMILY_LABELS:
            options = techniques_for(family)
            self.assertGreaterEqual(len(options), 3, family)
            keys = [t.key for t in options]
            self.assertEqual(len(keys), len(set(keys)), "claves duplicadas en " + family)
            for t in options:
                self.assertTrue(t.name and t.summary and t.when_to_use)
                self.assertTrue(t.frameworks)
                self.assertIn(t.complexity, ("baja", "media", "alta"))

    def test_all_families_produce_a_recommendation(self) -> None:
        from architect.catalog import FAMILY_LABELS

        for family in FAMILY_LABELS:
            ctx = context("caso", task=family, budget=5000)
            data = serialize_adr(ctx, run_review(ctx))
            self.assertEqual(data["problem"]["family"], family)
            self.assertTrue(data["recommendation"]["strategy"])
            self.assertTrue(data["technique_options"][0]["recommended"])


if __name__ == "__main__":
    unittest.main()
