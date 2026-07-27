"""Tests for the deterministic EDA-vs-recommendation router."""

import unittest

from architect.router import EDA_FIRST, RECOMMENDATION_ONLY, route


class RouterTests(unittest.TestCase):
    def test_dataset_present_triggers_eda(self) -> None:
        result = route("predecir precio", task="regression", has_dataset=True)
        self.assertEqual(result["recommended_path"], EDA_FIRST)
        self.assertTrue(result["eda_suggested"])

    def test_generative_goes_direct(self) -> None:
        result = route("chatbot sobre documentos PDF", task="nlp_generative")
        self.assertEqual(result["recommended_path"], RECOMMENDATION_ONLY)

    def test_vision_goes_direct(self) -> None:
        result = route("clasificar imágenes de productos", task="computer_vision")
        self.assertEqual(result["recommended_path"], RECOMMENDATION_ONLY)

    def test_tabular_with_data_mention_triggers_eda(self) -> None:
        result = route("predecir ventas a partir de un dataset etiquetado")
        self.assertEqual(result["recommended_path"], EDA_FIRST)
        self.assertEqual(result["family"], "regression")

    def test_conceptual_without_data_goes_direct(self) -> None:
        result = route("¿conviene regresión o clustering para mi caso?")
        self.assertEqual(result["recommended_path"], RECOMMENDATION_ONLY)


if __name__ == "__main__":
    unittest.main()
