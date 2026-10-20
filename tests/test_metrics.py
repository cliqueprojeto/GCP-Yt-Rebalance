from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audio_metrics import compare


class MetricsTests(unittest.TestCase):
    def test_identical_and_silence(self):
        result = compare(np.zeros((2, 10)), np.zeros((2, 10)))
        self.assertTrue(result["exact"])
        self.assertEqual(result["rmse"], 0)
        self.assertIsNone(result["snr_db"])

    def test_gain_change_is_detected(self):
        result = compare([0.25, -0.25], [0.5, -0.5])
        self.assertAlmostEqual(result["snr_db"], 0)
        self.assertEqual(result["max_abs_error"], 0.25)

    def test_truncation_and_invalid_samples_rejected(self):
        for a, b in [([0, 1], [0]), ([0], [np.nan]), ([], [])]:
            with self.assertRaises(ValueError):
                compare(a, b)

    def test_clipping_evidence(self):
        self.assertEqual(compare([0, 0], [1.01, -1.01])["candidate_over_full_scale"], 2)
