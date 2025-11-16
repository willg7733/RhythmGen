# RhythmGen

RhythmGen downloads a YouTube track, generates a beatmap, and plays it in a four-lane rhythm game. The gameplay now keeps a full ASCII aesthetic while still rendering smoothly inside the Pygame window—lanes, hit lines, and notes are drawn as moving ASCII characters instead of shapes.

## Requirements

- Python 3.10+
- System packages required by `librosa`/`pygame`
- The Python dependencies listed in `requirements.txt`
- A terminal/window that can display the 800×1200 Pygame surface

Set up a virtual environment and install the dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

1. Run `python main.py` and paste a YouTube link when prompted. The script downloads the audio (to `audio.mp3`), generates a beatmap, and launches the ASCII-styled game window automatically.
2. If you already have assets, you can run the game directly:

```bash
python game.py beatmap.json audio.wav
```

## Controls & UI

- Lanes are labeled `[A] [S] [D] [F]` at the bottom of the window.
- Press the corresponding key when the ASCII notes (`[ ]` / `<=>`) reach the `====` hit line.
- The HUD in the top-left shows your score and combo, and you can close the window or hit the ESC key to quit.

Enjoy the retro ASCII vibe with the responsiveness of the original Pygame engine.
