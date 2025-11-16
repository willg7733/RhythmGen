import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import math
import numpy as np
import librosa

try:
    import cv2  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency
    cv2 = None

from audioanalyzer import AudioAnalyzer

# -----------------------------------------
# RhythmGen - Full Game File (Enhanced UI)
# -----------------------------------------

# Lanes and main playfield
LANE_COUNT = 4
LANE_WIDTH = 120
NOTE_WIDTH = 90
NOTE_HEIGHT = 22
NOTE_SPEED = 320         # pixels per second
BASE_NOTE_SCORE = 100
MAX_MULTIPLIER = 7
PERFECTS_PER_MULTIPLIER = 5
NOTE_ENTRY_MIN_Y = -NOTE_HEIGHT  # allow notes to begin just off-screen at the top
HEADER_HEIGHT = 70
FOOTER_HEIGHT = 70
HIT_LINE_Y = 560         # y position where notes should be hit

# Window and layout
SIDEBAR_WIDTH = 260
WINDOW_WIDTH = LANE_COUNT * LANE_WIDTH + SIDEBAR_WIDTH
WINDOW_HEIGHT = 720

VIDEO_ASPECT_RATIO = 16 / 9
VIDEO_PANEL_MARGIN = 16
VIDEO_PANEL_BG = (5, 5, 10)
VIDEO_PANEL_BORDER = (40, 40, 55)
VIDEO_PANEL_TEXT = (180, 200, 220)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SFX_CLAP_PATH = os.path.join(ASSETS_DIR, "clap.mp3")
SFX_FIREWORKS_PATH = os.path.join(ASSETS_DIR, "fireworks.mp3")

MAIN_WIDTH = WINDOW_WIDTH - SIDEBAR_WIDTH  # playfield area width
PLAY_TOP = HEADER_HEIGHT 
PLAY_BOTTOM = WINDOW_HEIGHT - FOOTER_HEIGHT

# KEYS = [pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r]

KEYS = [pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_f]
# Timing windows (seconds)
HIT_WINDOW = 0.15
PERFECT_WINDOW = 0.05
MISS_THRESHOLD = 0.20

# ==================== COLOR PALETTE ====================
# Backgrounds
COLOR_BLACK = (0, 0, 0)
COLOR_BACKGROUND_GRADIENT_TOP = COLOR_BLACK
COLOR_BACKGROUND_GRADIENT_BOTTOM = COLOR_BLACK
COLOR_COUNTDOWN_OVERLAY = (20, 20, 30)
COLOR_PAUSE_OVERLAY = (15, 15, 25)
COLOR_END_OVERLAY = (10, 10, 20)

# Branding & Titles
COLOR_TITLE_CYAN = (0, 187, 249)
COLOR_TITLE_MAGENTA = (241, 91, 200)
COLOR_TITLE_BRIGHT_CYAN = (100, 255, 200)
COLOR_SUBTITLE = (180, 180, 220)

# Header & Footer
COLOR_HEADER_BG = COLOR_BLACK
COLOR_HEADER_BORDER = COLOR_BLACK
COLOR_FOOTER_BG = COLOR_BLACK
COLOR_FOOTER_BORDER = COLOR_BLACK
COLOR_FOOTER_TEXT = (200, 200, 220)

# Sidebar
COLOR_SIDEBAR_BG = COLOR_BLACK
COLOR_SIDEBAR_HEADER_BG = COLOR_BLACK
COLOR_SIDEBAR_BORDER = COLOR_BLACK
COLOR_SIDEBAR_TEXT = (230, 230, 240)
COLOR_SIDEBAR_LABEL = (200, 230, 255)
COLOR_MULTIPLIER_ACTIVE = (180, 255, 220)
COLOR_DIVIDER_LINE = (40, 40, 50)

# Progress Bar
COLOR_PROGRESS_BG = COLOR_BLACK
COLOR_PROGRESS_FILL = (0, 187, 249)

# Notes & Lanes
COLOR_NOTE_MIN = (0, 130, 255)  # Used with intensity calculation
COLOR_NOTE_MAX = (0, 255, 255)  # Used with intensity calculation
COLOR_HIT_LINE = (255, 255, 255)
COLOR_HIT_NOTE_PULSE = (255, 255, 255)  # With alpha
COLOR_RIPPLE = (255, 255, 255)  # With alpha
COLOR_LANE_LABEL = (180, 180, 200)

# Feedback Text
COLOR_FEEDBACK_PERFECT = (247, 229, 62)
COLOR_FEEDBACK_GOOD = (42, 229, 132)
COLOR_FEEDBACK_MISS = (229, 42, 57)

# Accuracy Display
COLOR_ACCURACY_PERFECT = (100, 255, 100)
COLOR_ACCURACY_GREAT = (150, 255, 150)
COLOR_ACCURACY_GOOD = (255, 255, 150)
COLOR_ACCURACY_POOR = (255, 150, 150)


# Button - Green (Resume/Retry)
COLOR_BUTTON_GREEN_HOVER = (100, 200, 100)
COLOR_BUTTON_GREEN_NORMAL = (60, 120, 60)
COLOR_BUTTON_GREEN_BORDER = (150, 255, 150)

COLOR_ONE = (100, 255, 100)    # Green
COLOR_TWO = (255, 200, 100)    # Orange
COLOR_THREE = (255, 100, 100)  # Red
COLOR_GO = (100, 255, 255)     # Cyan

# Button - Red (Menu/Quit)
COLOR_BUTTON_RED_HOVER = (200, 100, 100)
COLOR_BUTTON_RED_NORMAL = (120, 60, 60)
COLOR_BUTTON_RED_BORDER = (255, 150, 150)

# Button Text
COLOR_TEXT_WHITE = (255, 255, 255)
COLOR_TEXT_DARK_GRAY = (200, 200, 200)

# End Screen
COLOR_END_SCORE = (247, 229, 62)  # Yellow
COLOR_END_CONGRATS = (241, 91, 181)  # Pink

EQ_BAR = (0, 187, 249)
# =======================================================



class VideoPanel:
    def __init__(self, video_path, size, start_delay=0.0):
        self.video_path = video_path
        self.size = size
        self.start_delay = max(0.0, start_delay)
        has_cv2 = cv2 is not None
        path_exists = bool(video_path and os.path.isfile(video_path))
        self.enabled = has_cv2 and path_exists
        self.error_message = None
        self.cap = None
        self.frame_surface = pygame.Surface(size).convert()
        self.frame_surface.fill(VIDEO_PANEL_BG)
        self.last_frame_index = -1
        self.fps = 30.0
        self.total_frames = 0
        self.finished = False
        self.has_frame = False

        if self.enabled and cv2 is not None:
            self.cap = cv2.VideoCapture(video_path)  # type: ignore[call-arg]
            if not self.cap or not self.cap.isOpened():
                self.error_message = "Unable to open video"
                self.enabled = False
            else:
                fps = self.cap.get(cv2.CAP_PROP_FPS) if cv2 else 30.0
                if fps and fps > 0:
                    self.fps = fps
                total_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT) if cv2 else 0
                if total_frames:
                    self.total_frames = int(total_frames)
        else:
            if not video_path:
                self.error_message = "No video available"
            elif not os.path.isfile(video_path):
                self.error_message = "Video file missing"
            elif not has_cv2:
                self.error_message = "Install opencv-python to enable video playback"

    def update(self, song_time, allow_advance=True):
        if cv2 is None or not self.enabled or not self.cap or not allow_advance or self.finished:
            return

        playback_time = song_time - self.start_delay
        if playback_time < 0:
            return

        target_frame = int(playback_time * self.fps)
        if self.total_frames and target_frame >= self.total_frames:
            self.finished = True
            return

        if target_frame == self.last_frame_index:
            return

        frame = None
        needs_seek = (
            self.last_frame_index == -1
            or target_frame < self.last_frame_index
            or target_frame - self.last_frame_index > self.fps
        )

        if needs_seek:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, target_frame))
            ret, frame = self.cap.read()
            if not ret:
                self.finished = True
                return
            self.last_frame_index = target_frame
        else:
            while self.last_frame_index < target_frame:
                ret, frame = self.cap.read()
                if not ret:
                    self.finished = True
                    return
                self.last_frame_index += 1

        if frame is None:
            return
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        surface = pygame.image.frombuffer(rgb.tobytes(), (rgb.shape[1], rgb.shape[0]), "RGB")
        if surface.get_size() != self.size:
            surface = pygame.transform.smoothscale(surface, self.size)
        self.frame_surface = surface.convert()
        self.has_frame = True

    def draw(self, target_surface, rect):
        surface = self.frame_surface
        if surface.get_size() != rect.size:
            surface = pygame.transform.smoothscale(surface, rect.size)
        target_surface.blit(surface, rect.topleft)

    def close(self):
        if self.cap:
            self.cap.release()


class RhythmGame:
    def __init__(self, beatmap, audio_path, latency_offset=0.0, *, video_path=None, video_delay=0.0):
        """
        beatmap: list of dicts: {"time": float_seconds, "lane": int_0_to_3}
        audio_path: path to audio file (e.g., song.ogg)
        latency_offset: seconds to adjust timing relative to mixer clock
        """
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        
        # Ensure pygame is initialized
        if not pygame.get_init():
            pygame.init()

        pygame.display.set_caption("RhythmGen")
        
        # Reuse existing display if available, otherwise create new one
        existing_display = pygame.display.get_surface()
        if existing_display:
            self.display_surface = existing_display
            self.display_size = existing_display.get_size()
        else:
            display_info = pygame.display.Info()
            display_w = display_info.current_w or WINDOW_WIDTH
            display_h = display_info.current_h or WINDOW_HEIGHT
            self.display_size = (display_w, display_h)

            try:
                self.display_surface = pygame.display.set_mode(self.display_size, pygame.FULLSCREEN)
            except pygame.error:
                # Fallback to windowed mode if fullscreen fails
                self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
                self.display_size = (WINDOW_WIDTH, WINDOW_HEIGHT)

        # Logical rendering surface keeps existing coordinate system
        self.screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT)).convert()

        self.notes = beatmap[:]  # copy
        self.total_note_count = len(beatmap)
        
        # Initialize the external audio analyzer using the downloaded song
        self.audio_analyzer = AudioAnalyzer(audio_path)
        self.current_band_levels = list(self.audio_analyzer.band_levels)
        
        try:
            self.song = pygame.mixer.Sound(audio_path)
        except pygame.error as e:
            print(f"Error loading audio: {e}. Pygame mixer will still run, but you need a valid audio file.")
            self.song = None # Handle missing song gracefully

        self.latency_offset = latency_offset
        self.score = 0
        self.combo = 0
        self.max_combo = 0  # Track the highest combo achieved
        self.multiplier = 1
        self.perfect_hits_in_combo = 0
        self.missed_notes = 0
        self.accuracy = 100.0
        self.start_time_ms = 0
        
        # Countdown state
        self.countdown_active = True
        self.countdown_start_time = 0
        self.countdown_duration = 3.0  # 3 seconds countdown (3, 2, 1, GO)
        
        # Pause state
        self.paused = False
        self.pause_start_time = 0
        self.total_pause_time = 0.0  # Track accumulated pause time
        
        # End screen state
        self.game_ended = False
        self.end_screen_action = None  # "retry", "menu", or "quit"
        
        # Animation state
        self.frame_count = 0  # For pulse animations

        # Fonts (store base sizes so overlays can scale cleanly)
        self.ui_font_size = 30
        self.logo_font_size = 56
        self.label_font_size = 26
        self.feedback_font_small_size = 28
        self.feedback_font_large_size = 38  # Perfect is larger

        self.ui_font = pygame.font.Font(None, self.ui_font_size)
        self.logo_font = pygame.font.Font(None, self.logo_font_size)
        self.label_font = pygame.font.Font(None, self.label_font_size)
        self.feedback_font_small = pygame.font.Font(None, self.feedback_font_small_size)
        self.feedback_font_large = pygame.font.Font(None, self.feedback_font_large_size)
        self.countdown_font_size = 180
        self.countdown_font = pygame.font.Font(None, self.countdown_font_size)
        self.pause_title_font_size = 72
        self.pause_title_font = pygame.font.Font(None, self.pause_title_font_size)
        self.pause_hint_font_size = 36
        self.pause_hint_font = pygame.font.Font(None, self.pause_hint_font_size)
        self.end_title_font_size = 84
        self.end_title_font = pygame.font.Font(None, self.end_title_font_size)
        self.end_stats_font_size = 48
        self.end_stats_font = pygame.font.Font(None, self.end_stats_font_size)
        self.end_button_font_size = 42
        self.end_button_font = pygame.font.Font(None, self.end_button_font_size)

        self.sfx_clap = self._load_sound(SFX_CLAP_PATH)
        self.sfx_fireworks = self._load_sound(SFX_FIREWORKS_PATH)
        self.end_sfx_played = False

        # Visual feedback stores
        self.feedbacks = []  # floating labels above notes
        self._text_overlays = []
        self.hit_notes = []  # notes that were hit and are pulsing before disappearing
        self.ripples = []  # ripple effects traveling up and down lanes
        
        # Precompute subtle two-color gradient for main background
        self.background = self._create_vertical_gradient(COLOR_BACKGROUND_GRADIENT_TOP, COLOR_BACKGROUND_GRADIENT_BOTTOM)

        # Video panel setup
        panel_width = SIDEBAR_WIDTH - 2 * VIDEO_PANEL_MARGIN
        panel_height = int(panel_width / VIDEO_ASPECT_RATIO)
        self.video_panel_size = (panel_width, panel_height)
        self.video_panel = None
        self.video_panel_status = None
        if video_path:
            if cv2 is None:
                self.video_panel_status = "Install opencv-python to enable video playback"
            elif not os.path.isfile(video_path):
                self.video_panel_status = "Video file missing"
            else:
                try:
                    self.video_panel = VideoPanel(video_path, self.video_panel_size, start_delay=video_delay)
                    if not self.video_panel.enabled:
                        self.video_panel_status = self.video_panel.error_message or "Video unavailable"
                        self.video_panel = None
                except Exception as exc:  # pragma: no cover - defensive
                    self.video_panel = None
                    self.video_panel_status = f"Video error: {exc}"
        else:
            self.video_panel_status = "Video unavailable"

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

    def _load_sound(self, path):
        if not path or not os.path.isfile(path):
            return None
        try:
            return pygame.mixer.Sound(path)
        except pygame.error:
            return None

    def _play_end_sfx(self):
        if getattr(self, "end_sfx_played", False):
            return
        played = False
        for sound in (getattr(self, "sfx_clap", None), getattr(self, "sfx_fireworks", None)):
            if sound:
                sound.play()
                played = True
        if played:
            self.end_sfx_played = True

    def _lane_center_x(self, lane):
        return lane * LANE_WIDTH + LANE_WIDTH // 2

    def _note_rect(self, lane, y):
        return (
            lane * LANE_WIDTH + (LANE_WIDTH - NOTE_WIDTH) // 2,
            y,
            NOTE_WIDTH,
            NOTE_HEIGHT
        )

    def _reset_multiplier(self):
        self.multiplier = 1
        self.perfect_hits_in_combo = 0

    def _increase_multiplier(self):
        if self.multiplier < MAX_MULTIPLIER:
            self.multiplier += 1

    def _register_perfect_hit(self):
        if self.multiplier >= MAX_MULTIPLIER:
            return
        self.perfect_hits_in_combo += 1
        if self.perfect_hits_in_combo >= PERFECTS_PER_MULTIPLIER:
            self.perfect_hits_in_combo = 0
            self._increase_multiplier()

    def _recalculate_accuracy(self):
        """Calculate accuracy as percentage of notes hit successfully."""
        if self.total_note_count <= 0:
            self.accuracy = 0.0
            return
        # Accuracy = (total notes - missed notes) / total notes * 100
        self.accuracy = ((self.total_note_count - self.missed_notes) / self.total_note_count) * 100.0

    def _record_miss(self):
        """Increment missed notes counter and recalculate accuracy."""
        self.missed_notes += 1
        self._recalculate_accuracy()

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

        # Start countdown timer
        self.countdown_start_time = pygame.time.get_ticks()
        
        running = True
        while running:
            current_ticks = pygame.time.get_ticks()
            
            # Handle countdown
            if self.countdown_active:
                countdown_elapsed = (current_ticks - self.countdown_start_time) / 1000.0
                if countdown_elapsed >= self.countdown_duration + 0.5:  # Extra 0.5s for "GO"
                    # Countdown finished, start the song
                    self.countdown_active = False
                    if self.song:
                        self.song.play()
                    self.start_time_ms = pygame.time.get_ticks()
                    current_time = 0.0
                else:
                    # During countdown, time doesn't advance
                    current_time = -1.0
            elif self.paused:
                # During pause, time doesn't advance
                current_time = ((self.pause_start_time - self.start_time_ms) / 1000.0) + self.latency_offset - self.total_pause_time
            else:
                # Normal gameplay - Update Game Time (subtract accumulated pause time)
                current_time = ((current_ticks - self.start_time_ms) / 1000.0) + self.latency_offset - self.total_pause_time

            if self.video_panel:
                panel_time = max(0.0, current_time if isinstance(current_time, (int, float)) else 0.0)
                allow_advance = not self.countdown_active and not self.paused
                self.video_panel.update(panel_time, allow_advance=allow_advance)

            # Check if game should end (all notes gone and song finished)
            if not self.countdown_active and not self.paused and not self.game_ended:
                song_len = self.song.get_length() if self.song else 0
                if len(self.notes) == 0 and current_time >= song_len:
                    self.game_ended = True
                    if self.song:
                        self.song.stop()
                    self._play_end_sfx()

            # Process Real Audio for Visualizer using the song playback time
            if not self.countdown_active and not self.paused and not self.game_ended:
                self.current_band_levels = self.audio_analyzer.process_audio(current_time)
            
            # Handle Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.end_screen_action = "quit"
                    running = False

                if event.type == pygame.KEYDOWN:
                    # ESC key toggles pause (only after countdown and before end)
                    if event.key == pygame.K_ESCAPE and not self.countdown_active and not self.game_ended:
                        if self.paused:
                            # Unpause
                            pause_duration = (current_ticks - self.pause_start_time) / 1000.0
                            self.total_pause_time += pause_duration
                            self.paused = False
                            # Resume playback (don't restart, just unpause)
                            if self.song:
                                pygame.mixer.unpause()
                        else:
                            # Pause
                            self.paused = True
                            self.pause_start_time = current_ticks
                            if self.song:
                                pygame.mixer.pause()
                    
                    # Pause screen keyboard controls
                    elif self.paused:
                        if event.key == pygame.K_m:
                            # Return to menu
                            self.end_screen_action = "menu"
                            running = False
                    
                    # Game keys only work when not paused and not in countdown and not ended
                    elif event.key in KEYS and not self.countdown_active and not self.paused and not self.game_ended:
                        lane = KEYS.index(event.key)
                        self.check_hit(lane, current_time)
                    
                    # End screen keyboard controls
                    elif self.game_ended:
                        if event.key == pygame.K_r:
                            self.end_screen_action = "retry"
                            running = False
                        elif event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                            self.end_screen_action = "menu"
                            running = False
                
                # Pause screen mouse controls
                if event.type == pygame.MOUSEBUTTONDOWN and self.paused:
                    mouse_x, mouse_y = event.pos
                    # Adjust for scaling
                    scale, offset_x, offset_y = self._get_scale_and_offset()
                    logical_x = (mouse_x - offset_x) / scale
                    logical_y = (mouse_y - offset_y) / scale
                    
                    # Check if click is on pause buttons
                    action = self._check_pause_button_click(logical_x, logical_y)
                    if action == "resume":
                        pause_duration = (current_ticks - self.pause_start_time) / 1000.0
                        self.total_pause_time += pause_duration
                        self.paused = False
                        if self.song:
                            pygame.mixer.unpause()
                    elif action == "menu":
                        self.end_screen_action = "menu"
                        running = False
                
                # End screen mouse controls
                if event.type == pygame.MOUSEBUTTONDOWN and self.game_ended:
                    mouse_x, mouse_y = event.pos
                    # Adjust for scaling
                    scale, offset_x, offset_y = self._get_scale_and_offset()
                    logical_x = (mouse_x - offset_x) / scale
                    logical_y = (mouse_y - offset_y) / scale
                    
                    # Check if click is on retry or main menu button
                    action = self._check_button_click(logical_x, logical_y)
                    if action:
                        self.end_screen_action = action
                        running = False

            # Update Game State (only during active gameplay)
            if not self.countdown_active and not self.paused and not self.game_ended:
                self.check_misses(current_time)
            
            # Render
            self.render(current_time)
            clock.tick(60)

        # Clean up audio stream upon exit
        self.audio_analyzer.close()
        
        # Stop and unload the song to prevent it from playing when returning to menu
        if self.song:
            self.song.stop()
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()

        if self.video_panel:
            self.video_panel.close()
        
        # Return the action for main.py to handle
        return self.end_screen_action

    def check_hit(self, lane, current_time):
        # Check if there's a note in this lane within the hit window
        for note in self.notes[:]:
            if note["lane"] != lane:
                continue
            time_diff = note["time"] - current_time
            if abs(time_diff) <= HIT_WINDOW:
                # Calculate the actual y position of the note when hit
                time_until_hit = note["time"] - current_time
                note_y = HIT_LINE_Y - time_until_hit * NOTE_SPEED
                
                # Remove from active notes
                self.notes.remove(note)
                
                # Add to hit notes for pulse animation at the actual position
                self.hit_notes.append({
                    "lane": note["lane"],
                    "y": note_y,  # Use actual y position of note when hit
                    "pulse_frame": 0,  # Animation frame counter
                    "max_frames": 8    # How many frames to animate
                })
                
                # Add ripple effects traveling up and down the lane
                ripple_speed = 15  # pixels per frame
                self.ripples.append({
                    "lane": note["lane"],
                    "origin_y": note_y,
                    "offset": 0,  # Distance traveled from origin
                    "max_offset": 400,  # Maximum distance to travel
                    "speed": ripple_speed
                })
                
                self.combo += 1
                # Update max combo if current combo is higher
                if self.combo > self.max_combo:
                    self.max_combo = self.combo
                
                is_perfect = abs(time_diff) <= PERFECT_WINDOW
                applied_multiplier = self.multiplier
                self.score += BASE_NOTE_SCORE * applied_multiplier
                x = self._lane_center_x(lane)
                fb_y = HIT_LINE_Y - 40
                if is_perfect:
                    feedback_text = f"Perfect"
                    self.add_feedback(feedback_text, COLOR_FEEDBACK_PERFECT, x, fb_y, big=True)
                    self._register_perfect_hit()
                else:
                    self.add_feedback("Good", COLOR_FEEDBACK_GOOD, x, fb_y, big=False)
                return
        # Key pressed but no note to hit - just reset combo, don't count as miss
        self.combo = 0
        self._reset_multiplier()
        x = self._lane_center_x(lane)
        self.add_feedback("Miss", COLOR_FEEDBACK_MISS, x, HIT_LINE_Y - 40, big=False)

    def check_misses(self, current_time):
        # ... (check_misses remains the same)
        for note in self.notes[:]:
            if current_time > note["time"] + MISS_THRESHOLD:
                self.notes.remove(note)
                self.combo = 0
                self._reset_multiplier()
                self._record_miss()
                x = self._lane_center_x(note["lane"])
                self.add_feedback("Miss", COLOR_FEEDBACK_MISS, x, HIT_LINE_Y - 40, big=False)
                
    def _render_visualizer(self):
        """Renders the real-time, FFT-based Spectrum Bar Visualizer."""
        eq_area_height = 220
        padding = 14
        
        eq_area_rect = pygame.Rect(MAIN_WIDTH, WINDOW_HEIGHT - eq_area_height, SIDEBAR_WIDTH, eq_area_height)
        pygame.draw.rect(self.screen, COLOR_SIDEBAR_HEADER_BG, eq_area_rect)
        pygame.draw.rect(self.screen, COLOR_SIDEBAR_BORDER, eq_area_rect, 2)
        
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
            
            

            color = EQ_BAR
            
            pygame.draw.rect(self.screen, color, (x, y, bar_w, h), border_radius=0)
        
        pygame.draw.line(self.screen, COLOR_DIVIDER_LINE, (MAIN_WIDTH + padding, base_y), (WINDOW_WIDTH - padding, base_y), 1)

    def _render_countdown(self):
        """Render the countdown overlay (3, 2, 1, GO) with semi-transparent background."""
        countdown_elapsed = (pygame.time.get_ticks() - self.countdown_start_time) / 1000.0
        
        # Determine countdown text
        if countdown_elapsed < 1.0:
            text = "3"
            color = COLOR_THREE  # Red
        elif countdown_elapsed < 2.0:
            text = "2"
            color = COLOR_TWO  # Orange
        elif countdown_elapsed < 3.0:
            text = "1"
            color = COLOR_ONE  # Green
        elif countdown_elapsed < 3.5:
            text = "GO!"
            color = COLOR_GO  # Cyan
        else:
            return  # Countdown finished
        
        # Draw semi-transparent overlay across entire screen
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(180)  # Semi-transparent
        overlay.fill(COLOR_COUNTDOWN_OVERLAY)  # Dark gray
        self.screen.blit(overlay, (0, 0))
        
        # Draw countdown text in center
        center_x = WINDOW_WIDTH / 2
        center_y = WINDOW_HEIGHT / 2
        
        self._queue_text(
            self._text_overlays,
            self.countdown_font,
            text,
            color,
            center_x,
            center_y - 60,  # Offset for visual centering
            center=True,
            font_size=self.countdown_font_size
        )

    def _render_pause(self):
        """Render the pause overlay with semi-transparent background."""
        # Draw semi-transparent overlay across entire screen
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(200)  # More opaque than countdown
        overlay.fill(COLOR_PAUSE_OVERLAY)
        self.screen.blit(overlay, (0, 0))
        
        # Draw pause text in center
        center_x = WINDOW_WIDTH / 2
        center_y = WINDOW_HEIGHT / 2
        
        # Title: "Paused"
        self._queue_text(
            self._text_overlays,
            self.pause_title_font,
            "Paused",
            COLOR_END_SCORE,
            center_x,
            center_y - 120,
            center=True,
            font_size=self.pause_title_font_size
        )
        
        # Buttons
        button_width = 250
        button_height = 70
        button_spacing = 30
        
        # Get mouse position for hover effects
        mouse_pos = pygame.mouse.get_pos()
        scale, offset_x, offset_y = self._get_scale_and_offset()
        logical_mouse_x = (mouse_pos[0] - offset_x) / scale
        logical_mouse_y = (mouse_pos[1] - offset_y) / scale
        
        # Resume button
        resume_y = center_y - 20
        resume_rect = pygame.Rect(center_x - button_width / 2, resume_y, button_width, button_height)
        resume_hover = resume_rect.collidepoint(logical_mouse_x, logical_mouse_y)
        resume_color = COLOR_BUTTON_GREEN_HOVER if resume_hover else COLOR_BUTTON_GREEN_NORMAL
        resume_text_color = COLOR_TEXT_WHITE if resume_hover else COLOR_TEXT_DARK_GRAY
        
        pygame.draw.rect(self.screen, resume_color, resume_rect, border_radius=12)
        pygame.draw.rect(self.screen, COLOR_BUTTON_GREEN_BORDER, resume_rect, 3, border_radius=12)
        
        self._queue_text(
            self._text_overlays,
            self.pause_hint_font,
            "Resume (ESC)",
            resume_text_color,
            center_x,
            resume_y + button_height / 2 - 14,
            center=True,
            font_size=self.pause_hint_font_size
        )
        
        # Menu button
        menu_y = center_y + 70
        menu_rect = pygame.Rect(center_x - button_width / 2, menu_y, button_width, button_height)
        menu_hover = menu_rect.collidepoint(logical_mouse_x, logical_mouse_y)
        menu_color = COLOR_BUTTON_RED_HOVER if menu_hover else COLOR_BUTTON_RED_NORMAL
        menu_text_color = COLOR_TEXT_WHITE if menu_hover else COLOR_TEXT_DARK_GRAY
        
        pygame.draw.rect(self.screen, menu_color, menu_rect, border_radius=12)
        pygame.draw.rect(self.screen, COLOR_BUTTON_RED_BORDER, menu_rect, 3, border_radius=12)
        
        self._queue_text(
            self._text_overlays,
            self.pause_hint_font,
            "Main Menu (M)",
            menu_text_color,
            center_x,
            menu_y + button_height / 2 - 14,
            center=True,
            font_size=self.pause_hint_font_size
        )

    def _get_scale_and_offset(self):
        """Calculate the current scale and offset for the display."""
        display_w, display_h = self.display_size
        scale_to_height = display_h / WINDOW_HEIGHT
        scaled_w = int(round(WINDOW_WIDTH * scale_to_height))
        
        use_height_scaling = scaled_w <= display_w and scale_to_height > 0
        
        if not use_height_scaling:
            scale = display_w / WINDOW_WIDTH
            scaled_w = display_w
            scaled_h = int(round(WINDOW_HEIGHT * scale))
        else:
            scale = scale_to_height
            scaled_h = display_h
        
        offset_x = (display_w - scaled_w) // 2
        offset_y = (display_h - scaled_h) // 2
        
        return scale, offset_x, offset_y

    def _check_button_click(self, x, y):
        """Check if a click is on any end screen button."""
        # Calculate button positions (same as in _render_end_screen)
        center_x = WINDOW_WIDTH / 2
        center_y = WINDOW_HEIGHT / 2
        
        button_width = 200
        button_height = 60
        button_spacing = 40
        
        # Retry button
        retry_x = center_x - button_width - button_spacing / 2
        retry_y = center_y + 120
        retry_rect = pygame.Rect(retry_x, retry_y, button_width, button_height)
        
        # Main Menu button
        menu_x = center_x + button_spacing / 2
        menu_y = center_y + 120
        menu_rect = pygame.Rect(menu_x, menu_y, button_width, button_height)
        
        if retry_rect.collidepoint(x, y):
            return "retry"
        elif menu_rect.collidepoint(x, y):
            return "menu"
        return None
    
    def _check_pause_button_click(self, logical_x, logical_y):
        """Check if any button is clicked on the pause screen and return the action."""
        center_x = WINDOW_WIDTH / 2
        center_y = WINDOW_HEIGHT / 2
        button_width = 250
        button_height = 70
        
        # Resume button
        resume_y = center_y - 20
        resume_rect = pygame.Rect(center_x - button_width / 2, resume_y, button_width, button_height)
        
        # Menu button
        menu_y = center_y + 70
        menu_rect = pygame.Rect(center_x - button_width / 2, menu_y, button_width, button_height)
        
        if resume_rect.collidepoint(logical_x, logical_y):
            return "resume"
        elif menu_rect.collidepoint(logical_x, logical_y):
            return "menu"
        
        return None

    def _render_end_screen(self):
        """Render the end game screen with stats and buttons."""
        # Draw semi-transparent overlay across entire screen
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.set_alpha(220)  # Very opaque
        overlay.fill(COLOR_END_OVERLAY)
        self.screen.blit(overlay, (0, 0))
        
        center_x = WINDOW_WIDTH / 2
        center_y = WINDOW_HEIGHT / 2
        
        # Title: "Song Complete!"
        self._queue_text(
            self._text_overlays,
            self.end_title_font,
            "Song Complete!",
            COLOR_TITLE_BRIGHT_CYAN,
            center_x,
            center_y - 200,
            center=True,
            font_size=self.end_title_font_size
        )
        
        # Stats
        # Final Score
        self._queue_text(
            self._text_overlays,
            self.end_stats_font,
            f"Final Score: {self.score}",
            COLOR_END_SCORE,
            center_x,
            center_y - 100,
            center=True,
            font_size=self.end_stats_font_size
        )
        
        # Max Combo
        self._queue_text(
            self._text_overlays,
            self.end_stats_font,
            f"Max Combo: {self.max_combo}",
            COLOR_END_CONGRATS,
            center_x,
            center_y - 40,
            center=True,
            font_size=self.end_stats_font_size
        )
        
        # Accuracy
        if self.missed_notes == 0:
            accuracy_text = "Accuracy: 100%"
            accuracy_color = COLOR_ACCURACY_PERFECT
        else:
            accuracy_text = f"Accuracy: {self.accuracy:.1f}%"
            if self.accuracy >= 90:
                accuracy_color = COLOR_ACCURACY_GREAT
            elif self.accuracy >= 75:
                accuracy_color = COLOR_ACCURACY_GOOD
            else:
                accuracy_color = COLOR_ACCURACY_POOR
        
        self._queue_text(
            self._text_overlays,
            self.end_stats_font,
            accuracy_text,
            accuracy_color,
            center_x,
            center_y + 20,
            center=True,
            font_size=self.end_stats_font_size
        )
        
        # Buttons
        button_width = 200
        button_height = 60
        button_spacing = 40
        
        # Retry button
        retry_x = center_x - button_width - button_spacing / 2
        retry_y = center_y + 120
        retry_rect = pygame.Rect(retry_x, retry_y, button_width, button_height)
        
        # Check if mouse is hovering over retry button
        mouse_pos = pygame.mouse.get_pos()
        scale, offset_x, offset_y = self._get_scale_and_offset()
        logical_mouse_x = (mouse_pos[0] - offset_x) / scale
        logical_mouse_y = (mouse_pos[1] - offset_y) / scale
        
        retry_hover = retry_rect.collidepoint(logical_mouse_x, logical_mouse_y)
        retry_color = COLOR_BUTTON_GREEN_HOVER if retry_hover else COLOR_BUTTON_GREEN_NORMAL
        retry_text_color = COLOR_TEXT_WHITE if retry_hover else COLOR_TEXT_DARK_GRAY
        
        pygame.draw.rect(self.screen, retry_color, retry_rect, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_BUTTON_GREEN_BORDER, retry_rect, 3, border_radius=10)
        
        self._queue_text(
            self._text_overlays,
            self.end_button_font,
            "Retry (R)",
            retry_text_color,
            retry_x + button_width / 2,
            retry_y + button_height / 2 - 16,
            center=True,
            font_size=self.end_button_font_size
        )
        
        # Main Menu button
        menu_x = center_x + button_spacing / 2
        menu_y = center_y + 120
        menu_rect = pygame.Rect(menu_x, menu_y, button_width, button_height)
        
        menu_hover = menu_rect.collidepoint(logical_mouse_x, logical_mouse_y)
        menu_color = COLOR_BUTTON_RED_HOVER if menu_hover else COLOR_BUTTON_RED_NORMAL
        menu_text_color = COLOR_TEXT_WHITE if menu_hover else COLOR_TEXT_DARK_GRAY
        
        pygame.draw.rect(self.screen, menu_color, menu_rect, border_radius=10)
        pygame.draw.rect(self.screen, COLOR_BUTTON_RED_BORDER, menu_rect, 3, border_radius=10)
        
        self._queue_text(
            self._text_overlays,
            self.end_button_font,
            "Main Menu (Q)",
            menu_text_color,
            menu_x + button_width / 2,
            menu_y + button_height / 2 - 16,
            center=True,
            font_size=self.end_button_font_size
        )

    def render(self, current_time):
        self._text_overlays = []
        
        # Increment frame counter for animations (only when not paused)
        if not self.paused:
            self.frame_count += 1
        
        # Main background (playfield only)
        self.screen.blit(self.background, (0, 0))

        # Only render game elements if not on end screen
        if not self.game_ended:
            # Lanes in playfield
            for i in range(LANE_COUNT):
                pygame.draw.rect(
                    self.screen,
                    COLOR_LANE_LABEL,
                    (i * LANE_WIDTH, PLAY_TOP, LANE_WIDTH, PLAY_BOTTOM - PLAY_TOP),
                    2
                )

            # Hit line (where notes should be hit)
            pygame.draw.line(self.screen, COLOR_HIT_LINE, (0, HIT_LINE_Y), (MAIN_WIDTH, HIT_LINE_Y), 2)

            # Ripple effects traveling up and down lanes
            for ripple in self.ripples[:]:
                # Calculate fade based on distance traveled
                progress = ripple["offset"] / ripple["max_offset"]
                alpha = int(60 * (1.0 - progress))  # Faint ripple, max alpha 60
                
                if alpha <= 0:
                    self.ripples.remove(ripple)
                    continue
                
                # Calculate positions for upward and downward ripples
                y_up = ripple["origin_y"] - ripple["offset"]
                y_down = ripple["origin_y"] + ripple["offset"]
                
                # Lane boundaries
                lane_x = ripple["lane"] * LANE_WIDTH
                lane_center_x = lane_x + LANE_WIDTH // 2
                
                # Ripple thickness decreases as it travels
                thickness = max(2, int(8 * (1.0 - progress)))
                
                # Draw upward ripple (if in bounds)
                if y_up >= PLAY_TOP:
                    ripple_surface_up = pygame.Surface((LANE_WIDTH, thickness), pygame.SRCALPHA)
                    ripple_color = (*COLOR_RIPPLE, alpha)
                    pygame.draw.rect(ripple_surface_up, ripple_color, (0, 0, LANE_WIDTH, thickness))
                    self.screen.blit(ripple_surface_up, (lane_x, y_up))
                
                # Draw downward ripple (if in bounds)
                if y_down <= PLAY_BOTTOM:
                    ripple_surface_down = pygame.Surface((LANE_WIDTH, thickness), pygame.SRCALPHA)
                    ripple_color = (*COLOR_RIPPLE, alpha)
                    pygame.draw.rect(ripple_surface_down, ripple_color, (0, 0, LANE_WIDTH, thickness))
                    self.screen.blit(ripple_surface_down, (lane_x, y_down))
                
                # Update ripple position
                ripple["offset"] += ripple["speed"]
                if ripple["offset"] >= ripple["max_offset"]:
                    self.ripples.remove(ripple)

            # Notes
            min_note_y = NOTE_ENTRY_MIN_Y
            max_note_y = PLAY_BOTTOM + NOTE_HEIGHT
            for note in list(self.notes):
                time_until_hit = note["time"] - current_time
                y = HIT_LINE_Y - time_until_hit * NOTE_SPEED

                if y < min_note_y or y > max_note_y:
                    continue

                t = 0.0
                if HIT_LINE_Y > PLAY_TOP:
                    t = max(0.0, min(1.0, (y - PLAY_TOP) / (HIT_LINE_Y - PLAY_TOP)))
                intensity = int(130 + t * (255 - 130))
                color = (0, intensity, 255)

                pygame.draw.rect(self.screen, color, self._note_rect(note["lane"], y), border_radius=5)

            # Hit notes with pulse animation
            for hit_note in self.hit_notes[:]:
                # Calculate pulse scale (expands outward)
                progress = hit_note["pulse_frame"] / hit_note["max_frames"]
                pulse_scale = 1.0 + (progress * 0.5)  # Grows by 50%
                
                # Calculate alpha (fades out as it expands)
                alpha = int(255 * (1.0 - progress))
                
                # Calculate expanded dimensions
                base_width = NOTE_WIDTH
                base_height = NOTE_HEIGHT
                pulse_width = int(base_width * pulse_scale)
                pulse_height = int(base_height * pulse_scale)
                
                # Center the expanded note at the same position
                x_offset = (pulse_width - base_width) // 2
                y_offset = (pulse_height - base_height) // 2
                
                base_x = hit_note["lane"] * LANE_WIDTH + (LANE_WIDTH - NOTE_WIDTH) // 2
                pulse_x = base_x - x_offset
                pulse_y = hit_note["y"] - y_offset
                
                # Draw pulsing note with fade
                pulse_surface = pygame.Surface((pulse_width, pulse_height), pygame.SRCALPHA)
                color_with_alpha = (*COLOR_HIT_NOTE_PULSE, alpha)
                pygame.draw.rect(pulse_surface, color_with_alpha, (0, 0, pulse_width, pulse_height), border_radius=5)
                self.screen.blit(pulse_surface, (pulse_x, pulse_y))
                
                # Update animation
                hit_note["pulse_frame"] += 1
                if hit_note["pulse_frame"] >= hit_note["max_frames"]:
                    self.hit_notes.remove(hit_note)

            # Floating feedback labels
            for fb in self.feedbacks[:]:
                font = self.feedback_font_large if fb["big"] else self.feedback_font_small
                self._queue_text(
                    self._text_overlays,
                    font,
                    fb["text"],
                    fb["color"],
                    fb["x"],
                    fb["y"],
                    center=True,
                    alpha=max(0, fb["alpha"]),
                    font_size=self.feedback_font_large_size if fb["big"] else self.feedback_font_small_size
                )
                fb["y"] -= fb["rise"]       
                fb["alpha"] -= 7            
                fb["life"] -= 1
                if fb["life"] <= 0 or fb["alpha"] <= 0:
                    self.feedbacks.remove(fb)

            # Footer: Progress box beneath everything (playfield)
            footer_rect = pygame.Rect(0, WINDOW_HEIGHT - FOOTER_HEIGHT, MAIN_WIDTH, FOOTER_HEIGHT)
            pygame.draw.rect(self.screen, COLOR_FOOTER_BG, footer_rect)
            pygame.draw.rect(self.screen, COLOR_FOOTER_BORDER, footer_rect, 2)

            self._queue_text(
                self._text_overlays,
                self.label_font,
                "Progress",
                COLOR_FOOTER_TEXT,
                12,
                WINDOW_HEIGHT - FOOTER_HEIGHT + 10,
                font_size=self.label_font_size
            )

            # Progress bar inside footer
            song_len = self.song.get_length() if self.song else 0
            progress = 0.0 if song_len <= 0 else min(current_time / song_len, 1.0)
            bar_x = 12
            bar_y = WINDOW_HEIGHT - FOOTER_HEIGHT + 36
            bar_w = MAIN_WIDTH - 24
            bar_h = 18
            pygame.draw.rect(self.screen, COLOR_PROGRESS_BG, (bar_x, bar_y, bar_w, bar_h), border_radius=6)
            pygame.draw.rect(self.screen, COLOR_PROGRESS_FILL, (bar_x, bar_y, int(bar_w * progress), bar_h), border_radius=6)

            # Sidebar
            sidebar_rect = pygame.Rect(MAIN_WIDTH, 0, SIDEBAR_WIDTH, WINDOW_HEIGHT)
            pygame.draw.rect(self.screen, COLOR_SIDEBAR_BG, sidebar_rect)

            video_width, video_height = self.video_panel_size
            video_rect = pygame.Rect(
                MAIN_WIDTH + VIDEO_PANEL_MARGIN,
                20,
                video_width,
                video_height
            )
            pygame.draw.rect(self.screen, COLOR_SIDEBAR_HEADER_BG, video_rect)
            pygame.draw.rect(self.screen, VIDEO_PANEL_BORDER, video_rect, 2)

            if self.video_panel:
                self.video_panel.draw(self.screen, video_rect)
                if not self.video_panel.has_frame:
                    self._queue_text(
                        self._text_overlays,
                        self.ui_font,
                        "Loading video...",
                        VIDEO_PANEL_TEXT,
                        video_rect.centerx,
                        video_rect.centery - 16,
                        center=True,
                        font_size=self.ui_font_size
                    )
            else:
                pygame.draw.rect(self.screen, VIDEO_PANEL_BG, video_rect)
                placeholder = self.video_panel_status or "Video unavailable"
                lines = placeholder.split("\n")
                for idx, line in enumerate(lines):
                    self._queue_text(
                        self._text_overlays,
                        self.ui_font,
                        line,
                        VIDEO_PANEL_TEXT,
                        video_rect.centerx,
                        video_rect.y + 20 + idx * 32,
                        center=True,
                        font_size=self.ui_font_size
                    )

            stats_top = video_rect.bottom + 20
            stats_rect = pygame.Rect(MAIN_WIDTH + 8, stats_top, SIDEBAR_WIDTH - 16, 230)
            pygame.draw.rect(self.screen, COLOR_SIDEBAR_HEADER_BG, stats_rect)
            pygame.draw.rect(self.screen, COLOR_SIDEBAR_BORDER, stats_rect, 2)

            text_x = stats_rect.x + 12
            score_y = stats_top + 16
            combo_y = score_y + 44
            multiplier_y = combo_y + 44
            accuracy_y = multiplier_y + 44

            self._queue_text(
                self._text_overlays,
                self.ui_font,
                f"Score: {self.score}",
                COLOR_SIDEBAR_TEXT,
                text_x,
                score_y,
                font_size=self.ui_font_size
            )
            self._queue_text(
                self._text_overlays,
                self.ui_font,
                f"Combo: {self.combo}",
                COLOR_SIDEBAR_TEXT,
                text_x,
                combo_y,
                font_size=self.ui_font_size
            )

            if self.multiplier > 1:
                pulse_speed = 0.1 + (self.multiplier - 1) * 0.02
                pulse_wave = math.sin(self.frame_count * pulse_speed)
                size_boost = 1.0 + (self.multiplier - 1) * 0.35
                pulse_amplitude = 0.1 + (self.multiplier - 1) * 0.05
                size_multiplier = size_boost + (pulse_wave * pulse_amplitude)
                multiplier_font_size = int(self.ui_font_size * size_multiplier)
                base_multiplier_r = COLOR_MULTIPLIER_ACTIVE[0]
                color_intensity = base_multiplier_r + int(pulse_wave * 30)
                color_intensity = max(0, min(255, color_intensity))
                multiplier_color = (
                    color_intensity,
                    COLOR_MULTIPLIER_ACTIVE[1],
                    COLOR_MULTIPLIER_ACTIVE[2]
                )
            else:
                multiplier_font_size = self.ui_font_size
                multiplier_color = COLOR_MULTIPLIER_ACTIVE

            multiplier_font = pygame.font.Font(None, multiplier_font_size)

            self._queue_text(
                self._text_overlays,
                multiplier_font,
                f"x{self.multiplier}",
                multiplier_color,
                text_x,
                multiplier_y,
                font_size=multiplier_font_size
            )

            if self.missed_notes == 0:
                accuracy_label = "Accuracy: 100%"
            else:
                accuracy_label = f"Accuracy: {self.accuracy:.1f}%"

            self._queue_text(
                self._text_overlays,
                self.ui_font,
                accuracy_label,
                COLOR_SIDEBAR_LABEL,
                text_x,
                accuracy_y,
                font_size=self.ui_font_size
            )
            # Sidebar: Visualizer (Live Spectrum Bars)
            self._render_visualizer()

        # Header bar with logo drawn after notes so it always sits on top
        pygame.draw.rect(self.screen, COLOR_HEADER_BG, (0, 0, MAIN_WIDTH, HEADER_HEIGHT))
        pygame.draw.line(self.screen, COLOR_HEADER_BORDER, (0, HEADER_HEIGHT - 1), (MAIN_WIDTH, HEADER_HEIGHT - 1), 1)
        center_x = MAIN_WIDTH / 2
        self._queue_text(
            self._text_overlays,
            self.logo_font,
            "RhythmGen",
            COLOR_TITLE_CYAN,
            center_x + 2,
            12,
            center=True,
            font_size=self.logo_font_size
        )
        self._queue_text(
            self._text_overlays,
            self.logo_font,
            "RhythmGen",
            COLOR_TITLE_MAGENTA,
            center_x,
            10,
            center=True,
            font_size=self.logo_font_size
        )

        # Render countdown overlay if active
        if self.countdown_active:
            self._render_countdown()
        
        # Render pause overlay if paused
        if self.paused:
            self._render_pause()
        
        # Render end screen if game ended
        if self.game_ended:
            self._play_end_sfx()
            self._render_end_screen()

        scale, offset_x, offset_y = self._present_canvas()
        self._draw_text_overlays(scale, offset_x, offset_y)

    def _present_canvas(self):
        display_w, display_h = self.display_size
        scale_to_height = display_h / WINDOW_HEIGHT
        scaled_w = int(round(WINDOW_WIDTH * scale_to_height))
        scaled_h = display_h

        use_height_scaling = scaled_w <= display_w and scale_to_height > 0

        if not use_height_scaling:
            scale_to_width = display_w / WINDOW_WIDTH
            scaled_w = display_w
            scaled_h = int(round(WINDOW_HEIGHT * scale_to_width))
            scale = scale_to_width
        else:
            scale = scale_to_height

        integer_multiple = math.isclose(scale, round(scale)) and scale >= 1
        integer_multiple = integer_multiple or (
            scaled_w % WINDOW_WIDTH == 0 and scaled_h % WINDOW_HEIGHT == 0
        )

        if scaled_w == WINDOW_WIDTH and scaled_h == WINDOW_HEIGHT:
            canvas = self.screen
        elif integer_multiple:
            canvas = pygame.transform.scale(self.screen, (scaled_w, scaled_h))
        else:
            canvas = pygame.transform.smoothscale(self.screen, (scaled_w, scaled_h))

        offset_x = (display_w - scaled_w) // 2
        offset_y = (display_h - scaled_h) // 2

        self.display_surface.fill(COLOR_BLACK)
        self.display_surface.blit(canvas, (offset_x, offset_y))

        scale_factor = scaled_w / WINDOW_WIDTH if WINDOW_WIDTH else 1.0
        return scale_factor, offset_x, offset_y

    def _queue_text(self, overlay_list, font, text, color, x, y, *, center=False, alpha=255, font_size=None, font_path=None):
        overlay_list.append({
            "font": font,
            "text": text,
            "color": color,
            "x": x,
            "y": y,
            "center": center,
            "alpha": alpha,
            "font_size": font_size,
            "font_path": font_path
        })

    def _draw_text_overlays(self, scale, offset_x, offset_y):
        if not hasattr(self, "_text_overlays"):
            return
        for entry in self._text_overlays:
            font = entry["font"]
            text = entry["text"]
            color = entry["color"]
            alpha = entry["alpha"]
            font_size = entry.get("font_size")
            font_path = entry.get("font_path")

            effective_font = font
            if scale != 1.0 and font_size:
                scaled_size = max(1, int(round(font_size * scale)))
                effective_font = pygame.font.Font(font_path, scaled_size)

            surf = effective_font.render(text, True, color)
            if alpha < 255:
                surf = surf.copy()
                surf.set_alpha(alpha)

            draw_x = offset_x + entry["x"] * scale
            draw_y = offset_y + entry["y"] * scale

            if entry["center"]:
                draw_x -= surf.get_width() / 2
            draw_pos = (int(round(draw_x)), int(round(draw_y)))
            self.display_surface.blit(surf, draw_pos)

        pygame.display.flip()