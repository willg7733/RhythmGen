import librosa
import numpy as np
import math

def generate_beatmap(path, difficulty=0.2, lanes=4):
    """
    Generate a simple beatmap with a single difficulty parameter.
    difficulty: minimum seconds between notes (bigger = easier)
    """
    y, sr = librosa.load(path, sr=22050, mono=True)
    if y.size == 0:
        return []

    duration = len(y) / sr

    # Beat backbone
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    if len(beats):
        beat_times = librosa.frames_to_time(beats, sr=sr)
    else:
        # fallback evenly spaced grid
        beat_times = np.linspace(0.5, max(0.5, duration - 0.5),
                                 num=max(1, int(duration / max(0.5, difficulty))))

    # Intensity peaks
    rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=256, center=True)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=256, n_fft=1024)
    padded = np.concatenate(([-np.inf], rms, [-np.inf]))
    is_peak = (rms > padded[:-2]) & (rms > padded[2:])
    nz = rms[rms > 0]
    thresh = float(np.percentile(nz, 75)) if nz.size else 0.0

    peaks = [
        {"time": float(times[i]), "energy": float(rms[i])}
        for i in np.where(is_peak & (rms >= thresh))[0]
        if 0.05 < times[i] < duration - 0.05
    ]

    # Base notes
    base = [{"time": float(t), "energy": 0.0} for t in beat_times]

    # Merge & dedupe
    bucket = {}
    for c in base + peaks:
        k = int(round(c["time"] * 1000))
        if k not in bucket or c["energy"] > bucket[k]["energy"]:
            bucket[k] = c
    merged = sorted(bucket.values(), key=lambda x: x["time"])

    # Lane mapping = intensity
    energies = np.array([c["energy"] for c in merged])
    if energies.size and energies.max() > energies.min():
        norm = (energies - energies.min()) / (energies.max() - energies.min())
    else:
        norm = np.zeros_like(energies)

    notes = []
    last_t = -1e9
    last_lane = None
    for c, v in zip(merged, norm):
        t = c["time"]
        if t - last_t < difficulty:
            continue

        lane = int(math.floor(v * lanes))
        lane = max(0, min(lanes - 1, lane))

        # avoid repeating same lane
        if last_lane is not None and lane == last_lane:
            lane = (lane + 1) % lanes

        notes.append({"time": round(t, 4), "lane": lane})
        last_t = t
        last_lane = lane

    # Ensure start/end coverage
    if not notes:
        notes = [{"time": 0.1, "lane": 0},
                 {"time": round(max(0.2, duration - 0.05), 4), "lane": lanes - 1}]
    else:
        if notes[0]["time"] > 0.25:
            notes.insert(0, {"time": 0.1, "lane": 0})
        end_t = round(max(0.05, duration - 0.05), 4)
        if notes[-1]["time"] < duration - 0.25:
            notes.append({"time": end_t, "lane": lanes - 1})

    return notes