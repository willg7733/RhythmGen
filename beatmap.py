import librosa
import numpy as np

def generate_beatmap(path, difficulty=0.16, lanes=4):
    """
    Simple beatmap generator.
    
    Parameters:
    - path: audio file path
    - difficulty: minimum seconds between notes (larger = easier)
    - lanes: number of lanes (fixed intensity mapping)
    
    Notes are quantized to 16th notes.
    """
    y, sr = librosa.load(path, sr=22050, mono=True)
    if y.size == 0:
        return []

    duration = len(y) / sr

    # --- Beat tracking ---
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    if len(beats) >= 2:
        beat_times = librosa.frames_to_time(beats, sr=sr)
        # build full 16th-note grid
        sixteenth_grid = []
        for i in range(len(beat_times) - 1):
            interval = (beat_times[i+1] - beat_times[i]) / 4.0
            sixteenth_grid.extend([beat_times[i] + j*interval for j in range(4)])
        sixteenth_grid.append(beat_times[-1])
    else:
        # fallback evenly spaced grid
        grid_interval = max(0.125, difficulty)
        sixteenth_grid = np.arange(0.0, duration, grid_interval)

    # --- RMS peaks ---
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

    # --- Base notes (beats) ---
    if len(beats):
        base = [{"time": float(t), "energy": 0.0} for t in beat_times]
    else:
        base = []

    # --- Merge all candidates ---
    all_cands = base + peaks

    # --- Snap to nearest 16th-note ---
    for c in all_cands:
        nearest = min(sixteenth_grid, key=lambda t: abs(t - c["time"]))
        c["time"] = round(nearest, 4)

    # --- Remove duplicates (keep strongest energy) ---
    merged = sorted({c["time"]: c for c in all_cands}.values(), key=lambda x: x["time"])

    # --- Intensity -> lane mapping ---
    energies = np.array([c.get("energy", 0.0) for c in merged])
    if energies.size and energies.max() > energies.min():
        norm = (energies - energies.min()) / (energies.max() - energies.min())
    else:
        norm = np.zeros_like(energies)

    # --- Enforce difficulty spacing & lane rules ---
    notes = []
    last_t = -1e9
    last_lane = None
    for c, v in zip(merged, norm):
        t = c["time"]
        if t - last_t < difficulty:
            continue

        lane = int(v * lanes)
        lane = max(0, min(lanes - 1, lane))

        # avoid repeating same lane
        if last_lane is not None and lane == last_lane:
            lane = (lane + 1) % lanes

        notes.append({"time": t, "lane": lane})
        last_t = t
        last_lane = lane

    # --- Ensure start/end coverage ---
    if not notes:
        notes = [{"time": 0.1, "lane": 0}, {"time": round(max(0.2, duration - 0.05), 4), "lane": lanes - 1}]
    else:
        if notes[0]["time"] > 0.25:
            notes.insert(0, {"time": 0.1, "lane": 0})
        end_t = round(max(0.05, duration - 0.05), 4)
        if notes[-1]["time"] < duration - 0.25:
            notes.append({"time": end_t, "lane": lanes - 1})

    return notes