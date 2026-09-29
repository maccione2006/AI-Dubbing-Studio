from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol

from ai_dubbing_studio.audio.analysis import AudioMetrics, analyze_wav
from ai_dubbing_studio.core.comparison import CandidateAssessment, compare_audio, select_best_candidate
from ai_dubbing_studio.core.models import GenerationProfile, candidate_profiles


class SpeechProvider(Protocol):
    def generate_speech(
        self,
        text: str,
        voice_id: str,
        profile: GenerationProfile,
    ) -> bytes: ...


class WorkflowError(RuntimeError):
    def __init__(self, message: str, output_directory: Path, completed_candidates: int) -> None:
        super().__init__(message)
        self.output_directory = output_directory
        self.completed_candidates = completed_candidates


@dataclass(frozen=True)
class CandidateResult:
    profile: GenerationProfile | None
    audio_path: Path
    audio_metrics: AudioMetrics
    assessment: CandidateAssessment


@dataclass(frozen=True)
class WorkflowResult:
    source_metrics: AudioMetrics
    candidates: tuple[CandidateResult, ...]
    best_index: int
    output_directory: Path


ProgressCallback = Callable[[int, int, str], None]


def compare_existing_candidates(
    source_audio: str | Path,
    script: str,
    candidate_audio_paths: list[str | Path],
) -> WorkflowResult:
    cleaned_script = script.strip()
    if not cleaned_script:
        raise ValueError("The script cannot be empty.")
    if not candidate_audio_paths:
        raise ValueError("Select at least one candidate WAV file.")

    source_metrics = analyze_wav(source_audio)
    word_count = len(cleaned_script.split())
    candidates: list[CandidateResult] = []
    paths = [Path(path) for path in candidate_audio_paths]
    for path in paths:
        metrics = analyze_wav(path)
        candidates.append(
            CandidateResult(
                profile=None,
                audio_path=path,
                audio_metrics=metrics,
                assessment=compare_audio(source_metrics, metrics, word_count),
            )
        )

    assessments = [candidate.assessment for candidate in candidates]
    return WorkflowResult(
        source_metrics=source_metrics,
        candidates=tuple(candidates),
        best_index=select_best_candidate(assessments),
        output_directory=paths[0].parent,
    )


class DubbingWorkflow:
    def __init__(self, provider: SpeechProvider, max_candidates: int = 10) -> None:
        self._provider = provider
        if not 1 <= max_candidates <= 10:
            raise ValueError("Maximum candidate count must be between 1 and 10.")
        self._max_candidates = max_candidates

    def run(
        self,
        source_audio: str | Path,
        script: str,
        voice_id: str,
        output_root: str | Path,
        candidate_count: int = 3,
        progress: ProgressCallback | None = None,
    ) -> WorkflowResult:
        cleaned_script = script.strip()
        if not cleaned_script:
            raise ValueError("The script cannot be empty.")
        if len(cleaned_script) > 5000:
            raise ValueError("The script exceeds the 5000-character provider limit.")
        if not voice_id.strip():
            raise ValueError("Choose a voice before generating audio.")

        profiles = candidate_profiles(candidate_count, self._max_candidates)
        source_metrics = analyze_wav(source_audio)
        output_directory = self._create_output_directory(Path(output_root))
        word_count = len(cleaned_script.split())
        candidates: list[CandidateResult] = []

        for index, profile in enumerate(profiles, start=1):
            if progress:
                progress(index, len(profiles), profile.name)
            try:
                audio = self._provider.generate_speech(cleaned_script, voice_id.strip(), profile)
                if not audio:
                    raise ValueError("The provider returned no audio data.")
                audio_path = output_directory / f"candidate_{index:02d}.wav"
                with audio_path.open("xb") as output_file:
                    output_file.write(audio)
                metrics = analyze_wav(audio_path)
                candidates.append(
                    CandidateResult(
                        profile=profile,
                        audio_path=audio_path,
                        audio_metrics=metrics,
                        assessment=compare_audio(source_metrics, metrics, word_count),
                    )
                )
            except Exception as error:
                raise WorkflowError(
                    f"Generation stopped at candidate {index}/{len(profiles)}: {error} "
                    f"{len(candidates)} completed candidate(s) are preserved in {output_directory}.",
                    output_directory,
                    len(candidates),
                ) from error

        best_index = select_best_candidate([candidate.assessment for candidate in candidates])
        return WorkflowResult(
            source_metrics=source_metrics,
            candidates=tuple(candidates),
            best_index=best_index,
            output_directory=output_directory,
        )

    @staticmethod
    def _create_output_directory(output_root: Path) -> Path:
        output_root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_directory = output_root / f"dubbing_{timestamp}"
        output_directory.mkdir()
        return output_directory