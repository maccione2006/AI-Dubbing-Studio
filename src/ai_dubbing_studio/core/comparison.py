from __future__ import annotations

from dataclasses import dataclass

from ai_dubbing_studio.audio.analysis import AudioMetrics


@dataclass(frozen=True)
class MetricScore:
    name: str
    score: float
    original_value: float
    candidate_value: float
    unit: str


@dataclass(frozen=True)
class CandidateAssessment:
    score: float
    metrics: tuple[MetricScore, ...]
    unavailable_metrics: tuple[str, ...]

    @property
    def explanation(self) -> str:
        changes = "; ".join(
            f"{metric.name}: {metric.original_value:.2f}{metric.unit} -> "
            f"{metric.candidate_value:.2f}{metric.unit} (similarity {metric.score:.0f}%)"
            for metric in self.metrics
        )
        return (
            f"Score {self.score:.1f}/100. {changes}. "
            "Not automatically evaluated: " + ", ".join(self.unavailable_metrics) + "."
        )


def _similarity(relative_or_absolute_difference: float) -> float:
    return max(0.0, 100.0 - relative_or_absolute_difference)


def compare_audio(
    original: AudioMetrics,
    candidate: AudioMetrics,
    script_word_count: int,
) -> CandidateAssessment:
    if script_word_count < 1:
        raise ValueError("The script must contain at least one word.")

    duration_difference = (
        abs(candidate.duration_seconds - original.duration_seconds)
        / max(original.duration_seconds, 0.1)
        * 100
    )
    pause_difference = abs(candidate.pause_ratio - original.pause_ratio) * 100
    original_speech_time = original.duration_seconds * max(1.0 - original.pause_ratio, 0.1)
    candidate_speech_time = candidate.duration_seconds * max(1.0 - candidate.pause_ratio, 0.1)
    original_rate = script_word_count * 60 / max(original_speech_time, 0.1)
    candidate_rate = script_word_count * 60 / max(candidate_speech_time, 0.1)
    rate_difference = abs(candidate_rate - original_rate) / max(original_rate, 1.0) * 100
    intensity_difference = abs(candidate.intensity_dbfs - original.intensity_dbfs) * 5

    metrics = (
        MetricScore(
            "Duration",
            _similarity(duration_difference),
            original.duration_seconds,
            candidate.duration_seconds,
            "s",
        ),
        MetricScore(
            "Pauses",
            _similarity(pause_difference),
            original.pause_ratio * 100,
            candidate.pause_ratio * 100,
            "%",
        ),
        MetricScore(
            "Rhythm (script words/min)",
            _similarity(rate_difference),
            original_rate,
            candidate_rate,
            " wpm",
        ),
        MetricScore(
            "Intensity",
            _similarity(intensity_difference),
            original.intensity_dbfs,
            candidate.intensity_dbfs,
            " dBFS",
        ),
    )
    weights = (0.35, 0.25, 0.20, 0.20)
    overall = sum(metric.score * weight for metric, weight in zip(metrics, weights))
    return CandidateAssessment(
        score=overall,
        metrics=metrics,
        unavailable_metrics=(
            "voice similarity",
            "pronunciation",
            "emotion",
            "performance style",
        ),
    )


def select_best_candidate(
    assessments: list[CandidateAssessment],
) -> int:
    if not assessments:
        raise ValueError("At least one candidate assessment is required.")
    return max(range(len(assessments)), key=lambda index: assessments[index].score)