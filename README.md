🎵 RhythmGen

RhythmGen is a Python rhythm game that lets you search YouTube videos using yt-dlp, automatically generates a beatmap from the audio, and plays the selected video in a corner window during gameplay. No API keys required.

✨ Features

YouTube Search (yt-dlp)
Search and select videos directly inside the app—no API setup.

Video Playback In-Game
The chosen video plays in the corner while you play.

Auto Beatmap Generation
Beatmaps are created from the audio using onset detection.
(Difficulty modes not yet implemented.)

Main Menu UI
Launch the game, search videos, select music, and start playing from a simple menu.

📦 Installation
1. Clone the Repository
git clone https://github.com/yourusername/RhythmGen.git
cd RhythmGen

2. Install Dependencies
pip install -r requirements.txt

3. Install FFmpeg

Required for yt-dlp and media playback.

macOS: brew install ffmpeg

Linux: sudo apt install ffmpeg

Windows: Download from ffmpeg.org and add to PATH.


▶️ Running the Game

Start the application:

python main.py


From the main menu, you can:

Search YouTube

Browse results

Select a video

Download + process audio

Generate a beatmap

Play the rhythm game with the video visible onscreen


🚧 Roadmap

Difficulty modes

Beatmap generation inprovements

UI polish

Support for albums and playlists
