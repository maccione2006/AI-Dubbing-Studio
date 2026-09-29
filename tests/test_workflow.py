import math
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from ai_dubbing_studio.core.models import GenerationProfile
from ai_dubbing_studio.core.workflow import (
    DubbingWorkflow,
    WorkflowError,
    compare_existing_candidates,
)


def write_tone(path: Path, duration: float, amplitude: float = 0.4) -> bytes:
    sample_rate = 22050
    sample_count = int(sample_rate * duration)
    samples = [
        int(amplitude * 32767 * math.sin(2 * math.pi * 220 * index / sample_rate))
        for index in range(sample_count)
    ]
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(sample_rate)
        target.writeframes(struct.pack(f"<{sample_count}h", *samples))
    return path.read_bytes()


class FakeSpeechProvider:
    def __init__(self, audio: bytes):
        self.audio = audio
        self.calls: list[tuple[str, str, GenerationProfile]] = []

    def generate_speech(self, text: str, voice_id: str, profile: GenerationProfile) -> bytes:
        self.calls.append((text, voice_id, profile))
        return self.audio


class FailingSpeechProvider(FakeSpeechProvider):
    def generate_speech(self, text: str, voice_id: str, profile: GenerationProfile) -> bytes:
        if self.calls:
            raise RuntimeError("provider unavailable")
        return super().generate_speech(text, voice_id, profile)


class WorkflowTests(unittest.TestCase):
    def test_generates_candidates_and_selects_best_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.wav"
            candidate_audio = write_tone(root / "generated.wav", 1.0)
            write_tone(source, 1.0)
            provider = FakeSpeechProvider(candidate_audio)
            progress: list[tuple[int, int, str]] = []

            result = DubbingWorkflow(provider).run(
                source,
                "We can test this line.",
                "test-voice",
                root / "output",
                progress=lambda current, total, name: progress.append((current, total, name)),
            )
            self.assertTrue(all(candidate.audio_path.exists() for candidate in result.candidates))

        self.assertEqual(len(result.candidates), 3)
        self.assertEqual(result.best_index, 0)
        self.assertEqual(len(provider.calls), 3)
        self.assertEqual(len(progress), 3)

    def test_rejects_blank_script_before_provider_call(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.wav"
            audio = write_tone(source, 0.5)
            provider = FakeSpeechProvider(audio)

            with self.assertRaisesRegex(ValueError, "script cannot be empty"):
                DubbingWorkflow(provider).run(source, "  ", "voice", root / "out")

        self.assertEqual(provider.calls, [])

    def test_preserves_and_reports_partial_output_after_provider_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.wav"
            audio = write_tone(source, 0.5)
            provider = FailingSpeechProvider(audio)

            with self.assertRaises(WorkflowError) as raised:
                DubbingWorkflow(provider).run(source, "Test line.", "voice", root / "out")

            failure = raised.exception
            self.assertEqual(failure.completed_candidates, 1)
            self.assertTrue((failure.output_directory / "candidate_01.wav").exists())
            self.assertIn(str(failure.output_directory), str(failure))

    def test_enforces_configured_candidate_limit_in_core(self):
        with self.assertRaisesRegex(ValueError, "between 1 and 2"):
            DubbingWorkflow(FakeSpeechProvider(b""), max_candidates=2).run(
                "missing.wav", "Test line.", "voice", "output", candidate_count=3
            )

    def test_compares_wav_candidates_downloaded_from_web(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.wav"
            exact = root / "candidate-exact.wav"
            longer = root / "candidate-longer.wav"
            write_tone(source, 1.0)
            write_tone(exact, 1.0)
            write_tone(longer, 1.3)

            result = compare_existing_candidates(
                source,
                "A short sample script.",
                [longer, exact],
            )

        self.assertEqual(result.best_index, 1)
        self.assertEqual(result.candidates[1].audio_path, exact)
        self.assertIsNone(result.candidates[1].profile)

    def test_requires_at_least_one_downloaded_candidate(self):
        with self.assertRaisesRegex(ValueError, "at least one candidate"):
            compare_existing_candidates("missing.wav", "Script", [])


if __name__ == "__main__":
    unittest.main()