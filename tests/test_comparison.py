import unittest

from ai_dubbing_studio.audio.analysis import AudioMetrics
from ai_dubbing_studio.core.comparison import compare_audio, select_best_candidate
from ai_dubbing_studio.core.models import candidate_profiles


def metrics(duration: float, pauses: float, level: float) -> AudioMetrics:
    return AudioMetrics(duration, 0.1, level, pauses, 1, 22050, 1)


class ComparisonTests(unittest.TestCase):
    def test_exact_match_scores_highest_and_reports_unavailable_metrics(self):
        original = metrics(3.0, 0.1, -20.0)
        exact = compare_audio(original, original, 8)
        slower = compare_audio(original, metrics(4.0, 0.2, -24.0), 8)

        self.assertEqual(exact.score, 100.0)
        self.assertLess(slower.score, exact.score)
        self.assertEqual(select_best_candidate([slower, exact]), 1)
        self.assertIn("voice similarity", exact.explanation)

    def test_candidate_count_is_configurable_and_bounded(self):
        self.assertEqual(len(candidate_profiles(3)), 3)
        with self.assertRaises(ValueError):
            candidate_profiles(0)
        with self.assertRaisesRegex(ValueError, "between 1 and 4"):
            candidate_profiles(5, maximum=4)


if __name__ == "__main__":
    unittest.main()