import librosa
import numpy as np

def generate_beatmap(path, difficulty=0.25, lanes=4):
    y, sr = librosa.load(path, sr=22050, mono=True)
    if y.size == 0:
        return []

    duration = len(y) / sr

    # --- Onset detection ---
    # These are the "real" rhythmic events, not tied to a constant tempo
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env, 
        sr=sr,
        units='frames',
        # These parameters help filter noise. You may need to tune them.
        wait=1,         # min frames between onsets (approx 23ms)
        pre_avg=1,      # frames for pre-averaging
        post_avg=1,     # frames for post-averaging
        delta=0.08,     # threshold
        backtrack=False
    )
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    
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

    # --- Base notes (from onsets) ---
    base = [{"time": float(t), "energy": 0.0} for t in onset_times if 0.05 < t < duration - 0.05]

    # --- Merge all candidates ---
    all_cands = base + peaks

    # --- Remove duplicates (keep strongest energy) ---
    # Merge notes that are very close (e.g., < 25ms)
    # by rounding to a temporary time grid, then picking the one with max energy.
    merged_map = {}
    # 0.025s = 25ms. Adjust if notes are too close or too far.
    grid_resolution = 0.025 
    for c in all_cands:
        # Find the nearest "grid point"
        t_grid = round(c["time"] / grid_resolution) * grid_resolution
        t_grid = round(t_grid, 4) # avoid float precision issues
        
        # If this grid point is new, or if this note has more energy,
        # store it (using its *original*, non-rounded time).
        if t_grid not in merged_map or c["energy"] > merged_map[t_grid]["energy"]:
            merged_map[t_grid] = {"time": c["time"], "energy": c.get("energy", 0.0)}

    merged = sorted(merged_map.values(), key=lambda x: x["time"])


    # --- Intensity -> lane mapping ---
    energies = np.array([c.get("energy", 0.0) for c in merged])
    if energies.size and energies.max() > energies.min():
        norm = (energies - energies.min()) / (energies.max() - energies.min())
    else:
        norm = np.zeros_like(energies)

    # --- Enforce difficulty spacing & lane rules ---
    # The 'difficulty' param acts as a minimum time between notes
    notes = []
    last_t = -1e9
    last_lane = None
    for c, v in zip(merged, norm):
        t = c["time"]
        if t - last_t < difficulty:
            continue

        lane = int(v * lanes)
        lane = max(0, min(lanes - 1, lane))

        if last_lane is not None and lane == last_lane:
            lane = (lane + 1) % lanes

        notes.append({"time": t, "lane": lane})
        last_t = t
        last_lane = lane

    # --- Remove stray notes at start/end ---
    notes = [n for n in notes if 0.05 <= n["time"] <= duration - 0.05]

    return notes