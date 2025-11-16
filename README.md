# RhythmGen

RhythmGen downloads a YouTube track, generates a beatmap with `librosa`, and launches a Pygame-powered rhythm game complete with scoring, feedback, and a sidebar spectrum visualizer.

## Requirements

- Python 3.10+
- FFmpeg on your PATH (required by `yt-dlp` for conversion)
- System packages needed by SDL/Pygame (on Debian/Ubuntu: `sudo apt install libsdl2-dev libportmidi-dev`)
- Python dependencies from `requirements.txt`

Install Python dependencies into the provided virtual environment (recommended):

```bash
cd /home/faus/Code/RhythmGen
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
cd /home/faus/Code/RhythmGen
source .venv/bin/activate  # or use the provided interpreter path
python main.py
```

1. Paste a YouTube URL when prompted.
2. Wait for the audio download and beatmap generation to finish.
3. Play the song using the **A / S / D / F** keys to hit the four lanes.

## Visualizer

The sidebar equalizer now analyzes the same audio file that was downloaded for gameplay. Each frame it slices the song based on the current playback time, computes an FFT, and maps the energy into eight frequency bands using a logarithmic scale. This keeps the visualizer perfectly in sync with the music without requiring a live microphone input.

## Troubleshooting

- If the download step fails, ensure FFmpeg is installed and accessible.
- If the game window opens without audio, confirm your system mixer can play the decoded WAV/MP3 file.
- If SDL reports missing libraries, install the platform-specific runtime dependencies referenced above.
