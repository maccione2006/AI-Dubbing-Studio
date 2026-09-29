# AI Dubbing Studio

AI Dubbing Studio is a free, open-source desktop application that assists with
audio dubbing. The long-term goal is to analyze an original performance and its
script, help produce and compare alternate voice takes, and select the best
technical match. The current MVP is intentionally smaller: it analyzes PCM WAV
files locally, hands script text to the official ElevenLabs website, and ranks
WAV takes that the user downloads from that site.

The application is licensed under MIT. ElevenLabs is an independent service;
an account may be required and its generation features may incur charges.

## Current MVP

- Desktop interface built with Python and Tkinter.
- Load a script from a text file or enter it in the app.
- Analyze uncompressed PCM WAV audio locally for duration, silence pauses, RMS
	intensity, sample rate, and channels.
- Copy the script and open the official ElevenLabs speech-synthesis page in the
	browser. The user signs in, chooses a voice and generation parameters, and
	generates/downloads takes on the site.
- Import multiple downloaded PCM WAV candidates, compare them to the source,
	rank them using explicit acoustic metrics, and open the selected take.

The app does not automate website sign-in or clicks, does not store an
ElevenLabs API key, and does not upload the source audio. The script is copied
to the clipboard; the user pastes it into the website. Voice identity
similarity, pronunciation, emotion, and acting style are not yet automatically
measured. The comparison is a technical acoustic ranking, not a judgment of
translation quality or artistic performance.

## Requirements

- Windows, macOS, or Linux with Python 3.10 or newer and Tkinter.
- A web browser and ElevenLabs account only when generating takes on the site.
- No FFmpeg, GPU, API key, or local language model is required by the MVP.

Only uncompressed PCM WAV is supported for analysis and candidate import. MP3
and other compressed formats are not decoded yet.

## Installation

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m ai_dubbing_studio
```

This uses the virtual environment's Python directly, so activation and changes
to the PowerShell execution policy are not needed.

### macOS or Linux

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m ai_dubbing_studio
```

Tkinter must be present in the selected Python distribution. No `.env` file is
needed to run with the default settings. To customize paths, copy
`.env.example` to `.env`; local environment files are excluded from Git.

## Using The MVP

1. Select the original PCM WAV and choose **Analyze audio**.
2. Enter the script or load a `.txt` file.
3. Choose **Copy script and open ElevenLabs**. Paste the script on the official
	 site, choose the voice and parameters, generate the desired number of takes,
	 then download them as PCM WAV files.
4. Return to the desktop app, choose **Import downloaded WAVs**, select the
	 takes, and choose **Compare candidates**.
5. Review the scores and metric differences. The highest-scoring take is marked
	 as the best technical match; open it to listen in the system's audio player.

The app compares any number of imported takes. Its weighted score uses
duration (35%), pause ratio (25%), estimated speech rate outside silence (20%),
and RMS intensity (20%). The score and measured source/candidate values are
shown for each take. Since voice and generation parameters are selected on the
website, the app cannot currently explain parameter changes between takes.

## Configuration

Optional local settings are read from environment variables or `.env`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATA_DIR` | `data` | Application data directory |
| `TEMP_DIR` | `tmp` | Reserved temporary-data directory |
| `MODEL_CACHE_DIR` | `models` | Reserved local model cache |
| `USE_VEGAS_INTEGRATION` | `false` | Reserved; VEGAS integration is not implemented |

The MVP does not request an ElevenLabs API key. Login and generation take place
on the official website in the user's browser.

## Planned Work

The project is incomplete. The following goals are not implemented yet:

- Support common compressed audio formats through an optional decoder.
- Analyze speech segments, timing, pauses, cadence, pronunciation, and delivery
	in more detail; align script text to the source performance.
- Evaluate voice compatibility and compare speaker similarity, pronunciation,
	rhythm, intensity, emotion, and acting style using valid measurements rather
	than acoustic proxies.
- Explain differences between takes, including voice and generation settings
	when those details are available from the selected workflow.
- Improve candidate management, playback, and project/session persistence.
- Add VEGAS Pro import/placement as a separate optional integration, never a
	dependency of the core application.

The small Ollama models available on the initial target computer are text-only
and are not used as audio evaluators. The application does not download models
automatically. ElevenLabs stays a user-controlled website workflow in the MVP;
any future automation must use a supported, permitted integration and must not
take over the user's login session.

## Tests

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Tests use generated WAV fixtures and local fakes. They do not require an
ElevenLabs account, API key, or network access.

## Architecture

The UI is under `src/ai_dubbing_studio/ui`; WAV analysis and comparison logic
are separated into `audio` and `core`. Browser handoff is deliberate: the app
does not drive undocumented website controls. VEGAS remains future optional
work. See `docs/decisions/0001-mvp-architecture.md` for the initial design
decisions and constraints.
