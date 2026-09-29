from __future__ import annotations

import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AudioMetrics:
    duration_seconds: float
    rms_level: float
    intensity_dbfs: float
    pause_ratio: float
    pause_count: int
    sample_rate: int
    channels: int


def _sample_values(raw: bytes, sample_width: int) -> list[int]:
    if sample_width == 1:
        return [value - 128 for value in raw]
    if sample_width == 2:
        return [value[0] for value in struct.iter_unpack("<h", raw)]
    if sample_width == 3:
        return [
            int.from_bytes(raw[offset : offset + 3], "little", signed=True)
            for offset in range(0, len(raw), 3)
        ]
    if sample_width == 4:
        return [value[0] for value in struct.iter_unpack("<i", raw)]
    raise ValueError(f"Unsupported PCM sample width: {sample_width} bytes")


def analyze_wav(path: str | Path) -> AudioMetrics:
    """Measure duration, level, and interior silence in an uncompressed PCM WAV."""
    with wave.open(str(path), "rb") as source:
        if source.getcomptype() != "NONE":
            raise ValueError("Only uncompressed PCM WAV files are supported.")

        channels = source.getnchannels()
        sample_rate = source.getframerate()
        sample_width = source.getsampwidth()
        frame_count = source.getnframes()
        if channels < 1 or sample_rate < 1 or frame_count < 1:
            raise ValueError("The WAV file contains no audio frames.")

        block_frames = max(1, sample_rate // 100)
        blocks: list[tuple[int, int, float]] = []
        total_square = 0
        total_samples = 0
        peak_level = 0.0
        frame_offset = 0

        while raw := source.readframes(block_frames):
            samples = _sample_values(raw, sample_width)
            if not samples:
                continue
            square_sum = sum(sample * sample for sample in samples)
            level = math.sqrt(square_sum / len(samples)) / (2 ** (sample_width * 8 - 1))
            current_frames = len(samples) // channels
            blocks.append((frame_offset, frame_offset + current_frames, level))
            frame_offset += current_frames
            total_square += square_sum
            total_samples += len(samples)
            peak_level = max(peak_level, level)

    if not total_samples:
        raise ValueError("The WAV file contains no decodable PCM samples.")

    silence_threshold = max(0.001, peak_level * 0.08)
    silent_groups: list[tuple[int, int]] = []
    group_start: int | None = None
    group_end = 0
    for start, end, level in blocks:
        if level < silence_threshold:
            if group_start is None:
                group_start = start
            group_end = end
        elif group_start is not None:
            silent_groups.append((group_start, group_end))
            group_start = None
    if group_start is not None:
        silent_groups.append((group_start, group_end))

    min_pause_frames = int(sample_rate * 0.18)
    interior_pauses = [
        (start, end)
        for start, end in silent_groups
        if end - start + block_frames >= min_pause_frames
        and start > 0
        and end < frame_count
    ]
    paused_frames = sum(end - start for start, end in interior_pauses)
    duration = frame_count / sample_rate
    rms_level = math.sqrt(total_square / total_samples) / (2 ** (sample_width * 8 - 1))
    intensity_dbfs = 20 * math.log10(rms_level) if rms_level > 0 else -120.0

    return AudioMetrics(
        duration_seconds=duration,
        rms_level=rms_level,
        intensity_dbfs=intensity_dbfs,
        pause_ratio=paused_frames / frame_count,
        pause_count=len(interior_pauses),
        sample_rate=sample_rate,
        channels=channels,
    )