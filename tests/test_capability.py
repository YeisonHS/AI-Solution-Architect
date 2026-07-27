"""Tests for the deterministic AI Capability Matrix."""

import unittest

from architect import HardwareProfile, capability_matrix


def matrix_by_technique(hardware):
    return {entry.technique: entry for entry in capability_matrix(hardware)}


class CapabilityMatrixTests(unittest.TestCase):
    def test_laptop_recommends_rag_not_fine_tuning(self) -> None:
        laptop = HardwareProfile(
            cpu_cores=10, ram_gb=16, has_gpu=False, unified_memory=True
        )
        matrix = matrix_by_technique(laptop)
        self.assertTrue(matrix["rag"].recommended)
        self.assertGreaterEqual(matrix["rag"].score, 90)
        self.assertFalse(matrix["fine_tuning"].recommended)
        self.assertLess(matrix["fine_tuning"].score, 40)
        # Fine-tuning must rank below RAG on this machine.
        self.assertGreater(matrix["rag"].score, matrix["fine_tuning"].score)

    def test_gpu_server_enables_training(self) -> None:
        server = HardwareProfile(
            cpu_cores=16, ram_gb=64, has_gpu=True, vram_gb=48, storage_gb=1000
        )
        matrix = matrix_by_technique(server)
        self.assertEqual(matrix["rag"].score, 100)
        self.assertTrue(matrix["fine_tuning"].recommended)
        self.assertEqual(matrix["fine_tuning"].score, 100)

    def test_scores_are_deterministic_and_bounded(self) -> None:
        hardware = HardwareProfile(cpu_cores=8, ram_gb=32, has_gpu=True, vram_gb=16)
        first = capability_matrix(hardware)
        second = capability_matrix(hardware)
        self.assertEqual(
            [(e.technique, e.score) for e in first],
            [(e.technique, e.score) for e in second],
        )
        for entry in first:
            self.assertGreaterEqual(entry.score, 0)
            self.assertLessEqual(entry.score, 100)


if __name__ == "__main__":
    unittest.main()
