import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from ai_dubbing_studio.audio.analysis import analyze_wav


def write_test_wav(path: Path, sections: list[tuple[float, float]]) -> None:
    sample_rate = 8000
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(sample_rate)
        for duration, amplitude in sections:
            samples = [
                int(amplitude * 32767 * math.sin(2 * math.pi * 220 * index / sample_rate))
                for index in range(int(duration * sample_rate))
            ]
            target.writeframes(struct.pack(f"<{len(samples)}h", *samples))


class AudioAnalysisTests(unittest.TestCase):
    def test_analyzes_duration_level_and_interior_pause(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.wav"
            write_test_wav(path, [(0.5, 0.5), (0.3, 0.0), (0.5, 0.5)])

            metrics = analyze_wav(path)

        self.assertAlmostEqual(metrics.duration_seconds, 1.3, places=2)
        self.assertGreater(metrics.rms_level, 0.1)
        self.assertLess(metrics.intensity_dbfs, 0)
        self.assertEqual(metrics.pause_count, 1)
        self.assertGreater(metrics.pause_ratio, 0.15)
        self.assertEqual(metrics.sample_rate, 8000)

    def test_rejects_empty_wav(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.wav"
            with wave.open(str(path), "wb") as target:
                target.setnchannels(1)
                target.setsampwidth(2)
                target.setframerate(8000)

            with self.assertRaisesRegex(ValueError, "no audio frames"):
                analyze_wav(path)

    def test_detects_pause_near_minimum_duration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "short-pause.wav"
            write_test_wav(path, [(0.47, 0.5), (0.18, 0.0), (0.51, 0.5)])

            metrics = analyze_wav(path)

        self.assertEqual(metrics.pause_count, 1)


if __name__ == "__main__":
    unittest.main()