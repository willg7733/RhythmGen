import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import math
import numpy as np
import librosa
import threading


# --- Audio Analyzer Constants ---
CHUNK = 1024 # Samples per buffer
RATE = 44100 # Sample rate
# Frequency band ranges (Hz) for a 16-bar visualizer
# This maps frequency to the visual bars
FREQ_BANDS = [60, 100, 150, 220, 330, 480, 700, 1000, 1450, 2100, 3000, 4300, 6200, 9000, 13000, 20000]
# Note: FREQ_BANDS length determines the number of bars to draw
# Minimum non-zero amplitude fed into log calculations to avoid domain errors
MIN_BAND_AMPLITUDE = 1e-6
# -------------------------------------

class AudioAnalyzer:
    """Analyzes the downloaded song audio to drive the spectrum visualizer."""

    def __init__(self, audio_path):
        self.audio_path = audio_path
        self.band_levels = [0.0] * len(FREQ_BANDS)
        self.fft_cache = np.zeros(CHUNK // 2)
        self.window = np.hanning(CHUNK)
        self.audio_data, self.sample_rate = self._load_audio(audio_path)
        self.total_samples = len(self.audio_data) if self.audio_data is not None else 0
        
        # Threading for non-blocking audio processing
        self.processing_thread = None
        self.lock = threading.Lock()
        self.is_processing = False

    def _load_audio(self, audio_path):
        if not audio_path or not os.path.exists(audio_path):
            print(" WARNING: Audio file for visualizer not found. Bars will stay idle.")
            return None, RATE

        try:
            samples, sr = librosa.load(audio_path, sr=RATE, mono=True)
            if samples.size == 0:
                print(" WARNING: Loaded audio is empty. Visualizer disabled.")
                return None, sr
            return samples, sr
        except Exception as exc:
            print(f" WARNING: Failed to decode audio for visualizer: {exc}")
            return None, RATE

    def process_audio(self, playback_time):
        """Start non-blocking audio processing in a background thread."""
        # If already processing, skip this frame
        if self.is_processing:
            return self.band_levels
        
        # Start processing in background thread
        self.is_processing = True
        self.processing_thread = threading.Thread(
            target=self._process_audio_async, 
            args=(playback_time,),
            daemon=True
        )
        self.processing_thread.start()
        
        return self.band_levels
    
    def _process_audio_async(self, playback_time):
        """Internal method that runs in a background thread."""
        if self.audio_data is None:
            with self.lock:
                self.band_levels = [0.0] * len(FREQ_BANDS)
                self.is_processing = False
            return

        playback_time = max(0.0, playback_time)
        start_idx = int(playback_time * self.sample_rate)

        if start_idx >= self.total_samples:
            window = np.zeros(CHUNK)
        else:
            end_idx = start_idx + CHUNK
            window = self.audio_data[start_idx:end_idx]
            if window.shape[0] < CHUNK:
                window = np.pad(window, (0, CHUNK - window.shape[0]))

        window = window * self.window
        fft_data = np.abs(np.fft.fft(window))
        fft_cache = fft_data[:CHUNK // 2]
        band_levels = self._calculate_bands(fft_cache)
        
        # Update shared state with thread safety
        with self.lock:
            self.fft_cache = fft_cache
            self.band_levels = band_levels
            self.is_processing = False

    def _calculate_bands(self, fft_data):
        """Map FFT data to specific frequency bands."""
        levels = [0.0] * len(FREQ_BANDS)
        
        # Calculate frequency resolution
        freq_resolution = RATE / CHUNK
        
        for i, band_end_freq in enumerate(FREQ_BANDS):
            # Determine the FFT bin index corresponding to the band's end frequency
            bin_index = int(band_end_freq / freq_resolution)
            
            # Determine the starting bin index
            start_bin = 0 if i == 0 else int(FREQ_BANDS[i-1] / freq_resolution)
            
            if bin_index > start_bin and bin_index < len(fft_data):
                # Calculate the average amplitude in this frequency range
                band_sum = np.sum(fft_data[start_bin:bin_index])
                band_count = bin_index - start_bin

                # Normalize and scale the average amplitude. Use log scale for realism.
                # Clamp to MIN_BAND_AMPLITUDE so silence doesn't produce log-domain errors.
                avg_amplitude = max(band_sum / band_count, MIN_BAND_AMPLITUDE)

                # Apply a gain and clamp the result (visual normalization)
                log_level = math.log10(avg_amplitude) * 0.40
                levels[i] = max(0.0, min(1.0, log_level)) 
                
        return levels
        
    def close(self):
        """Clean up resources and wait for any pending processing to finish."""
        # Wait for processing thread to finish if it's running
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=0.1)  # Wait up to 100ms
