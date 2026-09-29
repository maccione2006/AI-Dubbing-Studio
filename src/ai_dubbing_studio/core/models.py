from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationProfile:
    name: str
    stability: float
    style: float
    speed: float


@dataclass(frozen=True)
class VoiceOption:
    voice_id: str
    name: str


def candidate_profiles(count: int, maximum: int = 10) -> list[GenerationProfile]:
    if not 1 <= maximum <= 10:
        raise ValueError("Maximum candidate count must be between 1 and 10.")
    if not 1 <= count <= maximum:
        raise ValueError(f"Candidate count must be between 1 and {maximum}.")

    presets = [
        GenerationProfile("Balanced", 0.50, 0.00, 1.00),
        GenerationProfile("Expressive", 0.35, 0.25, 0.95),
        GenerationProfile("Controlled", 0.65, 0.05, 1.05),
    ]
    profiles = presets[:count]
    while len(profiles) < count:
        index = len(profiles)
        profiles.append(
            GenerationProfile(
                f"Variation {index + 1}",
                stability=0.4 + (index % 4) * 0.08,
                style=(index % 4) * 0.08,
                speed=1.0 + ((index % 3) - 1) * 0.05,
            )
        )
    return profiles