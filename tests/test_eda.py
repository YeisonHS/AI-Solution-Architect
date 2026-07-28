"""Tests for the cache-level EDA sub-tool."""

import unittest

from architect.eda import EdaError, analyze_csv


CSV = (
    "id,precio,area,ciudad,activo\n"
    "1,100,50,BOG,true\n"
    "2,200,100,BOG,false\n"
    "3,300,150,MED,true\n"
    "4,400,200,MED,false\n"
    "5,500,250,CAL,true\n"
)


class EdaEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = analyze_csv(CSV)
        self.by_name = {c["name"]: c for c in self.report["columns"]}

    def test_rows_and_privacy(self) -> None:
        self.assertEqual(self.report["rows_analyzed"], 5)
        self.assertIn("no se almacenaron", self.report["privacy"])

    def test_column_types(self) -> None:
        self.assertEqual(self.by_name["id"]["type"], "id")
        self.assertEqual(self.by_name["precio"]["type"], "numeric")
        self.assertEqual(self.by_name["ciudad"]["type"], "enumerator")
        self.assertEqual(self.by_name["activo"]["type"], "boolean")

    def test_enumerator_encoding_and_map(self) -> None:
        ciudad = self.by_name["ciudad"]
        self.assertEqual(ciudad["encoding"], "one-hot")
        self.assertEqual(set(ciudad["encoding_map"].keys()), {"BOG", "MED", "CAL"})
        self.assertEqual(sorted(ciudad["encoding_map"].values()), [0, 1, 2])

    def test_numeric_stats_and_normalization(self) -> None:
        precio = self.by_name["precio"]
        self.assertEqual(precio["min"], 100)
        self.assertEqual(precio["max"], 500)
        self.assertIn("normalization", precio)
        self.assertEqual(precio["normalization"]["recommended"], "zscore")

    def test_perfect_correlation_detected(self) -> None:
        # precio and area are perfectly correlated.
        pair = next(
            (p for p in self.report["high_correlations"]
             if {p["a"], p["b"]} == {"precio", "area"}),
            None,
        )
        self.assertIsNotNone(pair)
        self.assertGreaterEqual(abs(pair["r"]), 0.99)

    def test_constant_column_flagged(self) -> None:
        report = analyze_csv("x,y\n1,7\n2,7\n3,7\n")
        by = {c["name"]: c for c in report["columns"]}
        self.assertEqual(by["y"]["type"], "constant")
        self.assertTrue(any("constante" in r.lower() for r in report["recommendations"]))

    def test_missing_values_counted(self) -> None:
        report = analyze_csv("a,b\n1,x\n2,\n3,y\n")
        by = {c["name"]: c for c in report["columns"]}
        self.assertEqual(by["b"]["n_missing"], 1)

    def test_empty_csv_rejected(self) -> None:
        with self.assertRaises(EdaError):
            analyze_csv("   ")

    def test_target_correlations_rank_features(self) -> None:
        csv = "years,bono,salary\n" + "\n".join(
            "{},{},{}".format(round(1.1 + i * 0.4, 1), i % 3, 30000 + i * 1500)
            for i in range(30)
        ) + "\n"
        report = analyze_csv(csv)
        tc = report["target_correlations"]
        self.assertTrue(tc)
        self.assertEqual(report["suggested_context"]["primary_target"], "salary")
        # years should correlate more strongly with salary than the noisy bono.
        by = {t["feature"]: abs(t["r"]) for t in tc}
        self.assertIn("years", by)
        self.assertGreater(by["years"], by.get("bono", 0))

    def test_date_column_flags_forecasting(self) -> None:
        csv = "fecha,ventas\n" + "\n".join(
            "2023-01-{:02d},{}".format((i % 28) + 1, 100 + i) for i in range(20)
        ) + "\n"
        report = analyze_csv(csv)
        by = {c["name"]: c for c in report["columns"]}
        self.assertEqual(by["fecha"]["type"], "datetime")
        self.assertEqual(report["date_columns"], ["fecha"])
        self.assertTrue(report["time_series_candidate"])
        self.assertTrue(any("forecasting" in r.lower() for r in report["recommendations"]))

    def test_high_missing_and_near_constant_flagged(self) -> None:
        # col a: 60% missing; col b: near-constant (dominant value); col c: target
        rows = []
        for i in range(20):
            a = "" if i % 5 != 0 else str(i)  # 80% missing
            b = "x" if i < 19 else "y"          # near constant
            rows.append("{},{},{}".format(a, b, 10 + i))
        csv = "a,b,c\n" + "\n".join(rows) + "\n"
        report = analyze_csv(csv)
        by = {c["name"]: c for c in report["columns"]}
        self.assertTrue(by["a"]["high_missing"])
        self.assertTrue(by["b"]["near_constant"])
        recs = " ".join(report["recommendations"]).lower()
        self.assertIn("faltantes", recs)
        self.assertIn("casi constantes", recs)

    def test_continuous_unique_column_is_not_id(self) -> None:
        # A continuous numeric column (all-unique) must NOT be treated as an id;
        # a sequential integer index must be. Correlation must be computed.
        csv = ",years,salary\n" + "\n".join(
            "{},{},{}".format(i, round(1.1 + i * 0.4, 1), 30000 + i * 1000)
            for i in range(25)
        ) + "\n"
        report = analyze_csv(csv)
        by = {c["name"]: c for c in report["columns"]}
        self.assertEqual(by["col_0"]["type"], "id")       # sequential index
        self.assertEqual(by["salary"]["type"], "numeric")  # continuous target
        self.assertEqual(by["years"]["type"], "numeric")
        pair = report["high_correlations"]
        self.assertTrue(pair)  # years vs salary are correlated
        self.assertEqual(report["suggested_context"]["primary_target"], "salary")
        self.assertEqual(report["suggested_context"]["suggested_task"], "regression")

    def test_target_suggestion_regression(self) -> None:
        # Last usable column is numeric -> regression.
        report = analyze_csv("ciudad,area,precio\nBOG,50,100\nMED,100,200\nCAL,150,300\n")
        ctx = report["suggested_context"]
        self.assertEqual(ctx["primary_target"], "precio")
        self.assertEqual(ctx["suggested_task"], "regression")
        cols = {c["column"]: c["suggested_task"] for c in ctx["target_candidates"]}
        self.assertEqual(cols["ciudad"], "classification")
        self.assertEqual(cols["area"], "regression")

    def test_target_suggestion_classification(self) -> None:
        report = analyze_csv("area,precio,segmento\n50,100,A\n100,200,B\n150,300,A\n")
        ctx = report["suggested_context"]
        self.assertEqual(ctx["primary_target"], "segmento")
        self.assertEqual(ctx["suggested_task"], "classification")


if __name__ == "__main__":
    unittest.main()
