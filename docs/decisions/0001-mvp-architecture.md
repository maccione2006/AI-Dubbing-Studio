# ADR 0001: MVP architecture

- Status: accepted
- Date: 2026-09-29

## Context

The target environment is Windows with Python 3.12, about 6 GB of RAM, and no
FFmpeg executable. Tkinter and Ollama are available, but the installed Ollama
models are text-only and cannot score audio performance. Voice and setting
selection should happen on the official ElevenLabs site without app-managed
API credentials.

## Decisions

- Use Tkinter for the desktop UI; it ships with the supported Python install
  and adds no runtime dependency.
- Start with PCM WAV input/output and analyze it with Python's `wave` module.
  Broader codecs can be added later behind an optional decoder when a supported
  FFmpeg installation is available.
- Keep audio analysis, candidate scoring, and UI in separate modules. The app
  does not make speech-generation API calls.
- Use a browser handoff to the official ElevenLabs site. Copy the script to the
  clipboard and open the site; the user selects a voice/settings and generates
  there, then imports downloaded WAV files for local comparison. Do not automate
  sign-in, cookies, or undocumented website controls, and do not store an API
  key in the app.
- Let the user generate any number of takes on the site. Score measurable
  duration, pause ratio, speech rate, and intensity against the source with
  explicit weights. Report voice
  identity similarity, pronunciation, emotion, and performance style as
  unavailable until an appropriate local or provider-backed evaluator exists;
  do not present proxies as those measurements.
- Do not invoke Ollama for audio work or download models automatically.
- Keep VEGAS integration out of the MVP and reserve it as a future optional
  adapter, isolated from the core.

## Implementation sequence

1. Add chunked WAV metrics and focused tests.
2. Add candidate comparison/selection for WAVs downloaded from the site.
3. Add a desktop workflow for audio, script, browser handoff, and comparison.
4. Validate imports and tests without requiring an API key or network.
5. Document supported formats, setup, limitations, privacy, and future work.

## Risks and limits

- The first release supports uncompressed PCM WAV only; compressed audio needs
  an optional decoder.
- ElevenLabs is a third-party service that may charge for use. The user
  explicitly starts each generation on the official website.
- Duration/pause/intensity are acoustic proxies, not a replacement for
  transcription, phoneme alignment, speaker embeddings, or emotion recognition.
- Tkinter availability depends on the Python distribution; the current
  Windows installation includes it.