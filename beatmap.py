import librosa
import numpy as np
import random

def generate_beatmap(audio_path, lanes=4):
    y, sr = librosa.load(audio_path)

    # Detect beats
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beats, sr=sr)

    # Create notes with random lane assignment
    notes = []
    for t in beat_times:
        notes.append({
            "time": float(t),
            "lane": random.randint(0, lanes - 1)
        })

    return notes

if __name__ == "__main__":
    notes = generate_beatmap("audio.mp3")
    print(notes[:20])

