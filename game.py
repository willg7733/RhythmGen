import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import math
import numpy as np
import pyaudio

# -----------------------------------------
# RhythmGen - Full Game File (Enhanced UI)
# -----------------------------------------

# Lanes and main playfield
LANE_COUNT = 4
LANE_WIDTH = 120
NOTE_WIDTH = 90
NOTE_HEIGHT = 22
NOTE_SPEED = 320         # pixels per second
HEADER_HEIGHT = 70
FOOTER_HEIGHT = 70
HIT_LINE_Y = 560         # y position where notes should be hit

# Window and layout
SIDEBAR_WIDTH = 260
WINDOW_WIDTH = LANE_COUNT * LANE_WIDTH + SIDEBAR_WIDTH
WINDOW_HEIGHT = 720

MAIN_WIDTH = WINDOW_WIDTH - SIDEBAR_WIDTH  # playfield area width
PLAY_TOP = HEADER_HEIGHT 
PLAY_BOTTOM = WINDOW_HEIGHT - FOOTER_HEIGHT

KEYS = [pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_f]

# Timing windows (seconds)
HIT_WINDOW = 0.15
PERFECT_WINDOW = 0.05
MISS_THRESHOLD = 0.20

# --- Audio Analyzer Constants ---
CHUNK = 1024 # Samples per buffer
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100 # Sample rate
# Frequency band ranges (Hz) for an 8-bar visualizer
# This maps frequency to the visual bars
FREQ_BANDS = [60, 150, 400, 1000, 2500, 6000, 12000, 20000] 
# Note: FREQ_BANDS length determines the number of bars to draw
# -------------------------------------

class AudioAnalyzer:
    """Handles real-time audio input, FFT, and spectrum calculation with robust device selection."""
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.band_levels = [0.0] * len(FREQ_BANDS)
        self.fft_cache = [0] * (CHUNK // 2)

        # 1. Attempt to find the best input device index
        input_index = self._find_input_device_index()
        
        if input_index is not None:
            # 2. Open the audio stream using the found index
            print(f"🎤 Opening audio stream on device index: {input_index}")
            self.stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
                input_device_index=input_index,  # Use the found index
                # Explicitly setting the default device will reduce ALSA errors
                # on some systems.
            )
        else:
            print("❌ WARNING: No suitable input audio device found. Visualizer will remain silent.")

    def _find_input_device_index(self):
        """Attempts to find the default or first available input device."""
        
        # 1. Try to get the default input device
        try:
            default_index = self.p.get_default_input_device_info()['index']
            if self.p.get_device_info_by_index(default_index).get('maxInputChannels') > 0:
                print(f"✅ Found default input device at index: {default_index}")
                return default_index
        except Exception:
            # If default fails (common on non-standard setups)
            pass 

        # 2. Iterate through all devices and return the first one that supports input
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            if device_info.get('maxInputChannels') > 0:
                print(f"🔍 Falling back to first available input device at index: {i}")
                return i
                
        return None # No input device found

    def process_audio(self):
        if self.stream is None:
            return

        try:
            # ... (rest of process_audio remains the same)
            data = self.stream.read(CHUNK, exception_on_overflow=False)
            data_int = np.frombuffer(data, dtype=np.int16)
            fft_data = np.abs(np.fft.fft(data_int))
            self.fft_cache = fft_data[:CHUNK // 2] 
            self.band_levels = self._calculate_bands(self.fft_cache)

        except IOError as e:
            print(f"IOError in audio stream: {e}")
            pass

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
                avg_amplitude = (band_sum / band_count)
                
                # Apply a gain and clamp the result (visual normalization)
                levels[i] = min(1.0, math.log10(avg_amplitude) * 0.05) 
                
        return levels
        
    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()

class RhythmGame:
    def __init__(self, beatmap, audio_path, latency_offset=0.0):
        """
        beatmap: list of dicts: {"time": float_seconds, "lane": int_0_to_3}
        audio_path: path to audio file (e.g., song.ogg)
        latency_offset: seconds to adjust timing relative to mixer clock
        """
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.init()

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("RhythmGen")

        self.notes = beatmap[:]  # copy
        
        # Initialize the external audio analyzer
        self.audio_analyzer = AudioAnalyzer() 
        self.current_band_levels = self.audio_analyzer.band_levels # Reference for rendering
        
        try:
            self.song = pygame.mixer.Sound(audio_path)
        except pygame.error as e:
            print(f"Error loading audio: {e}. Pygame mixer will still run, but you need a valid audio file.")
            self.song = None # Handle missing song gracefully

        self.latency_offset = latency_offset
        self.score = 0
        self.combo = 0
        self.start_time_ms = 0

        # Fonts
        self.ui_font = pygame.font.Font(None, 30)
        self.logo_font = pygame.font.Font(None, 56)
        self.label_font = pygame.font.Font(None, 26)
        self.feedback_font_small = pygame.font.Font(None, 28)
        self.feedback_font_large = pygame.font.Font(None, 38)  # Perfect is larger

        # Visual feedback stores
        self.feedbacks = []  # floating labels above notes
        
        # Precompute subtle two-color gradient for main background
        self.background = self._create_vertical_gradient((25, 10, 50), (5, 5, 10))

    # ---------------------------------------
    # Utility visuals
    # ---------------------------------------
    def _create_vertical_gradient(self, top_color, bottom_color):
        surf = pygame.Surface((MAIN_WIDTH, WINDOW_HEIGHT))
        for y in range(WINDOW_HEIGHT):
            t = y / WINDOW_HEIGHT
            r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
            g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
            b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (MAIN_WIDTH, y))
        return surf

    def _lane_center_x(self, lane):
        return lane * LANE_WIDTH + LANE_WIDTH // 2

    def _note_rect(self, lane, y):
        return (
            lane * LANE_WIDTH + (LANE_WIDTH - NOTE_WIDTH) // 2,
            y,
            NOTE_WIDTH,
            NOTE_HEIGHT
        )

    # ---------------------------------------
    # Feedback helpers
    # ---------------------------------------
    def add_feedback(self, text, color, x, y, big=False):
        # floating label that drifts upward and fades
        self.feedbacks.append({
            "text": text,
            "color": color,
            "x": x,
            "y": y,
            "alpha": 255,
            "life": 36,     # frames
            "rise": 1.25,   # pixels per frame
            "big": big
        })

    # ---------------------------------------
    # Game flow
    # ---------------------------------------
    def run(self):
        clock = pygame.time.Clock()

        if self.song:
            self.song.play()
        self.start_time_ms = pygame.time.get_ticks()

        running = True
        while running:
            # 1. Update Game Time
            current_time = ((pygame.time.get_ticks() - self.start_time_ms) / 1000.0) + self.latency_offset

            # 2. Process Real Audio for Visualizer
            self.audio_analyzer.process_audio()
            
            # 3. Handle Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if event.key in KEYS:
                        lane = KEYS.index(event.key)
                        self.check_hit(lane, current_time)

            # 4. Update Game State
            self.check_misses(current_time)
            
            # 5. Render
            self.render(current_time)
            clock.tick(60)

        # Clean up audio stream upon exit
        self.audio_analyzer.close()
        pygame.quit()

    def check_hit(self, lane, current_time):
        # ... (check_hit remains the same)
        for note in self.notes[:]:
            if note["lane"] != lane:
                continue
            time_diff = note["time"] - current_time
            if abs(time_diff) <= HIT_WINDOW:
                self.notes.remove(note)
                self.combo += 1
                self.score += 100
                x = self._lane_center_x(lane)
                fb_y = HIT_LINE_Y - 40
                if abs(time_diff) <= PERFECT_WINDOW:
                    self.add_feedback("Perfect", (255, 255, 140), x, fb_y, big=True)
                else:
                    self.add_feedback("Good", (120, 255, 180), x, fb_y, big=False)
                return
        self.combo = 0
        x = self._lane_center_x(lane)
        self.add_feedback("Miss", (255, 100, 100), x, HIT_LINE_Y - 40, big=False)

    def check_misses(self, current_time):
        # ... (check_misses remains the same)
        for note in self.notes[:]:
            if current_time > note["time"] + MISS_THRESHOLD:
                self.notes.remove(note)
                self.combo = 0
                x = self._lane_center_x(note["lane"])
                self.add_feedback("Miss", (255, 100, 100), x, HIT_LINE_Y - 40, big=False)
                
    def _render_visualizer(self):
        """Renders the real-time, FFT-based Spectrum Bar Visualizer."""
        eq_area_height = 220
        padding = 14
        
        eq_area_rect = pygame.Rect(MAIN_WIDTH, WINDOW_HEIGHT - eq_area_height, SIDEBAR_WIDTH, eq_area_height)
        pygame.draw.rect(self.screen, (35, 35, 45), eq_area_rect)
        pygame.draw.rect(self.screen, (85, 85, 110), eq_area_rect, 2)

        eq_label = self.label_font.render("Spectrum Analyzer", True, (200, 200, 220))
        self.screen.blit(eq_label, (MAIN_WIDTH + 16, WINDOW_HEIGHT - eq_area_height + 10))

        # --- Visualizer Logic using REAL audio data ---
        bars = len(self.current_band_levels)
        available_w = SIDEBAR_WIDTH - 2 * padding
        bar_gap = 6
        bar_w = max(4, (available_w - (bars - 1) * bar_gap) // bars)
        base_y = WINDOW_HEIGHT - 16
        max_bar_h = eq_area_height - 46

        for i in range(bars):
            # level is a value between 0.0 and 1.0 from the audio analyzer
            level = self.current_band_levels[i]
            
            # We use a trick here: we save the visual level as a percentage of max_bar_h
            current_visual_height = getattr(self, f'_bar_h_{i}', 10)
            
            # Target height based on actual level
            target_h = int(10 + level * (max_bar_h - 10))
            
            # Smooth the height for a realistic "fall" effect
            current_visual_height = current_visual_height * 0.7 + target_h * 0.3
            
            h = int(current_visual_height)
            setattr(self, f'_bar_h_{i}', h)

            x = MAIN_WIDTH + padding + i * (bar_w + bar_gap)
            y = base_y - h
            
            # t represents the intensity level (0.0 to 1.0)
            t = level
            
            r, g, b = 0, 0, 0
            
            if t < 0.5: # 0.0 to 0.5: Green dominated
                r = int(255 * t * 2) if t > 0.25 else 0 # starts adding red around 25%
                g = int(150 + 100 * t * 2) # Stays bright green
                b = 0
            elif t < 0.7: # 0.5 to 0.7: Yellow/Amber
                r = 255
                g = int(255 - 100 * (t - 0.5) * 5) # Green starts falling slightly
                b = 0
            else: # 0.7 to 1.0: Red dominated (Clipping zone)
                r = 255
                g = int(100 * (1 - t)) # Green fades out
                b = 0

            color = (max(0, min(255, r)), max(0, min(255, g)), b) # Clamp for safety
            
            pygame.draw.rect(self.screen, color, (x, y, bar_w, h), border_radius=0)
        
        pygame.draw.line(self.screen, (40, 40, 50), (MAIN_WIDTH + padding, base_y), (WINDOW_WIDTH - padding, base_y), 1)

    def render(self, current_time):
        # Main background (playfield only)
        self.screen.blit(self.background, (0, 0))

        # Header bar with logo, confined above playfield
        pygame.draw.rect(self.screen, (45, 45, 70), (0, 0, MAIN_WIDTH, HEADER_HEIGHT))
        pygame.draw.line(self.screen, (120, 120, 200), (0, HEADER_HEIGHT - 1), (MAIN_WIDTH, HEADER_HEIGHT - 1), 1)
        logo_text = self.logo_font.render("RhythmGen", True, (255, 0, 200))
        glow_text = self.logo_font.render("RhythmGen", True, (0, 255, 200))
        cx = MAIN_WIDTH // 2 - logo_text.get_width() // 2
        self.screen.blit(glow_text, (cx + 2, 12))
        self.screen.blit(logo_text, (cx, 10))

        # Lanes in playfield
        for i in range(LANE_COUNT):
            pygame.draw.rect(
                self.screen,
                (180, 180, 200),
                (i * LANE_WIDTH, PLAY_TOP, LANE_WIDTH, PLAY_BOTTOM - PLAY_TOP),
                2
            )

        # Hit line (where notes should be hit)
        pygame.draw.line(self.screen, (255, 255, 255), (0, HIT_LINE_Y), (MAIN_WIDTH, HIT_LINE_Y), 2)

        # Notes
        for note in list(self.notes):
            time_until_hit = note["time"] - current_time
            y = HIT_LINE_Y - time_until_hit * NOTE_SPEED

            if y < PLAY_TOP - 60 or y > PLAY_BOTTOM + NOTE_HEIGHT:
                continue

            t = 0.0
            if HIT_LINE_Y > PLAY_TOP:
                t = max(0.0, min(1.0, (y - PLAY_TOP) / (HIT_LINE_Y - PLAY_TOP)))
            intensity = int(130 + t * (255 - 130))
            color = (0, intensity, 255)

            pygame.draw.rect(self.screen, color, self._note_rect(note["lane"], y), border_radius=5)

        # Floating feedback labels
        for fb in self.feedbacks[:]:
            font = self.feedback_font_large if fb["big"] else self.feedback_font_small
            surf = font.render(fb["text"], True, fb["color"])
            surf.set_alpha(max(0, fb["alpha"]))
            self.screen.blit(surf, (fb["x"] - surf.get_width() // 2, fb["y"]))
            fb["y"] -= fb["rise"]       
            fb["alpha"] -= 7            
            fb["life"] -= 1
            if fb["life"] <= 0 or fb["alpha"] <= 0:
                self.feedbacks.remove(fb)

        # Footer: Progress box beneath everything (playfield)
        footer_rect = pygame.Rect(0, WINDOW_HEIGHT - FOOTER_HEIGHT, MAIN_WIDTH, FOOTER_HEIGHT)
        pygame.draw.rect(self.screen, (40, 40, 55), footer_rect)
        pygame.draw.rect(self.screen, (90, 90, 120), footer_rect, 2)

        label = self.label_font.render("Progress", True, (200, 200, 220))
        self.screen.blit(label, (12, WINDOW_HEIGHT - FOOTER_HEIGHT + 10))

        # Progress bar inside footer
        song_len = self.song.get_length() if self.song else 0
        progress = 0.0 if song_len <= 0 else min(current_time / song_len, 1.0)
        bar_x = 12
        bar_y = WINDOW_HEIGHT - FOOTER_HEIGHT + 36
        bar_w = MAIN_WIDTH - 24
        bar_h = 18
        pygame.draw.rect(self.screen, (65, 65, 85), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
        pygame.draw.rect(self.screen, (0, 220, 220), (bar_x, bar_y, int(bar_w * progress), bar_h), border_radius=6)

        # Sidebar
        sidebar_rect = pygame.Rect(MAIN_WIDTH, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT)
        pygame.draw.rect(self.screen, (22, 22, 28), sidebar_rect)

        # Sidebar: Score & Combo section
        sidebar_header = pygame.Rect(MAIN_WIDTH, 0, SIDEBAR_WIDTH, 140)
        pygame.draw.rect(self.screen, (35, 35, 45), sidebar_header)
        pygame.draw.rect(self.screen, (85, 85, 110), sidebar_header, 2)

        score_text = self.ui_font.render(f"Score: {self.score}", True, (230, 230, 240))
        combo_text = self.ui_font.render(f"Combo: {self.combo}", True, (230, 230, 240))
        self.screen.blit(score_text, (MAIN_WIDTH + 16, 24))
        self.screen.blit(combo_text, (MAIN_WIDTH + 16, 70))

        # Sidebar: Visualizer (Live Spectrum Bars)
        self._render_visualizer()

        pygame.display.flip()